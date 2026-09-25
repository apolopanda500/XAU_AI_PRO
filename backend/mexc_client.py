"""Cliente MEXC Spot/Futures em modo somente leitura.

Nenhum método deste módulo envia, cancela ou modifica ordens.
As credenciais são lidas exclusivamente do ambiente local.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode
from urllib.request import Request

from backend.universal_contracts import open_exchange_request, validate_exchange_base_url


class MexcError(RuntimeError):
    pass


class MexcClient:
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
        self.base_url = validate_exchange_base_url(os.getenv(
            f"MEXC_{suffix}_BASE_URL",
            "https://api.mexc.com" if normalized == "spot" else "https://contract.mexc.com",
        ), "mexc")
        self.api_key = (api_key if api_key is not None else os.getenv(f"MEXC_{suffix}_API_KEY", "")).strip()
        self.api_secret = (api_secret if api_secret is not None else os.getenv(f"MEXC_{suffix}_API_SECRET", "")).strip()

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def _get(self, path: str, params: dict[str, object] | None = None, signed: bool = False) -> object:
        query = dict(params or {})
        if signed:
            if not self.configured:
                raise MexcError(f"credenciais MEXC {self.market} não configuradas")
            query["timestamp"] = int(time.time() * 1000)
            payload = urlencode(query)
            query["signature"] = hmac.new(self.api_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        url = f"{validate_exchange_base_url(self.base_url, 'mexc')}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        headers = {"Accept": "application/json"}
        if signed and self.api_key:
            headers["X-MEXC-APIKEY"] = self.api_key
        try:
            with open_exchange_request(Request(url, headers=headers, method="GET"), timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise MexcError(f"MEXC {self.market} indisponível: {exc}") from exc
        if isinstance(data, dict) and data.get("code") not in (None, 0, 200, "0", "200"):
            raise MexcError(f"MEXC {self.market} rejeitou consulta: {data}")
        return data

    @staticmethod
    def _symbol(symbol: str) -> str:
        value = str(symbol or "").strip().upper()
        if not value:
            raise ValueError("symbol é obrigatório")
        return value

    @staticmethod
    def _rows(raw: object) -> list[object]:
        if isinstance(raw, list):
            return list(raw)
        if isinstance(raw, dict):
            data = raw.get("data")
            if isinstance(data, list):
                return list(data)
            if isinstance(data, dict):
                return [data]
            return [raw]
        return []

    def exchange_info(self) -> object:
        return self._get("/api/v3/exchangeInfo") if self.market == "spot" else self._get("/api/v1/contract/detail")

    def assets(self) -> object:
        return self.exchange_info()

    def account(self) -> object:
        return self._get("/api/v3/account", signed=True) if self.market == "spot" else self._get("/api/v1/private/account/assets", signed=True)

    def history(self, symbol: str = "", limit: int = 100) -> object:
        if self.market == "spot":
            params: dict[str, object] = {"limit": min(max(int(limit), 1), 1000)}
            if str(symbol or "").strip():
                params["symbol"] = self._symbol(symbol)
            return self._get("/api/v3/myTrades", params, signed=True)
        params = {"page_num": 1, "page_size": min(max(int(limit), 1), 1000)}
        if str(symbol or "").strip():
            params["symbol"] = self._symbol(symbol)
        return self._get("/api/v1/private/order/list/history", params, signed=True)

    def depth(self, symbol: str, limit: int = 20) -> object:
        symbol = self._symbol(symbol)
        if self.market == "spot":
            return self._get("/api/v3/depth", {"symbol": symbol, "limit": min(max(int(limit), 5), 100)})
        return self._get(f"/api/v1/contract/depth/{symbol}", {"limit": min(max(int(limit), 5), 100)})

    def trades(self, symbol: str, limit: int = 20) -> object:
        symbol = self._symbol(symbol)
        if self.market == "spot":
            return self._get("/api/v3/trades", {"symbol": symbol, "limit": min(max(int(limit), 5), 1000)})
        return self._get(f"/api/v1/contract/deals/{symbol}", {"limit": min(max(int(limit), 5), 1000)})

    def book_ticker(self, symbol: str = "") -> object:
        symbol = self._symbol(symbol) if str(symbol or "").strip() else ""
        if self.market == "spot":
            return self._get("/api/v3/ticker/bookTicker", {"symbol": symbol} if symbol else None)
        return self._get("/api/v1/contract/ticker", {"symbol": symbol} if symbol else None)

    def ticker(self, symbol: str) -> object | None:
        symbol = self._symbol(symbol)
        rows = self._rows(self.book_ticker(symbol))
        return next((row for row in rows if isinstance(row, dict) and str(row.get("symbol", "")).upper() == symbol), None)

    def ticker_batch(self, symbols: list[str] | tuple[str, ...] | None = None) -> list[object]:
        normalized = [self._symbol(item) for item in (symbols or []) if str(item or "").strip()]
        if self.market == "spot":
            raw = self._get("/api/v3/ticker/bookTicker")
        elif len(normalized) == 1:
            raw = self._get("/api/v1/contract/ticker", {"symbol": normalized[0]})
        else:
            raw = self._get("/api/v1/contract/ticker")
        rows = self._rows(raw)
        if not normalized:
            return rows
        wanted = set(normalized)
        return [row for row in rows if isinstance(row, dict) and str(row.get("symbol", "")).upper() in wanted]

    def stats_24h(self, symbol: str = "") -> object:
        symbol = self._symbol(symbol) if str(symbol or "").strip() else ""
        if self.market == "spot":
            return self._get("/api/v3/ticker/24hr", {"symbol": symbol} if symbol else None)
        return self._get("/api/v1/contract/ticker", {"symbol": symbol} if symbol else None)

    def _interval(self, value: str) -> str:
        normalized = str(value or "M5").strip().upper()
        intervals = {
            "spot": {"M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m", "H1": "60m", "H4": "4h", "D1": "1d"},
            "futures": {"M1": "Min1", "M5": "Min5", "M15": "Min15", "M30": "Min30", "H1": "Min60", "H4": "Hour4", "D1": "Day1"},
        }
        if normalized not in intervals[self.market]:
            raise ValueError(f"timeframe MEXC inválido: {value}")
        return intervals[self.market][normalized]

    def klines(self, symbol: str, interval: str = "M5", limit: int = 500,
               start_time: int | None = None, end_time: int | None = None) -> object:
        symbol = self._symbol(symbol)
        normalized_interval = self._interval(interval)
        params: dict[str, object] = {
            "interval": normalized_interval,
            "limit": min(max(int(limit), 1), 1000),
        }
        if start_time is not None:
            params["start"] = int(start_time)
        if end_time is not None:
            params["end"] = int(end_time)
        if self.market == "spot":
            params["symbol"] = symbol
            return self._get("/api/v3/klines", params)
        return self._get(f"/api/v1/contract/kline/{symbol}", params)

    def capabilities(self) -> dict[str, object]:
        return {
            "broker": "mexc",
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
