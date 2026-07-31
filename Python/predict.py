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
OUTPUT_PATH = PROJECT_ROOT / "MQL5" / "Files" / "Data" / "prediction.json"

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
    symbol_mask = df["Symbol"].astype(str).str.strip().str.upper().str.startswith("XAUUSD")
    df = df[symbol_mask]

    if df.empty:
        raise ValueError("Nenhum registro XAUUSD encontrado no dataset para previsão.")

    df["Time"] = pd.to_datetime(df["Time"])
    df = df.sort_values("Time").reset_index(drop=True)
    return df


def predict() -> None:
    """Run prediction on the latest dataset row and save results."""

    print("=" * 30)
    print(" XAU_AI_PRO AI PREDICT")
    print("=" * 30)

    model = load_model()
    df = _load_dataset()
    last = df.iloc[-1]

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
        ]],
        columns=FEATURES,
    )

    prediction, probability = run_prediction(model, x_data)
    result = build_result(prediction, probability, last)

    print(result)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print()
    print("prediction.json criado")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    predict()
