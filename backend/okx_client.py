from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request

from backend.universal_contracts import open_exchange_request, validate_exchange_base_url


class OkxError(RuntimeError):
    pass


class OkxClient:
    support_status = "code_only"
    production_ready = False

    def __init__(self, market: str = "spot", demo: bool = False, api_key: str | None = None, api_secret: str | None = None, api_passphrase: str | None = None) -> None:
        normalized = str(market or "spot").strip().lower()
        if normalized in {"crypto-spot", "spot"}:
            self.market = "spot"
            self.inst_type = "SPOT"
        elif normalized in {"crypto-futures", "futures", "swap"}:
            self.market = "futures"
            self.inst_type = "SWAP"
        else:
            raise ValueError("OKX aceita spot ou futures")
        suffix = self.market.upper()
        self.base = validate_exchange_base_url(os.getenv(f"OKX_{suffix}_BASE_URL", os.getenv("OKX_BASE_URL", "https://www.okx.com")), "okx")
        self.api_key = (api_key if api_key is not None else os.getenv(f"OKX_{suffix}_API_KEY", os.getenv("OKX_API_KEY", ""))).strip()
        self.secret = (api_secret if api_secret is not None else os.getenv(f"OKX_{suffix}_API_SECRET", os.getenv("OKX_API_SECRET", ""))).strip()
        self.passphrase = (api_passphrase if api_passphrase is not None else os.getenv(f"OKX_{suffix}_API_PASSPHRASE", os.getenv("OKX_API_PASSPHRASE", ""))).strip()
        self.demo = demo

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.secret and self.passphrase)

    def _get(self, path: str, params: dict[str, object] | None = None, signed: bool = False) -> object:
        query = dict(params or {})
        request_path = path
        if query:
            request_path = f"{path}?{urlencode(query)}"
        headers = {"Accept": "application/json"}
        if signed:
            if not self.configured:
                raise OkxError("credenciais OKX incompletas")
            timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            signed_text = f"{timestamp}GET{request_path}"
            signature = base64.b64encode(hmac.new(self.secret.encode(), signed_text.encode(), hashlib.sha256).digest()).decode()
            headers.update({
                "OK-ACCESS-KEY": self.api_key,
                "OK-ACCESS-SIGN": signature,
                "OK-ACCESS-TIMESTAMP": timestamp,
                "OK-ACCESS-PASSPHRASE": self.passphrase,
                "Content-Type": "application/json",
            })
            if self.demo:
                headers["x-simulated-trading"] = "1"
        try:
            with open_exchange_request(Request(f"{validate_exchange_base_url(self.base, 'okx')}{request_path}", headers=headers, method="GET"), timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise OkxError(f"OKX indisponível: {exc}") from exc
        if isinstance(data, dict):
            if "code" not in data:
                raise OkxError("resposta OKX sem code")
            if str(data.get("code", "")) not in {"0", ""}:
                raise OkxError(str(data.get("msg") or data))
            return data.get("data", data)
        return data

    @staticmethod
    def _symbol(symbol: str) -> str:
        value = str(symbol or "").strip().upper().replace("/", "-")
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
        return self._get("/api/v5/public/instruments", {"instType": self.inst_type})

    def assets(self) -> object:
        return self.exchange_info()

    def account(self) -> object:
        return self._get("/api/v5/account/balance", signed=True)

    def history(self, symbol: str = "", limit: int = 100) -> object:
        params: dict[str, object] = {"instType": self.inst_type, "limit": min(max(int(limit), 1), 100)}
        if str(symbol or "").strip():
            params["instId"] = self._symbol(symbol)
        return self._get("/api/v5/trade/fills", params, signed=True)

    def depth(self, symbol: str, limit: int = 20) -> object:
        rows = self._rows(self._get("/api/v5/market/books", {"instId": self._symbol(symbol), "sz": min(max(int(limit), 1), 400)}))
        row = rows[0] if rows and isinstance(rows[0], dict) else {}
        bids = row.get("bids", [])
        asks = row.get("asks", [])
        return {
            "bids": bids,
            "asks": asks,
            "b": bids,
            "a": asks,
            "ts": row.get("ts"),
            "timestamp": row.get("ts"),
        }

    def trades(self, symbol: str, limit: int = 20) -> object:
        rows = self._rows(self._get("/api/v5/market/trades", {"instId": self._symbol(symbol), "limit": min(max(int(limit), 1), 500)}))
        return rows

    def ticker(self, symbol: str) -> object | None:
        symbol = self._symbol(symbol)
        rows = self._rows(self._get("/api/v5/market/ticker", {"instId": symbol}))
        row = next((item for item in rows if isinstance(item, dict) and str(item.get("instId", "")).upper() == symbol), None)
        if row is None:
            return None
        return {
            **row,
            "last": row.get("last"),
            "bidPx": row.get("bidPx"),
            "askPx": row.get("askPx"),
        }

    def ticker_batch(self, symbols: list[str] | tuple[str, ...] | None = None) -> list[object]:
        normalized = [self._symbol(item) for item in (symbols or []) if str(item or "").strip()]
        rows = self._rows(self._get("/api/v5/market/tickers", {"instType": self.inst_type}))
        if not normalized:
            return rows
        wanted = set(normalized)
        return [row for row in rows if isinstance(row, dict) and str(row.get("instId", "")).upper() in wanted]

    def stats_24h(self, symbol: str = "") -> object:
        if str(symbol or "").strip():
            return self.ticker(symbol)
        return self.ticker_batch()

    def _interval(self, value: str) -> str:
        normalized = str(value or "M5").strip().upper()
        intervals = {"M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m", "H1": "1H", "H4": "4H", "D1": "1D"}
        if normalized not in intervals:
            raise ValueError(f"timeframe OKX inválido: {value}")
        return intervals[normalized]

    def klines(self, symbol: str, interval: str = "M5", limit: int = 500,
               start_time: int | None = None, end_time: int | None = None) -> object:
        params: dict[str, object] = {
            "instId": self._symbol(symbol),
            "bar": self._interval(interval),
            "limit": min(max(int(limit), 1), 300),
        }
        if start_time is not None:
            params["after"] = int(start_time)
        if end_time is not None:
            params["before"] = int(end_time)
        return self._get("/api/v5/market/candles", params)

    def capabilities(self) -> dict[str, object]:
        return {
            "broker": "okx",
            "market": self.market,
            "status": self.support_status,
            "production_ready": self.production_ready,
            "read_only": True,
            "execution": False,
            "withdrawals": False,
        }
