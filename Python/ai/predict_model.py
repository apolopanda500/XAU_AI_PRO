"""Model loader and prediction helper for XAU_AI_PRO."""

from __future__ import annotations

import joblib
from pathlib import Path
from typing import Any

import pandas as pd

MODEL_PATH = Path(__file__).resolve().parent.parent / "model.pkl"


def load_model() -> Any:
    """Load the trained model from disk."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Modelo não encontrado: {MODEL_PATH}")
    return joblib.load(MODEL_PATH)


def run_prediction(model: Any, x_data: pd.DataFrame) -> tuple[Any, Any]:
    """Run prediction and probability estimation on input data."""
    prediction = model.predict(x_data)[0]
    probability = model.predict_proba(x_data)[0]
    return prediction, probability
