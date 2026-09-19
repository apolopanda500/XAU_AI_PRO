"""Barreira de risco comum aos adaptadores de corretoras."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    max_volume: float = 0.10
    max_daily_loss_pct: float = 2.0
    max_exposure_pct: float = 5.0
    max_positions: int = 5
    withdrawals_enabled: bool = False


def validate_trade(*, volume: float, daily_loss_pct: float, exposure_pct: float, open_positions: int, limits: RiskLimits = RiskLimits()) -> None:
    """Rejeita uma operação que exceda qualquer limite local."""
    if volume <= 0 or volume > limits.max_volume:
        raise ValueError(f"volume fora do limite: máximo {limits.max_volume}")
    if daily_loss_pct >= limits.max_daily_loss_pct:
        raise ValueError(f"perda diária atingiu o limite de {limits.max_daily_loss_pct}%")
    if exposure_pct >= limits.max_exposure_pct:
        raise ValueError(f"exposição atingiu o limite de {limits.max_exposure_pct}%")
    if open_positions >= limits.max_positions:
        raise ValueError(f"limite de {limits.max_positions} posições atingido")


def withdrawal_allowed() -> bool:
    return False
