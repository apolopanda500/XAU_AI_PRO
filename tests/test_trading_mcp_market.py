"""Testes das ferramentas de mercado externo do MCP (roteamento puro, sem rede)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = str(Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import backend.trading_mcp as mcp  # noqa: E402


@pytest.fixture()
def http_stub(monkeypatch):
    chamadas: list[tuple[str, object]] = []

    def fake_http(path, payload=None, timeout=10.0):
        chamadas.append((path, payload))
        return {"http": 200, "path": path}

    monkeypatch.setattr(mcp, "_http", fake_http)
    return chamadas


def test_total_ferramentas_11():
    assert len(mcp.TOOLS) == 11


def test_fear_greed_rota_externa(http_stub):
    mcp.tool_call("fear_greed_index", {})
    path, payload = http_stub[-1]
    assert path.startswith("https://api.alternative.me/fng/")
    assert payload is None  # leitura: GET


def test_crypto_ticker_simbolo_normalizado(http_stub):
    mcp.tool_call("crypto_ticker", {"symbol": "btcusdt"})
    path, _ = http_stub[-1]
    assert path == "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"


def test_crypto_ticker_padrao_btc(http_stub):
    mcp.tool_call("crypto_ticker", {})
    assert http_stub[-1][0].endswith("symbol=BTCUSDT")


def test_ferramentas_de_mercado_sao_somente_leitura():
    nomes = {t["name"] for t in mcp.TOOLS}
    assert {"fear_greed_index", "crypto_ticker"}.issubset(nomes)
    for t in mcp.TOOLS:
        if t["name"] in {"fear_greed_index", "crypto_ticker"}:
            assert "execute" not in json.dumps(t["inputSchema"])