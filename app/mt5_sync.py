# -*- coding: utf-8 -*-
"""MT5 Sync - sincronizacao perfeita do terminal com o XAU_AI_PRO.

Consolida em um unico ponto: saldo/equity/margem, posicoes abertas,
historico de deals, journal do terminal (via arquivo de eventos) e o
dashboard. Tudo devolvido em JSON pronto para GUI, dashboard web e chat IA.
"""
from __future__ import annotations

import json
import sqlite3
import csv
from datetime import datetime
from pathlib import Path
from typing import Any

_APP_ROOT = Path(__file__).resolve().parent.parent
_DB = _APP_ROOT / "database" / "trading.db"
_JOURNAL_HINT = Path(_APP_ROOT).parent.parent.parent / "MQL5" / "Files" / "Data" / "forward_test_events.csv"


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB), check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def _ensure_tables() -> None:
    c = _conn()
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS account (
          id INTEGER PRIMARY KEY, login INTEGER, balance REAL, equity REAL,
          margin REAL, free_margin REAL, currency TEXT, server TEXT, ts TEXT
        );
        CREATE TABLE IF NOT EXISTS sync_positions (
          ticket INTEGER PRIMARY KEY, symbol TEXT, side TEXT, volume REAL,
          open_price REAL, sl REAL, tp REAL, profit REAL, ts TEXT
        );
        CREATE TABLE IF NOT EXISTS sync_deals (
          ticket INTEGER PRIMARY KEY, symbol TEXT, side TEXT, volume REAL,
          price REAL, profit REAL, fee REAL, ts TEXT
        );
        CREATE TABLE IF NOT EXISTS journal_lines (
          id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, source TEXT, text TEXT
        );
        """)
        # migracao: adiciona colunas que possam estar faltando em versoes antigas
        existing = {r[1] for r in c.execute("PRAGMA table_info(account)").fetchall()}
        for col, typ in (("login","INTEGER"),("free_margin","REAL"),("currency","TEXT"),("server","TEXT"),("ts","TEXT")):
            if col not in existing:
                c.execute(f"ALTER TABLE account ADD COLUMN {col} {typ}")
        c.commit()
    finally:
        c.close()


def _http_get(path: str) -> dict[str, Any] | None:
    """Consulta o MT5 Gateway local (127.0.0.1:9001). Retorna dict ou None."""
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(f"http://127.0.0.1:9001{path}",
                                     headers={"User-Agent": "XAU_AI_PRO/1.3.2"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def _read_csv_rows(path: Path, limit: int) -> list[dict[str, str]]:
    encodings = ("utf-16", "utf-8-sig", "utf-8", "latin-1")
    for enc in encodings:
        try:
            with open(path, encoding=enc, newline="") as fh:
                rows = list(csv.DictReader(fh))
            return rows[-limit:]
        except Exception:
            continue
    return []


def _snapshot_account() -> dict[str, Any]:
    # 1) Tenta o Gateway local (ja esta rodando, sem precisar de conexao extra)
    gw = _http_get("/api/account")
    if gw:
        # aceita ambos os formatos: {"account": {...}} ou {"login":...} direto
        a = gw.get("account") or gw
        if a.get("login") or a.get("balance"):
            return {
                "login": a.get("login"), "balance": a.get("balance"),
                "equity": a.get("equity"), "margin": a.get("margin"),
                "free_margin": a.get("margin_free") or a.get("free_margin"),
                "currency": a.get("currency"), "server": a.get("server") or "MT5",
            }
    # 2) Fallback: MT5Robot (conexao direta)
    try:
        from app.mt5_robot import get_robot
        robot = get_robot()
        info = robot.account_info() if robot else None
        if info:
            return {
                "login": info.get("login"), "balance": info.get("balance"),
                "equity": info.get("equity"), "margin": info.get("margin"),
                "free_margin": info.get("margin_free"), "currency": info.get("currency"),
                "server": info.get("server"),
            }
    except Exception:
        pass
    return {}


def _snapshot_positions() -> list[dict[str, Any]]:
    # 1) Gateway
    gw = _http_get("/api/positions")
    if gw and gw.get("positions") is not None:
        return [p if isinstance(p, dict) else dict(p) for p in gw["positions"]]
    # 2) Fallback MT5Robot
    try:
        from app.mt5_robot import get_robot
        robot = get_robot()
        if robot:
            return [p.to_dict() if hasattr(p, "to_dict") else dict(p)
                    for p in robot.get_positions()]
    except Exception:
        pass
    return []


def _snapshot_history(days: int = 30) -> list[dict[str, Any]]:
    # 1) Gateway
    gw = _http_get("/api/history")
    if gw is not None:
        return [gw] if isinstance(gw, dict) else list(gw)
    # 2) Fallback MT5Robot
    try:
        from app.mt5_robot import get_robot
        robot = get_robot()
        if robot:
            return [d.to_dict() if hasattr(d, "to_dict") else dict(d)
                    for d in robot.get_history(days=days)]
    except Exception:
        pass
    return []


def sync_account() -> dict[str, Any]:
    """Sincroniza saldo/equity/margem da conta para o DB."""
    _ensure_tables()
    acc = _snapshot_account()
    if not acc:
        return {"ok": False, "error": "MT5 nao conectado", "account": {}}
    c = _conn()
    try:
        c.execute("""
        INSERT INTO account (id, login, balance, equity, margin, free_margin, currency, server, ts)
        VALUES (1, ?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
          balance=excluded.balance, equity=excluded.equity, margin=excluded.margin,
          free_margin=excluded.free_margin, currency=excluded.currency,
          server=excluded.server, ts=excluded.ts
        """, (acc.get("login"), acc.get("balance"), acc.get("equity"),
              acc.get("margin"), acc.get("free_margin"), acc.get("currency"),
              acc.get("server"), datetime.utcnow().isoformat(timespec="seconds")))
        c.commit()
        return {"ok": True, "account": acc}
    finally:
        c.close()


def sync_positions() -> dict[str, Any]:
    """Sincroniza posicoes abertas."""
    _ensure_tables()
    pos = _snapshot_positions()
    c = _conn()
    try:
        c.execute("DELETE FROM sync_positions")
        ts = datetime.utcnow().isoformat(timespec="seconds")
        for p in pos:
            c.execute("""
            INSERT OR REPLACE INTO sync_positions
              (ticket, symbol, side, volume, open_price, sl, tp, profit, ts)
            VALUES (?,?,?,?,?,?,?,?,?)
            """, (p.get("ticket"), p.get("symbol"), p.get("type_str") or p.get("side"),
                  p.get("volume"), p.get("price_open"), p.get("sl"), p.get("tp"),
                  p.get("profit"), ts))
        c.commit()
        return {"ok": True, "count": len(pos), "positions": pos}
    finally:
        c.close()


def sync_history(days: int = 30) -> dict[str, Any]:
    """Sincroniza historico de deals dos ultimos N dias."""
    _ensure_tables()
    deals = _snapshot_history(days)
    c = _conn()
    try:
        c.execute("DELETE FROM sync_deals")
        ts = datetime.utcnow().isoformat(timespec="seconds")
        for d in deals:
            c.execute("""
            INSERT OR REPLACE INTO sync_deals
              (ticket, symbol, side, volume, price, profit, fee, ts)
            VALUES (?,?,?,?,?,?,?,?)
            """, (d.get("ticket"), d.get("symbol"), d.get("type_str") or d.get("side"),
                  d.get("volume"), d.get("price"), d.get("profit"), d.get("fee"), ts))
        c.commit()
        return {"ok": True, "count": len(deals), "deals": deals}
    finally:
        c.close()


def sync_journal(limit: int = 60) -> dict[str, Any]:
    """Le o journal/eventos do terminal (forward_test_events.csv) e grava no DB."""
    _ensure_tables()
    lines: list[dict[str, Any]] = []
    if _JOURNAL_HINT.exists():
        try:
            for row in _read_csv_rows(_JOURNAL_HINT, limit):
                ts = (row.get("Time") or row.get("time") or "").replace("\x00", "").strip()
                event = (row.get("Event") or row.get("event") or "").replace("\x00", "").strip()
                symbol = (row.get("Symbol") or row.get("symbol") or "").replace("\x00", "").strip()
                module = (row.get("Module") or row.get("module") or "").replace("\x00", "").strip()
                message = (row.get("Message") or row.get("message") or "").replace("\x00", "").strip()
                status = (row.get("Status") or row.get("status") or "").replace("\x00", "").strip()
                text = " | ".join(part for part in (event, symbol, module, message, status) if part)
                if ("." in ts and ":" in ts) or text:
                    lines.append({"ts": ts, "text": text[:300]})
        except Exception:
            pass
    c = _conn()
    try:
        ts = datetime.utcnow().isoformat(timespec="seconds")
        for ln in lines:
            c.execute("INSERT INTO journal_lines (ts, source, text) VALUES (?,?,?)",
                      (ln.get("ts") or ts, "csv", ln.get("text", "")))
        c.commit()
        return {"ok": True, "count": len(lines), "lines": lines}
    finally:
        c.close()


def to_export() -> dict[str, Any]:
    """Snapshot consolidado para GUI/dashboard/chat."""
    _ensure_tables()
    acc = _snapshot_account()
    pos = _snapshot_positions()
    hist = _snapshot_history(days=30)
    return {
        "ts": datetime.utcnow().isoformat(timespec="seconds"),
        "account": acc,
        "positions_count": len(pos),
        "positions": pos,
        "history_count": len(hist),
        "history": hist[:200],
        "conectado": bool(acc),
    }


def run_full_sync() -> dict[str, Any]:
    """Executa a sincronizacao completa (conta, posicoes, historico, journal)."""
    r_account = sync_account()
    r_pos = sync_positions()
    r_hist = sync_history(days=30)
    r_journal = sync_journal()
    return {
        "account": r_account,
        "positions": r_pos,
        "history": r_hist,
        "journal": r_journal,
        "ok": bool(r_account.get("ok") and r_pos.get("ok") and r_hist.get("ok") and r_journal.get("ok")),
    }


def journal_recent(limit: int = 40) -> list[dict[str, Any]]:
    """Ultimas linhas do journal gravadas no DB."""
    _ensure_tables()
    c = _conn()
    try:
        rows = c.execute("SELECT ts, source, text FROM journal_lines ORDER BY id DESC LIMIT ?",
                         (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        c.close()
