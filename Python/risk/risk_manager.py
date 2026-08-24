"""
XAU_AI_PRO - Risk Manager
V1.0

Responsabilidades:
- Daily Stop: limite de perda diária
- Weekly Stop: limite de perda semanal
- Drawdown Stop: limite de drawdown máximo
- Equity Protection: proteção de equity
- Redução automática de lote
- Pausa após sequência negativa
- Decisão de risco para cada operação
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("XAU_AI_PRO.RISK")


# ============================================================
# CONFIG
# ============================================================


@dataclass
class RiskConfig:
    """
    Configuração de gerenciamento de risco.

    Valores padrão conservadores:
    - Daily Stop: 2% do equity
    - Weekly Stop: 5% do equity
    - Drawdown Stop: 10% do equity
    - Equity Protection: 15% do equity
    - Redução de lote: 50% após 3 perdas consecutivas
    - Pausa: 2 horas após 4 perdas consecutivas
    """

    # --------------------------------------------------------
    # LIMITES DE PERDA
    # --------------------------------------------------------

    daily_stop_pct: float = 0.02  # 2% por dia
    weekly_stop_pct: float = 0.05  # 5% por semana
    drawdown_stop_pct: float = 0.10  # 10% drawdown máximo
    equity_protection_pct: float = 0.15  # 15% proteção de equity

    # --------------------------------------------------------
    # REDUÇÃO DE LOTE
    # --------------------------------------------------------

    lot_reduction_enabled: bool = True
    lot_reduction_after_losses: int = 3
    lot_reduction_factor: float = 0.5  # reduz 50%

    # --------------------------------------------------------
    # PAUSA APÓS SEQUÊNCIA NEGATIVA
    # --------------------------------------------------------

    pause_enabled: bool = True
    pause_after_losses: int = 4
    pause_duration_hours: float = 2.0

    # --------------------------------------------------------
    # RISCO POR OPERAÇÃO
    # --------------------------------------------------------

    risk_per_trade_pct: float = 0.01  # 1% por operação
    max_lot: float = 1.0
    min_lot: float = 0.01

    # --------------------------------------------------------
    # PERSISTÊNCIA
    # --------------------------------------------------------

    state_file: str | Path | None = None

    # --------------------------------------------------------
    # VALIDAÇÃO
    # --------------------------------------------------------

    def validate(self) -> None:
        """Valida os valores da configuração."""

        if not 0.0 < self.daily_stop_pct < 1.0:
            raise ValueError("daily_stop_pct deve estar entre 0 e 1.")

        if not 0.0 < self.weekly_stop_pct < 1.0:
            raise ValueError("weekly_stop_pct deve estar entre 0 e 1.")

        if not 0.0 < self.drawdown_stop_pct < 1.0:
            raise ValueError("drawdown_stop_pct deve estar entre 0 e 1.")

        if not 0.0 < self.equity_protection_pct < 1.0:
            raise ValueError("equity_protection_pct deve estar entre 0 e 1.")

        if not 0.0 < self.risk_per_trade_pct < 1.0:
            raise ValueError("risk_per_trade_pct deve estar entre 0 e 1.")

        if self.lot_reduction_after_losses < 1:
            raise ValueError("lot_reduction_after_losses deve ser >= 1.")

        if not 0.0 < self.lot_reduction_factor <= 1.0:
            raise ValueError("lot_reduction_factor deve estar entre 0 e 1.")

        if self.pause_after_losses < 1:
            raise ValueError("pause_after_losses deve ser >= 1.")

        if self.pause_duration_hours <= 0:
            raise ValueError("pause_duration_hours deve ser > 0.")


# ============================================================
# STATE
# ============================================================


@dataclass
class RiskState:
    """
    Estado atual do gerenciamento de risco.

    Persistido em JSON para sobreviver a reinicializações.
    """

    # --------------------------------------------------------
    # EQUITY
    # --------------------------------------------------------

    initial_equity: float = 0.0
    current_equity: float = 0.0
    peak_equity: float = 0.0

    # --------------------------------------------------------
    # PERÍODOS
    # --------------------------------------------------------

    day_start_equity: float = 0.0
    week_start_equity: float = 0.0
    current_day: str = ""
    current_week: str = ""

    # --------------------------------------------------------
    # SEQUÊNCIA
    # --------------------------------------------------------

    consecutive_losses: int = 0
    consecutive_wins: int = 0

    # --------------------------------------------------------
    # PAUSA
    # --------------------------------------------------------

    paused_until: str = ""

    # --------------------------------------------------------
    # LOTE
    # --------------------------------------------------------

    current_lot: float = 0.0
    base_lot: float = 0.0

    # --------------------------------------------------------
    # HISTÓRICO
    # --------------------------------------------------------

    trades: list[dict[str, Any]] = field(default_factory=list)

    # --------------------------------------------------------
    # PROPRIEDADES
    # --------------------------------------------------------

    @property
    def drawdown_pct(self) -> float:
        """Drawdown atual em percentual."""

        if self.peak_equity <= 0:
            return 0.0

        return (self.peak_equity - self.current_equity) / self.peak_equity

    @property
    def daily_pnl_pct(self) -> float:
        """P&L diário em percentual."""

        if self.day_start_equity <= 0:
            return 0.0

        return (self.current_equity - self.day_start_equity) / self.day_start_equity

    @property
    def weekly_pnl_pct(self) -> float:
        """P&L semanal em percentual."""

        if self.week_start_equity <= 0:
            return 0.0

        return (self.current_equity - self.week_start_equity) / self.week_start_equity

    @property
    def is_paused(self) -> bool:
        """Verifica se está em pausa."""

        if not self.paused_until:
            return False

        try:
            pause_time = datetime.fromisoformat(self.paused_until)
        except ValueError:
            return False

        return datetime.now() < pause_time

    @property
    def total_pnl_pct(self) -> float:
        """P&L total em percentual."""

        if self.initial_equity <= 0:
            return 0.0

        return (self.current_equity - self.initial_equity) / self.initial_equity

    # --------------------------------------------------------
    # SERIALIZAÇÃO
    # --------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""

        return {
            "initial_equity": self.initial_equity,
            "current_equity": self.current_equity,
            "peak_equity": self.peak_equity,
            "day_start_equity": self.day_start_equity,
            "week_start_equity": self.week_start_equity,
            "current_day": self.current_day,
            "current_week": self.current_week,
            "consecutive_losses": self.consecutive_losses,
            "consecutive_wins": self.consecutive_wins,
            "paused_until": self.paused_until,
            "current_lot": self.current_lot,
            "base_lot": self.base_lot,
            "trades": self.trades,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> RiskState:
        """Cria estado a partir de dicionário."""

        return cls(
            initial_equity=float(data.get("initial_equity", 0.0)),
            current_equity=float(data.get("current_equity", 0.0)),
            peak_equity=float(data.get("peak_equity", 0.0)),
            day_start_equity=float(data.get("day_start_equity", 0.0)),
            week_start_equity=float(data.get("week_start_equity", 0.0)),
            current_day=str(data.get("current_day", "")),
            current_week=str(data.get("current_week", "")),
            consecutive_losses=int(data.get("consecutive_losses", 0)),
            consecutive_wins=int(data.get("consecutive_wins", 0)),
            paused_until=str(data.get("paused_until", "")),
            current_lot=float(data.get("current_lot", 0.0)),
            base_lot=float(data.get("base_lot", 0.0)),
            trades=list(data.get("trades", [])),
        )


# ============================================================
# DECISION
# ============================================================


@dataclass
class RiskDecision:
    """
    Decisão de risco para uma operação.

    allow: True = pode operar, False = bloqueado
    reason: motivo do bloqueio (se houver)
    lot: lote recomendado
    """

    allow: bool
    reason: str = ""
    lot: float = 0.0
    risk_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""

        return {
            "allow": self.allow,
            "reason": self.reason,
            "lot": self.lot,
            "risk_pct": self.risk_pct,
        }


# ============================================================
# RISK MANAGER
# ============================================================


class RiskManager:
    """
    Gerenciador de risco central.

    Uso:

        config = RiskConfig()
        manager = RiskManager(config)

        manager.initialize(equity=10000.0, base_lot=0.10)

        decision = manager.evaluate_trade(
            symbol="XAUUSDc",
            signal="BUY",
            confidence=0.75,
        )

        if decision.allow:
            # executar operação com decision.lot
            pass

        manager.record_trade(
            symbol="XAUUSDc",
            signal="BUY",
            lot=decision.lot,
            pnl=+120.0,
        )
    """

    def __init__(
        self,
        config: RiskConfig | None = None,
    ) -> None:

        self.config = config if config is not None else RiskConfig()

        self.config.validate()

        self.state = RiskState()

        self._load_state()

    # ========================================================
    # INICIALIZAÇÃO
    # ========================================================

    def initialize(
        self,
        equity: float,
        base_lot: float,
    ) -> None:
        """
        Inicializa o gerenciador com equity e lote base.

        Deve ser chamado uma vez no início do dia.
        """

        if equity <= 0:
            raise ValueError("Equity deve ser maior que zero.")

        if base_lot <= 0:
            raise ValueError("Base lot deve ser maior que zero.")

        now = datetime.now()

        day_key = now.strftime("%Y-%m-%d")
        week_key = now.strftime("%Y-W%W")

        # ----------------------------------------------------
        # PRIMEIRA INICIALIZAÇÃO
        # ----------------------------------------------------

        if self.state.initial_equity <= 0:
            self.state.initial_equity = equity

        # ----------------------------------------------------
        # NOVO DIA
        # ----------------------------------------------------

        if self.state.current_day != day_key:
            self.state.current_day = day_key
            self.state.day_start_equity = equity

        # ----------------------------------------------------
        # NOVA SEMANA
        # ----------------------------------------------------

        if self.state.current_week != week_key:
            self.state.current_week = week_key
            self.state.week_start_equity = equity

        # ----------------------------------------------------
        # EQUITY
        # ----------------------------------------------------

        self.state.current_equity = equity

        self.state.peak_equity = max(self.state.peak_equity, equity)

        # ----------------------------------------------------
        # LOTE
        # ----------------------------------------------------

        self.state.base_lot = base_lot
        self.state.current_lot = base_lot

        self._save_state()

        logger.info(
            "RiskManager inicializado | " "equity=%.2f | base_lot=%.2f",
            equity,
            base_lot,
        )

    # ========================================================
    # AVALIAÇÃO DE OPERAÇÃO
    # ========================================================

    def evaluate_trade(
        self,
        symbol: str,
        signal: str,
        confidence: float,
    ) -> RiskDecision:
        """
        Avalia se uma operação pode ser executada.

        Verifica:
        1. Pausa ativa
        2. Daily Stop
        3. Weekly Stop
        4. Drawdown Stop
        5. Equity Protection
        6. Lote recomendado
        """

        # ----------------------------------------------------
        # PAUSA
        # ----------------------------------------------------

        if self.state.is_paused:

            return RiskDecision(
                allow=False,
                reason=(
                    "Pausa ativa após sequência negativa. "
                    f"Retoma em {self.state.paused_until}."
                ),
                lot=0.0,
                risk_pct=0.0,
            )

        # ----------------------------------------------------
        # DAILY STOP
        # ----------------------------------------------------

        if self.state.daily_pnl_pct <= -self.config.daily_stop_pct:

            return RiskDecision(
                allow=False,
                reason=(
                    f"Daily Stop atingido: "
                    f"{self.state.daily_pnl_pct * 100:.2f}% "
                    f"(limite: "
                    f"{self.config.daily_stop_pct * 100:.2f}%)"
                ),
                lot=0.0,
                risk_pct=0.0,
            )

        # ----------------------------------------------------
        # WEEKLY STOP
        # ----------------------------------------------------

        if self.state.weekly_pnl_pct <= -self.config.weekly_stop_pct:

            return RiskDecision(
                allow=False,
                reason=(
                    f"Weekly Stop atingido: "
                    f"{self.state.weekly_pnl_pct * 100:.2f}% "
                    f"(limite: "
                    f"{self.config.weekly_stop_pct * 100:.2f}%)"
                ),
                lot=0.0,
                risk_pct=0.0,
            )

        # ----------------------------------------------------
        # DRAWDOWN STOP
        # ----------------------------------------------------

        if self.state.drawdown_pct >= self.config.drawdown_stop_pct:

            return RiskDecision(
                allow=False,
                reason=(
                    f"Drawdown Stop atingido: "
                    f"{self.state.drawdown_pct * 100:.2f}% "
                    f"(limite: "
                    f"{self.config.drawdown_stop_pct * 100:.2f}%)"
                ),
                lot=0.0,
                risk_pct=0.0,
            )

        # ----------------------------------------------------
        # EQUITY PROTECTION
        # ----------------------------------------------------

        if self.state.total_pnl_pct <= -self.config.equity_protection_pct:

            return RiskDecision(
                allow=False,
                reason=(
                    f"Equity Protection ativada: "
                    f"{self.state.total_pnl_pct * 100:.2f}% "
                    f"(limite: "
                    f"{self.config.equity_protection_pct * 100:.2f}%)"
                ),
                lot=0.0,
                risk_pct=0.0,
            )

        # ----------------------------------------------------
        # LOTE RECOMENDADO
        # ----------------------------------------------------

        lot = self._calculate_lot(
            symbol=symbol,
            signal=signal,
            confidence=confidence,
        )

        return RiskDecision(
            allow=True,
            reason="Operação permitida.",
            lot=lot,
            risk_pct=self.config.risk_per_trade_pct,
        )

    # ========================================================
    # CÁLCULO DE LOTE
    # ========================================================

    def _calculate_lot(
        self,
        symbol: str,
        signal: str,
        confidence: float,
    ) -> float:
        """
        Calcula o lote recomendado.

        Fatores:
        1. Lote base
        2. Redução após perdas consecutivas
        3. Ajuste por confiança
        """

        lot = self.state.base_lot

        # ----------------------------------------------------
        # REDUÇÃO APÓS PERDAS
        # ----------------------------------------------------

        if self.config.lot_reduction_enabled:

            if self.state.consecutive_losses >= self.config.lot_reduction_after_losses:

                reduction_count = (
                    self.state.consecutive_losses
                    - self.config.lot_reduction_after_losses
                    + 1
                )

                lot *= self.config.lot_reduction_factor**reduction_count

        # ----------------------------------------------------
        # AJUSTE POR CONFIANÇA
        # ----------------------------------------------------

        # Confiança alta (>= 0.70) = lote cheio
        # Confiança média (0.55-0.70) = 75% do lote
        # Confiança baixa (< 0.55) = 50% do lote

        if confidence < 0.55:
            lot *= 0.50
        elif confidence < 0.70:
            lot *= 0.75

        # ----------------------------------------------------
        # LIMITES
        # ----------------------------------------------------

        lot = max(
            self.config.min_lot,
            min(
                lot,
                self.config.max_lot,
            ),
        )

        # Arredonda para 2 casas decimais
        lot = round(lot, 2)

        return lot

    # ========================================================
    # REGISTRO DE OPERAÇÃO
    # ========================================================

    def record_trade(
        self,
        symbol: str,
        signal: str,
        lot: float,
        pnl: float,
    ) -> None:
        """
        Registra o resultado de uma operação.

        Atualiza:
        - Equity
        - Sequência de perdas/ganhos
        - Pausa se necessário
        - Lote atual
        """

        # ----------------------------------------------------
        # ATUALIZA EQUITY
        # ----------------------------------------------------

        self.state.current_equity += pnl

        self.state.peak_equity = max(self.state.peak_equity, self.state.current_equity)

        # ----------------------------------------------------
        # SEQUÊNCIA
        # ----------------------------------------------------

        if pnl < 0:
            self.state.consecutive_losses += 1
            self.state.consecutive_wins = 0
        else:
            self.state.consecutive_wins += 1
            self.state.consecutive_losses = 0

        # ----------------------------------------------------
        # PAUSA APÓS SEQUÊNCIA NEGATIVA
        # ----------------------------------------------------

        if self.config.pause_enabled:

            if self.state.consecutive_losses >= self.config.pause_after_losses:

                pause_until = datetime.now() + timedelta(
                    hours=self.config.pause_duration_hours
                )

                self.state.paused_until = pause_until.isoformat()

                logger.warning(
                    "PAUSA ATIVADA | %d perdas consecutivas | " "retoma em %s",
                    self.state.consecutive_losses,
                    pause_until,
                )

        # ----------------------------------------------------
        # LOTE ATUAL
        # ----------------------------------------------------

        self.state.current_lot = lot

        # ----------------------------------------------------
        # HISTÓRICO
        # ----------------------------------------------------

        trade_record = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "signal": signal,
            "lot": lot,
            "pnl": pnl,
            "equity": self.state.current_equity,
        }

        self.state.trades.append(trade_record)

        # Mantém apenas os últimos 1000 trades
        if len(self.state.trades) > 1000:
            self.state.trades = self.state.trades[-1000:]

        self._save_state()

        logger.info(
            "Trade registrado | %s | %s | lot=%.2f | " "pnl=%.2f | equity=%.2f",
            symbol,
            signal,
            lot,
            pnl,
            self.state.current_equity,
        )

    # ========================================================
    # RESET DIÁRIO
    # ========================================================

    def reset_daily(
        self,
        equity: float,
    ) -> None:
        """
        Reseta o estado diário.

        Deve ser chamado no início de cada dia.
        """

        now = datetime.now()

        self.state.current_day = now.strftime("%Y-%m-%d")
        self.state.day_start_equity = equity
        self.state.current_equity = equity

        self._save_state()

        logger.info(
            "Reset diário | equity=%.2f",
            equity,
        )

    # ========================================================
    # RESET SEMANAL
    # ========================================================

    def reset_weekly(
        self,
        equity: float,
    ) -> None:
        """
        Reseta o estado semanal.

        Deve ser chamado no início de cada semana.
        """

        now = datetime.now()

        self.state.current_week = now.strftime("%Y-W%W")
        self.state.week_start_equity = equity
        self.state.current_equity = equity

        self._save_state()

        logger.info(
            "Reset semanal | equity=%.2f",
            equity,
        )

    # ========================================================
    # RESET COMPLETO
    # ========================================================

    def reset_all(
        self,
        equity: float,
    ) -> None:
        """
        Reseta todo o estado de risco.

        Deve ser chamado quando o usuário decidir
        recomeçar do zero.
        """

        self.state = RiskState()

        self.initialize(
            equity=equity,
            base_lot=self.state.base_lot if self.state.base_lot > 0 else 0.01,
        )

        logger.info(
            "Reset completo | equity=%.2f",
            equity,
        )

    # ========================================================
    # STATUS
    # ========================================================

    def status(self) -> dict[str, Any]:
        """
        Retorna o status atual do gerenciador de risco.
        """

        return {
            "equity": self.state.current_equity,
            "initial_equity": self.state.initial_equity,
            "peak_equity": self.state.peak_equity,
            "drawdown_pct": round(
                self.state.drawdown_pct * 100.0,
                4,
            ),
            "daily_pnl_pct": round(
                self.state.daily_pnl_pct * 100.0,
                4,
            ),
            "weekly_pnl_pct": round(
                self.state.weekly_pnl_pct * 100.0,
                4,
            ),
            "total_pnl_pct": round(
                self.state.total_pnl_pct * 100.0,
                4,
            ),
            "consecutive_losses": (self.state.consecutive_losses),
            "consecutive_wins": (self.state.consecutive_wins),
            "is_paused": self.state.is_paused,
            "paused_until": self.state.paused_until,
            "current_lot": self.state.current_lot,
            "base_lot": self.state.base_lot,
            "daily_stop_pct": round(
                self.config.daily_stop_pct * 100.0,
                4,
            ),
            "weekly_stop_pct": round(
                self.config.weekly_stop_pct * 100.0,
                4,
            ),
            "drawdown_stop_pct": round(
                self.config.drawdown_stop_pct * 100.0,
                4,
            ),
            "equity_protection_pct": round(
                self.config.equity_protection_pct * 100.0,
                4,
            ),
            "trades_count": len(self.state.trades),
        }

    # ========================================================
    # PERSISTÊNCIA
    # ========================================================

    def _state_path(self) -> Path:
        """Retorna o caminho do arquivo de estado."""

        if self.config.state_file is not None:
            return Path(self.config.state_file).expanduser()

        return Path(__file__).resolve().parent / "risk_state.json"

    def _save_state(self) -> None:
        """Salva o estado em JSON."""

        path = self._state_path()

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {
            "config": {
                "daily_stop_pct": self.config.daily_stop_pct,
                "weekly_stop_pct": self.config.weekly_stop_pct,
                "drawdown_stop_pct": self.config.drawdown_stop_pct,
                "equity_protection_pct": self.config.equity_protection_pct,
                "lot_reduction_enabled": self.config.lot_reduction_enabled,
                "lot_reduction_after_losses": self.config.lot_reduction_after_losses,
                "lot_reduction_factor": self.config.lot_reduction_factor,
                "pause_enabled": self.config.pause_enabled,
                "pause_after_losses": self.config.pause_after_losses,
                "pause_duration_hours": self.config.pause_duration_hours,
                "risk_per_trade_pct": self.config.risk_per_trade_pct,
                "max_lot": self.config.max_lot,
                "min_lot": self.config.min_lot,
            },
            "state": self.state.to_dict(),
        }

        path.write_text(
            json.dumps(
                payload,
                indent=4,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _load_state(self) -> None:
        """Carrega o estado de JSON se existir."""

        path = self._state_path()

        if not path.exists():
            return

        try:

            payload = json.loads(path.read_text(encoding="utf-8"))

            config_data = payload.get(
                "config",
                {},
            )

            # --------------------------------------------------
            # ATUALIZA CONFIG SE NECESSÁRIO
            # --------------------------------------------------

            for key, value in config_data.items():

                if hasattr(
                    self.config,
                    key,
                ):

                    setattr(
                        self.config,
                        key,
                        value,
                    )

            # --------------------------------------------------
            # CARREGA ESTADO
            # --------------------------------------------------

            state_data = payload.get(
                "state",
                {},
            )

            self.state = RiskState.from_dict(state_data)

            logger.info(
                "Estado de risco carregado: %s",
                path,
            )

        except Exception as exc:

            logger.warning(
                "Não foi possível carregar estado: %s",
                exc,
            )


# ============================================================
# TESTE
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print(" XAU_AI_PRO RISK MANAGER")
    print("=" * 70)
    print()

    config = RiskConfig()

    manager = RiskManager(config)

    manager.initialize(
        equity=10000.0,
        base_lot=0.10,
    )

    print("Status inicial:")
    print(manager.status())
    print()

    # --------------------------------------------------------
    # TESTE 1: OPERAÇÃO PERMITIDA
    # --------------------------------------------------------

    decision = manager.evaluate_trade(
        symbol="XAUUSDc",
        signal="BUY",
        confidence=0.75,
    )

    print("Decisão 1 (confiança alta):")
    print(decision.to_dict())
    print()

    # --------------------------------------------------------
    # TESTE 2: SEQUÊNCIA DE PERDAS
    # --------------------------------------------------------

    for i in range(4):

        manager.record_trade(
            symbol="XAUUSDc",
            signal="BUY",
            lot=0.10,
            pnl=-100.0,
        )

    print("Após 4 perdas consecutivas:")
    print(manager.status())
    print()

    # --------------------------------------------------------
    # TESTE 3: PAUSA ATIVA
    # --------------------------------------------------------

    decision = manager.evaluate_trade(
        symbol="XAUUSDc",
        signal="BUY",
        confidence=0.80,
    )

    print("Decisão durante pausa:")
    print(decision.to_dict())
    print()

    print("=" * 70)
