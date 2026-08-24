# -*- coding: utf-8 -*-
"""ETAPA 18.3 - Model Registry (fonte unica de verdade dos modelos).

Convencao unica: Python/models/{SYMBOL}_{TIMEFRAME}.pkl
Responde: exists, is_ready, version, age, feature_version, path, status.

Estados (18.1): READY / STALE / UNAVAILABLE / ERROR / TRAINING
Nenhum modelo inexistente pode ser interpretado como valido.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MODELS_DIR = Path(__file__).resolve().parent.parent / "Python" / "models"
FEATURE_VERSION = "25F"          # contrato 25 features (ETAPA 15.2.2)
MODEL_VERSION = "1.2.0"
# idade maxima aceita como READY (segundos) - 5 dias
MAX_AGE_READY_SEC = 5 * 24 * 3600

# estados validos
READY = "READY"
STALE = "STALE"
UNAVAILABLE = "UNAVAILABLE"
ERROR = "ERROR"
TRAINING = "TRAINING"


def model_path(symbol: str, timeframe: str) -> Path:
    return MODELS_DIR / f"{symbol}_{timeframe.upper()}.pkl"


def _mtime_age_sec(p: Path) -> float:
    if not p.exists():
        return float("inf")
    return max(0.0, datetime.now().timestamp() - p.stat().st_mtime)


def model_status(symbol: str, timeframe: str) -> dict[str, Any]:
    """Avalia o modelo e retorna metadados + estado."""
    p = model_path(symbol, timeframe)
    if not p.exists():
        return {
            "symbol": symbol, "timeframe": timeframe.upper(),
            "model": f"{symbol}_{timeframe.upper()}", "path": str(p),
            "exists": False, "status": UNAVAILABLE, "reason": "model_not_found",
        }
    try:
        age_sec = _mtime_age_sec(p)
        size = p.stat().st_size
        status = READY if age_sec <= MAX_AGE_READY_SEC else STALE
        return {
            "symbol": symbol, "timeframe": timeframe.upper(),
            "model": f"{symbol}_{timeframe.upper()}", "path": str(p),
            "exists": True, "status": status, "reason": "ok" if status == READY else "model_stale",
            "age_sec": int(age_sec), "age_hours": round(age_sec / 3600, 1),
            "size_bytes": size, "model_version": MODEL_VERSION,
            "feature_version": FEATURE_VERSION,
            "type": "pickle",
        }
    except Exception as e:  # noqa: BLE001
        return {
            "symbol": symbol, "timeframe": timeframe.upper(),
            "model": f"{symbol}_{timeframe.upper()}", "path": str(p),
            "exists": True, "status": ERROR, "reason": f"load_error: {e}",
        }


def ModelExists(symbol: str, timeframe: str) -> bool:
    return model_path(symbol, timeframe).exists()


def ModelIsReady(symbol: str, timeframe: str) -> bool:
    return model_status(symbol, timeframe)["status"] == READY


def ModelVersion(symbol: str, timeframe: str) -> str:
    return model_status(symbol, timeframe).get("model_version", "")


def ModelAge(symbol: str, timeframe: str) -> int:
    return int(model_status(symbol, timeframe).get("age_sec", -1))


def ModelFeatureVersion(symbol: str, timeframe: str) -> str:
    return model_status(symbol, timeframe).get("feature_version", "")


def ModelPath(symbol: str, timeframe: str) -> str:
    return str(model_path(symbol, timeframe))


def list_models() -> list[dict[str, Any]]:
    """Enumera todos os modelos validos em Python/models."""
    out = []
    if not MODELS_DIR.exists():
        return out
    for p in sorted(MODELS_DIR.glob("*.pkl")):
        stem = p.stem  # ex: XAUUSD_M5
        parts = stem.rsplit("_", 1)
        if len(parts) != 2:
            continue
        sym, tf = parts
        out.append(model_status(sym, tf))
    return out


# conveniencia para CLI
def registry_summary() -> str:
    models = list_models()
    if not models:
        return "REGISTRY | nenhum modelo encontrado em " + str(MODELS_DIR)
    lines = [f"REGISTRY | {len(models)} modelos | feature_version={FEATURE_VERSION}"]
    for m in models:
        lines.append(
            f"  {m['model']:14} {m['status']:12} age={m.get('age_hours','?')}h "
            f"size={round(m.get('size_bytes',0)/1e6,1)}MB"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(registry_summary())
    print("\nXAUUSD M5:", model_status("XAUUSD", "M5"))
    print("\nXAUUSD M15 (inexistente):", model_status("XAUUSD", "M15"))
