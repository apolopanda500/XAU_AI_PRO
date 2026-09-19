import pytest

from backend.universal_contracts import normalize_market
from backend.universal_router import UniversalRouter, UniversalRouterError


def test_normalize_market_accepts_app_aliases():
    assert normalize_market("crypto-spot") == "spot"
    assert normalize_market("crypto-futures") == "futures"
    assert normalize_market("forex") == "forex"


def test_router_accepts_crypto_spot_alias():
    result = UniversalRouter().prepare_order({"broker": "mexc", "market": "crypto-spot", "symbol": "BTCUSDT", "side": "buy", "order_type": "market", "quantity": 1, "request_id": "req-alias", "confirm": True})
    assert result["market"] == "spot"
    assert result["status"] == "pending_manual_review"


def test_gateway_build_derives_from_version_json():
    import backend.mt5_gateway as gateway

    assert gateway.GATEWAY_BUILD.startswith("xau-ai-pro-1.2.3-universal-")


def test_universal_positions_and_quotes_helpers_exist():
    import backend.mt5_gateway as gateway

    assert callable(gateway._universal_positions)
    assert callable(gateway._universal_quotes)
    assert callable(gateway._universal_depth)


@pytest.mark.parametrize("broker,market,symbol", [
    ("mexc", "spot", "BTCUSDT"),
    ("binance", "spot", "BTCUSDT"),
    ("mt5", "forex", "EURUSD"),
])
def test_router_prepares_one_independent_adapter(broker, market, symbol):
    router = UniversalRouter()
    result = router.prepare_order({"broker": broker, "market": market, "symbol": symbol, "side": "buy", "order_type": "market", "quantity": 1, "request_id": f"req-{broker}", "confirm": True})
    assert result["status"] == "pending_manual_review"
    assert result["adapter_payload"]["symbol"] == symbol


def test_router_rejects_duplicate_request_id():
    router = UniversalRouter()
    payload = {"broker": "mexc", "market": "spot", "symbol": "BTCUSDT", "side": "buy", "order_type": "market", "quantity": 1, "request_id": "same-request", "confirm": True}
    router.prepare_order(payload)
    with pytest.raises(UniversalRouterError, match="request_id"):
        router.prepare_order(payload)


@pytest.mark.parametrize("broker,market,symbol", [("mexc", "spot", "BTCUSDT"), ("binance", "spot", "BTCUSDT"), ("mt5", "forex", "EURUSD")])
def test_router_execution_is_blocked_without_enable_flag(broker, market, symbol):
    router = UniversalRouter()
    payload = {"broker": broker, "market": market, "symbol": symbol, "side": "buy", "order_type": "market", "quantity": 1, "request_id": f"safe-{broker}", "confirm": True}
    result = router.execute(payload, explicit_authorization=True)
    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert result["withdrawals_enabled"] is False
