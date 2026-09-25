from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode
from urllib.request import Request

from backend.universal_contracts import open_exchange_request, validate_exchange_base_url


class BybitError(RuntimeError):
    pass


class BybitClient:
    support_status = "code_only"
    production_ready = False

    def __init__(self, market: str = "spot", demo: bool = False, api_key: str | None = None, api_secret: str | None = None) -> None:
        normalized = str(market or "spot").strip().lower()
        if normalized in {"crypto-spot", "spot"}:
            self.market = "spot"
            self.category = "spot"
        elif normalized in {"crypto-futures", "futures", "linear", "inverse"}:
            self.market = "futures"
            self.category = "linear"
        else:
            raise ValueError("Bybit aceita spot ou futures")
        suffix = self.market.upper()
        default_base = "https://api-testnet.bybit.com" if demo else "https://api.bybit.com"
        self.base = validate_exchange_base_url(os.getenv(f"BYBIT_{suffix}_BASE_URL", os.getenv("BYBIT_BASE_URL", default_base)), "bybit")
        self.api_key = (api_key if api_key is not None else os.getenv(f"BYBIT_{suffix}_API_KEY", os.getenv("BYBIT_API_KEY", ""))).strip()
        self.secret = (api_secret if api_secret is not None else os.getenv(f"BYBIT_{suffix}_API_SECRET", os.getenv("BYBIT_API_SECRET", ""))).strip()
        self.demo = demo

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.secret)

    def _get(self, path: str, params: dict[str, object] | None = None, signed: bool = False) -> object:
        query = dict(params or {})
        if signed:
            if not self.configured:
                raise BybitError("credenciais Bybit não configuradas")
            timestamp = str(int(time.time() * 1000))
            recv_window = "5000"
            query["timestamp"] = timestamp
            query["recvWindow"] = recv_window
            encoded = urlencode(query)
            signature = hmac.new(
                self.secret.encode(),
                f"{timestamp}{self.api_key}{recv_window}{encoded}".encode(),
                hashlib.sha256,
            ).hexdigest()
            query["sign"] = signature
        url = f"{validate_exchange_base_url(self.base, 'bybit')}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        headers = {"Accept": "application/json", "X-BAPI-API-KEY": self.api_key}
        try:
            with open_exchange_request(Request(url, headers=headers, method="GET"), timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise BybitError(f"Bybit indisponível: {exc}") from exc
        if isinstance(data, dict):
            if "retCode" not in data:
                raise BybitError("resposta Bybit sem retCode")
            try:
                ret_code = int(data.get("retCode", 0) or 0)
            except (TypeError, ValueError):
                ret_code = -1
            if ret_code != 0:
                raise BybitError(str(data.get("retMsg") or data))
            return data.get("result", data)
        return data

    @staticmethod
    def _symbol(symbol: str) -> str:
        value = str(symbol or "").strip().upper()
        if not value:
            raise ValueError("symbol é obrigatório")
        return value

    @staticmethod
    def _result(raw: object) -> dict[str, object]:
        if isinstance(raw, dict) and isinstance(raw.get("result"), dict):
            return raw["result"]
        return raw if isinstance(raw, dict) else {}

    def exchange_info(self) -> object:
        return self._get("/v5/market/instruments-info", {"category": self.category})

    def assets(self) -> object:
        return self.exchange_info()

    def account(self) -> object:
        return self._get("/v5/account/wallet-balance", {"accountType": "UNIFIED"}, signed=True)

    def history(self, symbol: str = "", limit: int = 100) -> object:
        params: dict[str, object] = {"category": self.category, "limit": min(max(int(limit), 1), 1000)}
        if str(symbol or "").strip():
            params["symbol"] = self._symbol(symbol)
        return self._get("/v5/execution/list", params, signed=True)

    def depth(self, symbol: str, limit: int = 20) -> object:
        result = self._result(self._get("/v5/market/orderbook", {"category": self.category, "symbol": self._symbol(symbol), "limit": min(max(int(limit), 1), 200)}))
        bids = result.get("b", result.get("bids", []))
        asks = result.get("a", result.get("asks", []))
        return {
            "b": bids,
            "a": asks,
            "bids": bids,
            "asks": asks,
            "ts": result.get("ts"),
            "timestamp": result.get("ts"),
            "update_id": result.get("u", result.get("update_id")),
        }

    def trades(self, symbol: str, limit: int = 20) -> object:
        result = self._result(self._get("/v5/market/recent-trade", {"category": self.category, "symbol": self._symbol(symbol), "limit": min(max(int(limit), 1), 1000)}))
        rows = result.get("list", result.get("trades", []))
        return {"list": rows if isinstance(rows, list) else [], "trades": rows if isinstance(rows, list) else [], "ts": result.get("ts"), "timestamp": result.get("ts")}

    def ticker(self, symbol: str) -> object | None:
        symbol = self._symbol(symbol)
        result = self._result(self._get("/v5/market/tickers", {"category": self.category, "symbol": symbol}))
        rows = result.get("list", []) if isinstance(result, dict) else []
        row = next((item for item in rows if isinstance(item, dict) and str(item.get("symbol", "")).upper() == symbol), None)
        if row is None:
            return None
        return {
            **row,
            "lastPrice": row.get("lastPrice"),
            "bid1Price": row.get("bid1Price", row.get("bidPx")),
            "ask1Price": row.get("ask1Price", row.get("askPx")),
        }

    def ticker_batch(self, symbols: list[str] | tuple[str, ...] | None = None) -> list[object]:
        normalized = [self._symbol(item) for item in (symbols or []) if str(item or "").strip()]
        result = self._result(self._get("/v5/market/tickers", {"category": self.category}))
        rows = result.get("list", []) if isinstance(result, dict) else []
        if not normalized:
            return list(rows) if isinstance(rows, list) else []
        wanted = set(normalized)
        return [row for row in rows if isinstance(row, dict) and str(row.get("symbol", "")).upper() in wanted]

    def stats_24h(self, symbol: str = "") -> object:
        if str(symbol or "").strip():
            return self.ticker(symbol)
        return self.ticker_batch()

    def _interval(self, value: str) -> str:
        normalized = str(value or "M5").strip().upper()
        intervals = {"M1": "1", "M5": "5", "M15": "15", "M30": "30", "H1": "60", "H4": "240", "D1": "D"}
        if normalized not in intervals:
            raise ValueError(f"timeframe Bybit inválido: {value}")
        return intervals[normalized]

    def klines(self, symbol: str, interval: str = "M5", limit: int = 500,
               start_time: int | None = None, end_time: int | None = None) -> object:
        params: dict[str, object] = {
            "category": self.category,
            "symbol": self._symbol(symbol),
            "interval": self._interval(interval),
            "limit": min(max(int(limit), 1), 1000),
        }
        if start_time is not None:
            params["start"] = int(start_time)
        if end_time is not None:
            params["end"] = int(end_time)
        return self._get("/v5/market/kline", params)

    def capabilities(self) -> dict[str, object]:
        return {
            "broker": "bybit",
            "market": self.market,
            "status": self.support_status,
            "production_ready": self.production_ready,
            "read_only": True,
            "execution": False,
            "withdrawals": False,
        }
