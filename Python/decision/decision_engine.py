"""
XAU_AI_PRO - Decision Engine
V1.0

Responsabilidades:
- Integrar IA, qualidade de entrada e gerenciamento de risco
- Responder: "Esta operação possui vantagem estatística?"
- Tomar decisão final: EXECUTAR, REJEITAR, HOLD
- Gerar score de decisão
- Salvar decisões em JSON

Fluxo:
1. IA gera sinal (BUY/SELL/HOLD) + confiança
2. EntryFilter valida qualidade da entrada
3. RiskManager valida gerenciamento de risco
4. DecisionEngine combina tudo e decide
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("XAU_AI_PRO.DECISION")


# ============================================================
# CONFIG
# ============================================================


@dataclass
class DecisionConfig:
    """
    Configuração do motor de decisão.
    """

    # --------------------------------------------------------
    # PESOS
    # --------------------------------------------------------

    ai_weight: float = 0.40  # peso da IA
    entry_weight: float = 0.35  # peso da qualidade de entrada
    risk_weight: float = 0.25  # peso do gerenciamento de risco

    # --------------------------------------------------------
    # LIMIARES
    # --------------------------------------------------------

    min_decision_score: float = 0.60  # score mínimo para executar

    # --------------------------------------------------------
    # PERSISTÊNCIA
    # --------------------------------------------------------

    decision_file: str | Path | None = None

    # --------------------------------------------------------
    # VALIDAÇÃO
    # --------------------------------------------------------

    def validate(self) -> None:
        """Valida os valores da configuração."""

        total_weight = self.ai_weight + self.entry_weight + self.risk_weight

        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Pesos devem somar 1.0. " f"Atual: {total_weight:.3f}")

        if not 0.0 < self.min_decision_score < 1.0:
            raise ValueError("min_decision_score deve estar entre 0 e 1.")


# ============================================================
# TRADE DECISION
# ============================================================


@dataclass
class TradeDecision:
    """
    Decisão final de trade.

    action: EXECUTAR, REJEITAR, HOLD
    reason: motivo da decisão
    score: score de decisão (0-1)
    lot: lote recomendado
    details: detalhes de cada componente
    """

    action: str
    reason: str = ""
    score: float = 0.0
    lot: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""

        return {
            "action": self.action,
            "reason": self.reason,
            "score": self.score,
            "lot": self.lot,
            "details": self.details,
        }


# ============================================================
# DECISION ENGINE
# ============================================================


class DecisionEngine:
    """
    Motor de decisão central.

    Uso:

        config = DecisionConfig()
        engine = DecisionEngine(config)

        decision = engine.decide(
            symbol="XAUUSDc",
            signal="BUY",
            confidence=0.75,
            ai_score=0.80,
            entry_decision=entry_decision,
            risk_decision=risk_decision,
        )

        if decision.action == "EXECUTAR":
            # executar operação
            pass
    """

    def __init__(
        self,
        config: DecisionConfig | None = None,
    ) -> None:

        self.config = config if config is not None else DecisionConfig()

        self.config.validate()

        # ----------------------------------------------------
        # HISTÓRICO DE DECISÕES
        # ----------------------------------------------------

        self.decisions: list[dict[str, Any]] = []

        self._load_decisions()

    # ========================================================
    # DECIDE
    # ========================================================

    def decide(
        self,
        symbol: str,
        signal: str,
        confidence: float,
        ai_score: float,
        entry_decision: Any | None = None,
        risk_decision: Any | None = None,
    ) -> TradeDecision:
        """
        Toma a decisão final de trade.

        Parâmetros:
        - symbol: símbolo
        - signal: BUY/SELL/HOLD da IA
        - confidence: confiança da IA (0-1)
        - ai_score: score da IA (0-1)
        - entry_decision: EntryDecision do EntryFilter
        - risk_decision: RiskDecision do RiskManager
        """

        normalized_symbol = symbol.strip().upper()

        normalized_signal = signal.strip().upper()

        # ----------------------------------------------------
        # SINAL HOLD
        # ----------------------------------------------------

        if normalized_signal == "HOLD":

            decision = TradeDecision(
                action="HOLD",
                reason="IA indica HOLD. Sem operação.",
                score=0.0,
                lot=0.0,
                details={
                    "symbol": normalized_symbol,
                    "signal": normalized_signal,
                    "confidence": confidence,
                    "ai_score": ai_score,
                },
            )

            self._record_decision(decision)

            return decision

        # ----------------------------------------------------
        # COMPONENTES
        # ----------------------------------------------------

        details: dict[str, Any] = {
            "symbol": normalized_symbol,
            "signal": normalized_signal,
            "confidence": confidence,
            "ai_score": ai_score,
        }

        # ----------------------------------------------------
        # 1. IA
        # ----------------------------------------------------

        ai_passed = confidence >= 0.55 and ai_score >= 0.50

        details["ai"] = {
            "passed": ai_passed,
            "confidence": confidence,
            "ai_score": ai_score,
        }

        # ----------------------------------------------------
        # 2. QUALIDADE DE ENTRADA
        # ----------------------------------------------------

        entry_passed = True
        entry_score = 1.0

        if entry_decision is not None:

            entry_passed = bool(
                getattr(
                    entry_decision,
                    "allow",
                    True,
                )
            )

            entry_score = (
                float(
                    getattr(
                        entry_decision,
                        "score",
                        100.0,
                    )
                )
                / 100.0
            )

            details["entry"] = {
                "passed": entry_passed,
                "score": entry_score,
                "reason": getattr(
                    entry_decision,
                    "reason",
                    "",
                ),
            }

        else:

            details["entry"] = {
                "passed": True,
                "score": 1.0,
                "reason": "EntryFilter não informado.",
            }

        # ----------------------------------------------------
        # 3. GERENCIAMENTO DE RISCO
        # ----------------------------------------------------

        risk_passed = True
        risk_lot = 0.0

        if risk_decision is not None:

            risk_passed = bool(
                getattr(
                    risk_decision,
                    "allow",
                    True,
                )
            )

            risk_lot = float(
                getattr(
                    risk_decision,
                    "lot",
                    0.0,
                )
            )

            details["risk"] = {
                "passed": risk_passed,
                "lot": risk_lot,
                "reason": getattr(
                    risk_decision,
                    "reason",
                    "",
                ),
            }

        else:

            details["risk"] = {
                "passed": True,
                "lot": 0.0,
                "reason": "RiskManager não informado.",
            }

        # ----------------------------------------------------
        # SCORE DE DECISÃO
        # ----------------------------------------------------

        ai_component = confidence if ai_passed else 0.0

        entry_component = entry_score if entry_passed else 0.0

        risk_component = 1.0 if risk_passed else 0.0

        decision_score = (
            self.config.ai_weight * ai_component
            + self.config.entry_weight * entry_component
            + self.config.risk_weight * risk_component
        )

        details["decision_score"] = round(
            decision_score,
            4,
        )

        # ----------------------------------------------------
        # DECISÃO FINAL
        # ----------------------------------------------------

        if not ai_passed:

            decision = TradeDecision(
                action="REJEITAR",
                reason=(
                    "IA não confirma vantagem estatística. "
                    f"Confiança: {confidence:.2f}, "
                    f"Score IA: {ai_score:.2f}."
                ),
                score=decision_score,
                lot=0.0,
                details=details,
            )

        elif not entry_passed:

            decision = TradeDecision(
                action="REJEITAR",
                reason=(
                    "Qualidade de entrada insuficiente. "
                    "Vantagem estatística não confirmada."
                ),
                score=decision_score,
                lot=0.0,
                details=details,
            )

        elif not risk_passed:

            decision = TradeDecision(
                action="REJEITAR",
                reason=("Gerenciamento de risco bloqueou operação."),
                score=decision_score,
                lot=0.0,
                details=details,
            )

        elif decision_score < self.config.min_decision_score:

            decision = TradeDecision(
                action="REJEITAR",
                reason=(
                    f"Score de decisão {decision_score:.2f} "
                    f"abaixo do mínimo "
                    f"{self.config.min_decision_score:.2f}."
                ),
                score=decision_score,
                lot=0.0,
                details=details,
            )

        else:

            decision = TradeDecision(
                action="EXECUTAR",
                reason=(
                    "Vantagem estatística confirmada. "
                    "Operação de qualidade com risco controlado."
                ),
                score=decision_score,
                lot=risk_lot,
                details=details,
            )

        self._record_decision(decision)

        return decision

    # ========================================================
    # REGISTRO DE DECISÃO
    # ========================================================

    def _record_decision(
        self,
        decision: TradeDecision,
    ) -> None:
        """
        Registra a decisão no histórico.
        """

        record = {
            "timestamp": datetime.now().isoformat(),
            **decision.to_dict(),
        }

        self.decisions.append(record)

        # Mantém apenas os últimos 1000
        if len(self.decisions) > 1000:
            self.decisions = self.decisions[-1000:]

        self._save_decisions()

        logger.info(
            "Decisão: %s | score=%.2f | %s",
            decision.action,
            decision.score,
            decision.reason,
        )

    # ========================================================
    # PERSISTÊNCIA
    # ========================================================

    def _decision_path(self) -> Path:
        """Retorna o caminho do arquivo de decisões."""

        if self.config.decision_file is not None:
            return Path(self.config.decision_file).expanduser()

        return Path(__file__).resolve().parent / "decisions.json"

    def _save_decisions(self) -> None:
        """Salva decisões em JSON."""

        path = self._decision_path()

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            json.dumps(
                self.decisions,
                indent=4,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _load_decisions(self) -> None:
        """Carrega decisões de JSON se existir."""

        path = self._decision_path()

        if not path.exists():
            return

        try:

            self.decisions = json.loads(path.read_text(encoding="utf-8"))

            logger.info(
                "Decisões carregadas: %s",
                path,
            )

        except Exception as exc:

            logger.warning(
                "Não foi possível carregar decisões: %s",
                exc,
            )

    # ========================================================
    # STATUS
    # ========================================================

    def status(self) -> dict[str, Any]:
        """
        Retorna o status do motor de decisão.
        """

        executed = sum(
            1 for decision in self.decisions if decision.get("action") == "EXECUTAR"
        )

        rejected = sum(
            1 for decision in self.decisions if decision.get("action") == "REJEITAR"
        )

        hold = sum(1 for decision in self.decisions if decision.get("action") == "HOLD")

        return {
            "ai_weight": self.config.ai_weight,
            "entry_weight": self.config.entry_weight,
            "risk_weight": self.config.risk_weight,
            "min_decision_score": (self.config.min_decision_score),
            "total_decisions": len(self.decisions),
            "executed": executed,
            "rejected": rejected,
            "hold": hold,
        }


# ============================================================
# TESTE
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print(" XAU_AI_PRO DECISION ENGINE")
    print("=" * 70)
    print()

    config = DecisionConfig()

    engine = DecisionEngine(config)

    print("Status:")
    print(engine.status())
    print()

    # --------------------------------------------------------
    # TESTE 1: DECISÃO DE EXECUTAR
    # --------------------------------------------------------

    decision = engine.decide(
        symbol="XAUUSDc",
        signal="BUY",
        confidence=0.75,
        ai_score=0.80,
        entry_decision=type(
            "EntryDecision",
            (),
            {
                "allow": True,
                "score": 85.0,
                "reason": "Entrada de qualidade.",
            },
        )(),
        risk_decision=type(
            "RiskDecision",
            (),
            {
                "allow": True,
                "lot": 0.10,
                "reason": "Operação permitida.",
            },
        )(),
    )

    print("Decisão 1 (executar):")
    print(decision.to_dict())
    print()

    # --------------------------------------------------------
    # TESTE 2: DECISÃO DE REJEITAR (IA FRACA)
    # --------------------------------------------------------

    decision = engine.decide(
        symbol="XAUUSDc",
        signal="BUY",
        confidence=0.50,
        ai_score=0.40,
        entry_decision=type(
            "EntryDecision",
            (),
            {
                "allow": True,
                "score": 85.0,
                "reason": "Entrada de qualidade.",
            },
        )(),
        risk_decision=type(
            "RiskDecision",
            (),
            {
                "allow": True,
                "lot": 0.10,
                "reason": "Operação permitida.",
            },
        )(),
    )

    print("Decisão 2 (rejeitar - IA fraca):")
    print(decision.to_dict())
    print()

    # --------------------------------------------------------
    # TESTE 3: DECISÃO DE REJEITAR (RISCO BLOQUEADO)
    # --------------------------------------------------------

    decision = engine.decide(
        symbol="XAUUSDc",
        signal="BUY",
        confidence=0.80,
        ai_score=0.85,
        entry_decision=type(
            "EntryDecision",
            (),
            {
                "allow": True,
                "score": 90.0,
                "reason": "Entrada de qualidade.",
            },
        )(),
        risk_decision=type(
            "RiskDecision",
            (),
            {
                "allow": False,
                "lot": 0.0,
                "reason": "Daily Stop atingido.",
            },
        )(),
    )

    print("Decisão 3 (rejeitar - risco bloqueado):")
    print(decision.to_dict())
    print()

    print("=" * 70)
