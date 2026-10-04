# -*- coding: utf-8 -*-
"""G1/G2 — Automacao no-code: texto em PT/EN -> regra estruturada -> config de bot.

Exemplos:
  "comprar quando rsi < 30 com sl 50 e tp 100"
  "sell if macd crosses up and atr > 20, risk 1%"
  " Criar bot grid 2% com stop"

Tudo generico: simbolo/timeframe vem do contexto (chart MT5 / selecao), nunca fixo.
"""
from __future__ import annotations

import re
from typing import Any

from app.market_symbols import resolve_timeframe, base_symbol, default_symbol_fallback

ACTIONS = {"comprar": "buy", "compra": "buy", "buy": "buy",
           "vender": "sell", "venda": "sell", "sell": "sell",
           "fechar": "close", "close": "close"}

INDICATORS = {"rsi", "macd", "atr", "adx", "bb", "stoch", "ema", "sma"}

_CMP = {"<": "lt", ">": "gt", "<=": "lte", ">=": "gte", "==": "eq",
        "=": "eq", "cruzar": "cross", "cruza": "cross", "cross": "cross",
        "crosses": "cross", "acima": "gt", "abaixo": "lt", "above": "gt", "below": "lt"}


def parse_rule(text: str, symbol: str = "", timeframe: str = "") -> dict[str, Any]:
    """Converte condicao em texto livre para regra estruturada. Erro explicado, nunca excecao."""
    raw = (text or "").strip()
    if not raw:
        return {"ok": False, "error": "descreva a condicao (ex: comprar quando rsi < 30)"}
    low = raw.lower()
    action = ""
    for key, val in ACTIONS.items():
        if re.search(r"\b" + re.escape(key) + r"\b", low):
            action = val
            break
    if not action:
        return {"ok": False, "error": "acao nao identificada (use comprar/vender/fechar ou buy/sell/close)"}
    conditions: list[dict[str, Any]] = []
    for ind in INDICATORS:
        m = re.search(r"\b" + ind + r"\b\s*(<=|>=|<|>|==|=|cruzar|cruza|cross|crosses|acima|abaixo|above|below)?\s*([0-9]+(?:\.[0-9]+)?)?", low)
        if m:
            op_raw, val_raw = m.group(1) or "", m.group(2)
            op = _CMP.get(op_raw, "lt" if action == "buy" and ind == "rsi" else "info")
            conditions.append({"indicator": ind, "op": op,
                               "value": float(val_raw) if val_raw else None})
    if not conditions:
        return {"ok": False, "error": "indicador nao identificado (rsi, macd, atr, adx, bb, stoch, ema, sma)"}
    sl = _num(low, r"sl\s*([0-9]+)")
    tp = _num(low, r"tp\s*([0-9]+)")
    risk = _num(low, r"(?:risk|risc[oo])\s*([0-9]+(?:\.[0-9]+)?)\s*%?")
    sym = base_symbol(symbol) if symbol else default_symbol_fallback()
    tf = resolve_timeframe(timeframe)
    return {"ok": True, "rule": {"action": action, "conditions": conditions,
                                 "sl_points": sl, "tp_points": tp, "risk_percent": risk,
                                 "symbol": sym, "timeframe": tf, "source_text": raw}}


def build_bot(rule: dict[str, Any]) -> dict[str, Any]:
    """G2: regra estruturada -> config de bot pronta p/ o robo/EA (via prediction JSON)."""
    if not rule.get("ok"):
        return {"ok": False, "error": rule.get("error", "regra invalida")}
    r = rule["rule"]
    if not r.get("symbol"):
        return {"ok": False, "error": "simbolo nao definido — selecione no app ou anexe o EA no chart"}
    return {"ok": True, "bot": {
        "name": f"{r['action'].upper()} auto ({', '.join(c['indicator'].upper() for c in r['conditions'])})",
        "action": r["action"], "conditions": r["conditions"],
        "sl_points": r["sl_points"] or 0, "tp_points": r["tp_points"] or 0,
        "risk_percent": r["risk_percent"] or 1.0,
        "symbol": r["symbol"], "timeframe": r["timeframe"],
        "enabled": False,  # comeca pausado: usuario revisa e ativa (padrao tops 2026)
    }}


def list_models() -> list[str]:
    """Modelos treinados (.pkl) lidos do manifest — nada fixo no codigo."""
    try:
        import json
        from pathlib import Path
        manifest = Path(__file__).resolve().parent.parent / "Models" / "manifest.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        out = []
        for item in data.get("models", []):
            name = item.get("name") if isinstance(item, dict) else str(item)
            if name:
                out.append(str(name))
        return sorted(out)
    except Exception:
        return []


def _num(low: str, pattern: str) -> float | None:
    m = re.search(pattern, low)
    return float(m.group(1)) if m else None
