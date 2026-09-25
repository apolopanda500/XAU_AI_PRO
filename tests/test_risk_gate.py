import pytest

from backend.risk_gate import RiskLimits, validate_trade, withdrawal_allowed


def test_withdrawals_are_always_blocked():
    assert withdrawal_allowed() is False
    assert RiskLimits().withdrawals_enabled is False


def test_trade_within_limits_is_allowed():
    validate_trade(volume=0.01, daily_loss_pct=0.2, exposure_pct=1.0, open_positions=0, daily_trades=0, drawdown_pct=0.0)


BASE_RISK = {
    'volume': 0.01,
    'daily_loss_pct': 0.2,
    'exposure_pct': 1.0,
    'open_positions': 0,
    'daily_trades': 0,
    'drawdown_pct': 0.0,
}


@pytest.mark.parametrize('overrides', [
    {'volume': 0.11},
    {'daily_loss_pct': 2},
    {'exposure_pct': 5},
    {'open_positions': 5},
    {'daily_trades': 20},
    {'drawdown_pct': 15},
    {'daily_trades': float('nan')},
    {'daily_trades': 1.5},
    {'open_positions': -1},
])
def test_trade_outside_limits_is_rejected(overrides):
    with pytest.raises(ValueError):
        validate_trade(**{**BASE_RISK, **overrides})
