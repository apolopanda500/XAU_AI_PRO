# -*- coding: utf-8 -*-
import asyncio

import numpy as np
import pandas as pd
import pytest

from mcp.subgrp.financial_graph import FinancialSubgraph


def candles(seed: int, periods: int = 160) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 2000 + np.cumsum(rng.normal(0, 1, periods))
    return pd.DataFrame({
        "open": close - 0.2, "high": close + 0.8, "low": close - 0.8,
        "close": close, "volume": rng.integers(100, 1000, periods),
    }, index=pd.date_range("2026-01-01", periods=periods, freq="5min", tz="UTC"))


def test_rejects_incomplete_candles() -> None:
    with pytest.raises(ValueError, match="colunas"):
        asyncio.run(FinancialSubgraph().ingest_asset("XAUUSD", pd.DataFrame({"close": [1] * 40})))


def test_ingests_features_and_exports_json_safe_data() -> None:
    graph = FinancialSubgraph(lookback_bars=120)
    asyncio.run(graph.ingest_asset("XAUUSD", candles(1), "metal", "M5"))
    assert 0 <= graph.nodes["XAUUSD"].features["rsi"] <= 100
    assert len(graph.nodes["XAUUSD"].returns) >= 100
    report = asyncio.run(graph.to_dict())
    assert report["mode"] == "analysis_only"
    assert report["nodes"]["XAUUSD"]["returns"] is None


def test_computes_pairwise_correlation_with_real_series() -> None:
    graph = FinancialSubgraph(lookback_bars=150, max_lag=3)
    asyncio.run(graph.ingest_asset("XAUUSD", candles(2), "metal", "M5"))
    asyncio.run(graph.ingest_asset("BTCUSD", candles(3), "crypto", "M5"))
    edges = asyncio.run(graph.compute_correlations())
    assert len(edges) == 1
    assert edges[0].samples >= 20
    assert -1.0 <= edges[0].correlation <= 1.0
    assert abs(edges[0].lag) <= 3


def test_regime_is_analysis_only() -> None:
    graph = FinancialSubgraph()
    asyncio.run(graph.ingest_asset("XAUUSD", candles(4), "metal", "M5"))
    regime = asyncio.run(graph.detect_regime_shift())
    assert regime["mode"] == "analysis_only"
    assert regime["regime"] in {"risk_on", "risk_off", "neutral"}