"""Cliente Binance Spot/Futures somente leitura."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode
from urllib.request import Request

from backend.universal_contracts import open_exchange_request, validate_exchange_base_url


class BinanceError(RuntimeError):
    pass


class BinanceClient:
    market: str
    base: str

    def __init__(self, market: str = "spot", api_key: str | None = None, api_secret: str | None = None) -> None:
        normalized = str(market or "spot").strip().lower()
        if normalized in {"crypto-spot", "spot"}:
            normalized = "spot"
        elif normalized in {"crypto-futures", "futures", "futuros"}:
            normalized = "futures"
        else:
            raise ValueError("market deve ser spot ou futures")
        self.market = normalized
        suffix = normalized.upper()
        self.api_key = (api_key if api_key is not None else os.getenv(f"BINANCE_{suffix}_API_KEY", "")).strip()
        self.secret = (api_secret if api_secret is not None else os.getenv(f"BINANCE_{suffix}_API_SECRET", "")).strip()
        self.base = validate_exchange_base_url(os.getenv(
            f"BINANCE_{suffix}_BASE_URL",
            "https://api.binance.com" if normalized == "spot" else "https://fapi.binance.com",
        ), "binance")

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.secret)

    @property
    def _prefix(self) -> str:
        return "/api/v3" if self.market == "spot" else "/fapi/v1"

    def _get(self, path: str, params: dict[str, object] | None = None, signed: bool = False) -> object:
        query = dict(params or {})
        if signed:
            if not self.configured:
                raise BinanceError(f"credenciais Binance {self.market} não configuradas")
            query["timestamp"] = int(time.time() * 1000)
            payload = urlencode(query)
            query["signature"] = hmac.new(self.secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        url = f"{validate_exchange_base_url(self.base, 'binance')}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        headers = {"Accept": "application/json"}
        if signed and self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key
        try:
            with open_exchange_request(Request(url, headers=headers, method="GET"), timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise BinanceError(f"Binance {self.market} indisponível: {exc}") from exc
        if isinstance(data, dict) and data.get("code") is not None:
            try:
                if int(data["code"]) != 0:
                    raise BinanceError(str(data))
            except (TypeError, ValueError):
                pass
        return data

    @staticmethod
    def _symbol(symbol: str) -> str:
        value = str(symbol or "").strip().upper()
        if not value:
            raise ValueError("symbol é obrigatório")
        return value

    @staticmethod
    def _select(raw: object, symbol: str) -> object | None:
        if isinstance(raw, list):
            return next((item for item in raw if isinstance(item, dict) and str(item.get("symbol", "")).upper() == symbol), None)
        if isinstance(raw, dict):
            data = raw.get("data")
            if isinstance(data, list):
                return next((item for item in data if isinstance(item, dict) and str(item.get("symbol", "")).upper() == symbol), None)
            if isinstance(data, dict):
                return data if str(data.get("symbol", "")).upper() == symbol else None
            return raw if str(raw.get("symbol", "")).upper() == symbol else None
        return None

    def exchange_info(self) -> object:
        return self._get(f"{self._prefix}/exchangeInfo")

    def assets(self) -> object:
        return self.exchange_info()

    def account(self) -> object:
        return self._get("/api/v3/account", signed=True) if self.market == "spot" else self._get("/fapi/v2/account", signed=True)

    def history(self, symbol: str = "", limit: int = 100) -> object:
        params: dict[str, object] = {"limit": min(max(int(limit), 1), 1000)}
        if str(symbol or "").strip():
            params["symbol"] = self._symbol(symbol)
        return self._get("/api/v3/myTrades" if self.market == "spot" else "/fapi/v1/userTrades", params, signed=True)

    def ticker(self, symbol: str) -> object | None:
        symbol = self._symbol(symbol)
        book = self._select(self.book_ticker(symbol), symbol)
        stats = self._select(self.stats_24h(symbol), symbol)
        if not isinstance(book, dict):
            return stats if isinstance(stats, dict) else None
        if not isinstance(stats, dict):
            return book
        return {**stats, **book, "lastPrice": stats.get("lastPrice", stats.get("last"))}

    def ticker_batch(self, symbols: list[str] | tuple[str, ...] | None = None) -> list[object]:
        normalized = [self._symbol(item) for item in (symbols or []) if str(item or "").strip()]
        wanted = set(normalized)
        params: dict[str, object] | None = {"symbols": json.dumps(normalized, separators=(",", ":"))} if normalized and self.market == "spot" else None
        book_raw = self._get(f"{self._prefix}/ticker/bookTicker", params)
        book_rows = book_raw.get("data") if isinstance(book_raw, dict) and isinstance(book_raw.get("data"), list) else (book_raw if isinstance(book_raw, list) else [book_raw])
        try:
            stats_raw = self._get(f"{self._prefix}/ticker/24hr", params)
        except BinanceError:
            stats_raw = []
        stats_rows = stats_raw.get("data") if isinstance(stats_raw, dict) and isinstance(stats_raw.get("data"), list) else (stats_raw if isinstance(stats_raw, list) else [stats_raw])
        stats_by_symbol = {str(item.get("symbol", "")).upper(): item for item in stats_rows if isinstance(item, dict)}
        rows = []
        for item in book_rows if isinstance(book_rows, list) else []:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol", "")).upper()
            stats = stats_by_symbol.get(symbol, {})
            merged = {**stats, **item, "lastPrice": stats.get("lastPrice", stats.get("last"))}
            if symbol and (not wanted or symbol in wanted):
                rows.append(merged)
        return rows

    def stats_24h(self, symbol: str = "") -> object:
        symbol = self._symbol(symbol) if str(symbol or "").strip() else ""
        params = {"symbol": symbol} if symbol else None
        return self._get(f"{self._prefix}/ticker/24hr", params)

    def book_ticker(self, symbol: str = "") -> object:
        symbol = self._symbol(symbol) if str(symbol or "").strip() else ""
        params = {"symbol": symbol} if symbol else None
        return self._get(f"{self._prefix}/ticker/bookTicker", params)

    @staticmethod
    def _interval(value: str) -> str:
        normalized = str(value or "M5").strip().upper()
        intervals = {"M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m", "H1": "1h", "H4": "4h", "D1": "1d"}
        if normalized not in intervals:
            raise ValueError(f"timeframe Binance inválido: {value}")
        return intervals[normalized]

    def klines(self, symbol: str, interval: str = "M5", limit: int = 500,
               start_time: int | None = None, end_time: int | None = None) -> object:
        symbol = self._symbol(symbol)
        normalized_interval = self._interval(interval)
        maximum = 1000 if self.market == "spot" else 1500
        params: dict[str, object] = {
            "symbol": symbol,
            "interval": normalized_interval,
            "limit": min(max(int(limit), 1), maximum),
        }
        if start_time is not None:
            params["startTime"] = int(start_time)
        if end_time is not None:
            params["endTime"] = int(end_time)
        return self._get(f"{self._prefix}/klines", params)

    def depth(self, symbol: str, limit: int = 20) -> object:
        return self._get(f"{self._prefix}/depth", {"symbol": self._symbol(symbol), "limit": min(max(int(limit), 5), 100)})

    def trades(self, symbol: str, limit: int = 20) -> object:
        return self._get(f"{self._prefix}/trades", {"symbol": self._symbol(symbol), "limit": min(max(int(limit), 5), 1000)})

    def capabilities(self) -> dict[str, object]:
        return {
            "broker": "binance",
            "market": self.market,
            "status": "active",
            "read_only": True,
            "assets": True,
            "quotes": True,
            "batch_quotes": True,
            "candles": True,
            "depth": True,
            "trades": True,
            "stats24h": True,
            "account": True,
            "execution": False,
            "withdrawals": False,
        }
