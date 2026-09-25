from __future__ import annotations

import asyncio
import json

import pytest

from backend.backtest import run_backtest


def _candles(count: int = 80) -> list[dict[str, float]]:
    rows = []
    price = 2000.0
    for index in range(count):
        change = 1.5 if index % 9 == 0 else -0.8 if index % 5 == 0 else 0.2
        price += change
        rows.append({"time": index, "open": price - 0.2, "high": price + 0.8, "low": price - 0.8, "close": price})
    return rows


def test_backtest_nao_executa_ordens_e_devolve_metricas():
    result = run_backtest(_candles())
    assert result["ok"] is True
    assert result["live_execution"] is False
    assert result["mode"] == "historical_paper"
    assert result["candles"] == 80
    assert "equity_curve" in result
    assert "max_drawdown_pct" in result


def test_backtest_rejeita_dados_insuficientes():
    with pytest.raises(ValueError, match="30 candles"):
        run_backtest(_candles(29))


def test_backtest_rejeita_ohlc_inconsistente():
    candles = _candles()
    candles[0]["high"] = candles[0]["low"] - 1
    with pytest.raises(ValueError, match="OHLC"):
        run_backtest(candles)


def test_endpoint_backtest_consome_candles_reais(monkeypatch):
    from backend import fastapi_gateway

    monkeypatch.setattr(fastapi_gateway.gw, "_mt5_candles", lambda symbol, timeframe, count: {"ok": True, "source": "test_fixture", "candles": _candles(80)})
    response = asyncio.run(fastapi_gateway.backtest_run({"symbol": "XAUUSD", "timeframe": "M15", "count": 80}))
    payload = json.loads(response.body)
    assert response.status_code == 200
    assert payload["source"] == "test_fixture"
    assert payload["live_execution"] is False
