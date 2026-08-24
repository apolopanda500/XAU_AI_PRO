"""
XAU_AI_PRO — ETAPA 9.2: Forward Test em Conta Demo
Fase 9 — Testes Institucionais

Monitora o EA rodando em conta demo, lê audit_log.csv e
trade_history.csv do MT5, calcula métricas em tempo real
e compara performance demo vs backtest.

Uso:
    python Python/backtest/forward_test.py --monitor
    python Python/backtest/forward_test.py --report
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent

MT5_COMMON = Path("C:/Users/Micro/AppData/Roaming/MetaQuotes/Terminal/Common/Files")
REPORTS_DIR = PROJECT_ROOT / "Reports"

AUDIT_LOG_PATH = MT5_COMMON / "audit_log.csv"
TRADE_HISTORY_PATH = MT5_COMMON / "trade_history.csv"

sys.path.insert(0, str(BASE_DIR.parent))

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("XAU_AI_PRO.FORWARD")

# ============================================================
# CARREGA DADOS DE FORWARD TEST
# ============================================================


def load_audit_log() -> pd.DataFrame:
    """Carrega audit_log.csv do MT5."""

    if not AUDIT_LOG_PATH.exists():
        raise FileNotFoundError(
            f"Audit log não encontrado: {AUDIT_LOG_PATH}\n"
            "Execute o EA no MT5 para gerar logs de auditoria."
        )

    df = pd.read_csv(AUDIT_LOG_PATH)
    df.columns = [c.strip() for c in df.columns]

    if "Time" in df.columns:
        df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
        df = df.dropna(subset=["Time"])

    logger.info("Audit log carregado: %d entradas", len(df))
    return df


def load_trade_history() -> pd.DataFrame:
    """Carrega trade_history.csv do MT5."""

    if not TRADE_HISTORY_PATH.exists():
        raise FileNotFoundError(
            f"Trade history não encontrado: {TRADE_HISTORY_PATH}\n"
            "Execute o EA no MT5 para gerar histórico de trades."
        )

    df = pd.read_csv(TRADE_HISTORY_PATH)
    df.columns = [c.strip() for c in df.columns]

    if "Time" in df.columns:
        df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
        df = df.dropna(subset=["Time"])

    logger.info("Trade history carregado: %d trades", len(df))
    return df


# ============================================================
# CALCULA MÉTRICAS DE FORWARD TEST
# ============================================================


def calculate_forward_metrics(trades_df: pd.DataFrame) -> dict[str, Any]:
    """Calcula métricas em tempo real do forward test."""

    if trades_df.empty:
        return {"error": "Sem trades para analisar"}

    if "Profit" not in trades_df.columns:
        return {"error": "Coluna 'Profit' não encontrada"}

    profits = trades_df["Profit"].astype(float).to_numpy()

    total_trades = len(profits)
    wins = profits[profits > 0]
    losses = profits[profits < 0]

    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0.0
    total_profit = float(wins.sum())
    total_loss = float(abs(losses.sum()))

    profit_factor = total_profit / total_loss if total_loss > 0 else 999.0

    avg_win = float(wins.mean()) if len(wins) > 0 else 0.0
    avg_loss = float(abs(losses.mean())) if len(losses) > 0 else 0.0

    net_profit = float(profits.sum())

    # Drawdown
    cumulative = np.cumsum(profits)
    peak = np.maximum.accumulate(cumulative)
    drawdown = peak - cumulative
    max_dd = float(drawdown.max()) if len(drawdown) > 0 else 0.0

    # Equity curve
    equity_curve = cumulative.tolist()

    # Sequências
    win_streak = 0
    max_win_streak = 0
    loss_streak = 0
    max_loss_streak = 0

    for p in profits:
        if p > 0:
            win_streak += 1
            loss_streak = 0
            max_win_streak = max(win_streak, max_win_streak)
        elif p < 0:
            loss_streak += 1
            win_streak = 0
            max_loss_streak = max(loss_streak, max_loss_streak)

    return {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "net_profit": net_profit,
        "total_profit": total_profit,
        "total_loss": total_loss,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "max_drawdown": max_dd,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
        "current_win_streak": win_streak,
        "current_loss_streak": loss_streak,
        "equity_curve": equity_curve,
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# COMPARA FORWARD TEST COM BACKTEST
# ============================================================


def compare_with_backtest(
    forward: dict[str, Any],
    backtest_report: Path | None = None,
) -> dict[str, Any]:
    """Compara performance do forward test com backtest."""

    comparison = {
        "forward": forward,
        "backtest": None,
        "divergences": [],
    }

    if backtest_report and backtest_report.exists():
        with open(backtest_report, encoding="utf-8") as f:
            bt_data = json.load(f)

        if isinstance(bt_data, list) and len(bt_data) > 0:
            bt_result = bt_data[0].get("result", bt_data[0])
            comparison["backtest"] = bt_result

            bt_win_rate = bt_result.get("win_rate", 0) * 100
            fw_win_rate = forward.get("win_rate", 0)

            if abs(bt_win_rate - fw_win_rate) > 20:
                comparison["divergences"].append(
                    f"Win Rate divergente: BT={bt_win_rate:.1f}% FW={fw_win_rate:.1f}%"
                )

            bt_pf = bt_result.get("profit_factor", 0)
            fw_pf = forward.get("profit_factor", 0)

            if abs(bt_pf - fw_pf) > 0.5:
                comparison["divergences"].append(
                    f"Profit Factor divergente: BT={bt_pf:.2f} FW={fw_pf:.2f}"
                )

            bt_dd = bt_result.get("max_drawdown", 0)
            fw_dd = forward.get("max_drawdown", 0)

            if fw_dd > bt_dd * 1.5:
                comparison["divergences"].append(
                    f"Drawdown maior que backtest: BT={bt_dd:.2f} FW={fw_dd:.2f}"
                )

    return comparison


# ============================================================
# MONITOR FORWARD TEST EM TEMPO REAL
# ============================================================


def monitor_forward_test(interval: int = 60) -> None:
    """Monitora forward test em tempo real."""

    logger.info("Iniciando monitoramento (intervalo: %ds)", interval)
    logger.info("Pressione Ctrl+C para parar")

    try:
        while True:
            try:
                trades_df = load_trade_history()
                metrics = calculate_forward_metrics(trades_df)

                print()
                print("=" * 50)
                print(" FORWARD TEST — MÉTRICAS EM TEMPO REAL")
                print("=" * 50)
                print(f"  Trades: {metrics.get('total_trades', 0)}")
                print(f"  Win Rate: {metrics.get('win_rate', 0):.2f}%")
                print(f"  Profit Factor: {metrics.get('profit_factor', 0):.2f}")
                print(f"  Net Profit: {metrics.get('net_profit', 0):.2f}")
                print(f"  Max DD: {metrics.get('max_drawdown', 0):.2f}")
                print(f"  Win Streak: {metrics.get('current_win_streak', 0)}")
                print(f"  Loss Streak: {metrics.get('current_loss_streak', 0)}")
                print("=" * 50)

            except FileNotFoundError as exc:
                logger.warning("Aguardando dados: %s", exc)

            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("Monitoramento interrompido")


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="XAU_AI_PRO — Forward Test (Fase 9.2)",
    )

    parser.add_argument("--monitor", action="store_true", help="Monitora em tempo real")
    parser.add_argument("--report", action="store_true", help="Gera relatório único")
    parser.add_argument(
        "--compare",
        type=str,
        default=None,
        help="Relatório de backtest para comparação",
    )
    parser.add_argument("--interval", type=int, default=60, help="Intervalo (segundos)")

    args = parser.parse_args()

    if args.monitor:
        monitor_forward_test(args.interval)
        return

    try:
        trades_df = load_trade_history()
        metrics = calculate_forward_metrics(trades_df)

        if args.compare:
            bt_path = Path(args.compare)
            comparison = compare_with_backtest(metrics, bt_path)
            metrics["comparison"] = comparison

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = REPORTS_DIR / f"forward_test_{timestamp}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)

        print()
        print("=" * 50)
        print(" FORWARD TEST — RELATÓRIO")
        print("=" * 50)
        print(f"  Trades: {metrics.get('total_trades', 0)}")
        print(f"  Win Rate: {metrics.get('win_rate', 0):.2f}%")
        print(f"  Profit Factor: {metrics.get('profit_factor', 0):.2f}")
        print(f"  Net Profit: {metrics.get('net_profit', 0):.2f}")
        print(f"  Max DD: {metrics.get('max_drawdown', 0):.2f}")
        print("=" * 50)
        print(f"Relatório salvo: {filepath}")

        if args.compare and "comparison" in metrics:
            divergences = metrics["comparison"].get("divergences", [])
            if divergences:
                print()
                print("DIVERGÊNCIAS DETECTADAS:")
                for div in divergences:
                    print(f"  ⚠ {div}")
            else:
                print()
                print("✓ Performance consistente com backtest")

    except Exception as exc:
        logger.error("Erro: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
