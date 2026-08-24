# -*- coding: utf-8 -*-
"""ETAPA 18.6 - Confidence profissional.

A confianca da IA deixa de ser numero isolado. Toda previsao passa por
validacao composta:

  prediction + confidence + model_status + prediction_age
  + feature_integrity + model_version

Regra-chave (18.6):
  if model STALE or age > threshold -> NAO e BUY/SELL valido,
  mesmo que confidence seja alta.

Saida: status VALID / STALE / UNAVAILABLE / ERROR / CONFIDENCE_ERROR
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# limits
MIN_CONFIDENCE = 0.5        # abaixo disso, previsao fraca -> nao valida
MAX_AGE_VALID_SEC = 300     # age > 5min -> STALE


def evaluate_confidence(pred: dict[str, Any]) -> dict[str, Any]:
    """Valida composite da previsao retornada pelo Prediction Gateway.

    `pred` segue o contrato unico (model_registry/gateway). Retorna status
    final + razoes. NUNCA transforma stale/unavailable/error em sinal.
    """
    status = pred.get("status")
    # estados de erro vindo do gateway ja sao finais (unavailable/stale/error)
    if status in ("UNAVAILABLE", "STALE", "ERROR", "FEATURE_ERROR", "TRAINING"):
        return {
            "valid": False,
            "status": status,
            "prediction": None,
            "confidence": None,
            "signal": None,
            "reason": pred.get("reason", status.lower()),
        }

    # previsao presente -> READY
    confidence = pred.get("confidence")
    age_sec = pred.get("age_sec")

    # 1. confidence valida
    if confidence is None or confidence <= 0:
        return _conf_error("confidence_missing_or_zero", pred)
    if confidence < MIN_CONFIDENCE:
        return _conf_error(f"confidence_below_threshold({MIN_CONFIDENCE})", pred)

    # 2. age dentro do limite (mesmo READY, se age>max vira STALE)
    if age_sec is not None and age_sec > MAX_AGE_VALID_SEC:
        return {
            "valid": False, "status": "STALE", "prediction": None,
            "confidence": None, "signal": None,
            "reason": f"age_exceeds_max({age_sec}s>{MAX_AGE_VALID_SEC}s)",
        }

    # 3. feature integrity (se presente no pred)
    if pred.get("feature_version") is None:
        return _conf_error("feature_version_missing", pred)

    # 4. model_version presente
    if not pred.get("model_version"):
        return _conf_error("model_version_missing", pred)

    # 5. mapeia prediction int -> signal
    p = pred.get("prediction")
    if p is None:
        return _conf_error("prediction_missing", pred)
    signal = {0: "SELL", 1: "BUY"}.get(int(p), "NEUTRAL")

    return {
        "valid": True, "status": "VALID", "prediction": int(p),
        "confidence": round(float(confidence), 4), "signal": signal,
        "model_version": pred.get("model_version"),
        "feature_version": pred.get("feature_version"),
        "age_sec": age_sec,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _conf_error(reason: str, pred: dict[str, Any]) -> dict[str, Any]:
    return {
        "valid": False, "status": "CONFIDENCE_ERROR", "prediction": None,
        "confidence": None, "signal": None, "reason": reason,
    }


if __name__ == "__main__":
    # Predicado ficticio (teste estrutural)
    from prediction_gateway import predict
    # caso inexistente: conjunto NAO valido mesmo com confidence alta (vira UNAVAILABLE)
    fake_hot_but_stale = {"status": "STALE", "confidence": 0.84,
                          "age_sec": 900, "prediction": 1,
                          "model_version": "1.2.0", "feature_version": "25F-v1", "reason": "model_stale"}
    print("STALE conf 0.84 age 900s ->", evaluate_confidence(fake_hot_but_stale))

    fake_ready = {"status": "READY", "confidence": 0.84, "age_sec": 3,
                  "prediction": 1, "model_version": "1.2.0", "feature_version": "25F-v1"}
    print("READY conf 0.84 age 3s   ->", evaluate_confidence(fake_ready))
