"""
XAU_AI_PRO — ETAPA 9.3: Testes de Estresse
Fase 9 — Testes Institucionais

Simula cenários adversos para verificar robustez:
- Spread 3x maior que normal
- Gaps de preço (5%, 10%, 20%)
- Desconexão de broker (sem tick por 60s, 300s, 600s)
- Slippage elevado
- Volatilidade extrema

Uso:
    python Python/backtest/stress_test.py --scenario all
    python Python/backtest/stress_test.py --scenario spread
    python Python/backtest/stress_test.py --scenario gap
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent

sys.path.insert(0, str(BASE_DIR.parent))

from backtest.backtest_engine import (  # type: ignore[reportMissingImports]
    BacktestConfig,
    BacktestEngine,
)
from backtest.run_backtest import (  # type: ignore[reportMissingImports]
    filter_by_period,
    load_dataset,
)

DATASET_PATH = PROJECT_ROOT / "MQL5" / "Files" / "Data" / "dataset.csv"
REPORTS_DIR = PROJECT_ROOT / "Reports"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("XAU_AI_PRO.STRESS")


# ============================================================
# CENÁRIO: SPREAD ELEVADO
# ============================================================


def stress_spread(df: pd.DataFrame, multiplier: float = 3.0) -> pd.DataFrame:
    """Aumenta o spread em N vezes."""

    df_stress = df.copy()

    if "Spread" in df_stress.columns:
        df_stress["Spread"] = df_stress["Spread"] * multiplier

    logger.info("Cenário SPREAD: spread multiplicado por %.1fx", multiplier)
    return df_stress


# ============================================================
# CENÁRIO: GAP DE PREÇO
# ============================================================


def stress_gap(df: pd.DataFrame, gap_pct: float = 5.0) -> pd.DataFrame:
    """Aplica um gap de preço em um ponto aleatório."""

    df_stress = df.copy()

    if "Close" in df_stress.columns and len(df_stress) > 10:
        gap_idx = len(df_stress) // 2
        gap_factor = 1.0 + gap_pct / 100.0

        df_stress.loc[df_stress.index[gap_idx:], "Close"] *= gap_factor

        if "High" in df_stress.columns:
            df_stress.loc[df_stress.index[gap_idx:], "High"] *= gap_factor

        if "Low" in df_stress.columns:
            df_stress.loc[df_stress.index[gap_idx:], "Low"] *= gap_factor

        if "Open" in df_stress.columns:
            df_stress.loc[df_stress.index[gap_idx:], "Open"] *= gap_factor

    logger.info("Cenário GAP: %.1f%% aplicado no meio do dataset", gap_pct)
    return df_stress


# ============================================================
# CENÁRIO: SLIPPAGE ELEVADO
# ============================================================


def stress_slippage(df: pd.DataFrame, slippage_pct: float = 0.5) -> pd.DataFrame:
    """Adiciona slippage aleatório aos preços."""

    df_stress = df.copy()

    if "Close" in df_stress.columns:
        np.random.seed(42)
        slippage = (
            np.random.uniform(-slippage_pct, slippage_pct, len(df_stress)) / 100.0
        )
        df_stress["Close"] = df_stress["Close"] * (1.0 + slippage)

    logger.info("Cenário SLIPPAGE: ±%.2f%% aleatório", slippage_pct)
    return df_stress


# ============================================================
# CENÁRIO: VOLATILIDADE EXTREMA
# ============================================================


def stress_volatility(df: pd.DataFrame, multiplier: float = 2.0) -> pd.DataFrame:
    """Aumenta a volatilidade multiplicando ATR."""

    df_stress = df.copy()

    if "ATR" in df_stress.columns:
        df_stress["ATR"] = df_stress["ATR"] * multiplier

    logger.info("Cenário VOLATILIDADE: ATR multiplicado por %.1fx", multiplier)
    return df_stress


# ============================================================
# CENÁRIO: DESCONEXÃO (sem dados por período)
# ============================================================


def stress_disconnection(df: pd.DataFrame, remove_pct: float = 10.0) -> pd.DataFrame:
    """Remove uma porção dos dados para simular desconexão."""

    df_stress = df.copy()

    if len(df_stress) > 20:
        remove_count = int(len(df_stress) * remove_pct / 100.0)
        start_idx = len(df_stress) // 3
        df_stress = df_stress.drop(
            df_stress.index[start_idx : start_idx + remove_count]
        )
        df_stress = df_stress.reset_index(drop=True)

    logger.info("Cenário DESCONEXÃO: %.1f%% dos dados removidos", remove_pct)
    return df_stress


# ============================================================
# EXECUTA CENÁRIO DE ESTRESSE
# ============================================================


def run_stress_scenario(
    df: pd.DataFrame,
    symbol: str,
    scenario_name: str,
    stress_fn,
    config: BacktestConfig | None = None,
) -> dict[str, Any]:
    """Executa um cenário de estresse específico."""

    if config is None:
        config = BacktestConfig()

    engine = BacktestEngine(config)

    df_stress = stress_fn(df)

    try:
        result = engine.run(df=df_stress, symbol=symbol)

        return {
            "scenario": scenario_name,
            "symbol": symbol,
            "result": result.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.error("Erro no cenário %s: %s", scenario_name, exc)
        return {
            "scenario": scenario_name,
            "symbol": symbol,
            "error": str(exc),
            "timestamp": datetime.now().isoformat(),
        }


# ============================================================
# DEFINE CENÁRIOS
# ============================================================


def get_scenarios() -> dict[str, Any]:
    """Retorna dicionário de cenários de estresse."""

    return {
        "spread_3x": ("Spread 3x", lambda df: stress_spread(df, 3.0)),
        "spread_5x": ("Spread 5x", lambda df: stress_spread(df, 5.0)),
        "gap_5pct": ("Gap 5%", lambda df: stress_gap(df, 5.0)),
        "gap_10pct": ("Gap 10%", lambda df: stress_gap(df, 10.0)),
        "gap_20pct": ("Gap 20%", lambda df: stress_gap(df, 20.0)),
        "slippage_05": ("Slippage 0.5%", lambda df: stress_slippage(df, 0.5)),
        "slippage_1": ("Slippage 1.0%", lambda df: stress_slippage(df, 1.0)),
        "volatility_2x": ("Volatilidade 2x", lambda df: stress_volatility(df, 2.0)),
        "volatility_3x": ("Volatilidade 3x", lambda df: stress_volatility(df, 3.0)),
        "disconnect_10": ("Desconexão 10%", lambda df: stress_disconnection(df, 10.0)),
        "disconnect_20": ("Desconexão 20%", lambda df: stress_disconnection(df, 20.0)),
    }


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="XAU_AI_PRO — Testes de Estresse (Fase 9.3)",
    )

    parser.add_argument(
        "--scenario",
        type=str,
        default="all",
        help="Cenário: all, spread, gap, slippage, volatility, disconnect",
    )

    parser.add_argument(
        "--symbol",
        type=str,
        default="ALL",
        help="Símbolo para testar",
    )

    parser.add_argument(
        "--period",
        type=str,
        default="1Y",
        help="Período dos dados",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info(" XAU_AI_PRO — TESTES DE ESTRESSE (Fase 9.3)")
    logger.info("=" * 60)

    # Carrega dados
    df = load_dataset(args.symbol)
    df = filter_by_period(df, args.period)

    if df.empty:
        logger.error("Dataset vazio. Nada para testar.")
        sys.exit(1)

    # Determina símbolos
    if args.symbol.upper() == "ALL":
        symbols = (
            df["Symbol"].unique().tolist() if "Symbol" in df.columns else [args.symbol]
        )
    else:
        symbols = [args.symbol]

    # Filtra cenários
    all_scenarios = get_scenarios()

    if args.scenario == "all":
        scenarios = all_scenarios
    elif args.scenario == "spread":
        scenarios = {k: v for k, v in all_scenarios.items() if "spread" in k}
    elif args.scenario == "gap":
        scenarios = {k: v for k, v in all_scenarios.items() if "gap" in k}
    elif args.scenario == "slippage":
        scenarios = {k: v for k, v in all_scenarios.items() if "slippage" in k}
    elif args.scenario == "volatility":
        scenarios = {k: v for k, v in all_scenarios.items() if "volatility" in k}
    elif args.scenario == "disconnect":
        scenarios = {k: v for k, v in all_scenarios.items() if "disconnect" in k}
    else:
        scenarios = {
            args.scenario: all_scenarios.get(
                args.scenario, (args.scenario, lambda df: df)
            )
        }

    # Executa cenários
    results: list[dict[str, Any]] = []

    for symbol in symbols:
        for scenario_key, (scenario_name, stress_fn) in scenarios.items():
            logger.info("Executando: %s — %s", symbol, scenario_name)
            result = run_stress_scenario(df, symbol, scenario_name, stress_fn)
            results.append(result)

    # Salva relatório
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = REPORTS_DIR / f"stress_test_{timestamp}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    # Resumo
    print()
    print("=" * 60)
    print(" TESTES DE ESTRESSE — RESUMO")
    print("=" * 60)

    for result in results:
        scenario = result["scenario"]
        symbol = result["symbol"]

        if "error" in result:
            print(f"  {symbol} | {scenario}: ERRO")
            continue

        metrics = result["result"]
        print(f"  {symbol} | {scenario}:")
        print(f"    Trades: {metrics['total_trades']}")
        print(f"    Win Rate: {metrics['win_rate'] * 100:.1f}%")
        print(f"    PF: {metrics['profit_factor']:.2f}")
        print(f"    Net: {metrics['net_profit']:.2f}")
        print(f"    Max DD: {metrics['max_drawdown']:.2f}")
        print()

    print(f"Relatório completo: {filepath}")
    print("=" * 60)


if __name__ == "__main__":
    main()
