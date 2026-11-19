# -*- coding: utf-8 -*-
"""Pipeline de modelos UNIVERSAIS (agnósticos de ativo) — 18 features.

Contrato rígido em FEATURE_COLUMNS, gravado no manifesto com SHA-256.
Imports de ML são LAZY: extração e leitura do manifesto são Python puro.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "Models" / "production_universal"
MANIFEST_PATH = MODELS_DIR / "model_manifest.json"

FEATURE_COLUMNS: tuple[str, ...] = (
    "ret_1", "ret_3", "ret_6", "ret_12",
    "ema_fast_dist", "ema_slow_dist", "ema_slope",
    "rsi_14", "adx_14", "atr_pct",
    "bb_pos", "bb_width", "vol_ratio",
    "spread_atr_ratio", "hour_sin", "hour_cos",
    "regime_trend", "regime_vol",
)


def read_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any] | None:
    try:
        dado = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return dado if isinstance(dado, dict) else None


def verify_manifest_integrity(path: Path = MANIFEST_PATH) -> tuple[bool, str]:
    manifest = read_manifest(path)
    if not manifest:
        return False, "manifesto ausente ou invalido"
    colunas = manifest.get("feature_columns")
    if not isinstance(colunas, list) or len(colunas) != len(FEATURE_COLUMNS):
        return False, "contrato de features divergente"
    if tuple(colunas) != FEATURE_COLUMNS:
        return False, "ordem/nomes das features divergem do contrato"
    artifact = manifest.get("artifact")
    if not artifact:
        return False, "artefato nao declarado"
    arquivo = path.parent / str(artifact)
    if not arquivo.exists():
        return False, "artefato ausente"
    if hashlib.sha256(arquivo.read_bytes()).hexdigest() != str(manifest.get("sha256", "")):
        return False, "SHA-256 divergente"
    return True, "integridade confirmada"


def _mean(valores: Sequence[float]) -> float:
    return sum(valores) / len(valores) if valores else 0.0


def build_agnostic_features_pure(rows: Sequence[dict[str, Any]]) -> list[dict[str, float]]:
    """18 features adimensionais em Python puro (sem pandas/numpy)."""
    import math as _math
    closes = [float(r.get("close", 0.0)) for r in rows]
    out: list[dict[str, float]] = []

    def ret(i: int, k: int) -> float:
        return closes[i] / closes[i - k] - 1.0 if i >= k and closes[i - k] else 0.0

    def ema(span: int) -> list[float]:
        alpha = 2.0 / (span + 1.0)
        serie: list[float] = []
        prev = closes[0] if closes else 0.0
        for c in closes:
            prev = alpha * c + (1.0 - alpha) * prev
            serie.append(prev)
        return serie

    ema20, ema50 = ema(20), ema(50)

    for i, r in enumerate(rows):
        close = closes[i]
        high = float(r.get("high", close))
        low = float(r.get("low", close))
        tick = float(r.get("tick_volume", 1.0))
        spread = float(r.get("spread", 0.0))

        trs = []
        for j in range(max(0, i - 13), i + 1):
            pc = closes[j - 1] if j > 0 else closes[j]
            trs.append(max(high - low, abs(high - pc), abs(low - pc)))
        atr = _mean(trs)
        atr_pct = atr / close if close else 0.0

        deltas = [closes[j] - closes[j - 1] for j in range(max(1, i - 13), i + 1)]
        ganho = _mean([max(d, 0.0) for d in deltas])
        perda = _mean([max(-d, 0.0) for d in deltas])
        rs = ganho / perda if perda else 50.0
        rsi = (100.0 - 100.0 / (1.0 + rs)) / 100.0

        janela = closes[max(0, i - 19): i + 1]
        sma = _mean(janela)
        var = _mean([(x - sma) ** 2 for x in janela]) if janela else 0.0
        std = var ** 0.5 or 1e-6
        bb_pos = max(-2.0, min(2.0, (close - sma) / (2.0 * std)))
        bb_width = (4.0 * std) / sma if sma else 0.0

        vols = [float(x.get("tick_volume", 1.0)) for x in rows[max(0, i - 19): i + 1]]
        vm = _mean(vols)
        vol_ratio = min(5.0, tick / vm) if vm else 1.0

        hora = 12.0
        ts = r.get("time")
        if ts:
            try:
                import datetime as _dt
                hora = float(_dt.datetime.utcfromtimestamp(float(ts)).hour) if isinstance(ts, (int, float)) else float(_dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).hour)
            except (ValueError, TypeError, OSError):
                hora = 12.0

        ema_slope = (ema20[i] / ema20[i - 3] - 1.0) if i >= 3 and ema20[i - 3] else 0.0
        janela_atr = [abs(closes[j] / closes[j - 1] - 1.0) if j > 0 and closes[j - 1] else 0.0 for j in range(max(1, i - 49), i + 1)]
        mediana = sorted(janela_atr)[len(janela_atr) // 2] if janela_atr else 0.0

        feat = {
            "ret_1": ret(i, 1), "ret_3": ret(i, 3), "ret_6": ret(i, 6), "ret_12": ret(i, 12),
            "ema_fast_dist": (close - ema20[i]) / close if close else 0.0,
            "ema_slow_dist": (close - ema50[i]) / close if close else 0.0,
            "ema_slope": ema_slope,
            "rsi_14": rsi,
            "adx_14": min(1.0, abs(ema_slope) / atr_pct) if atr_pct else 0.25,
            "atr_pct": atr_pct,
            "bb_pos": bb_pos, "bb_width": bb_width, "vol_ratio": vol_ratio,
            "spread_atr_ratio": min(2.0, spread / atr) if atr else 0.0,
            "hour_sin": _math.sin(2 * _math.pi * hora / 24.0),
            "hour_cos": _math.cos(2 * _math.pi * hora / 24.0),
            "regime_trend": 1.0 if ema20[i] > ema50[i] else 0.0,
            "regime_vol": 1.0 if atr_pct > mediana else 0.0,
        }
        limpo = {k: (0.0 if v != v or v in (float("inf"), float("-inf")) else float(v)) for k, v in feat.items()}
        out.append({k: limpo[k] for k in FEATURE_COLUMNS})
    return out


def build_agnostic_features(df: Any) -> Any:
    import pandas as pd  # lazy
    feats = build_agnostic_features_pure(df.to_dict("records"))
    return pd.DataFrame(feats, columns=list(FEATURE_COLUMNS), index=df.index[: len(feats)])


def train_and_export_universal_model(rows: Sequence[dict[str, Any]], model_tag: str = "xau_universal_v2") -> dict[str, Any]:
    try:
        import numpy as np
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.metrics import log_loss, precision_score, roc_auc_score
        import joblib
    except ImportError as exc:
        raise RuntimeError("treino exige scikit-learn, numpy e joblib") from exc

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    feats = build_agnostic_features_pure(rows)
    if len(feats) < 40:
        raise ValueError("candles insuficientes para treino (minimo 40)")
    closes = [float(r.get("close", 0.0)) for r in rows[: len(feats)]]
    X = [[f[k] for k in FEATURE_COLUMNS] for f in feats]
    y = []
    for i in range(len(feats)):
        if i + 6 >= len(closes) or closes[i] == 0:
            y.append(0)
        else:
            atr = feats[i]["atr_pct"] * closes[i]
            y.append(1 if (closes[i + 6] / closes[i] - 1.0) > (0.5 * atr / closes[i]) else 0)
    split = int(len(X) * 0.8)
    Xtr, Xte, ytr, yte = X[:split], X[split:], y[:split], y[split:]
    base = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.04, max_depth=5, random_state=42)
    clf = CalibratedClassifierCV(base, method="isotonic", cv=3)
    clf.fit(np.asarray(Xtr), np.asarray(ytr))
    probs = clf.predict_proba(np.asarray(Xte))[:, 1]
    preds = (probs >= 0.58).astype(int)
    auc = float(roc_auc_score(yte, probs)) if len(set(yte)) > 1 else 0.5
    precision = float(precision_score(yte, preds, zero_division=0))
    loss = float(log_loss(yte, probs, labels=[0, 1]))
    artifact = f"{model_tag}.joblib"
    arquivo = MODELS_DIR / artifact
    joblib.dump(clf, arquivo)
    manifest = {
        "model_id": model_tag, "status": "ACTIVE_CALIBRATED", "agnostic": True,
        "feature_count": len(FEATURE_COLUMNS), "feature_columns": list(FEATURE_COLUMNS),
        "decision_threshold": 0.58,
        "metrics_oos": {"roc_auc": round(auc, 4), "precision_at_threshold": round(precision, 4), "log_loss": round(loss, 4), "samples_oos": len(Xte)},
        "artifact": artifact, "sha256": hashlib.sha256(arquivo.read_bytes()).hexdigest(),
        "trained_at_utc": int(time.time()),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
