"""Módulo de treinamento do modelo XAU_AI_PRO."""
import os
from pathlib import Path

import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


# ==========================================
# CAMINHOS
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

DATASET = Path(
    os.getenv(
        "XAU_AI_PRO_DATASET",
        BASE_DIR.parent / "MQL5" / "Files" / "Data" / "dataset.csv"
    )
).expanduser()

MODEL = BASE_DIR / "model.pkl"


# ==========================================
# TREINAMENTO
# ==========================================

def train():
    """Executa o treinamento do modelo RandomForestClassifier."""

    print("================================")
    print(" XAU_AI_PRO TRAINING ENGINE")
    print("================================")


    if not DATASET.exists():

        print("ERRO: dataset.csv não encontrado")
        print("Procurando em:", DATASET)
        return



    with open(DATASET, "rb") as f:
        raw = f.read()

    text = raw.decode("utf-16", errors="replace")

    lines = [line for line in text.splitlines() if line.strip()]
    start_idx = next((i for i, line in enumerate(lines) if line.startswith("2026")), 0)
    
    import io
    df = pd.read_csv(
        io.StringIO("\n".join(lines[start_idx:])),
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

    print(df.head())
    print(df.info())


    print("Dataset carregado")
    print(df.head())


    print()
    print(df.info())


    # ===============================
    # LIMPEZA
    # ===============================

    df = df.dropna()

    df = df[df["Symbol"].astype(str).str.startswith("XAUUSD")]


    if len(df) < 1:

        print(
            "Poucos dados para treinar:",
            len(df)
        )

        return



    # ===============================
    # FEATURES
    # ===============================

    features = [

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


    x = df[features]



    # ===============================
    # TARGET
    # ===============================
    #
    # Movimento próximo candle
    #
    # 1 = compra
    # 0 = espera/venda
    #

    df["Target"] = (
        df["Close"].shift(-1)
        >
        df["Close"]
    ).astype(int)


    df = df.dropna()



    x = df[features]

    y = df["Target"]



    # ===============================
    # SPLIT
    # ===============================

    x_train, x_test, y_train, y_test = train_test_split(

        x,
        y,
        test_size=0.2,
        shuffle=False

    )



    # ===============================
    # MODELO
    # ===============================

    model = RandomForestClassifier(

        n_estimators=200,

        max_depth=8,

        random_state=42

    )



    print()
    print("Treinando modelo...")


    model.fit(
        x_train,
        y_train
    )



    # ===============================
    # TESTE
    # ===============================

    pred = model.predict(
        x_test
    )


    acc = accuracy_score(
        y_test,
        pred
    )


    print()
    print(
        "Precisão:",
        round(acc*100,2),
        "%"
    )



    # ===============================
    # SALVAR MODELO
    # ===============================

    joblib.dump(

        model,

        MODEL

    )


    print()
    print(
        "Modelo criado:"
    )

    print(
        MODEL
    )



if __name__ == "__main__":

    train()

