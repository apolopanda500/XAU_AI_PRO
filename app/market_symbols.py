# -*- coding: utf-8 -*-
"""Resolver generico de simbolos/timeframes — sem hardcode de ativo."""
from __future__ import annotations
TIMEFRAMES = ["M1","M5","M15","M30","H1","H4","D1","W1","MN1"]
DEFAULT_TIMEFRAME = "M5"

def normalize_symbol(sym: str) -> str:
    s = (sym or "").strip().upper().replace("/","").replace("-","").replace(" ","")
    # remove sufixos de corretora: XAUUSDc, XAUUSDm, XAUUSD.pro -> base
    for suf in ("C","M",".PRO","PRO","_M","_C"):
        if len(s) > 6 and s.endswith(suf) and suf in ("C","M"):
            # só remove 1 char final se base conhecida (evita cortar EURUSD)
            base = s[:-1]
            if len(base) >= 6:
                return base
            return s
    if s.endswith(".PRO"):
        return s[:-4]
    return s

def base_symbol(sym: str) -> str:
    return normalize_symbol(sym)

def default_symbol_fallback() -> str:
    from app.config_manager import get_config
    v = (get_config().get("trading","default_symbol",default="") or "").strip().upper()
    if v:
        return normalize_symbol(v)
    syms = get_config().get("market","symbols",default=[]) or []
    if syms:
        return normalize_symbol(str(syms[0]))
    return ""  # sem ativo fixo — UI pede seleção / usa símbolo do chart MT5
