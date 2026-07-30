"""Módulo de treinamento do modelo XAU_AI_PRO."""
from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


# ==========================================
# CAMINHOS
# ==========================================

DATASET = Path(
    __import__("os").getenv(
        "XAU_AI_PRO_DATASET",
        BASE_DIR.parent / "MQL5" / "Files" / "Data" / "dataset.csv",
    )
).expanduser()

MODEL = BASE_DIR / "model.pkl"


# ==========================================
# TREINAMENTO
# ==========================================

def train():
    """Executa o treinamento do modelo RandomForestClassifier."""

    print("=" * 30)
    print(" XAU_AI_PRO TRAINING ENGINE")
    print("=" * 30)

    if not DATASET.exists():
        print("ERRO: dataset.csv não encontrado")
        print("Procurando em:", DATASET)
        return

    try:
        with open(DATASET, "rb") as f:
            raw = f.read()

        text = raw.decode("utf-16", errors="replace")
        lines = [line for line in text.splitlines() if line.strip()]
        start_idx = next((i for i, line in enumerate(lines) if line.startswith("2026")), 0)

        df = pd.read_csv(
            __import__("io").StringIO("\n".join(lines[start_idx:])),
            sep=",",
            header=None,
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

        print(df.head())
        print(df.info())

        df = df.dropna()
        df = df[df["Symbol"].astype(str).str.startswith("XAUUSD")]

        if len(df) < 1:
            print("Poucos dados para treinar:", len(df))
            return

    except Exception as e:
        print("ERRO ao carregar dataset:", e)
        return

    features = [
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

    df["Target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)
    df = df.dropna()

    x = df[features]
    y = df["Target"]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        shuffle=False,
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        random_state=42,
    )

    print()
    print("Treinando modelo...")
    model.fit(x_train, y_train)

    pred = model.predict(x_test)
    acc = accuracy_score(y_test, pred)

    print()
    print("Precisão:", round(acc * 100, 2), "%")

    try:
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL)
        print()
        print("Modelo criado:")
        print(MODEL)
    except Exception as e:
        print("ERRO ao salvar modelo:", e)


if __name__ == "__main__":
    train()
