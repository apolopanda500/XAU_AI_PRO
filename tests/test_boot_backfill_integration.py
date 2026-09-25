# -*- coding: utf-8 -*-
"""Integracao do boot/backfill (fechamento do gap analysis) - sem terminal MT5.

Valida, com MT5 fake e diretorios temporarios:
  - boot_report() do FastAPI: ok, mt5_ready False, snapshot parcial, sem excecao
  - snapshot_metrics("boot") persiste o primeiro ponto no historico
  - reconcile() com intents.jsonl vazio retorna checked=0 sem erro
  - evento "boot" registrado na telemetria (anel in-memory)

Uso: .venv/Scripts/python.exe tests/test_boot_backfill_integration.py
"""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ENV_KEYS = ("APPDATA", "XAU_MT5_COMMON_FILES", "XAU_APP_CONFIG", "XAU_AUDIT_FILE",
             "XAU_REAL_EMERGENCY_FILE", "XAU_INTENT_FILE", "XAU_TELEMETRY_FILE",
             "XAU_HEARTBEAT_FILE")


def _setup(tmp: str) -> tuple:
    os.environ["APPDATA"] = tmp
    os.environ["XAU_MT5_COMMON_FILES"] = str(Path(tmp) / "common")
    os.environ["XAU_APP_CONFIG"] = str(Path(tmp) / "config.json")
    os.environ["XAU_AUDIT_FILE"] = str(Path(tmp) / "audit.jsonl")
    os.environ["XAU_REAL_EMERGENCY_FILE"] = str(Path(tmp) / "STOP")
    os.environ["XAU_INTENT_FILE"] = str(Path(tmp) / "intents.jsonl")
    os.environ["XAU_TELEMETRY_FILE"] = str(Path(tmp) / "telemetry_history.jsonl")
    os.environ["XAU_HEARTBEAT_FILE"] = str(Path(tmp) / "heartbeat.json")
    fake = types.ModuleType("MetaTrader5")
    fake.initialize = lambda: True  # type: ignore[attr-defined]
    fake.positions_get = lambda *a, **k: []  # type: ignore[attr-defined]
    fake.history_deals_get = lambda *a, **k: []  # type: ignore[attr-defined]
    fake.account_info = lambda: None  # type: ignore[attr-defined]
    sys.modules["MetaTrader5"] = fake
    import backend.watchdog as watchdog_mod
    import backend.intent_log as intent_mod
    import backend.fastapi_gateway as fastapi_mod
    watchdog = importlib.reload(watchdog_mod)
    intent_log = importlib.reload(intent_mod)
    fastapi = importlib.reload(fastapi_mod)
    return watchdog, intent_log, fastapi


@pytest.fixture()
def boot_backfill_modules(tmp_path, monkeypatch):
    """Isola os modulos do boot/backfill para a execucao via pytest."""
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    return _setup(str(tmp_path))


def _assert_boot_report_sem_mt5(watchdog, intent_log, fastapi) -> None:
    out = fastapi.boot_report()
    assert out.get("ok") is True, out
    assert out.get("source") == "boot_report", out
    snap = out.get("snapshot") or {}
    assert "ts_iso" in snap and "equity" in snap, out
    assert snap.get("terminal_connected") is False, out
    hist = watchdog.history(10)
    assert hist.get("count", 0) >= 1, hist  # primeiro ponto persistido


def test_boot_report_sem_mt5(boot_backfill_modules) -> None:
    _assert_boot_report_sem_mt5(*boot_backfill_modules)


def _assert_boot_route_fastapi_sem_mt5(watchdog, intent_log, fastapi) -> None:
    import asyncio
    import json
    from fastapi.responses import JSONResponse
    out = asyncio.run(fastapi.boot_route())
    data = json.loads(bytes(out.body).decode("utf-8")) if isinstance(out, JSONResponse) else out
    assert data.get("ok") is True, data
    assert data.get("source") == "boot_status", data
    hist = watchdog.history(10)
    assert hist.get("count", 0) == 0, hist
    if isinstance(out, JSONResponse):
        assert out.status_code == 200, data


def test_boot_route_fastapi_sem_mt5(boot_backfill_modules) -> None:
    _assert_boot_route_fastapi_sem_mt5(*boot_backfill_modules)


def _assert_reconcile_vazio_sem_erro(watchdog, intent_log, fastapi) -> None:
    import MetaTrader5 as mt5
    report = intent_log.reconcile(mt5)
    assert report.get("ok") is True, report
    assert report.get("checked") == 0, report


def test_reconcile_vazio_sem_erro(boot_backfill_modules) -> None:
    _assert_reconcile_vazio_sem_erro(*boot_backfill_modules)


def _assert_evento_boot_na_telemetria(watchdog, intent_log, fastapi) -> None:
    watchdog.record("boot", {"mt5_ready": False, "reconcile": {"checked": 0}})
    tel = watchdog.telemetry(10)
    kinds = [e.get("kind") for e in tel.get("events", [])]
    assert "boot" in kinds, tel


def test_evento_boot_na_telemetria(boot_backfill_modules) -> None:
    _assert_evento_boot_na_telemetria(*boot_backfill_modules)


def main() -> int:
    antigos = {k: os.environ.get(k) for k in _ENV_KEYS}
    old_fake = sys.modules.get("MetaTrader5")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            mods = _setup(tmp)
            _assert_boot_report_sem_mt5(*mods)
            _assert_boot_route_fastapi_sem_mt5(*mods)
            _assert_reconcile_vazio_sem_erro(*mods)
            _assert_evento_boot_na_telemetria(*mods)
        print("BOOT_BACKFILL_INTEGRATION_OK")
        return 0
    except AssertionError as exc:
        print(f"BOOT_BACKFILL_INTEGRATION_FAIL: {exc}")
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
