import pytest

import backend.mt5_gateway as gateway_module
from backend import connection_store
from backend.binance_client import BinanceClient
from backend.bybit_client import BybitClient
from backend.broker_registry import capability_matrix
from backend.mexc_client import MexcClient
from backend.okx_client import OkxClient
from backend.mt5_gateway import _assets_from_raw, _candles_from_raw, _normalize_exchange_account, _universal_quotes
from backend.universal_contracts import validate_read_scope


def test_spot_zero_balance_is_zero_and_keeps_assets():
    result = _normalize_exchange_account({"balances": [{"asset": "USDT", "free": "0", "locked": "0"}]})
    assert result["balance"] == 0
    assert result["available"] == 0
    assert len(result["assets"]) == 1


def test_invalid_or_control_values_are_not_balance():
    result = _normalize_exchange_account({"balance": "3.67e20", "available": "NaN", "timestamp": 9999999999999})
    assert result["balance"] == 0
    assert result["available"] == 0


def test_universal_quotes_normalize_source_identity(monkeypatch):
    monkeypatch.setattr("backend.mt5_gateway._universal_quote", lambda broker, market, symbol: {
        "symbol": symbol.lower(), "bid": 100.0, "ask": 101.0, "source": "binance_api",
    })
    result = _universal_quotes("binance", "crypto-spot", ["btcusdt"])
    quote = result["quotes"][0]
    assert result["source"] == "universal_gateway"
    assert quote["broker"] == "binance"
    assert quote["market"] == "crypto-spot"
    assert quote["symbol"] == "BTCUSDT"
    assert quote["source"] == "binance_api"
    assert quote["timestamp"] is None
    assert quote["received_at"]


def test_read_scope_rejects_cross_market_and_oversized_symbol():
    assert validate_read_scope("binance", "spot", "btcusdt") == {
        "broker": "binance", "market": "crypto-spot", "symbol": "BTCUSDT"
    }
    with pytest.raises(ValueError, match="mercado"):
        validate_read_scope("binance", "forex", "EURUSD")
    with pytest.raises(ValueError, match="40 caracteres"):
        validate_read_scope("binance", "crypto-spot", "X" * 41)


def test_binance_futures_catalog_uses_nested_symbols():
    result = _assets_from_raw("binance", "crypto-futures", {
        "data": {"symbols": [{"symbol": "BTCUSDT", "status": "TRADING", "baseAsset": "BTC", "quoteAsset": "USDT"}]}
    })
    assert result["ok"] is True
    assert result["assets"][0]["symbol"] == "BTCUSDT"
    assert result["assets"][0]["enabled"] is True


def test_mexc_futures_columnar_candles_are_normalized():
    result = _candles_from_raw("mexc", "crypto-futures", "BTC_USDT", {
        "success": True,
        "data": {
            "time": [1700000000, 1700000300],
            "open": [100.0, 101.0],
            "close": [102.0, 103.0],
            "high": [103.0, 104.0],
            "low": [99.0, 100.0],
            "vol": [10.0, 11.0],
        },
    }, "M5")
    assert result["ok"] is True
    assert result["count"] == 2
    assert result["candles"][0]["close"] == 102.0
    assert result["candles"][0]["volume"] == 10.0


def test_exchange_timeframes_are_translated(monkeypatch):
    binance = BinanceClient("spot")
    mexc = MexcClient("futures")
    calls = []
    monkeypatch.setattr(binance, "_get", lambda path, params=None, signed=False: calls.append((path, params)) or [])
    monkeypatch.setattr(mexc, "_get", lambda path, params=None, signed=False: calls.append((path, params)) or [])
    binance.klines("BTCUSDT", "H1", 100)
    mexc.klines("BTC_USDT", "H1", 100)
    assert calls[0][1]["interval"] == "1h"
    assert calls[1][1]["interval"] == "Min60"
    with pytest.raises(ValueError, match="timeframe Binance"):
        binance.klines("BTCUSDT", "W1", 100)


def test_binance_quote_combines_book_and_stats(monkeypatch):
    client = BinanceClient("spot")
    monkeypatch.setattr(client, "book_ticker", lambda symbol="": {"symbol": "BTCUSDT", "bidPrice": "99", "askPrice": "101"})
    monkeypatch.setattr(client, "stats_24h", lambda symbol="": {"symbol": "BTCUSDT", "lastPrice": "100", "volume": "5"})
    assert client.ticker("BTCUSDT") == {
        "symbol": "BTCUSDT", "bidPrice": "99", "askPrice": "101", "lastPrice": "100", "volume": "5"
    }


def test_capability_matrix_is_single_and_fail_closed():
    matrix = capability_matrix()
    assert {row["broker"] for row in matrix} == {"mt5", "binance", "mexc", "bybit", "okx"}
    assert all(row["execution"] == [] for row in matrix)
    assert all(row["withdrawals"] is False for row in matrix)
    assert next(row for row in matrix if row["broker"] == "bybit")["status"] == "code_only"


def test_asset_capability_matrix_reflects_mt5_trade_mode():
    result = _assets_from_raw("mt5", "metals", {"symbols": [{"name": "XAUUSD", "visible": True, "trade_mode": 1}]})
    asset = result["assets"][0]
    assert asset["availability"] == "restricted"
    assert "long_only" in asset["restrictions"]
    assert all(item["status"] == "available" for item in asset["capability_matrix"])


@pytest.mark.parametrize(("client_type", "env_name"), [
    (BinanceClient, "BINANCE_SPOT_BASE_URL"),
    (MexcClient, "MEXC_SPOT_BASE_URL"),
    (BybitClient, "BYBIT_SPOT_BASE_URL"),
    (OkxClient, "OKX_SPOT_BASE_URL"),
])
@pytest.mark.parametrize("url", [
    "http://127.0.0.1:9001",
    "https://127.0.0.1",
    "https://169.254.169.254",
    "https://user:secret@api.binance.com",
    "https://api.binance.com:8443",
    "https://api.binance.com/path?x=1",
    "https://example.com",
])
def test_exchange_clients_reject_unsafe_base_urls(monkeypatch, client_type, env_name, url):
    monkeypatch.setenv(env_name, url)
    with pytest.raises(ValueError, match="URL base"):
        client_type("spot")


def test_exchange_clients_accept_official_urls(monkeypatch):
    monkeypatch.setenv("BINANCE_SPOT_BASE_URL", "https://api.binance.com")
    monkeypatch.setenv("MEXC_FUTURES_BASE_URL", "https://contract.mexc.com")
    monkeypatch.setenv("BYBIT_SPOT_BASE_URL", "https://api-testnet.bybit.com")
    monkeypatch.setenv("OKX_SPOT_BASE_URL", "https://www.okx.com")
    assert BinanceClient("spot").base == "https://api.binance.com"
    assert MexcClient("futures").base_url == "https://contract.mexc.com"
    assert BybitClient("spot", True).base == "https://api-testnet.bybit.com"
    assert OkxClient("spot").base == "https://www.okx.com"


def test_private_account_selection_is_exact_when_multiple_accounts_exist(monkeypatch):
    connections = [
        {"id": "binance:crypto-spot:a", "broker": "binance", "market": "crypto-spot", "active": True, "configured": True},
        {"id": "binance:crypto-spot:b", "broker": "binance", "market": "crypto-spot", "active": True, "configured": True},
    ]
    monkeypatch.setattr(connection_store, "list_connections", lambda: connections)
    monkeypatch.setattr(gateway_module, "list_connections", lambda: connections)
    with pytest.raises(LookupError, match="account_id"):
        gateway_module._universal_account("binance", "crypto-spot")

    class Client:
        def __init__(self):
            self.account_id = "binance:crypto-spot:a"
            self.api_key = ""
            self.secret = ""

        def account(self):
            return {"balances": [{"asset": "USDT", "free": "1", "locked": "0"}]}

    client = Client()
    monkeypatch.setattr(gateway_module, "_exchange_client", lambda *args, **kwargs: client)
    result = gateway_module._universal_account("binance", "crypto-spot", "binance:crypto-spot:a")
    assert result["account_id"] == "binance:crypto-spot:a"


def test_overview_passes_each_exact_connection_id(monkeypatch):
    seen = []
    connections = [
        {"id": "binance:crypto-spot:a", "broker": "binance", "market": "crypto-spot", "active": True, "configured": True},
        {"id": "binance:crypto-spot:b", "broker": "binance", "market": "crypto-spot", "active": True, "configured": True},
    ]
    monkeypatch.setattr(gateway_module, "list_connections", lambda: connections)
    monkeypatch.setattr(gateway_module, "resolve_connection", lambda account_id, broker, market: {"id": account_id})

    def account(broker, market, account_id=""):
        seen.append(account_id)
        return {"ok": True, "account": {"balance": 1}}

    monkeypatch.setattr(gateway_module, "_universal_account", account)
    monkeypatch.setattr(gateway_module, "_universal_positions", lambda broker, market, account_id="": {"positions": []})
    result = gateway_module._universal_overview()
    assert seen == ["binance:crypto-spot:a", "binance:crypto-spot:b"]
    assert [row["id"] for row in result["connections"]] == ["binance:crypto-spot:a", "binance:crypto-spot:b"]
