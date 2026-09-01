# -*- coding: utf-8 -*-
"""Análise de relações entre ativos, estritamente em modo somente leitura."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

_REQUIRED = {"open", "high", "low", "close"}


@dataclass
class AssetNode:
    symbol: str
    asset_class: str
    timeframe: str
    features: dict[str, float] = field(default_factory=dict)
    returns: pd.Series = field(default_factory=lambda: pd.Series(dtype=float), repr=False)


@dataclass
class CorrelationEdge:
    source: str
    target: str
    correlation: float
    lag: int = 0
    strength: str = "weak"
    samples: int = 0


def _number(value: Any, default: float = 0.0) -> float:
    """Garante valor numérico finito para UI e JSON."""
    try:
        value = float(value)
        return value if np.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def _candles(df: pd.DataFrame) -> pd.DataFrame:
    """Valida candles OHLCV recebidos de fontes externas."""
    missing = _REQUIRED.difference(df.columns)
    if missing:
        raise ValueError(f"Candles sem colunas: {', '.join(sorted(missing))}")
    clean = df.copy()
    for column in _REQUIRED:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")
    clean = clean.dropna(subset=list(_REQUIRED))
    if len(clean) < 30:
        raise ValueError("São necessários pelo menos 30 candles válidos")
    return clean


def _features(df: pd.DataFrame) -> tuple[dict[str, float], pd.Series]:
    """Calcula indicadores técnicos e retorna série de retornos logarítmicos."""
    candles = _candles(df)
    close = candles["close"].astype(float)
    returns = np.log(close / close.shift()).replace([np.inf, -np.inf], np.nan).dropna()
    if len(returns) < 20:
        raise ValueError("Retornos insuficientes para análise")
    delta = close.diff()
    gains = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    losses = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
    rsi = 100 - (100 / (1 + gains / losses.replace(0, np.nan)))
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal = macd.ewm(span=9, adjust=False).mean()
    tr = pd.concat([
        candles["high"] - candles["low"],
        (candles["high"] - close.shift()).abs(),
        (candles["low"] - close.shift()).abs(),
    ], axis=1).max(axis=1)
    std = close.std()
    features = {
        "rsi": _number(rsi.iloc[-1], 50.0),
        "macd_hist": _number((macd - signal).iloc[-1]),
        "atr": _number(tr.rolling(14, min_periods=14).mean().iloc[-1]),
        "volatility": _number(returns.std()),
        "returns": _number(returns.iloc[-1]),
        "zscore": _number((close.iloc[-1] - close.mean()) / std if std else 0.0),
    }
    return features, returns


def _best_correlation(first: pd.Series, second: pd.Series, max_lag: int) -> tuple[float, int, int]:
    """Calcula a melhor correlação Pearson entre duas séries alinhadas."""
    frame = pd.concat([first.rename("first"), second.rename("second")], axis=1).dropna()
    best = (0.0, 0, len(frame))
    for lag in range(-max_lag, max_lag + 1):
        pair = pd.concat([frame["first"], frame["second"].shift(lag)], axis=1).dropna()
        if len(pair) < 20:
            continue
        corr = _number(pair.iloc[:, 0].corr(pair.iloc[:, 1]))
        if abs(corr) > abs(best[0]):
            best = (corr, lag, len(pair))
    return best


class FinancialSubgraph:
    """Grafo financeiro em memória; não envia ordens nem altera o MT5."""

    def __init__(self, lookback_bars: int = 300, max_lag: int = 5) -> None:
        self.lookback_bars = max(30, int(lookback_bars))
        self.max_lag = max(0, min(int(max_lag), 30))
        self.nodes: dict[str, AssetNode] = {}
        self.edges: list[CorrelationEdge] = []
        self._lock = asyncio.Lock()

    async def ingest_asset(self, symbol: str, df: pd.DataFrame, asset_class: str = "unknown", timeframe: str = "M5") -> AssetNode:
        features, returns = _features(_candles(df).tail(self.lookback_bars))
        node = AssetNode(symbol.upper().strip(), asset_class, timeframe.upper().strip(), features, returns)
        async with self._lock:
            self.nodes[node.symbol] = node
        return node

    async def compute_correlations(self) -> list[CorrelationEdge]:
        async with self._lock:
            nodes = dict(self.nodes)
        edges: list[CorrelationEdge] = []
        symbols = sorted(nodes)
        for index, source in enumerate(symbols):
            for target in symbols[index + 1:]:
                corr, lag, samples = _best_correlation(nodes[source].returns, nodes[target].returns, self.max_lag)
                strength = "strong" if abs(corr) >= 0.70 else "medium" if abs(corr) >= 0.40 else "weak"
                edges.append(CorrelationEdge(source, target, corr, lag, strength, samples))
        edges.sort(key=lambda edge: abs(edge.correlation), reverse=True)
        async with self._lock:
            self.edges = edges
        return edges

    async def detect_regime_shift(self) -> dict[str, Any]:
        async with self._lock:
            nodes = list(self.nodes.values())
        volatility = _number(np.mean([node.features["volatility"] for node in nodes])) if nodes else 0.0
        momentum = _number(np.mean([node.features["returns"] for node in nodes])) if nodes else 0.0
        regime = "risk_on" if momentum > 0 and volatility < 0.02 else "risk_off" if momentum < 0 and volatility > 0.02 else "neutral"
        return {"timestamp": datetime.now(timezone.utc).isoformat(), "regime": regime,
                "avg_volatility": volatility, "avg_momentum": momentum,
                "node_count": len(nodes), "mode": "analysis_only"}

    async def to_dict(self) -> dict[str, Any]:
        async with self._lock:
            nodes = {key: {**asdict(value), "returns": None} for key, value in self.nodes.items()}
            edges = [asdict(edge) for edge in self.edges]
        return {"timestamp": datetime.now(timezone.utc).isoformat(), "lookback_bars": self.lookback_bars,
                "max_lag": self.max_lag, "nodes": nodes, "edges": edges, "mode": "analysis_only"}