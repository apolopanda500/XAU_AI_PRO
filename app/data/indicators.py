# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""Indicadores tecnicos avancados para analise de mercado.

Inclui: MACD, Stochastic, Ichimoku, Parabolic SAR, Williams %R,
CCI, Momentum, OBV, Aroon, DMI, e todos os indicadores classicos.
"""
from __future__ import annotations

import math
from typing import Any

def _sma(vals: list[float], n: int) -> list[float]:
    out, s, q = [], 0.0, []
    for v in vals:
        q.append(v)
        s += v
        if len(q) > n:
            s -= q.pop(0)
        out.append(s / len(q) if len(q) < n else s / n)
    return out

def _ema(vals: list[float], n: int) -> list[float]:
    out, k = [], 2.0 / (n + 1)
    e = None
    for v in vals:
        e = v if e is None else v * k + e * (1 - k)
        out.append(e)
    return out

def _std(vals: list[float], n: int) -> list[float]:
    out = []
    for i in range(len(vals)):
        w = vals[max(0, i - n + 1):i + 1]
        m = sum(w) / len(w)
        var = sum((x - m) ** 2 for x in w) / len(w)
        out.append(math.sqrt(var))
    return out

# ===========================================================================
# MACD (Moving Average Convergence Divergence)
# ===========================================================================
def macd(vals: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict[str, list[float]]:
    """Calcula MACD com linha de sinal e histograma."""
    ema_fast = _ema(vals, fast)
    ema_slow = _ema(vals, slow)
    macd_line = [ema_fast[i] - ema_slow[i] for i in range(len(vals))]
    signal_line = _ema(macd_line, signal)
    histogram = [macd_line[i] - signal_line[i] for i in range(len(vals))]
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}

# ===========================================================================
# Stochastic Oscillator
# ===========================================================================
def stochastic(highs: list[float], lows: list[float], closes: list[float],
               k_period: int = 14, d_period: int = 3) -> dict[str, list[float]]:
    """Calcula Stochastic %K e %D."""
    k_values = []
    for i in range(len(closes)):
        if i < k_period - 1:
            k_values.append(50.0)
        else:
            hh = max(highs[i - k_period + 1:i + 1])
            ll = min(lows[i - k_period + 1:i + 1])
            if hh == ll:
                k_values.append(50.0)
            else:
                k_values.append((closes[i] - ll) / (hh - ll) * 100)
    d_values = _sma(k_values, d_period)
    return {"k": k_values, "d": d_values}

# ===========================================================================
# Ichimoku Kinko Hyo
# ===========================================================================
def ichimoku(highs: list[float], lows: list[float], closes: list[float],
             tenkan: int = 9, kijun: int = 26, senkou_b: int = 52) -> dict[str, list[float]]:
    """Calcula Ichimoku: Tenkan-sen, Kijun-sen, Senkou Span A/B, Chikou Span."""
    tenkan_sen = []
    kijun_sen = []
    senkou_a = []
    senkou_b = []
    for i in range(len(closes)):
        # Tenkan-sen
        if i >= tenkan - 1:
            hh = max(highs[i - tenkan + 1:i + 1])
            ll = min(lows[i - tenkan + 1:i + 1])
            tenkan_sen.append((hh + ll) / 2)
        else:
            tenkan_sen.append(None)
        # Kijun-sen
        if i >= kijun - 1:
            hh = max(highs[i - kijun + 1:i + 1])
            ll = min(lows[i - kijun + 1:i + 1])
            kijun_sen.append((hh + ll) / 2)
        else:
            kijun_sen.append(None)
        # Senkou Span A
        if tenkan_sen[i] is not None and kijun_sen[i] is not None:
            senkou_a.append((tenkan_sen[i] + kijun_sen[i]) / 2)
        else:
            senkou_a.append(None)
        # Senkou Span B
        if i >= senkou_b - 1:
            hh = max(highs[i - senkou_b + 1:i + 1])
            ll = min(lows[i - senkou_b + 1:i + 1])
            senkou_b.append((hh + ll) / 2)
        else:
            senkou_b.append(None)
    # Chikou Span = close shifted back 26 periods
    chikou = [None] * len(closes)
    for i in range(len(closes)):
        if i + kijun < len(closes):
            chikou[i + kijun] = closes[i]
    return {
        "tenkan": tenkan_sen,
        "kijun": kijun_sen,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b,
        "chikou": chikou,
    }

# ===========================================================================
# Parabolic SAR
# ===========================================================================
def parabolic_sar(highs: list[float], lows: list[float], closes: list[float],
                  af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2) -> list[float]:
    """Calcula Parabolic SAR."""
    if len(closes) < 2:
        return [closes[0]] if closes else []
    sar = [0.0] * len(closes)
    trend_up = True
    ep = highs[0]
    af = af_start
    sar[0] = lows[0]
    for i in range(1, len(closes)):
        prev_sar = sar[i - 1]
        if trend_up:
            sar[i] = prev_sar + af * (ep - prev_sar)
            sar[i] = min(sar[i], lows[i - 1], lows[i - 2] if i >= 2 else lows[i - 1])
            if lows[i] < sar[i]:
                trend_up = False
                sar[i] = ep
                ep = lows[i]
                af = af_start
            else:
                if highs[i] > ep:
                    ep = highs[i]
                    af = min(af + af_step, af_max)
        else:
            sar[i] = prev_sar + af * (ep - prev_sar)
            sar[i] = max(sar[i], highs[i - 1], highs[i - 2] if i >= 2 else highs[i - 1])
            if highs[i] > sar[i]:
                trend_up = True
                sar[i] = ep
                ep = highs[i]
                af = af_start
            else:
                if lows[i] < ep:
                    ep = lows[i]
                    af = min(af + af_step, af_max)
    return sar

# ===========================================================================
# Williams %R
# ===========================================================================
def williams_r(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[float]:
    """Calcula Williams %R."""
    out = []
    for i in range(len(closes)):
        if i < period - 1:
            out.append(-50.0)
        else:
            hh = max(highs[i - period + 1:i + 1])
            ll = min(lows[i - period + 1:i + 1])
            if hh == ll:
                out.append(-50.0)
            else:
                out.append((hh - closes[i]) / (hh - ll) * -100)
    return out

# ===========================================================================
# CCI (Commodity Channel Index)
# ===========================================================================
def cci(highs: list[float], lows: list[float], closes: list[float], period: int = 20) -> list[float]:
    """Calcula CCI."""
    tp = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(len(closes))]
    out = []
    for i in range(len(tp)):
        if i < period - 1:
            out.append(0.0)
        else:
            w = tp[i - period + 1:i + 1]
            mean_tp = sum(w) / len(w)
            mean_dev = sum(abs(x - mean_tp) for x in w) / len(w)
            if mean_dev == 0:
                out.append(0.0)
            else:
                out.append((tp[i] - mean_tp) / (0.015 * mean_dev))
    return out

# ===========================================================================
# Momentum
# ===========================================================================
def momentum(vals: list[float], period: int = 10) -> list[float]:
    """Calcula Momentum (diferenca absoluta)."""
    out = []
    for i in range(len(vals)):
        if i < period:
            out.append(0.0)
        else:
            out.append(vals[i] - vals[i - period])
    return out

# ===========================================================================
# Rate of Change (ROC)
# ===========================================================================
def roc(vals: list[float], period: int = 10) -> list[float]:
    """Calcula Rate of Change (percentual)."""
    out = []
    for i in range(len(vals)):
        if i < period or vals[i - period] == 0:
            out.append(0.0)
        else:
            out.append((vals[i] - vals[i - period]) / vals[i - period] * 100)
    return out

# ===========================================================================
# OBV (On-Balance Volume)
# ===========================================================================
def obv(closes: list[float], volumes: list[float]) -> list[float]:
    """Calcula On-Balance Volume."""
    if not closes:
        return []
    out = [volumes[0] if volumes else 0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            out.append(out[-1] + (volumes[i] if i < len(volumes) else 0))
        elif closes[i] < closes[i - 1]:
            out.append(out[-1] - (volumes[i] if i < len(volumes) else 0))
        else:
            out.append(out[-1])
    return out

# ===========================================================================
# Aroon
# ===========================================================================
def aroon(highs: list[float], lows: list[float], period: int = 25) -> dict[str, list[float]]:
    """Calcula Aroon Up e Aroon Down."""
    up = []
    down = []
    for i in range(len(highs)):
        if i < period:
            up.append(50.0)
            down.append(50.0)
        else:
            w_high = highs[i - period:i + 1]
            w_low = lows[i - period:i + 1]
            idx_high = w_high.index(max(w_high))
            idx_low = w_low.index(min(w_low))
            up.append((period - idx_high) / period * 100)
            down.append((period - idx_low) / period * 100)
    return {"up": up, "down": down}

# ===========================================================================
# DMI (Directional Movement Index) + ADX
# ===========================================================================
def dmi(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> dict[str, list[float]]:
    """Calcula +DI, -DI e ADX."""
    if len(closes) < 2:
        return {"plus_di": [50], "minus_di": [50], "adx": [0]}
    plus_dm = []
    minus_dm = []
    trs = []
    for i in range(1, len(closes)):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(max(up, 0) if up > down else 0)
        minus_dm.append(max(down, 0) if down > up else 0)
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    plus_di = []
    minus_di = []
    dx_list = []
    for i in range(len(plus_dm)):
        if i < period - 1:
            plus_di.append(50.0)
            minus_di.append(50.0)
            dx_list.append(0.0)
        else:
            atr = sum(trs[max(0, i - period + 1):i + 1]) / period
            if atr == 0:
                plus_di.append(50.0)
                minus_di.append(50.0)
            else:
                pdi = sum(plus_dm[max(0, i - period + 1):i + 1]) / atr * 100
                mdi = sum(minus_dm[max(0, i - period + 1):i + 1]) / atr * 100
                plus_di.append(pdi)
                minus_di.append(mdi)
            denom = plus_di[i] + minus_di[i]
            if denom == 0:
                dx_list.append(0.0)
            else:
                dx_list.append(abs(plus_di[i] - minus_di[i]) / denom * 100)
    adx = _sma(dx_list, period)
    return {"plus_di": plus_di, "minus_di": minus_di, "adx": adx}

# ===========================================================================
# Bollinger Bands
# ===========================================================================
def bollinger(vals: list[float], period: int = 20, mult: float = 2.0) -> dict[str, list[float]]:
    """Calcula Bollinger Bands (media, banda superior, banda inferior)."""
    mid = _sma(vals, period)
    std = _std(vals, period)
    upper = [mid[i] + mult * std[i] for i in range(len(vals))]
    lower = [mid[i] - mult * std[i] for i in range(len(vals))]
    return {"middle": mid, "upper": upper, "lower": lower}

# ===========================================================================
# Keltner Channel
# ===========================================================================
def keltner(highs: list[float], lows: list[float], closes: list[float],
            ema_period: int = 20, atr_period: int = 10, mult: float = 1.5) -> dict[str, list[float]]:
    """Calcula Keltner Channel."""
    mid = _ema(closes, ema_period)
    trs = []
    for i in range(len(closes)):
        if i == 0:
            trs.append(highs[i] - lows[i])
        else:
            trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    atr = _sma(trs, atr_period)
    upper = [mid[i] + mult * atr[i] for i in range(len(closes))]
    lower = [mid[i] - mult * atr[i] for i in range(len(closes))]
    return {"middle": mid, "upper": upper, "lower": lower}

# ===========================================================================
# Donchian Channel
# ===========================================================================
def donchian(highs: list[float], lows: list[float], period: int = 20) -> dict[str, list[float]]:
    """Calcula Donchian Channel."""
    upper = []
    lower = []
    mid = []
    for i in range(len(highs)):
        if i < period - 1:
            upper.append(highs[i])
            lower.append(lows[i])
            mid.append((highs[i] + lows[i]) / 2)
        else:
            upper.append(max(highs[i - period + 1:i + 1]))
            lower.append(min(lows[i - period + 1:i + 1]))
            mid.append((upper[i] + lower[i]) / 2)
    return {"upper": upper, "lower": lower, "middle": mid}

# ===========================================================================
# Indicator Registry
# ===========================================================================
ALL_INDICATORS = {
    "sma": {"name": "Simple Moving Average", "func": lambda c, h, l, v: {"line": _sma(c, 20)}, "params": [{"name": "period", "default": 20, "min": 2, "max": 200}]},
    "ema": {"name": "Exponential Moving Average", "func": lambda c, h, l, v: {"line": _ema(c, 20)}, "params": [{"name": "period", "default": 20, "min": 2, "max": 200}]},
    "bb": {"name": "Bollinger Bands", "func": lambda c, h, l, v: bollinger(c, 20, 2), "params": [{"name": "period", "default": 20, "min": 5, "max": 50}, {"name": "mult", "default": 2.0, "min": 0.5, "max": 5.0}]},
    "macd": {"name": "MACD", "func": lambda c, h, l, v: macd(c, 12, 26, 9), "params": [{"name": "fast", "default": 12, "min": 5, "max": 30}, {"name": "slow", "default": 26, "min": 15, "max": 50}, {"name": "signal", "default": 9, "min": 5, "max": 20}]},
    "rsi": {"name": "RSI", "func": lambda c, h, l, v: {"line": _rsi(c, 14)}, "params": [{"name": "period", "default": 14, "min": 5, "max": 50}]},
    "stoch": {"name": "Stochastic", "func": lambda c, h, l, v: stochastic(h, l, c, 14, 3), "params": [{"name": "k_period", "default": 14, "min": 5, "max": 30}, {"name": "d_period", "default": 3, "min": 2, "max": 10}]},
    "atr": {"name": "ATR", "func": lambda c, h, l, v: {"line": _atr_gen(h, l, c, 14)}, "params": [{"name": "period", "default": 14, "min": 5, "max": 50}]},
    "cci": {"name": "CCI", "func": lambda c, h, l, v: {"line": cci(h, l, c, 20)}, "params": [{"name": "period", "default": 20, "min": 10, "max": 50}]},
    "momentum": {"name": "Momentum", "func": lambda c, h, l, v: {"line": momentum(c, 10)}, "params": [{"name": "period", "default": 10, "min": 5, "max": 30}]},
    "williams_r": {"name": "Williams %R", "func": lambda c, h, l, v: {"line": williams_r(h, l, c, 14)}, "params": [{"name": "period", "default": 14, "min": 5, "max": 30}]},
    "obv": {"name": "On-Balance Volume", "func": lambda c, h, l, v: {"line": obv(c, v)}, "params": []},
    "ichimoku": {"name": "Ichimoku", "func": lambda c, h, l, v: ichimoku(h, l, c, 9, 26, 52), "params": []},
    "parabolic_sar": {"name": "Parabolic SAR", "func": lambda c, h, l, v: {"line": parabolic_sar(h, l, c, 0.02, 0.02, 0.2)}, "params": [{"name": "af_start", "default": 0.02, "min": 0.01, "max": 0.1}, {"name": "af_max", "default": 0.2, "min": 0.1, "max": 0.5}]},
    "aroon": {"name": "Aroon", "func": lambda c, h, l, v: aroon(h, l, c, 25), "params": [{"name": "period", "default": 25, "min": 10, "max": 50}]},
    "dmi": {"name": "DMI/ADX", "func": lambda c, h, l, v: dmi(h, l, c, 14), "params": [{"name": "period", "default": 14, "min": 5, "max": 30}]},
    "keltner": {"name": "Keltner Channel", "func": lambda c, h, l, v: keltner(h, l, c, 20, 10, 1.5), "params": [{"name": "ema_period", "default": 20, "min": 10, "max": 50}, {"name": "atr_period", "default": 10, "min": 5, "max": 30}]},
    "donchian": {"name": "Donchian Channel", "func": lambda c, h, l, v: donchian(h, l, c, 20), "params": [{"name": "period", "default": 20, "min": 5, "max": 50}]},
}

def _rsi(vals: list[float], n: int) -> list[float]:
    out, gains, losses, prev = [], [], [], None
    for v in vals:
        if prev is None:
            out.append(50.0)
        else:
            ch = v - prev
            gains.append(max(ch, 0.0))
            losses.append(max(-ch, 0.0))
            if len(gains) >= n:
                ag = sum(gains[-n:]) / n
                al = sum(losses[-n:]) / n
                rs = ag / al if al > 0 else 100.0
                out.append(100.0 - 100.0 / (1.0 + rs))
            else:
                out.append(50.0)
        prev = v
    return out

def _atr_gen(highs: list[float], lows: list[float], closes: list[float], n: int) -> list[float]:
    trs = []
    for i in range(len(closes)):
        if i == 0:
            trs.append(highs[i] - lows[i])
        else:
            trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    out = []
    atr = None
    for i, tr in enumerate(trs):
        if i < n - 1:
            out.append(0.0)
        elif i == n - 1:
            atr = sum(trs[:n]) / n
            out.append(atr)
        else:
            atr = (atr * (n - 1) + tr) / n
            out.append(atr)
    return out

def calculate(name: str, closes: list[float], highs: list[float] = None, lows: list[float] = None, volumes: list[float] = None) -> dict[str, Any]:
    """Calcula um indicador pelo nome."""
    ind = ALL_INDICATORS.get(name.lower())
    if ind is None:
        return {}
    highs = highs or closes
    lows = lows or closes
    volumes = volumes or [0] * len(closes)
    return ind["func"](closes, highs, lows, volumes)
