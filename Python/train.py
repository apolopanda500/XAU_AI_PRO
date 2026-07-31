"""Módulo de treinamento do modelo XAU_AI_PRO."""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split  # type: ignore[import]

# Constantes
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
sys.path.append(str(BASE_DIR))

DATASET_PATH = Path(
    os.getenv(
        "XAU_AI_PRO_DATASET",
        PROJECT_ROOT / "MQL5" / "Files" / "Data" / "dataset.csv",
    )
).expanduser()

MODEL_PATH = BASE_DIR / "model.pkl"

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
    """Carrega e pré-processa o dataset de treinamento."""
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
        raise ValueError("Nenhum registro encontrado no dataset para treinamento.")

    df["Time"] = pd.to_datetime(df["Time"])
    df = df.sort_values("Time").reset_index(drop=True)

    # Feature engineering
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


def train() -> None:
    """Executa o treinamento do modelo RandomForestClassifier."""
    print("=" * 30)
    print(" XAU_AI_PRO TRAINING ENGINE")
    print("=" * 30)

    try:
        df = _load_dataset()
    except (FileNotFoundError, ValueError) as e:
        print(f"ERRO ao carregar dataset: {e}")
        return

    print(f"Dados carregados: {len(df)} registros")
    print(df.head())
    print(df.info())

    # Cria target: 1 se Close futuro > Close atual, senão 0
    # Usa forward return normalizado para melhor qualidade
    df["Future_Return"] = df["Close"].shift(-1) / df["Close"] - 1
    df["Target"] = (df["Future_Return"] > 0).astype(int)
    df = df.dropna()

    if len(df) < 10:
        print("Poucos dados para treinar após pré-processamento:", len(df))
        return

    x = df[FEATURES]
    y = df["Target"]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        shuffle=False,
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    print()
    print("Treinando modelo...")
    model.fit(x_train, y_train)

    pred = model.predict(x_test)
    acc = accuracy_score(y_test, pred)

    print()
    print(f"Precisão: {round(acc * 100, 2)}%")

    try:
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        print()
        print("Modelo criado:")
        print(MODEL_PATH)
    except Exception as e:
        print(f"ERRO ao salvar modelo: {e}")


if __name__ == "__main__":
    train()
