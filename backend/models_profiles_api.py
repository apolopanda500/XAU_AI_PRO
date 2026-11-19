# -*- coding: utf-8 -*-
"""Perfis de modelo por ativo — 100% dinâmicos, zero ativo fixo."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "Models" / "production_universal" / "model_manifest.json"

_METRICS_FALLBACK: dict[str, Any] = {
    "model_id": "modelo_sem_manifesto",
    "roc_auc": 0.5,
    "precision_pct": 50.0,
    "feature_count": 18,
}


def load_manifest_metrics(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    if not path.exists():
        return dict(_METRICS_FALLBACK)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        oos = data.get("metrics_oos") or {}
        return {
            "model_id": str(data.get("model_id") or _METRICS_FALLBACK["model_id"]),
            "roc_auc": float(oos.get("roc_auc", _METRICS_FALLBACK["roc_auc"])),
            "precision_pct": round(float(oos.get("precision_at_threshold", 0.5)) * 100.0, 1),
            "feature_count": int(data.get("feature_count", 18)),
        }
    except (ValueError, TypeError, OSError, KeyError):
        return dict(_METRICS_FALLBACK)


def build_asset_profile_from_spec(spec: dict[str, Any], model_meta: dict[str, Any]) -> dict[str, Any]:
    symbol = str(spec.get("symbol", "")).strip()
    category = str(spec.get("category") or spec.get("asset_class") or "").upper()
    try:
        spread = int(spec.get("spread", 15))
    except (TypeError, ValueError):
        spread = 15
    try:
        atr_pts = int(spec.get("atr_points", 120))
    except (TypeError, ValueError):
        atr_pts = 120
    timeframe = str(spec.get("timeframe", "M15"))

    if "METAL" in category:
        max_spread, min_atr, min_adx, sessao = 45, 110, 22, "Londres / Nova York"
    elif "INDEX" in category or "INDICE" in category:
        max_spread, min_atr, min_adx, sessao = 60, 150, 24, "Abertura NY"
    elif "CRYPTO" in category:
        max_spread, min_atr, min_adx, sessao = 80, 200, 25, "Contínuo 24/7"
    else:
        max_spread, min_atr, min_adx, sessao = 25, 45, 20, "Europa / América"

    if spread > max_spread:
        status = "HIGH_SPREAD_VETO"
    elif atr_pts < min_atr:
        status = "LOW_VOLATILITY"
    else:
        status = "READY"

    return {
        "symbol": symbol,
        "assetClass": category or "FOREX",
        "timeframe": timeframe,
        "modelId": model_meta["model_id"],
        "rocAuc": model_meta["roc_auc"],
        "precisionPct": model_meta["precision_pct"],
        "featureCount": model_meta["feature_count"],
        "requirements": {"minAtrPoints": min_atr, "maxSpreadPoints": max_spread, "minAdx": min_adx, "preferredSession": sessao},
        "liveStatus": status,
    }


def build_profiles(catalog: list[dict[str, Any]], model_meta: dict[str, Any]) -> list[dict[str, Any]]:
    return [build_asset_profile_from_spec(item, model_meta) for item in catalog
            if isinstance(item, dict) and str(item.get("symbol", "")).strip()]


def parse_catalog(raw: str) -> list[dict[str, Any]]:
    try:
        dado = json.loads(raw or "[]")
    except (ValueError, TypeError):
        return []
    return [item for item in dado if isinstance(item, dict)] if isinstance(dado, list) else []
