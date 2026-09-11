# -*- coding: utf-8 -*-
"""Testes das funcoes de indicadores e persistencia de layout da aba Graficos."""
import math

from app.tabs.charts import (_atr, _bb, _ema, _rsi, _sma, _vwap,
                             deserialize_layout, serialize_layout)


def _mk_candles(n=30, start=100.0, step=0.5, vol=10):
    out = []
    price = start
    for i in range(n):
        o = price
        c = price + (1 if i % 2 == 0 else -1) * step
        out.append({"time": str(i), "open": o, "high": max(o, c) + 0.1,
                    "low": min(o, c) - 0.1, "close": c, "volume": vol})
        price = c
    return out


def test_sma_periodos():
    assert _sma([1, 2, 3, 4], 2) == [1, 1.5, 2.5, 3.5]
    assert _sma([5, 5, 5], 3) == [5, 5, 5]


def test_ema_comprimento_e_primeiro():
    vals = [10.0, 11.0, 12.0, 11.5]
    out = _ema(vals, 3)
    assert len(out) == len(vals)
    assert out[0] == 10.0
    assert out[-1] > 11.0  # segue a serie


def test_bollinger_ordem():
    vals = [float(i) for i in range(30)]
    mid, up, lo = _bb(vals, 20, 2.0)
    assert len(mid) == len(up) == len(lo) == 30
    assert all(u >= m >= l for u, m, l in zip(up, mid, lo))
    assert math.isclose(mid[-1], _sma(vals, 20)[-1])


def test_rsi_faixa():
    vals = [float(i) for i in range(1, 31)]  # tendencia de alta
    out = _rsi(vals, 14)
    assert len(out) == 30
    assert all(0.0 <= v <= 100.0 for v in out)
    assert out[-1] > 50


def test_rsi_tendencia_baixa():
    vals = [float(30 - i) for i in range(30)]
    out = _rsi(vals, 14)
    assert out[-1] < 50


def test_atr_comprimento_e_nones():
    candles = _mk_candles(30)
    out = _atr(candles, 14)
    assert len(out) == 30
    assert out[0:14] == [None] * 14
    assert all(v is not None and v > 0 for v in out[14:])
    assert out[15] is not None


def test_vwap_volume_constante_segue_typical():
    candles = _mk_candles(10, vol=5)
    out = _vwap(candles)
    assert len(out) == 10
    # com volume constante, VWAP acumulado converge para a media de typical
    import statistics
    typ = [(c["high"] + c["low"] + c["close"]) / 3.0 for c in candles]
    assert math.isclose(out[-1], statistics.mean(typ), abs_tol=1e-9)


def test_layout_round_trip():
    inds = {"sma20": {"type": "sma", "period": 20, "color": "#FF00FF"},
            "rsi14": {"type": "rsi", "period": 14}}
    drawings = [{"tool": "trend", "pts": [(0.1, 100.0), (0.9, 105.5)]},
                {"tool": "fib", "pts": [(0.2, 98.0), (0.8, 110.0)]},
                {"tool": "hline", "pts": [(0.0, 101.25)]}]
    payload = serialize_layout(inds, drawings)
    inds2, drw2 = deserialize_layout(payload)
    assert set(inds2) == set(inds)
    assert inds2["sma20"]["period"] == 20
    assert len(drw2) == 3
    assert drw2[0]["tool"] == "trend"
    assert drw2[0]["pts"][1] == (0.9, 105.5)
    assert drw2[2]["pts"][0][1] == 101.25


def test_deserialize_rejeita_lixo():
    inds, drw = deserialize_layout({"indicators": [{"name": "x", "period": "abc"}],
                                    "drawings": [{"tool": "rect", "pts": [(0.0, 1.0), (0.5, "x")]},
                                                 {"tool": "free", "pts": "nao-e-lista"},
                                                 "lixo"]})
    assert "x" in inds
    assert inds["x"]["period"] == "abc"
    assert len(drw) == 0