import pytest
from backend.mexc_execution import MexcExecutionAdapter, MexcExecutionError
from backend.binance_execution import BinanceExecutionAdapter, BinanceExecutionError
from backend.mt5_execution import MT5ExecutionAdapter, MT5ExecutionError


@pytest.mark.parametrize("adapter,error", [
    (MexcExecutionAdapter(), MexcExecutionError),
    (BinanceExecutionAdapter(), BinanceExecutionError),
    (MT5ExecutionAdapter(), MT5ExecutionError),
])
def test_adapters_require_manual_confirmation_and_request_id(adapter, error):
    with pytest.raises(error):
        adapter.prepare(symbol="BTCUSDT", side="buy", order_type="market", quantity=1, request_id="", confirm=False)


@pytest.mark.parametrize("adapter,error", [
    (MexcExecutionAdapter(), MexcExecutionError),
    (BinanceExecutionAdapter(), BinanceExecutionError),
    (MT5ExecutionAdapter(), MT5ExecutionError),
])
def test_adapters_reject_insufficient_balance(adapter, error):
    with pytest.raises(error):
        adapter.prepare(symbol="BTCUSDT", side="buy", order_type="market", quantity=2, request_id="req-1", confirm=True, available=1)


@pytest.mark.parametrize("adapter", [MexcExecutionAdapter(), BinanceExecutionAdapter(), MT5ExecutionAdapter()])
def test_adapters_do_not_send_by_default(adapter):
    order = adapter.prepare(symbol="BTCUSDT", side="buy", order_type="market", quantity=1, request_id="req-safe", confirm=True, available=2)
    result = adapter.execute(order, explicit_authorization=True)
    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert result["withdrawals_enabled"] is False
