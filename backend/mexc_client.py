"""Cliente MEXC Spot/Futures: leitura publica e envio de ordem.

Leitura e escrita usam a mesma assinatura HMAC-SHA256. Nenhum metodo deste
modulo envia, cancela ou modifica ordem fora de ``create_order``; nao existe
contraparte de saque ou transferencia.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request

from backend.universal_contracts import open_exchange_request, validate_exchange_base_url


class MexcError(RuntimeError):
    pass


def _http_detail(exc: HTTPError) -> str:
    """Corpo do erro da corretora, sem credencial em lugar nenhum."""
    try:
        raw = exc.read().decode("utf-8", "replace")[:400]
    except Exception:
        return str(exc)
    try:
        parsed = json.loads(raw)
    except ValueError:
        return raw
    if isinstance(parsed, dict):
        return str(parsed.get("msg") or parsed.get("error") or parsed)[:400]
    return raw


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

    def _post_form(self, path: str, params: dict[str, object]) -> object:
        """POST spot assinado por query (mesmo esquema do GET assinado)."""
        payload = dict(params)
        payload["timestamp"] = int(time.time() * 1000)
        encoded = urlencode(payload)
        payload["signature"] = hmac.new(self.api_secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        url = f"{validate_exchange_base_url(self.base_url, 'mexc')}{path}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-MEXC-APIKEY": self.api_key,
        }
        request = Request(url, data=urlencode(payload).encode("utf-8"), headers=headers, method="POST")
        return self._read(request, path)

    def _post_json(self, path: str, body: dict[str, object]) -> object:
        """POST futures assinado no cabecalho (ApiKey/Request-Time/Signature)."""
        timestamp = int(time.time() * 1000)
        payload = json.dumps(body, separators=(",", ":"))
        base = validate_exchange_base_url(self.base_url, "mexc")
        signed_text = f"{self.api_key}{timestamp}{payload}"
        signature = hmac.new(self.api_secret.encode(), signed_text.encode(), hashlib.sha256).hexdigest()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "ApiKey": self.api_key,
            "Request-Time": str(timestamp),
            "Signature": signature,
            "Recv-Window": "5000",
        }
        request = Request(f"{base}{path}", data=payload.encode("utf-8"), headers=headers, method="POST")
        return self._read(request, path)

    def _read(self, request: Request, path: str) -> object:
        try:
            with open_exchange_request(request, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = _http_detail(exc)
            raise MexcError(f"MEXC recusou a ordem em {path} (HTTP {exc.code}): {detail}") from exc
        except MexcError:
            raise
        except Exception as exc:
            raise MexcError(f"MEXC indisponível: {exc}") from exc
        if isinstance(data, dict) and data.get("code") not in (None, 0, 200, "0", "200"):
            raise MexcError(f"MEXC rejeitou {path}: {data}")
        if isinstance(data, dict) and data.get("success") is False:
            raise MexcError(f"MEXC rejeitou {path}: {data}")
        return data

    def create_order(self, *, symbol: str, side: str, order_type: str, quantity: float,
                     price: float | None = None, request_id: str) -> dict[str, object]:
        """Envia ordem spot ou de futuros. Sem contraparte de saque."""
        kind = str(order_type or "market").lower()
        if kind not in {"market", "limit"}:
            raise MexcError(f"tipo de ordem MEXC não suportado: {order_type}")
        if kind == "limit" and (price is None or float(price) <= 0):
            raise MexcError("preço é obrigatório para ordem limit")
        symbol = self._symbol(symbol)

        if self.market == "spot":
            params: dict[str, object] = {
                "symbol": symbol,
                "side": str(side).upper(),
                "type": kind.upper(),
                "quantity": quantity,
                "newClientOrderId": request_id,
            }
            if kind == "limit":
                params["price"] = price
            data = self._post_form("/api/v3/order", params)
            return data if isinstance(data, dict) else {"raw": data}

        body: dict[str, object] = {
            "symbol": symbol,
            "side": 1 if str(side).lower() == "buy" else 3,
            "type": 1 if kind == "limit" else 5,
            "openType": 2,
            "positionMode": 2,
            "vol": quantity,
            "price": price if kind == "limit" else 0,
            "externalOid": request_id,
        }
        data = self._post_json("/api/v1/private/order/create", body)
        if isinstance(data, dict):
            inner = data.get("data")
            if isinstance(inner, dict):
                return {**inner, "orderId": inner.get("orderId") or inner.get("order_id") or ""}
            return data
        return {"raw": data}

    @staticmethod
    def _symbol(symbol: str) -> str:
        """Normaliza o par para o formato da MEXC.

       .Delegado a `backend.exchange_symbols`, que e a fonte unica da regra.
        Antes isto era so `.upper()` e o operador escrevia `BTC/USD` ou
        `XAUUSD` e a exchange respondia HTTP 400 sem explicar o motivo.

        O formato da MEXC e o par concatenado contra USDT (`BTCUSDT`,
        `MXUSDT`) — confirmado na documentacao oficial de `POST /api/v3/order`.
        """
        from backend.exchange_symbols import par_exchange

        return par_exchange(symbol, "MEXC spot")

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
