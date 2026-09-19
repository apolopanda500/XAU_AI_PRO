from backend.reconciliation import reconcile_order


def test_reconciliation_accepts_matching_ticket_and_position():
    request = {"request_id": "req-1", "symbol": "BTCUSDT"}
    response = {"ticket": "ticket-1", "request_id": "req-1"}
    position = {"symbol": "BTCUSDT", "quantity": 1}
    result = reconcile_order(request, response, position)
    assert result["ok"] is True
    assert result["status"] == "reconciled"


def test_reconciliation_rejects_mismatched_request_and_symbol():
    request = {"request_id": "req-1", "symbol": "BTCUSDT"}
    response = {"ticket": "ticket-1", "request_id": "req-other"}
    position = {"symbol": "ETHUSDT", "quantity": 1}
    result = reconcile_order(request, response, position)
    assert result["ok"] is False
    assert result["status"] == "mismatch"
    assert "request_id divergente" in result["errors"]
    assert "símbolo da posição divergente" in result["errors"]


def test_reconciliation_rejects_missing_ticket_or_quantity():
    result = reconcile_order({"request_id": "req-1", "symbol": "BTCUSDT"}, {}, {"symbol": "BTCUSDT", "quantity": 0})
    assert result["ok"] is False
    assert "ticket ausente" in result["errors"]
    assert "posição sem quantidade válida" in result["errors"]
