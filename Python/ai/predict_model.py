import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))


import joblib
import pandas as pd

from data.data_engine_xau import DataEngineXAU
from data.data_pipeline import DataPipeline


print("=== XAU_AI_PRO AI PREDICT ===")


# ==========================
# CARREGAR MODELO
# ==========================

MODEL_PATH = Path(__file__).parent / "model.pkl"

model = joblib.load(MODEL_PATH)


print("Modelo carregado.")



# ==========================
# CARREGAR DADOS
# ==========================

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



# ==========================
# ÚLTIMO CANDLE
# ==========================

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
    [
        last[features]
    ]
)



# ==========================
# PREVISÃO
# ==========================

prediction = model.predict(X)[0]

probability = model.predict_proba(X)[0]


buy_probability = probability[1] * 100
sell_probability = probability[0] * 100



print("----------------------------")
print("ATIVO:", last["Symbol"])
print("PREÇO:", last["Close"])
print("----------------------------")

print(
    f"BUY:  {buy_probability:.2f}%"
)

print(
    f"SELL: {sell_probability:.2f}%"
)



if prediction == 1:

    print("SINAL AI: BUY")

else:

    print("SINAL AI: SELL")



print("----------------------------")