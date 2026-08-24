"""
XAU_AI_PRO - Decision Engine Package
V1.0

Módulos:
- decision_engine: Motor de decisão que integra IA, qualidade de entrada e risco.
"""

from .decision_engine import (
    DecisionConfig,
    DecisionEngine,
    TradeDecision,
)

__all__ = [
    "DecisionConfig",
    "DecisionEngine",
    "TradeDecision",
]
