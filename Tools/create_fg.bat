@echo off
cd /d "C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO"

:: Cria o arquivo financial_graph.py
(
echo # -*- coding: utf-8 -*-
echo """Motor de analise por nografos (subgraphs) de mercado financeiro."""
echo from __future__ import annotations
echo import asyncio
echo from dataclasses import dataclass, field
echo from typing import Dict, List, Optional, Tuple
echo from datetime import datetime
echo import numpy as np
echo import pandas as pd
echo.
echo @dataclass
echo class AssetNode:
echo     symbol: str
echo     asset_class: str
echo     timeframe: str
echo     features: Dict[str, float] = field(default_factory=dict^)
echo.
echo     def __post_init__(self^) -> None:
echo         if not self.features:
echo             self.features = dict(rsi=50.0, macd_hist=0.0, atr=0.0, volatility=0.0, returns=0.0, zscore=0.0^)
echo.
echo @dataclass
echo class CorrelationEdge:
echo     source: str
echo     target: str
echo     correlation: float
echo     lag: int = 0
echo     strength: str = "weak"
echo.
echo def _compute_tech_features(df^) -> Dict[str, float]:
echo     closes = df["close"^]
echo     diffs = closes.diff(^)
echo     gains = diffs.clip(lower=0^).rolling(14^).mean(^)
echo     losses = -diffs.clip(upper=0^).rolling(14^).mean(^)
echo     rsi = float(100 - (100 / (1 + (gains / losses.replace(0, np.nan)).iloc[-1]))
echo     macd_line = closes.ewm(span=12, adjust=False^).mean(^) - closes.ewm(span=26, adjust=False^).mean(^)
echo     signal = macd_line.ewm(span=9, adjust=False^).mean(^)
echo     macd_hist = float((macd_line - signal^).iloc[-1])
echo     tr = pd.concat([(df["high"^] - df["low"^]).abs(^), (df["high"^] - df["close"^].shift(^)).abs(^), (df["low"^] - df["close"^].shift(^)).abs(^)], axis=1^).max(axis=1^)
echo     atr = float(tr.rolling(14^).mean(^).iloc[-1])
echo     vol = float(diffs.std(^))
echo     return dict(rsi=rsi, macd_hist=macd_hist, atr=atr, volatility=vol, returns=float(diffs.iloc[-1]), zscore=float((closes.iloc[-1] - closes.mean(^^) ) / closes.std(^^^)^))
echo.
echo class FinancialSubgraph:
echo     def __init__(self^, lookback_bars: int = 100^, max_lag: int = 5^):
echo         self.lookback_bars = lookback_bars
echo         self.max_lag = max_lag
echo         self.nodes = {}
echo         self.edges = []
echo         self._lock = asyncio.Lock(^)
echo.
echo     async def ingest_asset(self^, symbol: str^, df: pd.DataFrame^, asset_class: str = "metal"^, timeframe: str = "M5"^) -> AssetNode:
echo         if df.empty or len(df^) < 14:
echo             raise ValueError(f"DataFrame para {symbol} muito pequeno"^)
echo         df_tail = df.tail(self.lookback_bars^)
echo         features = _compute_tech_features(df_tail^)
echo         node = AssetNode(symbol^=symbol^, asset_class^=asset_class^, timeframe^=timeframe^, features^=features^)
echo         async with self._lock:
echo             self.nodes[symbol] = node
echo         return node
echo.
echo     async def compute_correlations(self^) -> List:
echo         async with self._lock:
echo             symbols = list(self.nodes.keys(^))
echo         if len(symbols^) < 2:
echo             return []
echo         edges = []
echo         for i, sym_a in enumerate(symbols^):
echo             for sym_b in symbols[i + 1:]:
echo                 ret_a = self.nodes[sym_a].features.get("returns", 0.0^)
echo                 ret_b = self.nodes[sym_b].features.get("returns", 0.0^)
echo                 corr = float(np.corrcoef([ret_a], [ret_b])[0, 1])
echo                 lag = 0
echo                 strength = "strong" if abs(corr^) > 0.7 else "medium" if abs(corr^) > 0.4 else "weak"
echo                 edges.append(CorrelationEdge(source^=sym_a^, target^=sym_b^, correlation^=corr^, lag^=lag^, strength^=strength^)^)
echo         async with self._lock:
echo             self.edges = sorted(edges^, key=lambda e: abs(e.correlation^), reverse=True^)
echo         return self.edges
echo.
echo     async def detect_regime_shift(self^) -> Dict:
echo         async with self._lock:
echo             snapshot = dict(self.nodes^)
echo         vols = [n.features.get("volatility", 0.0^) for n in snapshot.values(^)]
echo         avg_vol = float(np.mean(vols^)) if vols else 0.0
echo         moms = [n.features.get("returns", 0.0^) for n in snapshot.values(^)]
echo         avg_mom = float(np.mean(moms^)) if moms else 0.0
echo         regime = "risk_on" if avg_vol < 0.02 and avg_mom > 0 else "risk_off" if avg_vol > 0.04 and avg_mom < 0 else "neutral"
echo         return dict(timestamp=datetime.utcnow().isoformat(^), regime^=regime^, avg_volatility^=avg_vol^, avg_momentum^=avg_mom^, node_count^=len(snapshot^)^)
echo.
echo     async def to_dict(self^) -> Dict:
echo         async with self._lock:
echo             nodes_data = {s: dict(symbol^=n.symbol^, asset_class^=n.asset_class^, timeframe^=n.timeframe^, features^=n.features^) for s, n in self.nodes.items(^)}
echo             edges_data = [dict(source^=e.source^, target^=e.target^, correlation^=round(e.correlation^, 4^)^, lag^=e.lag^, strength^=e.strength^) for e in self.edges]
echo         return dict(timestamp^=datetime.utcnow().isoformat(^), lookback_bars^=self.lookback_bars^, nodes^=nodes_data^, edges^=edges_data^)
echo.
echo async def create_financial_subgraph(lookback: int = 100^) -> FinancialSubgraph:
echo     return FinancialSubgraph(lookback_bars^=lookback^)
) > "mcp\subgrp\financial_graph.py"

echo [OK] financial_graph.py criado
py_compile "mcp\subgrp\financial_graph.py"
if %errorlevel% equ 0 (
  echo [OK] financial_graph.py compila sem erros
) else (
  echo [ERRO] financial_graph.py tem problemas de sintaxe
)