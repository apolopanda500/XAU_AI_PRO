"""LEGACY/ORFAO - NAO CONECTADO (15.3). Usar pipeline.py (predict_all -> save_prediction_json).

Model loader and prediction helper for XAU_AI_PRO.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, cast

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parent.parent / "model.pkl"


class _Model(Protocol):
    """Protocol for trained ML models with predict and predict_proba."""

    def predict(self, x: pd.DataFrame) -> np.ndarray: ...
    def predict_proba(self, x: pd.DataFrame) -> np.ndarray: ...


class Classifier(_Model, Protocol):
    """Protocol for scikit-learn-like classifiers."""


def load_model() -> Classifier:
    """Load the trained model from disk."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Modelo não encontrado: {MODEL_PATH}")
    return cast(Classifier, joblib.load(MODEL_PATH))


def run_prediction(
    model: Classifier, x_data: pd.DataFrame
) -> tuple[int | str, np.ndarray]:
    """Run prediction and probability estimation on input data."""
    return model.predict(x_data)[0], model.predict_proba(x_data)[0]
