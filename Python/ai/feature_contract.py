# -*- coding: utf-8 -*-
"""ETAPA 18.2 - Contrato Operacional de Features (25F).

Fecha definitivamente treinamento == prediccao:
  nomes, quantidade, ordem, versao do feature set.
Somente importa deste modulo o FEATURES canonico (nao duplicar em outros).

Esta camada valida:
  - ordem das features
  - presenca de NaN (rejeicao)
  - tipos esperados
  - versao do feature set (hash) para deteccao de drift

Uso:
    from feature_contract import FEATURES, FEATURE_VERSION, validate_feature_frame
"""
from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
import pandas as pd

# Versao do feature set (bump a cada mudanca estrutural de FEATURES)
FEATURE_VERSION = "25F-v1"

# Contrato canonico de 25 features (fonte unica - NAO duplicar)
FEATURES: list[str] = [
    "Open", "High", "Low", "Close", "Volume", "Spread",          # 6 base
    "ATR", "ADX", "RSI",                                          # 3 indicadores
    "KCI_VD", "KCI_MAIN", "KDI_PLUS", "KDI_MINUS",               # 4 KCI/KDI
    "BodySize", "RangeSize", "UpperShadow", "LowerShadow",        # 4 candles
    "ATR_Pct", "RSI_Diff", "Close_Diff", "Volume_MA",            # 4 derivadas
    "ADX_Change", "KCI_VD_Pct", "KDI_Diff", "KCI_MAIN_Change",   # 4 tendencia
]  # total = 25

# tipos esperados (colunas numericas)
_NUMERIC_COLS = set(FEATURES)


def feature_hash() -> str:
    """Hash das features (ordem + nomes) - detecta drift de feature set."""
    return hashlib.sha256("|".join(FEATURES).encode("utf-8")).hexdigest()[:16]


def validate_feature_frame(df: pd.DataFrame) -> dict[str, Any]:
    """Valida DataFrame contra o contrato 25F.

    Retorna dict com status valid/invalid + razoes detalhadas.
    Nunca levanta excecao (sempre reporta estado).
    """
    result: dict[str, Any] = {
        "feature_version": FEATURE_VERSION,
        "feature_hash": feature_hash(),
        "expected_count": len(FEATURES),
        "status": "VALID",
        "errors": [],
    }
    cols = list(df.columns)

    # 1. Quantidade de features
    if len(cols) != len(FEATURES):
        result["status"] = "FEATURE_ERROR"
        result["errors"].append(
            f"count_mismatch: esperado={len(FEATURES)} obtido={len(cols)}"
        )

    # 2. Nomes/ordem exata
    if cols != FEATURES:
        wrong = [i for i, (a, b) in enumerate(zip(cols, FEATURES)) if a != b]
        result["status"] = "FEATURE_ERROR"
        result["errors"].append(f"order/name_mismatch em indices: {wrong[:10]}")

    # 3. Tipos numericos
    for c in FEATURES:
        if c in df.columns and not pd.api.types.is_numeric_dtype(df[c]):
            result["status"] = "FEATURE_ERROR"
            result["errors"].append(f"tipo_nao_numerico: {c}")

    # 4. NaN / infinito (rejeicao - dados invalidos nao viram previsao)
    nan_cols = []
    for c in FEATURES:
        if c in df.columns:
            try:
                if df[c].isna().any() or np.isinf(df[c]).any():
                    nan_cols.append(c)
            except Exception:  # noqa: BLE001
                nan_cols.append(c)
    if nan_cols:
        result["status"] = "FEATURE_ERROR"
        result["errors"].append(f"nan/inf presente em: {nan_cols[:10]}")

    return result


def prepare_features_contract(df: pd.DataFrame) -> pd.DataFrame:
    """Versao do contrato de prepare_features: retorna X na ordem canonica.

    Valida e levanta ValueError com detalhes claros (para treino/predicao).
    """
    missing = [f for f in FEATURES if f not in df.columns]
    if missing:
        raise ValueError(f"Features ausentes no contrato 25F: {missing}")
    x = df[FEATURES].copy()
    if x.isna().any().any():
        raise ValueError("Features com NaN - rejeitado pelo contrato")
    return x


if __name__ == "__main__":
    print(f"CONTRATO 18.2 | {len(FEATURES)} features | versao={FEATURE_VERSION} hash={feature_hash()}")
    print(feature_hash.__doc__ or "")
