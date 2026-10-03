from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request

from backend.universal_contracts import open_exchange_request, validate_exchange_base_url


class OkxError(RuntimeError):
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
        rows = parsed.get("data")
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            parsed = rows[0]
        return str(parsed.get("msg") or parsed.get("error") or parsed)[:400]
    return raw


class OkxClient:
    support_status = "active"
    production_ready = False

    # A OKX responde 403 a qualquer requisicao sem User-Agent reconhecivel.
    USER_AGENT = "XAU-AI-PRO/1.2.4 (+gateway local)"

    # Quotes publicas da OKX usam o par separado por hifen (BTC-USDT); o app
    # trabalha com o par concatenado (BTCUSDT) e converte aqui.
    QUOTE_SUFFIXES = ("USDT", "USDC", "USD", "BTC", "ETH", "EUR")

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
        headers = {"Accept": "application/json", "User-Agent": self.USER_AGENT}
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

    def _post(self, path: str, body: dict[str, object]) -> object:
        """POST de envio (ordem). Assinatura HMAC cobre timestamp+metodo+rota+corpo."""
        if not self.configured:
            raise OkxError("credenciais OKX incompletas")
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        payload = json.dumps(body, separators=(",", ":"))
        signed_text = f"{timestamp}POST{path}{payload}"
        signature = base64.b64encode(hmac.new(self.secret.encode(), signed_text.encode(), hashlib.sha256).digest()).decode()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": self.USER_AGENT,
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
        }
        if self.demo:
            headers["x-simulated-trading"] = "1"
        url = f"{validate_exchange_base_url(self.base, 'okx')}{path}"
        request = Request(url, data=payload.encode("utf-8"), headers=headers, method="POST")
        try:
            with open_exchange_request(request, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = _http_detail(exc)
            raise OkxError(f"OKX recusou a ordem (HTTP {exc.code}): {detail}") from exc
        except OkxError:
            raise
        except Exception as exc:
            raise OkxError(f"OKX indisponível: {exc}") from exc
        if isinstance(data, dict):
            if "code" not in data:
                raise OkxError("resposta OKX sem code")
            if str(data.get("code", "")) not in {"0", ""}:
                raise OkxError(str(data.get("msg") or data))
            return data.get("data", data)
        return data

    def create_order(self, *, symbol: str, side: str, order_type: str, quantity: float,
                     price: float | None = None, request_id: str) -> dict[str, object]:
        """Envia ordem spot/swap. Sem contraparte de saque em nenhum ramo."""
        kind = str(order_type or "market").lower()
        if kind not in {"market", "limit"}:
            raise OkxError(f"tipo de ordem OKX não suportado: {order_type}")
        if kind == "limit" and (price is None or float(price) <= 0):
            raise OkxError("preço é obrigatório para ordem limit")
        body: dict[str, object] = {
            "instId": self._inst_id(symbol),
            "tdMode": "cash" if self.market == "spot" else "cross",
            "side": str(side).lower(),
            "ordType": kind,
            "sz": str(quantity),
            "clOrdId": request_id,
        }
        if kind == "limit":
            body["px"] = str(price)
        rows = self._post("/api/v5/trade/order", body)
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            return rows[0]
        return rows if isinstance(rows, dict) else {"raw": rows}

    @classmethod
    def _symbol(cls, symbol: str) -> str:
        """InstId da OKX: `BASE-QUOTE` com hifen.

        POR QUE DELEGA (2026-10-02)
        ============================
        Esta metodo ja tinha a tabela de quotes e o hifen, e foi a unica das
        quatro que acertava o formato. Mas ele tinha dois furos:

        1. Sem quote reconhecido, devolvia o valor cru — `EURUSD` virava
           `EURUSD`, que nao existe na OKX.
        2. Aceitava `EUR/USDT` e produzia `EUR-USDT`, um par que nao existe.

        Agora a identificacao do quote e a recusa de forex vem de
        `backend.exchange_symbols`, a fonte unica da regra; a OKX so
        acrescenta o hifen, que e a unica diferenca de formato entre ela e as
        outras tres.
        """
        from backend.exchange_symbols import QUOTES_ORDENADOS, par_exchange

        concatenado = par_exchange(symbol, "OKX spot")
        # O hifen entra antes do ULTIMO quote reconhecido. A lista vem do
        # normalizador, e `OKX.QUOTE_SUFFIXES` fica como espelho para o resto
        # do modulo OKX que ainda a consome.
        for quote in QUOTES_ORDENADOS:
            if concatenado.endswith(quote) and len(concatenado) > len(quote):
                return f"{concatenado[: -len(quote)]}-{quote}"
        return concatenado


    def _inst_id(self, symbol: str) -> str:
        """InstId da OKX: no futuro, o par concatenado vira um swap."""
        inst_id = self._symbol(symbol)
        if self.market == "futures" and inst_id.count("-") == 1:
            return f"{inst_id}-SWAP"
        return inst_id

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
            params["instId"] = self._inst_id(symbol)
        return self._get("/api/v5/trade/fills", params, signed=True)

    def depth(self, symbol: str, limit: int = 20) -> object:
        rows = self._rows(self._get("/api/v5/market/books", {"instId": self._inst_id(symbol), "sz": min(max(int(limit), 1), 400)}))
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
        rows = self._rows(self._get("/api/v5/market/trades", {"instId": self._inst_id(symbol), "limit": min(max(int(limit), 1), 500)}))
        return rows

    def ticker(self, symbol: str) -> object | None:
        inst_id = self._inst_id(symbol)
        rows = self._rows(self._get("/api/v5/market/ticker", {"instId": inst_id}))
        row = next((item for item in rows if isinstance(item, dict) and str(item.get("instId", "")).upper() == inst_id), None)
        if row is None:
            return None
        return {
            **row,
            "last": row.get("last"),
            "bidPx": row.get("bidPx"),
            "askPx": row.get("askPx"),
        }

    def ticker_batch(self, symbols: list[str] | tuple[str, ...] | None = None) -> list[object]:
        normalized = [self._inst_id(item) for item in (symbols or []) if str(item or "").strip()]
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
            "instId": self._inst_id(symbol),
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
