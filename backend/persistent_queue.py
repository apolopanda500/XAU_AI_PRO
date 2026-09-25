# -*- coding: utf-8 -*-
"""Fila persistente de comandos (Fase 4 do gap analysis).

Quando o terminal MT5 esta indisponivel, comandos DEMO sao registrados
para revisao manual. Nenhum item e reexecutado automaticamente.
  - Itens legados "pending" sao imobilizados, inclusive apos restart.
  - Resultado incerto nunca e tratado como permissao para retry.
  - A parada de emergencia (REAL_EMERGENCY_STOP) pausa o processamento.
  - Recomendado rodar um unico gateway por vez (fila em arquivo compartilhado).

Arquivo: %APPDATA%\\XAU_AI_PRO\\command_queue.json (env XAU_QUEUE_FILE).
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

QUEUE_FILE = Path(os.getenv("XAU_QUEUE_FILE", str(
    Path(os.environ.get("APPDATA", "")) / "XAU_AI_PRO" / "command_queue.json")))
MAX_ATTEMPTS = int(os.getenv("XAU_QUEUE_MAX_ATTEMPTS", "5") or 5)
INTERVAL_SEC = float(os.getenv("XAU_QUEUE_INTERVAL", "5.0") or 5.0)

_LOCK = threading.RLock()
_ITEMS: list[dict] = []
_LOADED = False
_LAST_RUN: dict = {"last_run": None, "sent": 0, "failed": 0, "skipped": 0,
                   "pending": 0, "error": None}
_LOOP_STARTED = False
_RUNNERS: dict[str, Callable[..., dict]] = {}


def _now() -> str:
    return datetime.now().isoformat()


def register_runner(kind: str, fn: Callable[..., dict]) -> None:
    _RUNNERS[kind] = fn


def _load() -> None:
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    try:
        if QUEUE_FILE.exists():
            data = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        _ITEMS.append(item)
    except Exception:
        pass


def _save() -> None:
    try:
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        QUEUE_FILE.write_text(json.dumps(_ITEMS, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    except Exception:
        pass


def enqueue(kind: str, payload: dict, route: str = "",
            kwargs: dict | None = None) -> str:
    """Persiste um comando para execucao futura; retorna o queue_id."""
    item = {"queue_id": uuid.uuid4().hex[:12], "kind": kind, "route": route,
            "payload": payload, "kwargs": kwargs or {}, "status": "pending",
            "attempts": 0, "max_attempts": MAX_ATTEMPTS, "last_error": None,
            "created_at": _now(), "updated_at": _now()}
    with _LOCK:
        _load()
        _ITEMS.append(item)
        _save()
    return item["queue_id"]


def _mark(queue_id: str, status: str, error: str | None = None,
          bump_attempt: bool = False) -> None:
    with _LOCK:
        for item in _ITEMS:
            if item.get("queue_id") == queue_id:
                item["status"] = status
                item["updated_at"] = _now()
                if error is not None:
                    item["last_error"] = str(error)[:200]
                if bump_attempt:
                    item["attempts"] = int(item.get("attempts", 0) or 0) + 1
                break
        _save()


# Erros definitivos: reenvio nunca resolveria (evita loop de retry inutil).
_FATAL_MARKS = ("nao encontrada", "nao encontrado", "somente conta", "desabilitada",
                "desabilitadas", "desabilitado", "confirm_demo", "confirm_real",
                "simbolo indisponivel", "cotacao indisponivel", "obrigatorio",
                "volume parcial", "exige")


def _is_fatal(error: str) -> bool:
    low = str(error or "").lower()
    return any(mark in low for mark in _FATAL_MARKS)


def process_one(mt5=None) -> dict:
    """Imobiliza o proximo item legado; jamais despacha uma ordem ao MT5."""
    from backend import mt5_gateway as gw
    if gw.REAL_EMERGENCY_STOP.exists():
        return {"ok": False, "paused": "emergency_stop"}
    with _LOCK:
        _load()
        item = next((x for x in _ITEMS if x.get("status") == "pending"), None)
    if not item:
        return {"ok": True, "empty": True}
    _mark(item["queue_id"], "manual_review",
          error="resultado incerto; conciliar com a conta antes de nova acao")
    return {"ok": False, "queue_id": item["queue_id"], "manual_review": True}


def _runners_default() -> None:
    """Registra os runners de comandos DEMO/real da fila (idempotente)."""
    if _RUNNERS:
        return
    from backend import mt5_gateway as gw
    register_runner("close", gw._demo_close)
    register_runner("close_all", lambda p: gw._demo_close_all(p))
    register_runner("close_symbol", gw._demo_close_symbol)
    register_runner("partial_close", gw._demo_partial_close)
    register_runner("manage_modify", lambda p: gw._demo_manage(p, "modify"))
    register_runner("manage_breakeven", lambda p: gw._demo_manage(p, "breakeven"))
    register_runner("manage_trailing", lambda p: gw._demo_manage(p, "trailing"))
    register_runner("set_protection", gw._demo_protection)
    register_runner("remove_protection", lambda p: gw._demo_protection(p, True))
    register_runner("cancel_order", gw._demo_cancel_orders)
    register_runner("cancel_all_orders", lambda p: gw._demo_cancel_orders(p, True))


_KIND_BY_ROUTE = {
    "/api/demo/close": "close",
    "/api/demo/close-all": "close_all",
    "/api/demo/close-symbol": "close_symbol",
    "/api/demo/partial-close": "partial_close",
    "/api/demo/modify-position": "manage_modify",
    "/api/demo/breakeven": "manage_breakeven",
    "/api/demo/trailing": "manage_trailing",
    "/api/demo/set-protection": "set_protection",
    "/api/demo/remove-protection": "remove_protection",
    "/api/demo/cancel-order": "cancel_order",
    "/api/demo/cancel-all-orders": "cancel_all_orders",
}


def offline_fallback_kind(kind: str, payload: dict, exc: Exception) -> dict | None:
    """Registra comando offline sem programar execucao automatica.

    Retorna None quando: kind vazio/ordem (nunca enfileira), env DEMO off ou
    terminal ONLINE (nesse caso o erro tem outra causa e segue o fluxo normal).
    """
    from backend import mt5_gateway as gw
    if not kind or kind == "order":
        return None
    if os.getenv("XAU_ENABLE_DEMO_ORDERS", "0") != "1":
        return None
    try:
        mt5 = gw._mt5()
        info = mt5.terminal_info() if mt5 else None
        connected = bool(info and getattr(info, "connected", False))
    except Exception:
        connected = False
    if connected:
        return None  # terminal online: o erro e outro; trata normal
    queue_id = enqueue(kind, payload, route=str(kind))
    _mark(queue_id, "manual_review", error="terminal offline; resultado incerto")
    return {"ok": False, "queued": True, "queue_id": queue_id,
            "manual_review": True,
            "error": "terminal MT5 offline; solicitacao registrada sem reenvio automatico"}


def _loop() -> None:
    _runners_default()
    while True:
        try:
            report = process_one()
            _LAST_RUN.update({"last_run": _now(), "report": report, "error": None})
        except Exception as exc:
            _LAST_RUN.update({"last_run": _now(), "error": str(exc)[:200]})
        time.sleep(max(0.5, INTERVAL_SEC))


def start_queue_loop() -> None:
    """Sobe o loop da fila persistente (idempotente)."""
    global _LOOP_STARTED
    with _LOCK:
        if _LOOP_STARTED:
            return
        _LOOP_STARTED = True
    threading.Thread(target=_loop, name="command-queue", daemon=True).start()


def queue_status() -> dict:
    """Resumo da fila para o frontend/system (contagens por status)."""
    with _LOCK:
        _load()
        items = [dict(x) for x in _ITEMS]
    pending = sum(1 for x in items if x.get("status") == "pending")
    sent = sum(1 for x in items if x.get("status") == "sent")
    failed = sum(1 for x in items if x.get("status") == "failed")
    skipped = sum(1 for x in items if x.get("status") == "skipped")
    manual_review = sum(1 for x in items if x.get("status") == "manual_review")
    recent = [{"queue_id": x.get("queue_id"), "kind": x.get("kind"),
               "status": x.get("status"), "attempts": x.get("attempts"),
               "last_error": x.get("last_error"), "created_at": x.get("created_at"),
               "updated_at": x.get("updated_at")} for x in reversed(items[-10:])]
    report = dict(_LAST_RUN)
    return {"ok": True, "count": len(items), "pending": pending, "sent": sent,
             "failed": failed, "skipped": skipped, "manual_review": manual_review,
             "recent": recent, "last_run": report,
            "file": str(QUEUE_FILE), "source": "persistent_queue"}
