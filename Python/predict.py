"""Module for running AI predictions on XAUUSD market data."""

import json
import os
from pathlib import Path

import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

MODEL = BASE_DIR / "model.pkl"
DATASET = Path(
    os.getenv(
        "XAU_AI_PRO_DATASET",
        PROJECT_ROOT / "MQL5" / "Files" / "Data" / "dataset.csv",
    )
).expanduser()
OUTPUT = PROJECT_ROOT / "MQL5" / "Files" / "Data" / "prediction.json"


def predict():
    """Run prediction on the latest dataset row and save results."""

    print("==============================")
    print(" XAU_AI_PRO AI PREDICT")
    print("==============================")

    if not MODEL.exists():
        raise FileNotFoundError(f"Modelo não encontrado: {MODEL}")

    if not DATASET.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {DATASET}")

    model = joblib.load(MODEL)

    df = pd.read_csv(
        DATASET,
        encoding="utf-16",
        sep=",",
        header=None
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
        "RSI"
    ]

    df = df.dropna()

    symbol_mask = df["Symbol"].astype(str).str.upper().str.startswith("XAUUSD")
    df = df[symbol_mask]

    df["Time"] = pd.to_datetime(df["Time"])

    df = df.sort_values("Time")

    if df.empty:
        raise ValueError("Nenhum registro XAUUSD encontrado no dataset para previsão.")

    print(df.tail())

    last = df.iloc[-1]

    x_data = pd.DataFrame(
        [
            [
                last["Open"],
                last["High"],
                last["Low"],
                last["Close"],
                last["Volume"],
                last["Spread"],
                last["ATR"],
                last["ADX"],
                last["RSI"],
            ]
        ],
        columns=[
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "Spread",
            "ATR",
            "ADX",
            "RSI",
        ],
    )

    prediction = model.predict(x_data)[0]

    probability = model.predict_proba(x_data)[0]

    if len(probability) == 1:
        sell = float(probability[0]) if prediction == 0 else 0.0
        buy = float(probability[0]) if prediction == 1 else 0.0
    else:
        sell = float(probability[0])
        buy = float(probability[1])

    signal = "BUY" if prediction == 1 else "SELL"

    score = max(
        buy,
        sell
    ) * 100

    result = {
        "symbol": str(last["Symbol"]),
        "signal": signal,
        "price": float(last["Close"]),
        "buy": round(buy * 100, 2),
        "sell": round(sell * 100, 2),
        "score": round(score, 2)
    }

    print(result)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            result,
            f,
            indent=4
        )

    print()
    print("prediction.json criado")
    print(OUTPUT)


if __name__ == "__main__":
    predict()
