# -*- coding: utf-8 -*-
"""Smoke extra: historico de telemetria + rate limit por categoria.

Uso: .venv/Scripts/python.exe tests/test_telemetry_history_smoke.py
"""
import sys
import time
from pathlib import Path
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _reload_gw(monkey_env):
    import os
    saved = {k: os.environ.get(k) for k in monkey_env}
    for key, value in monkey_env.items():
        os.environ[key] = value
    fake = ModuleType("MetaTrader5")
    sys.modules["MetaTrader5"] = fake
    import importlib
    import backend.watchdog as watchdog_mod
    import backend.mt5_gateway as gw_mod
    watchdog = importlib.reload(watchdog_mod)  # HISTORY_FILE usa XAU_TELEMETRY_FILE isolado
    module = importlib.reload(gw_mod)
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    return module


def test_history_persiste_jsonl(tmp_path):
    gw_file = tmp_path / "hist.jsonl"
    gw = _reload_gw({"XAU_TELEMETRY_FILE": str(gw_file)})
    rows = []
    for _ in range(3):
        snap = gw.watchdog.snapshot_metrics("smoke")
        rows.append(snap)
        time.sleep(0.01)
    hist = gw.watchdog.history(10)
    assert hist["ok"] is True
    assert hist["count"] == 3
    assert hist["snapshots"][0]["ts"] >= hist["snapshots"][-1]["ts"]
    assert hist["last"] is not None
    assert gw_file.exists()


def test_rate_limit_separado_por_categoria(tmp_path):
    gw = _reload_gw({"XAU_RATE_LIMIT": "2", "XAU_RATE_LIMIT_CMD": "1"})
    handler = gw.Handler.__new__(gw.Handler)
    handler.command = "GET"
    handler.headers = {}
    ok1, _ = gw.Handler._autorizado(handler)
    ok2, _ = gw.Handler._autorizado(handler)
    ok3, motivo3 = gw.Handler._autorizado(handler)
    assert ok1 and ok2
    assert not ok3 and motivo3 == "rate"
    post = gw.Handler.__new__(gw.Handler)
    post.command = "POST"
    post.headers = {}
    pok1, _ = gw.Handler._autorizado(post)
    pok2, motivo2 = gw.Handler._autorizado(post)
    assert pok1  # comando tem janela propria: ainda cabe 1
    assert not pok2 and motivo2 == "rate"  # cota de comandos = 1


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        test_history_persiste_jsonl(Path(tmp))
    import tempfile as _t
    with _t.TemporaryDirectory() as tmp2:
        test_rate_limit_separado_por_categoria(Path(tmp2))
    print("TELEMETRY_HISTORY_SMOKE_OK")
