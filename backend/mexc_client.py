"""Cliente MEXC Spot/Futures em modo somente leitura.

Nenhum método deste módulo envia, cancela ou modifica ordens.
As credenciais são lidas exclusivamente do ambiente local.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json


class MexcError(RuntimeError):
    """Erro normalizado da API MEXC."""


class MexcClient:
    def __init__(self, market: str = "spot") -> None:
        if market not in {"spot", "futures"}:
            raise ValueError("market deve ser spot ou futures")
        self.market = market
        self.base_url = os.getenv(
            "MEXC_SPOT_BASE_URL" if market == "spot" else "MEXC_FUTURES_BASE_URL",
            "https://api.mexc.com" if market == "spot" else "https://contract.mexc.com",
        ).rstrip("/")
        self.api_key = os.getenv(f"MEXC_{market.upper()}_API_KEY", "").strip()
        self.api_secret = os.getenv(f"MEXC_{market.upper()}_API_SECRET", "").strip()

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
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-MEXC-APIKEY"] = self.api_key
        try:
            with urlopen(Request(url, headers=headers, method="GET"), timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise MexcError(f"MEXC {self.market} indisponível: {exc}") from exc
        if isinstance(data, dict) and data.get("code") not in (None, 0, 200):
            raise MexcError(f"MEXC {self.market} rejeitou consulta: {data}")
        return data

    def exchange_info(self) -> object:
        return self._get("/api/v3/exchangeInfo") if self.market == "spot" else self._get("/api/v1/contract/detail")

    def account(self) -> object:
        return self._get("/api/v3/account", signed=True) if self.market == "spot" else self._get("/api/v1/private/account/assets", signed=True)

    def history(self, symbol: str = "", limit: int = 100) -> object:
        if self.market == "spot":
            params: dict[str, object] = {"limit": min(max(limit, 1), 1000)}
            if symbol.strip(): params["symbol"] = symbol.strip().upper()
            return self._get("/api/v3/myTrades", params, signed=True)
        params = {"page_num": 1, "page_size": min(max(limit, 1), 1000)}
        if symbol.strip(): params["symbol"] = symbol.strip().upper()
        return self._get("/api/v1/private/order/list/history", params, signed=True)
    def depth(self, symbol: str, limit: int = 20) -> object:
        symbol = symbol.strip().upper()
        if self.market == "spot": return self._get("/api/v3/depth", {"symbol": symbol, "limit": min(max(limit, 5), 100)})
        return self._get(f"/api/v1/contract/depth/{symbol}", {"limit": min(max(limit, 5), 100)})
    def trades(self, symbol: str, limit: int = 20) -> object:
        if self.market == "spot": return self._get("/api/v3/trades", {"symbol": symbol.upper(), "limit": min(max(limit, 5), 100)})
        return self._get(f"/api/v1/contract/deals/{symbol.upper()}", {"limit": min(max(limit, 5), 100)})
    def ticker(self, symbol: str) -> object:
        symbol = symbol.strip().upper()
        if self.market == "spot":
            return self._get("/api/v3/ticker/bookTicker", {"symbol": symbol})
        return self._get(f"/api/v1/contract/ticker", {"symbol": symbol})
