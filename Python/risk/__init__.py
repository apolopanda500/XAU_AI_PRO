"""
XAU_AI_PRO - Risk Management Package
V1.0

Módulos:
- risk_manager: Daily Stop, Weekly Stop, Drawdown Stop, Equity Protection,
               redução automática de lote, pausa após sequência negativa.
"""

from .risk_manager import (
    RiskConfig,
    RiskDecision,
    RiskManager,
    RiskState,
)

__all__ = [
    "RiskConfig",
    "RiskDecision",
    "RiskManager",
    "RiskState",
]
