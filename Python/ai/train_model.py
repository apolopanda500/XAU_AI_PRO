"""LEGACY/ORFAO - NAO CONECTADO (15.3). Usar pipeline.py (train_all_models -> models/{symbol}_{tf}.pkl).
"""
import sys
from pathlib import Path

# adiciona pasta raiz Python
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))


import joblib
from data.data_engine_xau import DataEngineXAU
from data.data_pipeline import DataPipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Importa features do contrato unificado
from ai.feature_engineering import FEATURES, build_features, prepare_features


def main() -> None:
    print("=== XAU_AI_PRO TRAIN MODEL ===")

    # ===============================
    # CARREGAR DATASET
    # ===============================

    engine = DataEngineXAU()

    df = engine.load()

    pipeline = DataPipeline(df)

    df = (
        pipeline.convert_numeric()
        .remove_empty()
        .clean()
        .sort_time()
        .remove_duplicates()
        .reset()
        .get()
    )

    print(df.head())
    print(df.shape)

    # ===============================
    # CRIAR TARGET
    # ===============================

    # previsão próxima vela
    df["Target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)

    df.dropna(inplace=True)

    # ===============================
    # FEATURES
    # ===============================

    # Usa as 25 features definidas no contrato
    df = build_features(df)

    # Valida e seleciona apenas as features esperadas
    X = prepare_features(df)
    y = df["Target"]

    # ===============================
    # TREINO
    # ===============================

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    model = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42)

    model.fit(X_train, y_train)

    accuracy = model.score(X_test, y_test)

    print("==============================")
    print("MODELO TREINADO")
    print("ACURÁCIA:", accuracy)
    print("==============================")

    # ===============================
    # SALVAR MODELO
    # ===============================

    MODEL_PATH = Path(__file__).parent / "model.pkl"

    joblib.dump(model, MODEL_PATH)

    print("MODELO SALVO:")
    print(MODEL_PATH)


if __name__ == "__main__":
    main()

