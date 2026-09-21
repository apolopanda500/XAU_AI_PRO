# -*- coding: utf-8 -*-
"""Watchdog do EA + telemetria (Fase 3 do gap analysis).

Classifica a saude do EA via heartbeat (arquivo comum com o MT5):
  - `alive`   : heartbeat recent (< ttl_sec)
  - `frozen`  : arquivo fresh no disco, mas timestamp estagnado (EA travado)
  - `stale`   : arquivo antigo (EA offline ha tempo)
  - `missing` : arquivo ausente (EA nunca rodou / terminal fechado)
  - `unknown` : formato/timestamp invalido

Telemetria in-memory (ring buffer 500) de eventos do sistema: reconciliacao
de intents, guardian (set/remove/parciais/BE/trailing), watchdog recovery e
erros. Endpoint consolidado /api/telemetry.

Seguranca: o watchdog e somente-leitura (nunca envia comandos ao MT5); a
recovery grava apenas eventos de telemetria. Decisao de acao fica no trader.
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

HEARTBEAT_FILE = Path(os.getenv("XAU_HEARTBEAT_FILE", str(
    Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal" / "Common" / "Files" / "XAU_AI_PRO_heartbeat.json")))
HEARTBEAT_TTL_SEC = float(os.getenv("XAU_HEARTBEAT_TTL", "120") or 120)
RING_MAX = 500
_RING: list[dict] = []
_LOCK = threading.Lock()
_WATCHDOG_CACHE: dict = {}


def _now() -> float:
    return datetime.now().timestamp()


def _classify_heartbeat(hb: dict, age_sec: float, file_age_sec: float) -> str:
    """Classifica o estado do EA a partir do heartbeat e das idades."""
    if hb.get("invalid"):
        return "unknown"
    hb_ts = hb.get("ts_epoch")
    hb_time = float(hb_ts) if isinstance(hb_ts, (int, float)) and hb_ts > 0 else 0.0
    now = _now()
    if hb_time <= 0:
        return "unknown"
    if now - hb_time <= HEARTBEAT_TTL_SEC:
        return "alive"
    if file_age_sec <= HEARTBEAT_TTL_SEC:
        return "frozen"   # arquivo fresh no disco, timestamp estagnado
    return "stale"


def ea_state() -> dict:
    """Estado de liveness do EA (somente leitura; nunca envia comandos)."""
    path = HEARTBEAT_FILE
    payload: dict = {}
    invalid = False
    hb_time = 0.0
    exists = path.exists()
    file_age = (time.time() - path.stat().st_mtime) if exists else -1.0
    if exists:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                invalid = True
        except Exception:
            invalid = True
        raw = str(payload.get("timestamp", ""))
        try:
            hb_time = datetime.strptime(raw, "%Y.%m.%d %H:%M:%S").replace(
                tzinfo=timezone.utc).timestamp()
        except (ValueError, TypeError):
            invalid = True
        else:
            invalid = False
    age = max(0.0, _now() - hb_time) if hb_time > 0 else -1.0
    state = _classify_heartbeat(
        {"invalid": invalid, "ts_epoch": hb_time}, age, file_age)
    result = {"ok": True, "state": state,
              "heartbeat_age_sec": round(age, 1) if age >= 0 else None,
              "file_age_sec": round(file_age, 1) if file_age >= 0 else None,
              "ttl_sec": HEARTBEAT_TTL_SEC, "file": str(path),
              "payload": payload, "source": "watchdog"}
    with _LOCK:
        _WATCHDOG_CACHE.update(result)
    return result


def last_ea_state() -> dict:
    """Ultimo estado conhecido (cache) sem re-ler o arquivo."""
    with _LOCK:
        return dict(_WATCHDOG_CACHE)


def record(event_kind: str, data: dict, severity: str = "info") -> None:
    """Grava um evento de telemetria no ring buffer (best-effort)."""
    item = {"ts": _now(), "ts_iso": datetime.now().isoformat(),
            "kind": event_kind, "severity": severity, "data": data}
    with _LOCK:
        _RING.append(item)
        del _RING[:-RING_MAX]


def telemetry(limit: int = 100) -> dict:
    """Snapshot da telemetria para o painel."""
    with _LOCK:
        rows = list(_RING[-max(1, min(int(limit), 500)):])
        kinds: dict[str, int] = {}
        sev: dict[str, int] = {}
        for item in _RING:
            k = str(item.get("kind", ""))
            s = str(item.get("severity", ""))
            kinds[k] = kinds.get(k, 0) + 1
            sev[s] = sev.get(s, 0) + 1
    return {"ok": True, "events": list(reversed(rows)), "count": len(rows),
            "total": len(_RING), "by_kind": kinds, "by_severity": sev,
            "ea": last_ea_state(), "source": "watchdog"}


def _telemetry_hook(kind: str, payload: dict, severity: str = "info") -> None:
    """Hook chamado pelo guardian/intents para espelhar eventos aqui."""
    record(kind, payload, severity)


def record_intent(event_kind: str, data: dict, severity: str = "info") -> None:
    """Espelho de eventos do intent log na telemetria."""
    record(event_kind, data, severity)


def recovery(
    # Monitora o EA e registra recovery em telemetria (somente-leitura).
    actions: list | None = None) -> dict:
    state_now = ea_state()
    state = str(state_now.get("state", "unknown"))
    severity = "info" if state == "alive" else ("warning" if state in {"frozen", "stale"} else "error")
    record("watchdog_recovery", {"state": state, "state_before": state_now}, severity)
    if state != "alive":
        # Sem acao automatica: decisao de restart/manual fica com o trader.
        pass
    return {"ok": True, "state": state, "severity": severity,
            "actions": actions or []}


# ---------------------------------------------------------------------------
# Telemetria historica persistida (JSONL; observabilidade temporal).
# ---------------------------------------------------------------------------
HISTORY_FILE = Path(os.getenv("XAU_TELEMETRY_FILE", str(
    Path(os.environ.get("APPDATA", "")) / "XAU_AI_PRO" / "telemetry_history.jsonl")))
HISTORY_MAX_BYTES = int(os.getenv("XAU_TELEMETRY_MAX_BYTES", str(2 * 1024 * 1024)) or 0)
_SNAP_LOCK = threading.Lock()
_LAST_SNAPSHOT: dict = {}


def snapshot_metrics(source: str = "loop") -> dict:
    """Um snapshot pontual de saude/conta; persiste em JSONL com rotacao simples.

    Falhas de MT5 sao toleradas: campos ficam None e o snapshot ainda registra
    o estado do EA/watchdog (util justamente quando o terminal caiu).
    """
    snapshot: dict = {"ts": _now(), "ts_iso": datetime.now().isoformat(),
                      "source": source}
    try:
        from backend import mt5_gateway as gw
        payload = gw._payload()
        account = payload.get("account") or {}
        snapshot.update({
            "terminal_connected": bool(payload.get("terminal_connected")),
            "equity": account.get("equity"),
            "balance": account.get("balance"),
            "margin_free": account.get("margin_free"),
            "positions": len(payload.get("positions", []) or []),
            "floating_profit": (payload.get("exposure") or {}).get("floating_profit"),
        })
    except Exception as exc:
        snapshot["terminal_connected"] = False
        snapshot["error"] = str(exc)[:200]
    try:
        snapshot["ea_state"] = ea_state().get("state")
    except Exception:
        snapshot["ea_state"] = "unknown"
    with _SNAP_LOCK:
        _LAST_SNAPSHOT.clear()
        _LAST_SNAPSHOT.update(snapshot)
        try:
            HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            if HISTORY_MAX_BYTES > 0 and HISTORY_FILE.exists() \
               and HISTORY_FILE.stat().st_size > HISTORY_MAX_BYTES:
                HISTORY_FILE.write_text("", encoding="utf-8")  # rotacao simples
            with HISTORY_FILE.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(snapshot, ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass
    return snapshot


def history(limit: int = 120) -> dict:
    """Ultimos snapshots persistidos (mais recentes primeiro)."""
    limit = max(1, min(int(limit), 1000))
    rows: list[dict] = []
    try:
        if HISTORY_FILE.exists():
            lines = HISTORY_FILE.read_text(encoding="utf-8").splitlines()
            for line in reversed(lines[-limit:]):
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        pass
    with _SNAP_LOCK:
        last = dict(_LAST_SNAPSHOT)
    return {"ok": True, "snapshots": rows, "count": len(rows),
            "file": str(HISTORY_FILE), "last": last or None, "source": "watchdog"}


def _history_loop(interval_sec: float) -> None:
    while True:
        try:
            snapshot_metrics("loop")
        except Exception:
            pass
        time.sleep(max(10.0, interval_sec))


def start_telemetry_loop() -> None:
    """Sobe o coletor periodico (idempotente; intervalo via XAU_TELEMETRY_INTERVAL)."""
    with _LOCK:
        if getattr(start_telemetry_loop, "_started", False):
            return
        start_telemetry_loop._started = True  # type: ignore[attr-defined]
    interval = float(os.getenv("XAU_TELEMETRY_INTERVAL", "60") or 60)
    threading.Thread(target=_history_loop, args=(interval,),
                     name="telemetry-history", daemon=True).start()