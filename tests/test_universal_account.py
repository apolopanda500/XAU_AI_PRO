from backend.mt5_gateway import _normalize_exchange_account, _universal_quotes


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
    assert quote["timestamp"]
    assert quote["received_at"]
