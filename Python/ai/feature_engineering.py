"""
XAU_AI_PRO - Feature Engineering
V1.0

Responsabilidades:
- Centralizar a engenharia de features usada por train.py, predict.py e pipeline.py
- Garantir consistencia entre treino e predicao
- Exportar a lista FEATURES para uso em todo o pipeline
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ============================================================
# FEATURES
# ============================================================

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
    "KCI_VD",
    "KCI_MAIN",
    "KDI_PLUS",
    "KDI_MINUS",
    "BodySize",
    "RangeSize",
    "UpperShadow",
    "LowerShadow",
    "ATR_Pct",
    "RSI_Diff",
    "Close_Diff",
    "Volume_MA",
    "ADX_Change",
    "KCI_VD_Pct",
    "KDI_Diff",
    "KCI_MAIN_Change",
]


# ============================================================
# BUILD FEATURES
# ============================================================


def build_features(df: pd.DataFrame, dropna: bool = False) -> pd.DataFrame:
    """
    Adiciona features derivadas ao DataFrame.

    Espera colunas: Open, High, Low, Close, Volume,
    Spread, ATR, ADX, RSI.

    Retorna o DataFrame com as features adicionais.
    """
    if df.empty:
        return df

    # Garante colunas KCI (datasets antigos podem nao ter KCI_VD,
    # KCI_MAIN, KDI_PLUS, KDI_MINUS -> evita KeyError)
    for kci in ("KCI_VD", "KCI_MAIN", "KDI_PLUS", "KDI_MINUS"):
        if kci not in df.columns:
            df[kci] = 0.0

    # Body size (corpo do candle)
    df["BodySize"] = df["Close"] - df["Open"]

    # Range size (amplitude do candle)
    df["RangeSize"] = df["High"] - df["Low"]

    # Upper shadow (sombra superior)
    df["UpperShadow"] = df["High"] - df[["Open", "Close"]].max(axis=1)

    # Lower shadow (sombra inferior)
    df["LowerShadow"] = df[["Open", "Close"]].min(axis=1) - df["Low"]

    # ATR percentual (volatilidade relativa)
    df["ATR_Pct"] = (df["ATR"] / df["Close"]) * 100

    # RSI diff (variacao do RSI)
    df["RSI_Diff"] = df["RSI"].diff().fillna(0)

    # Close diff (variacao do preco)
    df["Close_Diff"] = df["Close"].diff().fillna(0)

    # Volume moving average (media movel do volume)
    df["Volume_MA"] = df["Volume"].rolling(window=5, min_periods=1).mean()

    # ADX change (variacao do ADX)
    df["ADX_Change"] = df["ADX"].diff().fillna(0)

    # KCI Volatility Distance percentual (volatilidade relativa ao preco)
    df["KCI_VD_Pct"] = (df["KCI_VD"] / df["Close"]) * 100

    # KCI Direcional diff (diferenca entre forca de alta e baixa)
    df["KDI_Diff"] = df["KDI_PLUS"] - df["KDI_MINUS"]

    # KCI Main change (variacao da forca da tendencia)
    df["KCI_MAIN_Change"] = df["KCI_MAIN"].diff().fillna(0)

    if dropna:
        df = df.dropna()

    return df


# ============================================================
# PREPARE X
# ============================================================


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna apenas as colunas de features, na ordem correta.
    Garante que todas as features existam no DataFrame.
    """
    missing = [f for f in FEATURES if f not in df.columns]
    if missing:
        raise ValueError(f"Features ausentes: {missing}")

    return df[FEATURES].copy()


# ============================================================
# TESTE
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print(" XAU_AI_PRO FEATURE ENGINEERING")
    print("=" * 50)
    print()
    print(f"Features ({len(FEATURES)}):")
    for f in FEATURES:
        print(f"  - {f}")
    print()

    # Dado sintetico para teste
    np.random.seed(42)
    n = 10
    df = pd.DataFrame(
        {
            "Open": np.random.uniform(4000, 4100, n),
            "High": np.random.uniform(4100, 4200, n),
            "Low": np.random.uniform(3900, 4000, n),
            "Close": np.random.uniform(4000, 4100, n),
            "Volume": np.random.randint(1000, 5000, n),
            "Spread": np.random.uniform(20, 50, n),
            "ATR": np.random.uniform(5, 15, n),
            "ADX": np.random.uniform(15, 40, n),
            "RSI": np.random.uniform(20, 80, n),
            "KCI_VD": np.random.uniform(0.5, 5.0, n),
            "KCI_MAIN": np.random.uniform(20, 80, n),
            "KDI_PLUS": np.random.uniform(10, 90, n),
            "KDI_MINUS": np.random.uniform(10, 90, n),
        }
    )

    df = build_features(df)
    print("Features geradas:")
    print(df.head())
    print()
    print("prepare_features:")
    x = prepare_features(df)
    print(x.head())
    print()
    print("=" * 50)
