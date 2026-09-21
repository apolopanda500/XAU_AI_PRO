# -*- coding: utf-8 -*-
"""Integracao HTTP da fila persistente offline (Fase 4) - Handler direto, sem servidor.

Valida de ponta a ponta, sem terminal MT5 instalado:
  - /api/demo/close com terminal offline  -> 202 + comando enfileirado
  - /api/demo/close com terminal online   -> 403 (erro real, NAO enfileira)
  - /api/demo/order (ordem)               -> 403 e NUNCA enfileira
  - GET /api/queue/status                 -> 200 com contagens

Uso: .venv/Scripts/python.exe tests/test_queue_gateway_integration.py
"""
from __future__ import annotations

import importlib
import io
import json
import os
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ENV_KEYS = ("APPDATA", "XAU_MT5_COMMON_FILES", "XAU_APP_CONFIG", "XAU_AUDIT_FILE",
             "XAU_REAL_EMERGENCY_FILE", "XAU_QUEUE_FILE", "XAU_ENABLE_DEMO_ORDERS")


class _Ctx:
    """Estado compartilhado entre os testes (gateway + fila + fake MT5)."""
    gw = None
    pq = None
    fake = None


def _setup(tmp: str) -> None:
    os.environ["APPDATA"] = tmp
    os.environ["XAU_MT5_COMMON_FILES"] = str(Path(tmp) / "common")
    os.environ["XAU_APP_CONFIG"] = str(Path(tmp) / "config.json")
    os.environ["XAU_AUDIT_FILE"] = str(Path(tmp) / "audit.jsonl")
    os.environ["XAU_REAL_EMERGENCY_FILE"] = str(Path(tmp) / "STOP")
    os.environ["XAU_QUEUE_FILE"] = str(Path(tmp) / "command_queue.json")
    os.environ["XAU_ENABLE_DEMO_ORDERS"] = "1"
    _Ctx.fake = types.ModuleType("MetaTrader5")
    sys.modules["MetaTrader5"] = _Ctx.fake
    import backend.persistent_queue as pq  # primeiro import: envs ja aplicados
    import backend.mt5_gateway as gw_mod
    _Ctx.pq, _Ctx.gw = pq, gw_mod


def _make_handler(path: str, body: bytes = b""):
    handler = _Ctx.gw.Handler.__new__(_Ctx.gw.Handler)
    handler.path = path
    handler.rfile = io.BytesIO(body)
    handler.wfile = io.BytesIO()
    handler.headers = {"Content-Type": "application/json",
                       "Content-Length": str(len(body))}
    status: list[int] = []
    handler.send_response = lambda code, *a, **k: status.append(code)  # type: ignore[method-assign]
    handler.end_headers = lambda: None  # type: ignore[method-assign]
    handler.send_header = lambda name, value: None  # type: ignore[method-assign]
    return handler, status


def _json_out(handler) -> dict:
    return json.loads(handler.wfile.getvalue().decode("utf-8"))


def test_offline_close_enfileira_202():
    handler, status = _make_handler("/api/demo/close", b'{"ticket": 123}')
    _Ctx.gw.Handler.do_POST(handler)
    assert status == [202], f"status inesperado {status}: {_json_out(handler)}"
    data = _json_out(handler)
    assert data.get("queued") is True and data.get("queue_id")
    resumo = _Ctx.pq.queue_status()
    assert resumo["pending"] >= 1
    assert "close" in [x["kind"] for x in resumo["recent"]]


def test_terminal_online_nao_enfileira():
    _Ctx.fake.terminal_info = lambda: types.SimpleNamespace(connected=True)
    antes = _Ctx.pq.queue_status()["count"]
    handler, status = _make_handler("/api/demo/close", b'{"ticket": 456}')
    _Ctx.gw.Handler.do_POST(handler)
    assert status == [403], f"status inesperado {status}: {_json_out(handler)}"
    assert _Ctx.pq.queue_status()["count"] == antes


def test_ordem_nunca_enfileira():
    handler, status = _make_handler("/api/demo/order", b"{}")
    _Ctx.gw.Handler.do_POST(handler)
    assert status == [403], f"status inesperado {status}: {_json_out(handler)}"
    resumo = _Ctx.pq.queue_status()
    assert all(x.get("kind") != "order" for x in resumo["recent"])


def test_get_queue_status_200():
    handler, status = _make_handler("/api/queue/status")
    _Ctx.gw.Handler.do_GET(handler)
    assert status == [200], f"status inesperado {status}"
    data = _json_out(handler)
    assert data.get("ok") is True and "pending" in data and "count" in data


def main() -> int:
    antigos = {k: os.environ.get(k) for k in _ENV_KEYS}
    old_fake = sys.modules.get("MetaTrader5")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            _setup(tmp)
            test_offline_close_enfileira_202()
            test_terminal_online_nao_enfileira()
            test_ordem_nunca_enfileira()
            test_get_queue_status_200()
        print("QUEUE_GATEWAY_INTEGRATION_OK")
        return 0
    except AssertionError as exc:
        print(f"QUEUE_GATEWAY_INTEGRATION_FAIL: {exc}")
        return 1
    finally:
        for key, value in antigos.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if old_fake is None:
            sys.modules.pop("MetaTrader5", None)
        else:
            sys.modules["MetaTrader5"] = old_fake


if __name__ == "__main__":
    raise SystemExit(main())
