import sys, os

code = r'''
# -*- coding: utf-8 -*-
"""Motor de analise por nografos (subgraphs) de mercado financeiro."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np
import pandas as pd


@dataclass
class AssetNode:
    symbol: str
    asset_class: str
    timeframe: str
    features: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not self.features:
            self.features = dict(rsi=50.0, macd_hist=0.0, atr=0.0, volatility=0.0, returns=0.0, zscore=0.0)


@dataclass
class CorrelationEdge:
    source: str
    target: str
    correlation: float
    lag: int = 0
    strength: str = "weak"
'''

target = os.path.join(os.path.dirname(__file__), "mcp", "subgrp", "financial_graph.py")
os.makedirs(os.path.dirname(target), exist_ok=True)
with open(target, "w", encoding="utf-8") as f:
    f.write(code)
print(f"[OK] Parte 1 escrita: {target}")

# Parte 2: Adiciona helpers e classe FinancialSubgraph
with open(target, "a", encoding="utf-8") as f:
    f.write(r'''

def _tech_features(df):
    """Calcula features tecnicas."""
    closes = df["close"]
    diffs = closes.diff()
    gains = diffs.clip(lower=0).rolling(14).mean()
    losses = -diffs.clip(upper=0).rolling(14).mean()
    rsi = float(100 - (100 / (1 + (gains / losses.replace(0, np.nan))).iloc[-1])
    ema12 = closes.ewm(span=12, adjust=False).mean()
    ema26 = closes.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = float((macd_line - signal).iloc[-1])
    tr = pd.concat([
        (df["high"] - df["low"]).abs(),
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs()
    ], axis=1).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1])
    vol = float(diffs.std())
    return dict(
        rsi=rsi, macd_hist=macd_hist, atr=atr, volatility=vol,
        returns=float(diffs.iloc[-1]),
        zscore=float((closes.iloc[-1] - closes.mean()) / closes.std())
    )


def _cross_corr(s1, s2, max_lag=5):
    """Correlacao cruzada com deteccao de lag."""
    s1n = (s1 - s1.mean()) / s1.std()
    s2n = (s2 - s2.mean()) / s2.std()
    best_corr, best_lag = 0.0, 0
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            corr = (s1n.iloc[:lag] * s2n.iloc[-lag:]).mean()
        elif lag > 0:
            corr = (s1n.iloc[lag:] * s2n.iloc[:-lag]).mean()
        else:
            corr = (s1n * s2n).mean()
        if abs(corr) > abs(best_corr):
            best_corr, best_lag = float(corr), lag
    return best_corr, best_lag


class FinancialSubgraph:
    """Motor de analise por nografos de mercado financeiro."""

    def __init__(self, lookback_bars=100, max_lag=5):
        self.lookback_bars = lookback_bars
        self.max_lag = max_lag
        self.nodes = {}
        self.edges = []
        self._lock = asyncio.Lock()

    async def ingest_asset(self, symbol, df, asset_class="metal", timeframe="M5"):
        """Ingere dados OHLCV de um ativo."""
        if df.empty or len(df) < 14:
            raise ValueError(f"DataFrame para {symbol} muito pequeno")
        df_tail = df.tail(self.lookback_bars)
        features = _tech_features(df_tail)
        node = AssetNode(symbol=symbol, asset_class=asset_class,
                         timeframe=timeframe, features=features)
        async with self._lock:
            self.nodes[symbol] = node
        return node

    async def compute_correlations(self):
        """Calcula correlacoes entre todos os nos."""
        async with self._lock:
            symbols = list(self.nodes.keys())
        if len(symbols) < 2:
            return []
        edges = []
        for i, a in enumerate(symbols):
            for b in symbols[i + 1:]:
                ra = self.nodes[a].features.get("returns", 0.0)
                rb = self.nodes[b].features.get("returns", 0.0)
                corr, lag = _cross_corr(pd.Series([ra]), pd.Series([rb]), self.max_lag)
                strength = "strong" if abs(corr) > 0.7 else "medium" if abs(corr) > 0.4 else "weak"
                edges.append(CorrelationEdge(source=a, target=b, correlation=corr, lag=lag, strength=strength))
        async with self._lock:
            self.edges = sorted(edges, key=lambda e: abs(e.correlation), reverse=True)
        return self.edges

    async def detect_regime_shift(self):
        """Detecta mudanca de regime de mercado."""
        async with self._lock:
            snapshot = dict(self.nodes)
        vols = [n.features.get("volatility", 0.0) for n in snapshot.values()]
        avg_vol = float(np.mean(vols)) if vols else 0.0
        moms = [n.features.get("returns", 0.0) for n in snapshot.values()]
        avg_mom = float(np.mean(moms)) if moms else 0.0
        regime = "risk_on" if avg_vol < 0.02 and avg_mom > 0 else "risk_off" if avg_vol > 0.04 and avg_mom < 0 else "neutral"
        return dict(timestamp=datetime.utcnow().isoformat(), regime=regime, avg_volatility=avg_vol, avg_momentum=avg_mom, node_count=len(snapshot))

    async def to_dict(self):
        """Serializa estado."""
        async with self._lock:
            nodes_data = {s: dict(symbol=n.symbol, asset_class=n.asset_class, timeframe=n.timeframe, features=n.features) for s, n in self.nodes.items()}
            edges_data = [dict(source=e.source, target=e.target, correlation=round(e.correlation, 4), lag=e.lag, strength=e.strength) for e in self.edges]
        return dict(timestamp=datetime.utcnow().isoformat(), lookback_bars=self.lookback_bars, nodes=nodes_data, edges=edges_data)


async def create_financial_subgraph(lookback=100):
    """Factory assincrona."""
    return FinancialSubgraph(lookback_bars=lookback)
''')

print("[OK] Parte 2 (classe + helpers) escrita")

# Parte 3: Valida sintaxe
import py_compile
try:
    py_compile.compile(target, doraise=True)
    print("[OK] financial_graph.py compila sem erros")
except py_compile.PyCompileError as e:
    print(f"[ERRO] {e}")
    sys.exit(1)
