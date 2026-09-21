# -*- coding: utf-8 -*-
"""Smoke test do Watchdog/Telemetria (Fase 3) - roda sem MT5 instalado.

Uso: .venv/Scripts/python.exe tests/test_watchdog_smoke.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import watchdog as w  # noqa: E402


def test_classificacao_heartbeat():
    agora = w._now()
    assert w._classify_heartbeat({"invalid": True}, 0, 0) == "unknown"
    assert w._classify_heartbeat({"invalid": False, "ts_epoch": 0}, 0, 0) == "unknown"
    assert w._classify_heartbeat({"invalid": False, "ts_epoch": agora}, 0, 0) == "alive"
    # arquivo fresh + timestamp estagnado -> frozen
    assert w._classify_heartbeat({"invalid": False, "ts_epoch": agora - 3600}, 3600, 5) == "frozen"
    # arquivo antigo -> stale
    assert w._classify_heartbeat({"invalid": False, "ts_epoch": agora - 3600}, 3600, 3600) == "stale"


def test_telemetria_ring():
    w._RING.clear()
    w.record("teste", {"x": 1})
    w.record("teste", {"x": 2}, severity="warning")
    snapshot = w.telemetry(10)
    assert snapshot["ok"] is True
    assert snapshot["count"] == 2
    assert snapshot["by_kind"].get("teste") == 2
    assert snapshot["by_severity"].get("warning") == 1
    assert snapshot["events"][0]["kind"] == "teste"  # mais recente primeiro


def test_recovery_somente_leitura():
    resultado = w.recovery()
    assert resultado["ok"] is True
    assert resultado["state"] in {"alive", "frozen", "stale", "missing", "unknown"}
    assert resultado["actions"] == []


if __name__ == "__main__":
    test_classificacao_heartbeat()
    test_telemetria_ring()
    test_recovery_somente_leitura()
    print("WATCHDOG_SMOKE_OK")
