"""Barreira de risco comum aos adaptadores de corretoras."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    max_volume: float = 0.10
    max_daily_loss_pct: float = 2.0
    max_exposure_pct: float = 5.0
    max_positions: int = 5
    max_daily_trades: int = 20
    max_drawdown_pct: float = 15.0
    max_spread: float | None = None
    max_notional: float | None = None
    withdrawals_enabled: bool = False


def validate_trade(
    *,
    volume: float,
    daily_loss_pct: float,
    exposure_pct: float,
    open_positions: int,
    daily_trades: int,
    drawdown_pct: float,
    spread: float | None = None,
    notional: float | None = None,
    limits: RiskLimits = RiskLimits(),
) -> None:
    """Rejeita uma operação que exceda qualquer limite local."""
    values = (volume, daily_loss_pct, exposure_pct, drawdown_pct)
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("métricas de risco devem ser finitas")
    if isinstance(open_positions, bool) or isinstance(daily_trades, bool):
        raise ValueError("contagens de risco devem ser inteiras")
    if not all(math.isfinite(float(value)) for value in (open_positions, daily_trades)):
        raise ValueError("contagens de risco devem ser finitas")
    if int(open_positions) != open_positions or int(daily_trades) != daily_trades:
        raise ValueError("contagens de risco devem ser inteiras")
    if open_positions < 0 or daily_trades < 0:
        raise ValueError("contagens de risco não podem ser negativas")
    if volume <= 0 or volume > limits.max_volume:
        raise ValueError(f"volume fora do limite: máximo {limits.max_volume}")
    if daily_loss_pct >= limits.max_daily_loss_pct:
        raise ValueError(f"perda diária atingiu o limite de {limits.max_daily_loss_pct}%")
    if exposure_pct >= limits.max_exposure_pct:
        raise ValueError(f"exposição atingiu o limite de {limits.max_exposure_pct}%")
    if open_positions >= limits.max_positions:
        raise ValueError(f"limite de {limits.max_positions} posições atingido")
    if daily_trades >= limits.max_daily_trades:
        raise ValueError(f"limite diário de {limits.max_daily_trades} operações atingido")
    if drawdown_pct >= limits.max_drawdown_pct:
        raise ValueError(f"drawdown atingiu o limite de {limits.max_drawdown_pct}%")
    if limits.max_spread is not None and (spread is None or spread > limits.max_spread):
        raise ValueError(f"spread fora do limite: máximo {limits.max_spread}")
    if limits.max_notional is not None and (notional is None or notional > limits.max_notional):
        raise ValueError(f"notional fora do limite: máximo {limits.max_notional}")


def withdrawal_allowed() -> bool:
    return False
