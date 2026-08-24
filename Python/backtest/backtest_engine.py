"""
XAU_AI_PRO - Backtest Engine
V1.0

Responsabilidades:
- Executar backtest sério sobre dados históricos
- Calcular métricas profissionais:
  - Profit Factor
  - Expectancy
  - Win Rate
  - Average Win
  - Average Loss
  - Drawdown
  - Recovery Factor
  - Sharpe Ratio
  - SQN (System Quality Number)
- Gerar relatório completo
- Salvar resultados em JSON
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("XAU_AI_PRO.BACKTEST")


# ============================================================
# CONFIG
# ============================================================


@dataclass
class BacktestConfig:
    """
    Configuração do backtest.

    Valores padrão:
    - Capital inicial: 10.000
    - Risco por operação: 1%
    - Lote base: 0.10
    - Sem custos de corretagem
    """

    initial_capital: float = 10000.0
    risk_per_trade_pct: float = 0.01
    base_lot: float = 0.10
    commission_per_lot: float = 0.0
    slippage_pct: float = 0.0

    # --------------------------------------------------------
    # VALIDAÇÃO
    # --------------------------------------------------------

    def validate(self) -> None:
        """Valida os valores da configuração."""

        if self.initial_capital <= 0:
            raise ValueError("initial_capital deve ser > 0.")

        if not 0.0 < self.risk_per_trade_pct < 1.0:
            raise ValueError("risk_per_trade_pct deve estar entre 0 e 1.")

        if self.base_lot <= 0:
            raise ValueError("base_lot deve ser > 0.")

        if self.commission_per_lot < 0:
            raise ValueError("commission_per_lot deve ser >= 0.")

        if self.slippage_pct < 0:
            raise ValueError("slippage_pct deve ser >= 0.")


# ============================================================
# RESULT
# ============================================================


@dataclass
class BacktestResult:
    """
    Resultado completo do backtest.

    Contém todas as métricas profissionais.
    """

    # --------------------------------------------------------
    # BÁSICO
    # --------------------------------------------------------

    symbol: str = ""
    initial_capital: float = 0.0
    final_capital: float = 0.0
    net_profit: float = 0.0
    total_trades: int = 0

    # --------------------------------------------------------
    # MÉTRICAS DE RENTABILIDADE
    # --------------------------------------------------------

    profit_factor: float = 0.0
    expectancy: float = 0.0
    win_rate: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    recovery_factor: float = 0.0
    sharpe_ratio: float = 0.0
    sqn: float = 0.0

    # --------------------------------------------------------
    # DETALHES
    # --------------------------------------------------------

    total_wins: int = 0
    total_losses: int = 0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_trade_duration: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0

    # --------------------------------------------------------
    # SÉRIES
    # --------------------------------------------------------

    equity_curve: list[float] = field(default_factory=list)
    drawdown_curve: list[float] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)

    # --------------------------------------------------------
    # SERIALIZAÇÃO
    # --------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""

        return {
            "symbol": self.symbol,
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "net_profit": self.net_profit,
            "total_trades": self.total_trades,
            "profit_factor": self.profit_factor,
            "expectancy": self.expectancy,
            "win_rate": self.win_rate,
            "average_win": self.average_win,
            "average_loss": self.average_loss,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "recovery_factor": self.recovery_factor,
            "sharpe_ratio": self.sharpe_ratio,
            "sqn": self.sqn,
            "total_wins": self.total_wins,
            "total_losses": self.total_losses,
            "gross_profit": self.gross_profit,
            "gross_loss": self.gross_loss,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss,
            "avg_trade_duration": self.avg_trade_duration,
            "best_trade": self.best_trade,
            "worst_trade": self.worst_trade,
            "equity_curve": self.equity_curve,
            "drawdown_curve": self.drawdown_curve,
            "trades": self.trades,
        }

    # --------------------------------------------------------
    # RELATÓRIO
    # --------------------------------------------------------

    def report(self) -> str:
        """Gera relatório formatado."""

        lines = [
            "=" * 70,
            f" BACKTEST REPORT - {self.symbol}",
            "=" * 70,
            "",
            f"Capital inicial : {self.initial_capital:,.2f}",
            f"Capital final   : {self.final_capital:,.2f}",
            f"Lucro líquido   : {self.net_profit:,.2f}",
            f"Total de trades : {self.total_trades}",
            "",
            "--- Métricas de Rentabilidade ---",
            f"Profit Factor   : {self.profit_factor:.4f}",
            f"Expectancy      : {self.expectancy:.4f}",
            f"Win Rate        : {self.win_rate * 100:.2f}%",
            f"Average Win     : {self.average_win:.2f}",
            f"Average Loss    : {self.average_loss:.2f}",
            f"Max Drawdown    : {self.max_drawdown:,.2f} "
            f"({self.max_drawdown_pct * 100:.2f}%)",
            f"Recovery Factor : {self.recovery_factor:.4f}",
            f"Sharpe Ratio    : {self.sharpe_ratio:.4f}",
            f"SQN             : {self.sqn:.4f}",
            "",
            "--- Detalhes ---",
            f"Total wins      : {self.total_wins}",
            f"Total losses    : {self.total_losses}",
            f"Gross profit    : {self.gross_profit:,.2f}",
            f"Gross loss      : {self.gross_loss:,.2f}",
            f"Largest win     : {self.largest_win:.2f}",
            f"Largest loss    : {self.largest_loss:.2f}",
            f"Best trade      : {self.best_trade:.2f}",
            f"Worst trade     : {self.worst_trade:.2f}",
            "=" * 70,
        ]

        return "\n".join(lines)


# ============================================================
# BACKTEST ENGINE
# ============================================================


class BacktestEngine:
    """
    Motor de backtest sério.

    Uso:

        config = BacktestConfig()
        engine = BacktestEngine(config)

        result = engine.run(
            df=df,
            symbol="XAUUSDc",
            signals=signals_df,
        )

        print(result.report())
    """

    def __init__(
        self,
        config: BacktestConfig | None = None,
    ) -> None:

        self.config = config if config is not None else BacktestConfig()

        self.config.validate()

    # ========================================================
    # RUN
    # ========================================================

    def run(
        self,
        df: pd.DataFrame,
        symbol: str,
        signals: pd.DataFrame | None = None,
    ) -> BacktestResult:
        """
        Executa o backtest.

        df: DataFrame com colunas Time, Open, High, Low, Close,
            Volume, Spread, ATR, ADX, RSI
        symbol: símbolo a testar
        signals: DataFrame opcional com colunas
            Time, Signal (BUY/SELL/HOLD), Confidence
        """

        # ----------------------------------------------------
        # FILTRA SÍMBOLO
        # ----------------------------------------------------

        symbol_df = df[
            df["Symbol"].astype(str).str.strip().str.upper() == symbol.strip().upper()
        ].copy()

        if symbol_df.empty:
            raise ValueError(f"Nenhum dado encontrado para {symbol}.")

        symbol_df.sort_values(
            "Time",
            inplace=True,
        )

        symbol_df.reset_index(
            drop=True,
            inplace=True,
        )

        # ----------------------------------------------------
        # SE NÃO HOUVER SINAIS, GERA SINAIS SIMPLES
        # ----------------------------------------------------

        if signals is None:

            signals = self._generate_signals(symbol_df)

        # ----------------------------------------------------
        # EXECUTA TRADES
        # ----------------------------------------------------

        trades = self._execute_trades(
            symbol_df,
            signals,
        )

        # ----------------------------------------------------
        # CALCULA MÉTRICAS
        # ----------------------------------------------------

        result = self._calculate_metrics(
            symbol=symbol,
            trades=trades,
        )

        return result

    # ========================================================
    # GERA SINAIS SIMPLES
    # ========================================================

    def _generate_signals(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Gera sinais simples baseados em RSI e ADX.

        BUY: RSI < 30 e ADX > 20
        SELL: RSI > 70 e ADX > 20
        HOLD: caso contrário
        """

        signals = pd.DataFrame(
            {
                "Time": df["Time"],
                "Signal": "HOLD",
                "Confidence": 0.0,
            }
        )

        buy_mask = (df["RSI"] < 30) & (df["ADX"] > 20)

        sell_mask = (df["RSI"] > 70) & (df["ADX"] > 20)

        signals.loc[
            buy_mask,
            "Signal",
        ] = "BUY"

        signals.loc[
            buy_mask,
            "Confidence",
        ] = 0.70

        signals.loc[
            sell_mask,
            "Signal",
        ] = "SELL"

        signals.loc[
            sell_mask,
            "Confidence",
        ] = 0.70

        return signals

    # ========================================================
    # EXECUTA TRADES
    # ========================================================

    def _execute_trades(
        self,
        df: pd.DataFrame,
        signals: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        """
        Executa trades com base nos sinais.

        Estratégia:
        - Entra no sinal BUY/SELL
        - Sai no próximo sinal oposto ou HOLD
        - Calcula P&L com base na variação de preço
        """

        trades: list[dict[str, Any]] = []

        # ----------------------------------------------------
        # MERGE SINAIS COM DADOS
        # ----------------------------------------------------

        merged = df.merge(
            signals,
            on="Time",
            how="inner",
        )

        if merged.empty:
            return trades

        # ----------------------------------------------------
        # EXECUTA
        # ----------------------------------------------------

        position: str | None = None
        entry_price: float = 0.0
        entry_time: pd.Timestamp | None = None
        entry_lot: float = 0.0

        for index, row in merged.iterrows():

            signal = str(row.get("Signal", "HOLD")).strip().upper()

            price = float(row["Close"])
            timestamp = row["Time"]

            # --------------------------------------------------
            # ABRE POSIÇÃO
            # --------------------------------------------------

            if position is None and signal in ("BUY", "SELL"):

                position = signal
                entry_price = price
                entry_time = timestamp
                entry_lot = self.config.base_lot

                continue

            # --------------------------------------------------
            # FECHA POSIÇÃO
            # --------------------------------------------------

            if position is not None:

                if signal == "HOLD":
                    continue

                if signal == position:
                    continue

                # ----------------------------------------------
                # CALCULA P&L
                # ----------------------------------------------

                if position == "BUY":

                    pnl = (price - entry_price) / entry_price * entry_lot * 100000.0

                else:  # SELL

                    pnl = (entry_price - price) / entry_price * entry_lot * 100000.0

                # ----------------------------------------------
                # CUSTOS
                # ----------------------------------------------

                commission = self.config.commission_per_lot * entry_lot

                slippage = price * self.config.slippage_pct / 100.0 * entry_lot

                pnl -= commission
                pnl -= slippage

                # ----------------------------------------------
                # REGISTRA TRADE
                # ----------------------------------------------

                trades.append(
                    {
                        "entry_time": (
                            entry_time.isoformat() if entry_time is not None else ""
                        ),
                        "exit_time": (timestamp.isoformat()),
                        "signal": position,
                        "entry_price": entry_price,
                        "exit_price": price,
                        "lot": entry_lot,
                        "pnl": pnl,
                    }
                )

                # ----------------------------------------------
                # NOVA POSIÇÃO
                # ----------------------------------------------

                position = signal
                entry_price = price
                entry_time = timestamp
                entry_lot = self.config.base_lot

        # ----------------------------------------------------
        # FECHA POSIÇÃO ABERTA NO FINAL
        # ----------------------------------------------------

        if position is not None and not merged.empty:

            last_row = merged.iloc[-1]

            price = float(last_row["Close"])
            timestamp = last_row["Time"]

            if position == "BUY":

                pnl = (price - entry_price) / entry_price * entry_lot * 100000.0

            else:

                pnl = (entry_price - price) / entry_price * entry_lot * 100000.0

            commission = self.config.commission_per_lot * entry_lot

            pnl -= commission

            trades.append(
                {
                    "entry_time": (
                        entry_time.isoformat() if entry_time is not None else ""
                    ),
                    "exit_time": (timestamp.isoformat()),
                    "signal": position,
                    "entry_price": entry_price,
                    "exit_price": price,
                    "lot": entry_lot,
                    "pnl": pnl,
                }
            )

        return trades

    # ========================================================
    # CALCULA MÉTRICAS
    # ========================================================

    def _calculate_metrics(
        self,
        symbol: str,
        trades: list[dict[str, Any]],
    ) -> BacktestResult:
        """
        Calcula todas as métricas profissionais.
        """

        result = BacktestResult(
            symbol=symbol,
            initial_capital=self.config.initial_capital,
        )

        if not trades:

            result.final_capital = self.config.initial_capital
            result.net_profit = 0.0
            result.equity_curve = [self.config.initial_capital]
            result.drawdown_curve = [0.0]

            return result

        # ----------------------------------------------------
        # P&L
        # ----------------------------------------------------

        pnls = np.array([trade["pnl"] for trade in trades])

        result.total_trades = len(trades)
        result.trades = trades

        result.net_profit = float(pnls.sum())

        result.final_capital = self.config.initial_capital + result.net_profit

        # ----------------------------------------------------
        # WINS / LOSSES
        # ----------------------------------------------------

        wins = pnls[pnls > 0]
        losses = pnls[pnls < 0]

        result.total_wins = len(wins)
        result.total_losses = len(losses)

        result.gross_profit = float(wins.sum())

        result.gross_loss = float(abs(losses.sum()))

        # ----------------------------------------------------
        # WIN RATE
        # ----------------------------------------------------

        result.win_rate = (
            result.total_wins / result.total_trades if result.total_trades > 0 else 0.0
        )

        # ----------------------------------------------------
        # AVERAGE WIN / LOSS
        # ----------------------------------------------------

        result.average_win = float(wins.mean()) if len(wins) > 0 else 0.0

        result.average_loss = float(losses.mean()) if len(losses) > 0 else 0.0

        # ----------------------------------------------------
        # PROFIT FACTOR
        # ----------------------------------------------------

        result.profit_factor = (
            result.gross_profit / result.gross_loss
            if result.gross_loss > 0
            else (float("inf") if result.gross_profit > 0 else 0.0)
        )

        # ----------------------------------------------------
        # EXPECTANCY
        # ----------------------------------------------------

        result.expectancy = (
            result.net_profit / result.total_trades if result.total_trades > 0 else 0.0
        )

        # ----------------------------------------------------
        # LARGEST WIN / LOSS
        # ----------------------------------------------------

        result.largest_win = float(wins.max()) if len(wins) > 0 else 0.0

        result.largest_loss = float(losses.min()) if len(losses) > 0 else 0.0

        result.best_trade = float(pnls.max())

        result.worst_trade = float(pnls.min())

        # ----------------------------------------------------
        # EQUITY CURVE
        # ----------------------------------------------------

        equity = self.config.initial_capital

        equity_curve = [equity]

        for pnl in pnls:

            equity += pnl
            equity_curve.append(float(equity))

        result.equity_curve = equity_curve

        # ----------------------------------------------------
        # DRAWDOWN
        # ----------------------------------------------------

        peak = self.config.initial_capital

        drawdown_curve = [0.0]

        max_drawdown = 0.0
        max_drawdown_pct = 0.0

        for equity_value in equity_curve:

            peak = max(peak, equity_value)

            drawdown = peak - equity_value
            drawdown_pct = drawdown / peak if peak > 0 else 0.0

            drawdown_curve.append(float(drawdown_pct))

            max_drawdown = max(max_drawdown, drawdown)

            max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)

        result.drawdown_curve = drawdown_curve
        result.max_drawdown = max_drawdown
        result.max_drawdown_pct = max_drawdown_pct

        # ----------------------------------------------------
        # RECOVERY FACTOR
        # ----------------------------------------------------

        result.recovery_factor = (
            result.net_profit / max_drawdown
            if max_drawdown > 0
            else (float("inf") if result.net_profit > 0 else 0.0)
        )

        # ----------------------------------------------------
        # SHARPE RATIO
        # ----------------------------------------------------

        returns = np.diff(equity_curve) / np.array(equity_curve[:-1])

        if len(returns) > 1:

            std_returns = float(np.std(returns))

            if std_returns > 0:

                result.sharpe_ratio = (
                    float(np.mean(returns)) / std_returns * np.sqrt(252.0)
                )

        # ----------------------------------------------------
        # SQN (SYSTEM QUALITY NUMBER)
        # ----------------------------------------------------

        if result.total_trades > 1:

            std_pnls = float(np.std(pnls))

            if std_pnls > 0:

                result.sqn = result.expectancy / std_pnls * np.sqrt(result.total_trades)

        return result

    # ========================================================
    # SALVAR RESULTADO
    # ========================================================

    def save_result(
        self,
        result: BacktestResult,
        output_path: str | Path,
    ) -> Path:
        """
        Salva o resultado do backtest em JSON.
        """

        path = Path(output_path).expanduser()

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            json.dumps(
                result.to_dict(),
                indent=4,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        logger.info(
            "Backtest salvo: %s",
            path,
        )

        return path


# ============================================================
# TESTE
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print(" XAU_AI_PRO BACKTEST ENGINE")
    print("=" * 70)
    print()

    # --------------------------------------------------------
    # CRIA DADOS SINTÉTICOS
    # --------------------------------------------------------

    np.random.seed(42)

    n = 500

    dates = pd.date_range(
        start="2026-01-01",
        periods=n,
        freq="1h",
    )

    close = 4000.0 + np.cumsum(
        np.random.normal(
            0,
            5,
            n,
        )
    )

    df = pd.DataFrame(
        {
            "Time": dates,
            "Symbol": "XAUUSDc",
            "Open": close - 1.0,
            "High": close + 5.0,
            "Low": close - 5.0,
            "Close": close,
            "Volume": np.random.randint(
                1000,
                5000,
                n,
            ),
            "Spread": np.random.uniform(
                20,
                50,
                n,
            ),
            "ATR": np.random.uniform(
                5,
                15,
                n,
            ),
            "ADX": np.random.uniform(
                15,
                40,
                n,
            ),
            "RSI": np.random.uniform(
                20,
                80,
                n,
            ),
        }
    )

    # --------------------------------------------------------
    # EXECUTA BACKTEST
    # --------------------------------------------------------

    config = BacktestConfig()

    engine = BacktestEngine(config)

    result = engine.run(
        df=df,
        symbol="XAUUSDc",
    )

    print(result.report())
    print()

    print("=" * 70)
