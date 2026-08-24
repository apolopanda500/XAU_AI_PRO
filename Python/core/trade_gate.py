"""
XAU_AI_PRO - Trade Gate
V1.0

Responsabilidades:
- Decidir se uma nova operação pode ser executada
- Centralizar a checagem entre:
  * RiskManager (daily/weekly/drawdown/pause/equity)
  * Posições abertas (anti-loop / anti-duplicação)
- Ser o UNICO ponto de bloqueio para qualquer executor
  (backtest, live, replay)

NAO QUEBRA NADA:
- BacktestEngine.run() ainda funciona sem Gate
- RiskManager/EntryFilter/DecisionEngine nao sao alterados
- Se RiskManager nao for passado, gate cai pra "allow=True"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("XAU_AI_PRO.GATE")


@dataclass
class TradeGateConfig:
    """
    Configuracao do gate de execucao.

    Valores conservadores:
    - allow_when_no_risk_manager: True (backtest legado continua)
    - block_if_position_open: True (evita duplicacao)
    - debounce_candles: 1 (proximo candle minimo)
    """

    allow_when_no_risk_manager: bool = True
    block_if_position_open: bool = True
    debounce_candles: int = 1
    state_file: str | Path | None = None


@dataclass
class GateDecision:
    """
    Decisao do gate.

    allow: True = pode executar, False = bloqueado
    reason: motivo (para log/auditoria)
    lot: lote final (vem do RiskManager se houver)
    """

    allow: bool
    reason: str = ""
    lot: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "allow": self.allow,
            "reason": self.reason,
            "lot": self.lot,
        }


@dataclass
class PositionState:
    """
    Estado de posicoes abertas em memoria.

    Chave: simbolo (normalizado em UPPER).
    """

    open_positions: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_trade_bar: dict[str, int] = field(default_factory=dict)


class TradeGate:
    """
    Gatekeeper central de novas operacoes.

    Uso simples (sem risco):

        gate = TradeGate()
        decision = gate.can_trade(symbol="XAUUSDc", signal="BUY",
                                   confidence=0.7)
        if decision.allow:
            ...

    Uso completo (com RiskManager):

        risk = RiskManager(RiskConfig())
        gate = TradeGate(risk_manager=risk)

        decision = gate.can_trade(symbol="XAUUSDc", signal="BUY",
                                   confidence=0.7, bar_index=42)
        if decision.allow:
            gate.register_entry(symbol="XAUUSDc", lot=decision.lot,
                                bar_index=42)
            ...
        gate.register_exit(symbol="XAUUSDc", bar_index=43)
    """

    def __init__(
        self,
        risk_manager: Any | None = None,
        config: TradeGateConfig | None = None,
    ) -> None:

        self.config = config if config is not None else TradeGateConfig()

        self.risk_manager = risk_manager
        self.positions = PositionState()

    def can_trade(
        self,
        symbol: str,
        signal: str,
        confidence: float = 0.0,
        bar_index: int | None = None,
    ) -> GateDecision:
        """
        Decide se uma nova entrada pode ser executada.

        Ordem de checagem:
        1. Posicao aberta no mesmo simbolo (anti-duplicacao)
        2. Debounce (anti-mesmo-candle em sinais seguidos)
        3. RiskManager (pausa, daily/weekly/drawdown, equity)
        """

        normalized_symbol = symbol.strip().upper()

        # 1. POSICAO ABERTA
        if self.config.block_if_position_open:
            if normalized_symbol in self.positions.open_positions:
                return GateDecision(
                    allow=False,
                    reason=(
                        f"Ja existe posicao aberta em "
                        f"{normalized_symbol}. "
                        "Aguarde o fechamento."
                    ),
                    lot=0.0,
                )

        # 2. DEBOUNCE
        if self.config.debounce_candles > 0 and bar_index is not None:
            last_bar = self.positions.last_trade_bar.get(
                normalized_symbol,
                -(10**9),
            )
            if (bar_index - last_bar) < self.config.debounce_candles:
                return GateDecision(
                    allow=False,
                    reason=(
                        f"Debounce ativo em {normalized_symbol}. "
                        f"Ultimo trade no candle {last_bar}, "
                        f"atual {bar_index}. "
                        f"Minimo: {self.config.debounce_candles}."
                    ),
                    lot=0.0,
                )

        # 3. RISK MANAGER
        if self.risk_manager is None:
            if not self.config.allow_when_no_risk_manager:
                return GateDecision(
                    allow=False,
                    reason=(
                        "RiskManager nao configurado e "
                        "gate esta em modo conservador."
                    ),
                    lot=0.0,
                )
            return GateDecision(
                allow=True,
                reason="Gate sem RiskManager: permitido.",
                lot=0.0,
            )

        risk_decision = self.risk_manager.evaluate_trade(
            symbol=normalized_symbol,
            signal=signal,
            confidence=confidence,
        )

        if not risk_decision.allow:
            return GateDecision(
                allow=False,
                reason=f"RiskManager: {risk_decision.reason}",
                lot=0.0,
            )

        return GateDecision(
            allow=True,
            reason="Aprovado pelo RiskManager.",
            lot=risk_decision.lot,
        )

    def register_entry(
        self,
        symbol: str,
        side: str,
        lot: float,
        bar_index: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """
        Marca uma posicao como aberta.
        """

        normalized_symbol = symbol.strip().upper()

        self.positions.open_positions[normalized_symbol] = {
            "side": side.strip().upper(),
            "lot": float(lot),
            "entry_bar": bar_index,
            "extra": extra or {},
        }

        if bar_index is not None:
            self.positions.last_trade_bar[normalized_symbol] = bar_index

        logger.info(
            "Gate: posicao aberta | %s | %s | lot=%.2f",
            normalized_symbol,
            side,
            lot,
        )

    def register_exit(
        self,
        symbol: str,
        bar_index: int | None = None,
        pnl: float = 0.0,
    ) -> None:
        """
        Marca a posicao como fechada e registra P&L no RiskManager.
        """

        normalized_symbol = symbol.strip().upper()

        position = self.positions.open_positions.pop(
            normalized_symbol,
            None,
        )

        if bar_index is not None:
            self.positions.last_trade_bar[normalized_symbol] = bar_index

        if position is not None and self.risk_manager is not None:
            self.risk_manager.record_trade(
                symbol=normalized_symbol,
                signal=position["side"],
                lot=position["lot"],
                pnl=pnl,
            )

        logger.info(
            "Gate: posicao fechada | %s | pnl=%.2f",
            normalized_symbol,
            pnl,
        )

    def status(self) -> dict[str, Any]:
        return {
            "open_positions": dict(self.positions.open_positions),
            "last_trade_bar": dict(self.positions.last_trade_bar),
            "has_risk_manager": (self.risk_manager is not None),
            "config": {
                "allow_when_no_risk_manager": (self.config.allow_when_no_risk_manager),
                "block_if_position_open": (self.config.block_if_position_open),
                "debounce_candles": (self.config.debounce_candles),
            },
        }


# ============================================================
# TESTE (separado em test_trade_gate.py)
# ============================================================
# O bloco `if __name__ == "__main__":` foi removido deste
# arquivo para evitar pisar em risk_state.json de producao.
# Use: python core/test_trade_gate.py
