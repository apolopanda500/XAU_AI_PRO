# -*- coding: utf-8 -*-
"""ETAPA 18.7 + 18.11 - Integracao AI -> DecisionEngine com Fail-Safe.

A IA e um COMPONENTE decisorio (nao autoridade absoluta).
Fluxo:
  prediction_gateway.predict -> confidence.evaluate_confidence
    -> se VALID -> DecisionEngine.decide
    -> se !VALID -> segura (AI=UNAVAILABLE) e deixa o tecnico/risco decidir

Fail-Safe (18.11):
  Python OFF / Model ERROR / Features ERROR / Prediction STALE /
  Confidence invalida / Latencia excessiva -> AI = UNAVAILABLE
  e o sistema superior decide TECHNICAL_ONLY ou SAFE.
"""
from __future__ import annotations

import time
from typing import Any

try:
    # Caminhos relativos (rodar a partir de Python/)
    from prediction_gateway import predict
    from ai import confidence as conf
    from ai import ai_event_stream as ev
except Exception:  # noqa: BLE001
    # fallback de import (para uso como modulo embarcado)
    from Python.prediction_gateway import predict
    from Python.ai import confidence as conf
    from Python.ai import ai_event_stream as ev

# limites (18.11)
MAX_LATENCY_MS = 2000   # > 2s -> AI_WARNING


def decision_from_ai(
    symbol: str,
    timeframe: str,
    features,
    decision_engine,
    max_age_sec: int = 300,
) -> dict[str, Any]:
    """Obtem prediction, valida confianca e delega ao DecisionEngine.

    Retorna dict com:
      - ai_valid: bool (se a IA contribuiu)
      - ai_status: READY/UNAVAILABLE/STALE/ERROR/FEATURE_ERROR/AI_WARNING
      - decision: resultado do DecisionEngine (se chegou a ele)
      - reasons
    """
    t0 = time.perf_counter()

    # 1. Prediction via Gateway (ja valida modelo/features/stale)
    pred = predict(symbol, timeframe, features, max_age_sec=max_age_sec)

    # 2. Latencia excessiva -> Fail-Safe (nao usa a predicao)
    latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    pred["_latency_ms"] = latency_ms

    # 3. Validacao composta da confianca (18.6)
    c = conf.evaluate_confidence(pred)

    # 4. Fail-Safe: se a IA nao esta VALID, nao vira sinal
    if not c.get("valid"):
        # emite eventos de estado IA no stream (18.8)
        st = c.get("status", "UNAVAILABLE")
        reason = c.get("reason", "fail_safe")
        symb = symbol.upper()
        if st == "STALE":
            ev.ai_stale(symb, timeframe, c.get("age_sec", pred.get("age_sec", 0)))
        elif st == "UNAVAILABLE":
            ev.ai_unavailable(symb, timeframe, reason)
        elif st == "ERROR":
            ev.ai_error(symb, timeframe, reason)
        elif st == "FEATURE_ERROR":
            ev.ai_feature_error(symb, timeframe, reason)

        # IA indisponivel -> sinal retirado (deixa tecnico/risco decidir)
        return {
            "ai_valid": False,
            "ai_status": st,
            "ai_reason": reason,
            "signal": None,
            "decision": None,
            "latency_ms": latency_ms,
            "mode": "TECHNICAL_ONLY" if pred.get("_latency_ms", 0) <= MAX_LATENCY_MS else "SAFE",
        }

    # 5. IA VALID -> delega ao DecisionEngine
    signal = c["signal"]  # BUY/SELL
    confidence = c["confidence"]
    decision = decision_engine.decide(
        symbol=symbol,
        signal=signal,
        confidence=confidence,
        ai_score=confidence,
    )

    # emite evento AI_PREDICTION de sucesso
    ev.ai_prediction(symbol.upper(), timeframe, signal, confidence, value=str(round(confidence, 4)))

    return {
        "ai_valid": True,
        "ai_status": "READY",
        "signal": signal,
        "confidence": confidence,
        "decision": decision,
        "latency_ms": latency_ms,
        "mode": "AI_+_TECHNICAL",
    }
