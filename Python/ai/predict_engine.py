"""LEGACY/ORFAO - NAO CONECTADO (15.3). Usar pipeline.py (predict_all -> save_prediction_json).
Signal builder para previsoes XAU_AI_PRO (mantido como referencia).
"""

from __future__ import annotations

from typing import Any
from datetime import datetime
import os

# Versão do modelo (definida no ambiente ou configuração)
MODEL_VERSION = os.getenv("MODEL_VERSION", "1.2.0-RC1")


def build_result(
    prediction: Any, 
    probability: Any, 
    last_row: Any,
    model_version: str = MODEL_VERSION,
    timestamp: str | None = None
) -> dict[str, Any]:
    """Build the prediction result dictionary.
    
    Args:
        prediction: Predicted class label (0 or 1). Use -1 for UNAVAILABLE.
        probability: Array-like of class probabilities.
        last_row: Last row of the dataset with market data.
        model_version: Version of the model used for prediction.
        timestamp: ISO format timestamp of when prediction was made.
    
    Returns:
        Dictionary with prediction signal, price, buy/sell percentages, 
        score, model version, and timestamp.
    """
    # Tratamento de estado UNAVAILABLE
    if prediction == -1 or prediction is None:
        return {
            "symbol": str(last_row.get("Symbol", "")),
            "signal": "UNAVAILABLE",
            "price": float(last_row.get("Close", 0)),
            "buy": 0.0,
            "sell": 0.0,
            "score": 0.0,
            "model_version": model_version,
            "timestamp": timestamp or datetime.now().isoformat(),
        }
    
    probabilities = list(probability)

    if len(probabilities) >= 2:
        sell = float(probabilities[0])
        buy = float(probabilities[1])
    else:
        sell = float(probabilities[0])
        buy = float(probabilities[0])

    signal = "BUY" if prediction == 1 else "SELL"
    score = max(buy, sell) * 100

    return {
        "symbol": str(last_row.get("Symbol", "")),
        "signal": signal,
        "price": float(last_row.get("Close", 0)),
        "buy": round(buy * 100, 2),
        "sell": round(sell * 100, 2),
        "score": round(score, 2),
        "model_version": model_version,
        "timestamp": timestamp or datetime.now().isoformat(),
    }
