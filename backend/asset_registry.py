"""Catalogo dinamico de ativos fornecidos pelo terminal MT5."""
from __future__ import annotations

def _value(item, name: str, default=None):
    value = getattr(item, name, default)
    return default if value is None else value

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
    """Retorna todos os ativos conhecidos pelo MT5 com suas capacidades."""
    rows = []
    for item in mt5.symbols_get() or []:
        symbol = str(_value(item, "name", "") or "").strip()
        if not symbol:
            continue
        visible = bool(_value(item, "visible", False))
        if not include_hidden and not visible:
            continue
        path = str(_value(item, "path", "") or "")
        base = str(_value(item, "currency_base", "") or "")
        profit = str(_value(item, "currency_profit", "") or "")
        rows.append({"symbol": symbol, "description": str(_value(item, "description", "") or ""), "path": path, "visible": visible, "asset_class": _asset_class(symbol, path, base, profit), "currency_base": base, "currency_profit": profit, "digits": int(_value(item, "digits", 0) or 0), "point": float(_value(item, "point", 0.0) or 0.0), "trade_mode": int(_value(item, "trade_mode", 0) or 0), "volume_min": float(_value(item, "volume_min", 0.0) or 0.0), "volume_max": float(_value(item, "volume_max", 0.0) or 0.0), "volume_step": float(_value(item, "volume_step", 0.0) or 0.0)})
    return sorted(rows, key=lambda row: row["symbol"].upper())
