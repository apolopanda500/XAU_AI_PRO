# -*- coding: utf-8 -*-
"""Resolver generico de simbolos/timeframes — sem hardcode de ativo."""
from __future__ import annotations
TIMEFRAMES = ["M1","M5","M15","M30","H1","H4","D1","W1","MN1"]

# POR QUE AQUI NAO HÁ MAIS UM `DEFAULT_TIMEFRAME`
# ==============================================
# A constante existia com valor "M5" e quem chamasse `DEFAULT_TIMEFRAME`
# recebia M5 sem ter pedido. Isso e exatamente o que o AGENTS.md proibe:
# "nenhum simbolo pode ser presumido" — e um timeframe presumido e a mesma
# coisa: o operador pede H1, recebe o grafico de M5, e nao tem como saber que
# o que ele ve nao e o que ele pediu.
#
# A regra que substitui: timeframe VAZIO e RECUSA COM MOTIVO, nao default.
# Para usar `resolve_timeframe()`, o chamador escolhe explicitamente.
DEFAULT_TIMEFRAME = ""


def resolve_timeframe(pedido: str | None = None) -> str:
    """Resolve o timeframe pedido. Vazio e recusa, nunca M5.

    WHY THIS EXISTS
    ---------------
    Havia dois jeitos de resolver timeframe e os dois escondiam a escolha:

    - `DEFAULT_TIMEFRAME = "M5"`: devolvia M5 para quem nao pediu nada.
    - `tfmap.get(minutes, mt5.TIMEFRAME_M5)`: devolvia M5 para quem pediu um
      timeframe que o mapa nao conheceva, sem aviso nenhum.

    Nos dois, o operador via um grafico de timeframe diferente do que pediu e
    nao tinha como descobrir. Aqui o vazio e erro com motivo.
    """
    bruto = str(pedido or "").strip().upper()
    if not bruto:
        return ""
    if bruto in TIMEFRAMES:
        return bruto
    # Aceita o nome em portugues/MT5 ("1H", "H1", "D") alem da forma do catalogo.
    equivalencias = {
        "1M": "M1", "3M": "M3", "5M": "M5", "15M": "M15", "30M": "M30",
        "1H": "H1", "60M": "H1", "4H": "H4", "240M": "H4",
        "1D": "D1", "D": "D1", "1440M": "D1", "1W": "W1", "W": "W1", "1MN": "MN1",
    }
    return equivalencias.get(bruto, "")

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
