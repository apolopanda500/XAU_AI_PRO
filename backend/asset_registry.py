"""Catalogo dinamico de ativos fornecidos pelo terminal MT5."""
from __future__ import annotations

import math


def _value(item, name: str, default=None):
    value = getattr(item, name, default)
    return default if value is None else value


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _integer(value):
    number = _number(value)
    return None if number is None else int(number)


def _asset_class(name: str, path: str, base: str, profit: str) -> str:
    text = f"{name} {path} {base} {profit}".upper()
    if any(token in text for token in ("CRYPTO", "BITCOIN", "ETHEREUM", "BTC", "ETH", "USDT", "USDC", "SOL", "XRP")):
        return "crypto"
    if any(token in text for token in ("FOREX", "FX", "CURRENCY")):
        return "forex"
    if any(token in text for token in ("STOCK", "EQUITY", "SHARES", "ACTIONS")):
        return "equity"
    if any(token in text for token in ("INDEX", "INDICES")):
        return "index"
    if any(token in text for token in ("FUTURE", "FUTURES")):
        return "future"
    if any(token in text for token in ("METAL", "GOLD", "SILVER")):
        return "metal"
    return "other"


def discover_assets(mt5, include_hidden: bool = True) -> list[dict]:
    rows = []
    symbols = mt5.symbols_get()
    if symbols is None:
        return rows
    for item in symbols or []:
        symbol = str(_value(item, "name", "") or "").strip()
        if not symbol:
            continue
        visible_value = _value(item, "visible", None)
        visible = None if visible_value is None else bool(visible_value)
        if not include_hidden and visible is not True:
            continue
        path = str(_value(item, "path", "") or "")
        base = str(_value(item, "currency_base", "") or "")
        profit = str(_value(item, "currency_profit", "") or "")
        rows.append({
            "symbol": symbol,
            "description": _value(item, "description", None),
            "path": path or None,
            "visible": visible,
            "asset_class": _asset_class(symbol, path, base, profit),
            "currency_base": base or None,
            "currency_profit": profit or None,
            "digits": _integer(_value(item, "digits", None)),
            "point": _number(_value(item, "point", None)),
            "trade_mode": _integer(_value(item, "trade_mode", None)),
            "volume_min": _number(_value(item, "volume_min", None)),
            "volume_max": _number(_value(item, "volume_max", None)),
            "volume_step": _number(_value(item, "volume_step", None)),
            "change_pct": None,
        })
    return sorted(rows, key=lambda row: row["symbol"].upper())
