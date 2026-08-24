"""
XAU_AI_PRO — ETAPA 9.1: Script de Backtest Automatizado
Fase 9 — Testes Institucionais

Executa backtest de longa duração sobre dataset.csv histórico,
calcula métricas profissionais e salva relatório em JSON.

Uso:
    python Python/backtest/run_backtest.py --symbol XAUUSDc --period 1Y
    python Python/backtest/run_backtest.py --symbol ALL --period 6M
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent

sys.path.insert(0, str(BASE_DIR.parent))

from backtest.backtest_engine import (  # type: ignore[reportMissingImports]
    BacktestConfig,
    BacktestEngine,
)

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("XAU_AI_PRO.BACKTEST_RUN")

# ============================================================
# DATASET PATH
# ============================================================

DATASET_PATH = PROJECT_ROOT / "MQL5" / "Files" / "Data" / "dataset.csv"
REPORTS_DIR = PROJECT_ROOT / "Reports"


# ============================================================
# CARREGA DATASET
# ============================================================


def load_dataset(symbol: str | None = None) -> pd.DataFrame:
    """Carrega dataset.csv e filtra por símbolo se especificado."""

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset não encontrado: {DATASET_PATH}\n"
            "Execute o EA no MT5 para gerar o dataset primeiro."
        )

    logger.info("Carregando dataset: %s", DATASET_PATH)

    df = pd.read_csv(DATASET_PATH)

    # Normaliza colunas
    df.columns = [col.strip() for col in df.columns]

    # Converte Time
    if "Time" in df.columns:
        df["Time"] = pd.to_datetime(df["Time"], errors="coerce")

    # Remove linhas inválidas
    df = df.dropna(subset=["Time"])

    # Filtra por símbolo
    if symbol and symbol.upper() != "ALL":
        if "Symbol" in df.columns:
            mask = (
                df["Symbol"].astype(str).str.strip().str.upper()
                == symbol.strip().upper()
            )
            df = df[mask].copy()

    logger.info("Dataset carregado: %d linhas", len(df))

    return df


# ============================================================
# FILTRA POR PERÍODO
# ============================================================


def filter_by_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """Filtra DataFrame por período (1M, 3M, 6M, 1Y, ALL)."""

    if period.upper() == "ALL":
        return df

    if "Time" not in df.columns:
        return df

    now = df["Time"].max()

    period_map = {
        "1M": timedelta(days=30),
        "3M": timedelta(days=90),
        "6M": timedelta(days=180),
        "1Y": timedelta(days=365),
        "2Y": timedelta(days=730),
    }

    delta = period_map.get(period.upper())

    if delta is None:
        raise ValueError(f"Período inválido: {period}. Use: 1M, 3M, 6M, 1Y, 2Y, ALL")

    cutoff = now - delta
    filtered = df[df["Time"] >= cutoff].copy()

    logger.info("Filtrado por período %s: %d linhas", period, len(filtered))

    return filtered


# ============================================================
# EXECUTA BACKTEST PARA UM SÍMBOLO
# ============================================================


def run_backtest_for_symbol(
    df: pd.DataFrame,
    symbol: str,
    config: BacktestConfig | None = None,
) -> dict[str, Any]:
    """Executa backtest para um símbolo específico."""

    if config is None:
        config = BacktestConfig()

    engine = BacktestEngine(config)

    logger.info("Executando backtest para %s...", symbol)

    try:
        result = engine.run(df=df, symbol=symbol)
        report = result.report()
        print(report)

        return {
            "symbol": symbol,
            "result": result.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error("Erro no backtest de %s: %s", symbol, exc)
        return {
            "symbol": symbol,
            "error": str(exc),
            "timestamp": datetime.now().isoformat(),
        }


# ============================================================
# SALVA RELATÓRIO
# ============================================================


def save_report(results: list[dict[str, Any]], output_dir: Path | None = None) -> Path:
    """Salva resultados do backtest em JSON."""

    if output_dir is None:
        output_dir = REPORTS_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backtest_{timestamp}.json"
    filepath = output_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    logger.info("Relatório salvo: %s", filepath)

    return filepath


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    """Entry point do script de backtest automatizado."""

    parser = argparse.ArgumentParser(
        description="XAU_AI_PRO — Backtest Automatizado (Fase 9.1)",
    )

    parser.add_argument(
        "--symbol",
        type=str,
        default="ALL",
        help="Símbolo para testar (ex: XAUUSDc, BTCUSDc) ou ALL para todos",
    )

    parser.add_argument(
        "--period",
        type=str,
        default="1Y",
        help="Período: 1M, 3M, 6M, 1Y, 2Y, ALL",
    )

    parser.add_argument(
        "--capital",
        type=float,
        default=10000.0,
        help="Capital inicial (default: 10000)",
    )

    parser.add_argument(
        "--lot",
        type=float,
        default=0.10,
        help="Lote base (default: 0.10)",
    )

    parser.add_argument(
        "--commission",
        type=float,
        default=0.0,
        help="Comissão por lote (default: 0.0)",
    )

    parser.add_argument(
        "--slippage",
        type=float,
        default=0.0,
        help="Slippage em %% (default: 0.0)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Diretório de saída (default: Reports/)",
    )

    args = parser.parse_args()

    # ============================================================
    # CONFIGURA BACKTEST
    # ============================================================

    config = BacktestConfig(
        initial_capital=args.capital,
        base_lot=args.lot,
        commission_per_lot=args.commission,
        slippage_pct=args.slippage,
    )

    config.validate()

    logger.info("=" * 60)
    logger.info(" XAU_AI_PRO — BACKTEST AUTOMATIZADO (Fase 9.1)")
    logger.info("=" * 60)
    logger.info("Símbolo: %s", args.symbol)
    logger.info("Período: %s", args.period)
    logger.info("Capital: %.2f", args.capital)
    logger.info("Lote: %.2f", args.lot)
    logger.info("=" * 60)

    # ============================================================
    # CARREGA E FILTRA DADOS
    # ============================================================

    df = load_dataset(args.symbol)
    df = filter_by_period(df, args.period)

    if df.empty:
        logger.error("Dataset vazio após filtro. Nada para testar.")
        sys.exit(1)

    # ============================================================
    # DETERMINA SÍMBOLOS PARA TESTAR
    # ============================================================

    if args.symbol.upper() == "ALL":
        symbols = (
            df["Symbol"].unique().tolist() if "Symbol" in df.columns else [args.symbol]
        )
    else:
        symbols = [args.symbol]

    logger.info("Símbolos para testar: %s", symbols)

    # ============================================================
    # EXECUTA BACKTEST
    # ============================================================

    results: list[dict[str, Any]] = []

    for symbol in symbols:
        result = run_backtest_for_symbol(df, symbol.strip(), config)
        results.append(result)

    # ============================================================
    # SALVA RELATÓRIO
    # ============================================================

    output_dir = Path(args.output) if args.output else None
    report_path = save_report(results, output_dir)

    # ============================================================
    # RESUMO FINAL
    # ============================================================

    print()
    print("=" * 60)
    print(" RESUMO DO BACKTEST")
    print("=" * 60)

    for result in results:
        symbol = result["symbol"]

        if "error" in result:
            print(f"  {symbol}: ERRO — {result['error']}")
            continue

        metrics = result["result"]
        print(f"  {symbol}:")
        print(f"    Trades: {metrics['total_trades']}")
        print(f"    Win Rate: {metrics['win_rate'] * 100:.2f}%")
        print(f"    Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"    Net Profit: {metrics['net_profit']:.2f}")
        print(
            f"    Max DD: {metrics['max_drawdown']:.2f} ({metrics['max_drawdown_pct'] * 100:.2f}%)"
        )
        print(f"    Sharpe: {metrics['sharpe_ratio']:.2f}")
        print(f"    SQN: {metrics['sqn']:.2f}")
        print()

    print(f"Relatório completo: {report_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
