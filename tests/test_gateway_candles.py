"""Cobertura do endpoint de candles OHLC (copy_rates) do gateway MT5."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

from backend.universal_contracts import timestamp_iso

ROOT = str(Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture()
def gw(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XAU_MT5_COMMON_FILES", str(tmp_path / "common"))
    monkeypatch.setenv("XAU_APP_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setenv("XAU_AUDIT_FILE", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("XAU_REAL_EMERGENCY_FILE", str(tmp_path / "STOP"))
    fake = ModuleType("MetaTrader5")
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake)
    import backend.mt5_gateway as gw_mod
    return importlib.reload(gw_mod)


class FakeRates:
    """Imita o ndarray do copy_rates (acesso por chave)."""

    def __init__(self, rows):
        self._rows = rows

    def __len__(self):
        return len(self._rows)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._rows[key]
        return [row[key] for row in self._rows]


@pytest.fixture()
def fake_mt5_candles(gw, monkeypatch):
    rows = [
        {"time": 1700000000 + i * 300, "open": 2000.0 + i, "high": 2001.0 + i,
         "low": 1999.0 + i, "close": 2000.5 + i, "tick_volume": 100 + i,
         "spread": 1, "real_volume": 0}
        for i in range(50)
    ]
    holder: dict = {"rates": FakeRates(rows), "last": {}}

    def fake_copy_rates(symbol, timeframe, count):
        holder["last"] = {"symbol": symbol, "timeframe": timeframe, "count": count}
        return holder["rates"]

    monkeypatch.setattr(gw, "copy_rates", fake_copy_rates, raising=False)
    monkeypatch.setattr(gw, "_mt5", lambda: type("M", (), {"copy_rates": staticmethod(fake_copy_rates)})())
    return holder


def test_candles_ok_ordenados(gw, fake_mt5_candles):
    out = gw._mt5_candles("XAUUSD", "M5", 50)
    assert out["ok"] is True
    assert out["count"] == 50
    times = [row["time"] for row in out["candles"]]
    assert times == sorted(times)
    first = out["candles"][0]
    assert {"open", "high", "low", "close", "time", "volume"} <= set(first)


def test_candles_clamp_count(gw, fake_mt5_candles):
    gw._mt5_candles("XAUUSD", "M5", 99999)
    assert fake_mt5_candles["last"]["count"] <= 2000
    gw._mt5_candles("XAUUSD", "M5", 0)
    assert fake_mt5_candles["last"]["count"] >= 10


def test_candles_timeframe_valido(gw, fake_mt5_candles):
    gw._mt5_candles("XAUUSD", "H1", 100)
    assert fake_mt5_candles["last"]["timeframe"] == 16385  # código MT5 de H1
    with pytest.raises(ValueError, match="timeframe MT5 inválido"):
        gw._mt5_candles("XAUUSD", "timeframe-estranho", 100)


def test_candles_sem_dados_nao_inventa(gw, fake_mt5_candles, monkeypatch):
    monkeypatch.setattr(gw, "_mt5", lambda: type("M", (), {"copy_rates": staticmethod(lambda *a, **k: None)})())
    out = gw._mt5_candles("XAUUSD", "M5", 50)
    assert out["ok"] is False
    assert out["candles"] == [] and out["count"] == 0


def test_candle_parser_accepts_numpy_structured_rows(gw):
    dtype = np.dtype([
        ("time", "int64"), ("open", "float64"), ("high", "float64"),
        ("low", "float64"), ("close", "float64"), ("tick_volume", "int64"),
    ])
    rates = np.array([(1700000000, 100.0, 102.0, 99.0, 101.0, 10)], dtype=dtype)
    monkeypatch = type("M", (), {"copy_rates_from_pos": staticmethod(lambda *args: rates)})
    original = gw._mt5
    gw._mt5 = lambda: monkeypatch
    try:
        result = gw._mt5_candles("XAUUSD", "M5", 10)
    finally:
        gw._mt5 = original
    assert result["count"] == 1
    assert result["candles"][0]["close"] == 101.0
    assert result["candles"][0]["volume"] == 10


def test_timestamp_aceita_escalar_numpy():
    assert timestamp_iso(np.int64(1_700_000_000)) == "2023-11-14T22:13:20.000Z"
