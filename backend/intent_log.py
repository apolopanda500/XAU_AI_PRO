# -*- coding: utf-8 -*-
"""Intent Log + Reconciliacao (Fase 2 do gap analysis).

Registro append-only (JSONL) de cada intencao que alteraria a conta:
  - {"event": "requested", ...}  antes do envio ao MT5
  - {"event": "result", ...}     resposta real do MT5
  - {"event": "reconciled", ...} boot encontrou a operacao na conta
  - {"event": "unknown", ...}    boot NAO encontrou a operacao

Nunca reescreve linhas: o status final de um intent e derivado dos eventos.
A reconciliacao compara intents pendentes com posicoes abertas e deals do dia
(magic 2026001), classificando como executada/desconhecida. Corrompidos sao
ignorados linha a linha (best-effort).

Arquivo: %APPDATA%\\XAU_AI_PRO\\intents.jsonl (env XAU_INTENT_FILE).
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

INTENT_FILE = Path(os.getenv("XAU_INTENT_FILE", str(
    Path(os.environ.get("APPDATA", "")) / "XAU_AI_PRO" / "intents.jsonl")))
DEMO_MAGIC = 2026001
_LOCK = threading.Lock()


def time_now() -> float:
    return datetime.now().timestamp()


def record_intent(kind: str, data: dict, intent_id: str | None = None,
                  status: str = "pending", extra: dict | None = None) -> str:
    """Anexa um evento ao log. Retorna o intent_id (novo ou herdado)."""
    intent_id = intent_id or uuid.uuid4().hex[:12]
    try:
        event = {"ts": time_now(), "ts_iso": datetime.now().isoformat(),
                 "intent_id": intent_id, "kind": kind, "status": status, "data": data}
        if extra:
            event["extra"] = extra
        with _LOCK:
            INTENT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with INTENT_FILE.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass  # auditoria nunca bloqueia operacao
    return intent_id


def _read_events() -> list[dict]:
    events: list[dict] = []
    try:
        if not INTENT_FILE.exists():
            return events
        with INTENT_FILE.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue  # linha corrompida e ignorada
                if isinstance(item, dict):
                    events.append(item)
    except Exception:
        pass
    return events


def pending_intents(max_age_sec: float = 0.0) -> list[dict]:
    """Intents 'requested' sem result/reconciled/unknown correspondente.

    max_age_sec > 0 filtra somente intents mais novos que o limite (para
    reconciliacao considerar apenas os recentes/relevantes).
    """
    requested: dict[str, dict] = {}
    closed: set[str] = set()
    for event in _read_events():
        intent_id = str(event.get("intent_id", ""))
        if not intent_id:
            continue
        status = str(event.get("status", ""))
        if status == "pending":
            requested.setdefault(intent_id, event)
        elif status in {"sent", "failed", "reconciled", "unknown"}:
            closed.add(intent_id)
    cutoff = time_now() - max_age_sec if max_age_sec > 0 else 0.0
    return [event for intent_id, event in requested.items()
            if intent_id not in closed and event.get("ts", 0.0) >= cutoff]


def reconcile(mt5, max_age_sec: float = 86400.0) -> dict:
    """Classifica intents pendentes comparando com a conta real do MT5.

    Criterio: posicao aberta OU deal do dia com magic 2026001 cujo horario
    seja >= (ts do intent - 60s) e simbolo compativel. Encontrou -> reconciled;
    intent antigo sem rastro -> unknown; recente sem rastro segue pendente.
    """
    pend = pending_intents(max_age_sec=max_age_sec)
    if not pend:
        return {"ok": True, "checked": 0, "reconciled": 0, "unknown": 0, "still_pending": 0}
    ref_time = datetime.now()
    open_positions: list = []
    day_deals: list = []
    try:
        open_positions = list(mt5.positions_get() or [])
    except Exception:
        open_positions = []
    try:
        day_deals = list(mt5.history_deals_get(
            ref_time.replace(hour=0, minute=0, second=0, microsecond=0), ref_time) or [])
    except Exception:
        day_deals = []
    checked = reconciled = unknown = still = 0
    for event in pend:
        checked += 1
        data = event.get("data") or {}
        symbol = str(data.get("symbol", "")).upper()
        ts = float(event.get("ts", 0.0) or 0.0)
        floor_ts = ts - 60.0
        found = ""
        try:
            for pos in open_positions:
                if int(getattr(pos, "magic", 0)) != DEMO_MAGIC:
                    continue
                if symbol and str(getattr(pos, "symbol", "")).upper() != symbol:
                    continue
                if float(getattr(pos, "time", 0.0) or 0.0) >= floor_ts:
                    found = f"position:{int(getattr(pos, 'ticket', 0))}"
                    break
            if not found:
                for deal in day_deals:
                    if int(getattr(deal, "magic", 0)) != DEMO_MAGIC:
                        continue
                    if symbol and str(getattr(deal, "symbol", "")).upper() != symbol:
                        continue
                    if float(getattr(deal, "time", 0.0) or 0.0) >= floor_ts:
                        found = f"deal:{int(getattr(deal, 'ticket', 0))}"
                        break
        except Exception:
            found = ""
        if found:
            reconciled += 1
            record_intent(event.get("kind", "demo_order"), data,
                          intent_id=str(event.get("intent_id")), status="reconciled",
                          extra={"evidence": found})
        elif ts < time_now() - max_age_sec or ts < time_now() - 600.0:
            unknown += 1
            record_intent(event.get("kind", "demo_order"), data,
                          intent_id=str(event.get("intent_id")), status="unknown",
                          extra={"evidence": "sem rastro na conta"})
        else:
            still += 1
    return {"ok": True, "checked": checked, "reconciled": reconciled,
            "unknown": unknown, "still_pending": still}


def snapshot(limit: int = 50) -> dict:
    """Ultimos eventos consolidados por intent (para o painel/auditoria)."""
    events = _read_events()
    grouped: dict[str, dict] = {}
    order: list[str] = []
    for event in events:
        intent_id = str(event.get("intent_id", ""))
        if not intent_id:
            continue
        if intent_id not in grouped:
            grouped[intent_id] = {"intent_id": intent_id, "kind": event.get("kind"),
                                  "ts": event.get("ts"), "ts_iso": event.get("ts_iso"),
                                  "data": event.get("data"), "status": "pending",
                                  "events": []}
            order.append(intent_id)
        item = grouped[intent_id]
        item["events"].append({"status": event.get("status"), "ts_iso": event.get("ts_iso"),
                               "extra": event.get("extra")})
        status = str(event.get("status", ""))
        if status in {"sent", "failed", "reconciled", "unknown"}:
            item["status"] = status
    rows = [grouped[i] for i in order][-max(1, min(int(limit), 500)):]
    return {"ok": True, "intents": list(reversed(rows)), "count": len(rows),
            "file": str(INTENT_FILE), "source": "intent_log"}
