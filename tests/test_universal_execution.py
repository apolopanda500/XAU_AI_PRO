import pytest
from backend.reconciliation import reconcile_order
from backend.universal_router import UniversalRouter, UniversalRouterError

def payload():
    return {"broker":"mexc","market":"spot","symbol":"BTCUSDT","side":"buy","order_type":"market","quantity":0.001,"account_id":"mexc-account","request_id":"test-001","confirm":True}

def test_router_prepares_mexc_order_without_sending(monkeypatch):
    monkeypatch.setenv("XAU_ENABLE_MEXC_EXECUTION", "0")
    result = UniversalRouter().execute_mexc(payload(), explicit_authorization=True)
    assert result["status"] == "blocked"
    assert result["withdrawals_enabled"] is False

def test_router_rejects_without_explicit_authorization():
    with pytest.raises(Exception, match="autoriz"):
        UniversalRouter().execute_mexc(payload(), explicit_authorization=False)

def test_reconciliation_accepts_matching_ticket_and_position():
    result = reconcile_order(payload(), {"orderId":"42","externalOid":"test-001"}, {"symbol":"BTCUSDT","quantity":0.001})
    assert result["ok"] is True
    assert result["status"] == "reconciled"

def test_reconciliation_rejects_mismatch():
    result = reconcile_order(payload(), {"orderId":"42","externalOid":"other"}, {"symbol":"ETHUSDT","quantity":0.001})
    assert result["ok"] is False
    assert len(result["errors"]) == 2
