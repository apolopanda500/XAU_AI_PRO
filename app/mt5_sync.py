# -*- coding: utf-8 -*-
"""MT5 Sync - sincronizacao perfeita do terminal com o XAU_AI_PRO.

Consolida em um unico ponto: saldo/equity/margem, posicoes abertas,
historico de deals, journal do terminal (via arquivo de eventos) e o
dashboard. Tudo devolvido em JSON pronto para GUI, dashboard web e chat IA.
"""
from __future__ import annotations

import json
import sqlite3
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
        c.commit()
    finally:
        c.close()


def _snapshot_account() -> dict[str, Any]:
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
            for raw in _JOURNAL_HINT.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]:
                if not raw.strip():
                    continue
                parts = raw.split(",")
                lines.append({"ts": parts[0] if parts else "", "text": raw[:300]})
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
        "ok": bool(r_account.get("ok")) or True,  # conta pode estar offline
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