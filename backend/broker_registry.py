from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BrokerDefinition:
    id: str
    label: str
    markets: tuple[str, ...]
    asset_classes: tuple[str, ...]
    public_data: bool
    account_read: bool
    demo: bool
    real: bool
    execution: bool
    status: str


MT5_MARKETS = ("forex", "metals", "indices", "stocks", "commodities", "bonds", "crypto-spot", "crypto-futures", "other")
EXCHANGE_MARKETS = ("crypto-spot", "crypto-futures")
MT5_CAPABILITIES = ("assets", "quotes", "batch_quotes", "candles", "account", "positions", "orders", "history", "journal")
EXCHANGE_CAPABILITIES = ("assets", "quotes", "batch_quotes", "candles", "depth", "trades", "stats24h", "account", "positions", "history")

BROKERS: dict[str, BrokerDefinition] = {
    "mt5": BrokerDefinition("mt5", "MetaTrader 5", MT5_MARKETS, ("forex", "metal", "index", "equity", "commodity", "bond", "crypto", "other"), True, True, True, False, False, "active"),
    "binance": BrokerDefinition("binance", "Binance", EXCHANGE_MARKETS, ("crypto",), True, True, False, False, False, "active"),
    "mexc": BrokerDefinition("mexc", "MEXC", EXCHANGE_MARKETS, ("crypto",), True, True, False, False, False, "active"),
    "bybit": BrokerDefinition("bybit", "Bybit", EXCHANGE_MARKETS, ("crypto",), True, True, False, False, False, "code_only"),
    "okx": BrokerDefinition("okx", "OKX", EXCHANGE_MARKETS, ("crypto",), True, True, False, False, False, "code_only"),
    "bitget": BrokerDefinition("bitget", "Bitget", EXCHANGE_MARKETS, ("crypto",), True, False, False, False, False, "planned"),
    "coinbase": BrokerDefinition("coinbase", "Coinbase", EXCHANGE_MARKETS, ("crypto",), True, False, False, False, False, "planned"),
    "kraken": BrokerDefinition("kraken", "Kraken", EXCHANGE_MARKETS, ("crypto",), True, False, False, False, False, "planned"),
    "kucoin": BrokerDefinition("kucoin", "KuCoin", EXCHANGE_MARKETS, ("crypto",), True, False, False, False, False, "planned"),
}

MARKET_CAPABILITIES: dict[str, dict[str, tuple[str, ...]]] = {
    "mt5": {market: MT5_CAPABILITIES for market in MT5_MARKETS},
    "binance": {market: EXCHANGE_CAPABILITIES for market in EXCHANGE_MARKETS},
    "mexc": {market: EXCHANGE_CAPABILITIES for market in EXCHANGE_MARKETS},
    "bybit": {market: EXCHANGE_CAPABILITIES for market in EXCHANGE_MARKETS},
    "okx": {market: EXCHANGE_CAPABILITIES for market in EXCHANGE_MARKETS},
    "bitget": {market: () for market in EXCHANGE_MARKETS},
    "coinbase": {market: () for market in EXCHANGE_MARKETS},
    "kraken": {market: () for market in EXCHANGE_MARKETS},
    "kucoin": {market: () for market in EXCHANGE_MARKETS},
}


def normalize_market(value: str) -> str:
    normalized = str(value or "").strip().lower()
    aliases = {
        "crypto": "crypto-spot", "spot": "crypto-spot", "cripto-spot": "crypto-spot",
        "futures": "crypto-futures", "futuros": "crypto-futures", "crypto_futures": "crypto-futures",
        "forex": "forex", "metals": "metals", "indices": "indices", "stocks": "stocks",
        "commodities": "commodities", "bonds": "bonds", "options": "options", "other": "other",
    }
    return aliases.get(normalized, normalized)


def get_broker(broker: str) -> BrokerDefinition | None:
    return BROKERS.get(str(broker or "").strip().lower())


def normalize_read_scope(broker: str, market: str, symbol: str = "") -> dict[str, str]:
    normalized_broker = str(broker or "").strip().lower()
    normalized_market = normalize_market(market)
    definition = get_broker(normalized_broker)
    if definition is None:
        raise ValueError("corretora não suportada")
    if normalized_market not in definition.markets:
        raise ValueError(f"mercado não suportado para {normalized_broker}")
    normalized_symbol = str(symbol or "").strip().upper()
    if len(normalized_symbol) > 40:
        raise ValueError("symbol excede 40 caracteres")
    return {"broker": normalized_broker, "market": normalized_market, "symbol": normalized_symbol}


def list_brokers(include_planned: bool = False, include_code_only: bool = False) -> list[dict[str, Any]]:
    allowed = {"active"}
    if include_code_only:
        allowed.add("code_only")
    if include_planned:
        allowed.add("planned")
    return [
        {
            "id": item.id,
            "label": item.label,
            "markets": list(item.markets),
            "asset_classes": list(item.asset_classes),
            "public_data": item.public_data,
            "account_read": item.account_read,
            "demo": item.demo,
            "real": item.real,
            "execution": item.execution,
            "status": item.status,
        }
        for item in BROKERS.values()
        if item.status in allowed
    ]


def supported_brokers(include_planned: bool = False, include_code_only: bool = False) -> set[str]:
    return {item["id"] for item in list_brokers(include_planned=include_planned, include_code_only=include_code_only)}


def read_brokers() -> set[str]:
    return supported_brokers(include_code_only=False)


def code_only_brokers() -> set[str]:
    return {item.id for item in BROKERS.values() if item.status == "code_only"}


def capabilities_for(broker: str, market: str) -> tuple[str, ...]:
    scope = normalize_read_scope(broker, market)
    return tuple(MARKET_CAPABILITIES.get(scope["broker"], {}).get(scope["market"], ()))


def capability_matrix(include_planned: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for definition in BROKERS.values():
        if definition.status == "planned" and not include_planned:
            continue
        for market in definition.markets:
            capabilities = tuple(MARKET_CAPABILITIES.get(definition.id, {}).get(market, ()))
            rows.append({
                "broker": definition.id,
                "market": market,
                "status": definition.status,
                "read_only": definition.status in {"active", "code_only"},
                "capabilities": list(capabilities),
                "execution": [],
                "withdrawals": False,
                "transfers": False,
            })
    return rows
