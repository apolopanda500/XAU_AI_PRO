"""Module for running AI predictions on XAUUSD market data."""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

import pandas as pd

# Constantes
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
sys.path.append(str(BASE_DIR))

from ai.predict_model import load_model, run_prediction
from ai.predict_engine import build_result

MODEL_PATH = BASE_DIR / "model.pkl"
DATASET_PATH = Path(
    os.getenv(
        "XAU_AI_PRO_DATASET",
        PROJECT_ROOT / "MQL5" / "Files" / "Data" / "dataset.csv",
    )
).expanduser()
OUTPUT_DIR = PROJECT_ROOT / "MQL5" / "Files" / "Data"

FEATURES = [
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "Spread",
    "ATR",
    "ADX",
    "RSI",
    "BodySize",
    "RangeSize",
    "UpperShadow",
    "LowerShadow",
    "ATR_Pct",
    "RSI_Diff",
    "Close_Diff",
    "Volume_MA",
    "ADX_Change",
]


def _load_dataset() -> pd.DataFrame:
    """Carrega e pré-processa o dataset para previsão."""
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {DATASET_PATH}")

    with open(DATASET_PATH, "rb") as f:
        raw = f.read()

    text = raw.decode("utf-16", errors="replace")
    lines = [line for line in text.splitlines() if line.strip()]
    start_idx = next((i for i, line in enumerate(lines) if line.startswith("2026")), 0)

    df = pd.read_csv(
        io.StringIO("\n".join(lines[start_idx:])),
        sep=",",
        header=None,
        on_bad_lines="skip",
    )

    df.columns = [
        "Time",
        "Symbol",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "Spread",
        "ATR",
        "ADX",
        "RSI",
    ]

    df = df.dropna()

    if df.empty:
        raise ValueError("Nenhum registro encontrado no dataset para previsão.")

    df["Time"] = pd.to_datetime(df["Time"])
    df = df.sort_values(by="Time").reset_index(drop=True)

    # Feature engineering (igual ao train.py)
    df["BodySize"] = df["Close"] - df["Open"]
    df["RangeSize"] = df["High"] - df["Low"]
    df["UpperShadow"] = df["High"] - df[["Open", "Close"]].max(axis=1)
    df["LowerShadow"] = df[["Open", "Close"]].min(axis=1) - df["Low"]
    df["ATR_Pct"] = (df["ATR"] / df["Close"]) * 100
    df["RSI_Diff"] = df["RSI"].diff().fillna(0)
    df["Close_Diff"] = df["Close"].diff().fillna(0)
    df["Volume_MA"] = df["Volume"].rolling(window=5, min_periods=1).mean()
    df["ADX_Change"] = df["ADX"].diff().fillna(0)

    return df


def _predict_symbol(model: object, df: pd.DataFrame, symbol: str) -> dict | None:
    """Gera predição para um símbolo específico."""
    symbol_df = df[df["Symbol"].astype(str).str.strip() == symbol]

    if symbol_df.empty:
        print(f"  Sem dados para {symbol}, pulando...")
        return None

    last: pd.Series = symbol_df.iloc[-1]

    x_data = pd.DataFrame(
        [[
            last["Open"],
            last["High"],
            last["Low"],
            last["Close"],
            last["Volume"],
            last["Spread"],
            last["ATR"],
            last["ADX"],
            last["RSI"],
            last["BodySize"],
            last["RangeSize"],
            last["UpperShadow"],
            last["LowerShadow"],
            last["ATR_Pct"],
            last["RSI_Diff"],
            last["Close_Diff"],
            last["Volume_MA"],
            last["ADX_Change"],
        ]],
        columns=FEATURES,
    )

    prediction, probability = run_prediction(model, x_data)
    result = build_result(prediction, probability, last)

    return result


def predict() -> None:
    """Run prediction on all symbols and save results per symbol."""

    print("=" * 30)
    print(" XAU_AI_PRO AI PREDICT (MULTI-SYMBOL)")
    print("=" * 30)

    model = load_model()
    df = _load_dataset()

    # Lista de símbolos únicos no dataset
    symbols = df["Symbol"].astype(str).str.strip().unique()

    print(f"Símbolos encontrados: {len(symbols)}")
    for s in symbols:
        print(f"  - {s}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    predictions_made = 0

    for symbol in symbols:
        if not symbol:
            continue

        print(f"\nPredizendo {symbol}...")

        result = _predict_symbol(model, df, symbol)

        if result is None:
            continue

        print(f"  Resultado: {result}")

        # Salvar prediction_{symbol}.json
        output_file = OUTPUT_DIR / f"prediction_{symbol}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4)

        print(f"  Salvo: {output_file}")
        predictions_made += 1

    print()
    print(f"Predições geradas: {predictions_made}/{len(symbols)}")
    print(f"Diretório: {OUTPUT_DIR}")


if __name__ == "__main__":
    predict()