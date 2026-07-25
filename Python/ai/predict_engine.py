import sys
from pathlib import Path
from datetime import datetime
import json
import csv

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import joblib
import pandas as pd

from data.data_engine_xau import DataEngineXAU
from data.data_pipeline import DataPipeline


# ======================================
# CONFIG
# ======================================

MODEL_PATH = Path(__file__).parent / "model.pkl"

PREDICTION_FILE = Path(__file__).parent / "prediction.json"

HISTORY_FILE = Path(__file__).parent / "ai_history.csv"


MIN_CONFIDENCE = 70



# ======================================
# CARREGAR MODELO
# ======================================

model = joblib.load(MODEL_PATH)


# ======================================
# DATA
# ======================================

engine = DataEngineXAU()

df = engine.load()


pipeline = DataPipeline(df)


df = (
    pipeline
    .convert_numeric()
    .remove_empty()
    .clean()
    .sort_time()
    .remove_duplicates()
    .reset()
    .get()
)



# ======================================
# ÚLTIMO CANDLE
# ======================================

last = df.iloc[-1]


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


X = pd.DataFrame(
    [last[features]]
)



# ======================================
# AI PREDICTION
# ======================================

prediction = model.predict(X)[0]

prob = model.predict_proba(X)[0]


sell = round(float(prob[0] * 100),2)
buy  = round(float(prob[1] * 100),2)



if buy >= MIN_CONFIDENCE:

    signal = "BUY"
    score = buy


elif sell >= MIN_CONFIDENCE:

    signal = "SELL"
    score = sell


else:

    signal = "WAIT"
    score = max(buy,sell)



# ======================================
# JSON PARA MT5
# ======================================

output = {

    "symbol": str(last["Symbol"]),

    "signal": signal,

    "score": score,

    "buy_probability": buy,

    "sell_probability": sell,

    "price": float(last["Close"]),

    "atr": float(last["ATR"]),

    "adx": float(last["ADX"]),

    "rsi": float(last["RSI"]),

    "time": str(datetime.now())

}



with open(
    PREDICTION_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        indent=4
    )



# ======================================
# HISTÓRICO
# ======================================

new_file = not HISTORY_FILE.exists()


with open(
    HISTORY_FILE,
    "a",
    newline="",
    encoding="utf-8"
) as f:


    writer = csv.writer(f)


    if new_file:

        writer.writerow(output.keys())


    writer.writerow(output.values())



print("==============================")
print("XAU_AI_PRO AI ENGINE V2")
print("==============================")

print("ATIVO:", output["symbol"])
print("PREÇO:", output["price"])

print(
    "BUY:",
    buy,
    "%"
)

print(
    "SELL:",
    sell,
    "%"
)

print(
    "SINAL:",
    signal
)

print(
    "SCORE:",
    score
)

print("==============================")
print("prediction.json criado")