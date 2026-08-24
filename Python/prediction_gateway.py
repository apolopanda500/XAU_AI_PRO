# -*- coding: utf-8 -*-
"""ETAPA 18.4 - Prediction Gateway (camada unica EA -> Model -> Validation -> Prediction).

Fluxo: Model Registry -> validacao -> prediction -> contrato unico.
Regra 18.5: nenhum estado (STALE/UNAVAILABLE/ERROR) vira BUY/SELL.

Contrato de saida (18.4):
{
  symbol, timeframe, model, model_version, status,
  prediction, confidence, timestamp, feature_version
}
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import model_registry as reg

# limite de features esperadas (contrato 25F)
FEATURE_COUNT = 25


def detect_feature_count(features: Any) -> int | None:
    """Retorna numero de features se detectavel, senao None (indeterminado)."""
    try:
        import numpy as np
        arr = np.asarray(features)
        if arr.ndim == 2:
            return int(arr.shape[1])
        if arr.ndim == 1:
            return int(arr.shape[0])
    except Exception:  # noqa: BLE001
        pass
    try:
        return len(features)
    except Exception:  # noqa: BLE001
        return None


def unified_error(symbol: str, tf: str, status: str, reason: str, **kw) -> dict[str, Any]:
    """Retorna resposta padronizada de erro (nunca BUY/SELL)."""
    return {
        "symbol": symbol, "timeframe": tf.upper(),
        "model": f"{symbol}_{tf.upper()}",
        "model_version": reg.MODEL_VERSION,
        "feature_version": reg.FEATURE_VERSION,
        "status": status, "reason": reason,
        "prediction": None, "confidence": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **kw,
    }


def predict(symbol: str, timeframe: str, features: Any = None, max_age_sec: int = reg.MAX_AGE_READY_SEC) -> dict[str, Any]:
    """Prediction Gateway: valida modelo, carrega, preve, retorna contrato unico."""
    status = reg.model_status(symbol, timeframe)
    tf = timeframe.upper()
    _t0 = time.perf_counter()

    # 18.5: modelo inexistente -> UNAVAILABLE
    if not status["exists"]:
        return unified_error(symbol, tf, "UNAVAILABLE", "model_not_found")

    # 18.5: modelo corrompido -> ERROR
    if status["status"] == "ERROR":
        return unified_error(symbol, tf, "ERROR", status.get("reason", "load_error"))

    # 18.5: modelo antigo -> STALE (nunca previsao valida)
    if status["status"] == "STALE":
        return unified_error(
            symbol, tf, "STALE", "model_stale",
            age_sec=status.get("age_sec"),
            prediction=status["prediction"] if False else None,
        )

    # 18.6: valida features
    feat_ok = True
    feat_count = detect_feature_count(features) if features is not None else None
    if features is None:
        feat_ok = False
        feat_reason = "features_missing"
    elif feat_count is not None and feat_count != FEATURE_COUNT:
        feat_ok = False
        feat_reason = "feature_count_mismatch"
    else:
        feat_reason = "ok"

    if not feat_ok:
        return unified_error(symbol, tf, "FEATURE_ERROR", feat_reason,
                             feature_count=feat_count)

    # Carrega e preve (ja validado READY + features)
    try:
        import pickle
        with open(status["path"], "rb") as fh:
            model = pickle.load(fh)
        # features padrao se nao fornecido: usar linha 0 do modelo? exige contexto.
        # Aqui esperamos features explicitas (DataFrame 1xN ou array 1xN).
        pred_int = int(model.predict(features)[0])
        prob = model.predict_proba(features)[0]
        prob_buy = float(prob[1]) if len(prob) > 1 else 0.0
        confidence = float(max(prob)) if len(prob) else 0.0
    except Exception as e:  # noqa: BLE001
        return unified_error(symbol, tf, "ERROR", f"prediction_error: {e}")

    latency_ms = round((time.perf_counter() - _t0) * 1000.0, 2)
    return {
        "symbol": symbol, "timeframe": tf, "model": f"{symbol}_{tf}",
        "model_version": reg.MODEL_VERSION, "feature_version": reg.FEATURE_VERSION,
        "status": "READY",
        "prediction": int(pred_int), "confidence": round(confidence, 4),
        "prob_buy": round(prob_buy, 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latency_ms": latency_ms,
        "age_sec": status.get("age_sec"),
    }


if __name__ == "__main__":
    print("=== Prediction Gateway - casos 18.12 (parciais sem features reais) ===")
    print("XAUUSD M15 (inexistente):", predict("XAUUSD", "M15"))
    print("XAUUSD M5  (STALE):", predict("XAUUSD", "M5"))
