from backend.mt5_gateway import _normalize_exchange_account


def test_spot_zero_balance_is_zero_and_keeps_assets():
    result = _normalize_exchange_account({"balances": [{"asset": "USDT", "free": "0", "locked": "0"}]})
    assert result["balance"] == 0
    assert result["available"] == 0
    assert len(result["assets"]) == 1


def test_invalid_or_control_values_are_not_balance():
    result = _normalize_exchange_account({"balance": "3.67e20", "available": "NaN", "timestamp": 9999999999999})
    assert result["balance"] == 0
    assert result["available"] == 0
