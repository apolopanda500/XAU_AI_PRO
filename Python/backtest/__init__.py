"""
XAU_AI_PRO - Backtest Package
V1.0

Módulos:
- backtest_engine: Backtest sério com métricas profissionais.
"""

from .backtest_engine import (
    BacktestConfig,
    BacktestEngine,
    BacktestResult,
)

__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestResult",
]
