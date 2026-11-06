# -*- coding: utf-8 -*-
"""ETAPA 18.3 - Model Registry (fonte unica de verdade dos modelos).

Convencao unica: Python/models/{SYMBOL}_{TIMEFRAME}.pkl
Responde: exists, is_ready, version, age, feature_version, path, status.

Estados (18.1): READY / STALE / UNAVAILABLE / ERROR / TRAINING
Nenhum modelo inexistente pode ser interpretado como valido.
"""
from __future__ import annotations

import os
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _resolve_models_dir() -> Path:
    """Resolve o diretorio de modelos.

    Ordem de prioridade (para suporte a download sob demanda):
      1. Variavel de ambiente XAU_AI_PRO_MODELS (maquina de destino / instalador);
      2. Subpasta 'models' junto a este modulo (Python/models);
      3. Fallback: <raiz>/Python/models.

    No bundle congelado o `__file__` fica dentro de `<instalacao>/bridge/_internal`,
    entao o `mkdir` abaixo criava um diretorio VAZIO dentro de Program Files.
    Esse dir vazio passava a vencer a resolucao de modelos do gateway e
    `/api/ai/trained` devolvia `models: []`. No app instalado apenas LEMOS:
    nada aqui escreve dentro do pacote.
    """
    env = os.getenv("XAU_AI_PRO_MODELS", "").strip()
    if env:
        p = Path(env).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p
    default = Path(__file__).resolve().parent.parent / "Python" / "models"
    if not getattr(sys, "frozen", False):
        default.mkdir(parents=True, exist_ok=True)
    return default


MODELS_DIR = _resolve_models_dir()
# P1.48 (01/11/2026): esta constante dizia "25F" e mentia sobre o contrato real.
# MEDIDO nos artefactos: os .meta.json gravados por train_v2 dizem
# feature_version = "25F-v2" com feature_count = 25. Passa a coincidir com
# Python/ai/train_v2.py::FEATURE_VERSION, e model_status le o valor do
# proprio artefacto quando ele existe (o artefacto e a fonte, o constante e
# apenas o fallback).
FEATURE_VERSION = "25F-v2"       # contrato 25 features (ETAPA 15.2.2 / train_v2)
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


# P1.48 (01/11/2026): o registo do gateway ignorava o veredicto de publicacao.
# MEDIDO: backend/ai_inference.py recusa servir um modelo cujo .meta.json diz
# publicable=false, mas este registo (consumido por prediction_gateway.py)
# devolvia READY a esse mesmo modelo. Dois lados do mesmo dado a discordarem
# sobre o mesmo nome de estado. Le-se o .meta.json ao lado do pickle e o
# veredicto passa a valer ca dentro. Sem .meta.json nada muda (compatibilidade
# com artefactos antigos), mas a ausencia fica registada como publicable=None
# em vez de ser apresentada como publicavel.
def _read_meta(p: Path) -> dict:
    meta = p.with_suffix(".meta.json")
    if not meta.exists():
        return {}
    try:
        return json.loads(meta.read_text(encoding="utf-8"))
    except Exception:
        return {}


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
        # P1.48: o artefacto e a fonte. O .meta.json manda no veredicto de
        # publicacao e na versao de features; as constantes sao so fallback.
        meta = _read_meta(p)
        feat_ver = str(meta.get("feature_version") or FEATURE_VERSION)
        feat_count = meta.get("feature_count")
        publicable = meta.get("publicable", None)
        publish_reason = str(meta.get("publish_reason") or "")
        if publicable is False:
            # Recusa identica a de backend/ai_inference.py: um modelo
            # reprovado na porta de edge nao pode ser servido com READY.
            return {
                "symbol": symbol, "timeframe": timeframe.upper(),
                "model": f"{symbol}_{timeframe.upper()}", "path": str(p),
                "exists": True, "status": ERROR,
                "reason": "not_publishable: " + (publish_reason or "publicable=false"),
                "publicable": False, "publish_reason": publish_reason,
                "age_sec": int(age_sec), "age_hours": round(age_sec / 3600, 1),
                "size_bytes": size, "model_version": MODEL_VERSION,
                "feature_version": feat_ver, "feature_count": feat_count,
                "type": "pickle",
            }
        status = READY if age_sec <= MAX_AGE_READY_SEC else STALE
        return {
            "symbol": symbol, "timeframe": timeframe.upper(),
            "model": f"{symbol}_{timeframe.upper()}", "path": str(p),
            "exists": True, "status": status, "reason": "ok" if status == READY else "model_stale",
            "publicable": publicable,
            "age_sec": int(age_sec), "age_hours": round(age_sec / 3600, 1),
            "size_bytes": size, "model_version": MODEL_VERSION,
            "feature_version": feat_ver, "feature_count": feat_count,
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


def model_catalog() -> list[dict[str, Any]]:
    """Inventário somente leitura; não desserializa modelos nem presume treino pelo nome."""
    catalog = []
    for item in list_models():
        path = Path(item["path"])
        meta_path = path.with_suffix(".meta.json")
        entry: dict[str, Any] = {
            "artifact": path.name,
            "status": item["status"],
            "training_verified": False,
            "training_metadata_status": "missing",
            "trained_symbol": None,
            "trained_timeframe": None,
            "train_date": None,
            "algorithm": None,
            "model_version": None,
            "dataset_version": None,
            "feature_count": None,
        }
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if not isinstance(meta, dict):
                    raise ValueError("metadados não são um objeto")
                symbol = meta.get("symbol")
                timeframe = meta.get("timeframe")
                if symbol != item["symbol"] or timeframe != item["timeframe"]:
                    entry["training_metadata_status"] = "mismatch"
                else:
                    entry.update({
                        "trained_symbol": symbol,
                        "trained_timeframe": timeframe,
                        "train_date": meta.get("train_date"),
                        "algorithm": meta.get("algorithm"),
                        "model_version": meta.get("model_version"),
                        "dataset_version": meta.get("dataset_version"),
                        "feature_count": meta.get("feature_count"),
                    })
                    entry["training_metadata_status"] = "present"
            except (OSError, ValueError, UnicodeError):
                entry["training_metadata_status"] = "invalid"
        catalog.append(entry)
    return catalog


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
