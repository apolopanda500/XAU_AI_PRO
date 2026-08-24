"""
XAU AI PRO - MarketLive
Cotações em tempo real.

Estratégia de provedores (config "live_provider"):
  - auto    : tenta MetaTrader5 primeiro, senão yfinance
  - mt5     : usa apenas MetaTrader5 (precisa MT5 aberto/terminal)
  - yfinance: usa apenas Yahoo Finance (via internet)

Retorna para cada símbolo: preço, bid, ask, variação (abs e %) e timestamp,
além de uma leitura de tendência curta (últimos candles M5 via MT5 quando
disponível) para alimentar o painel.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any

from config_store import get_api_config

# Mapeamento de símbolos da corretora para tickers Yahoo Finance
YF_MAP = {
    "XAUUSD": "GC=F",  # ouro futuro
    "XAUUSDc": "GC=F",
    "GOLD#": "GC=F",
    "GOLD": "GC=F",
    "BTCUSD": "BTC-USD",
    "BTCUSD#": "BTC-USD",
    "BTCUSDC": "BTC-USD",
    "ETHUSD#": "ETH-USD",
    "ETHUSD": "ETH-USD",
    "EURUSD": "EURUSD=X",
    "EURUSD#": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "GBPUSD#": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "USDJPY#": "JPY=X",
    "AUDUSD": "AUDUSD=X",
    "AUDUSD#": "AUDUSD=X",
    "USDCAD": "USDCAD=X",
    "USDCAD#": "USDCAD=X",
    "NZDUSD": "NZDUSD=X",
    "NZDUSD#": "NZDUSD=X",
    "SPX500": "^GSPC",
    "NAS100": "^IXIC",
    "US30": "^DJI",
    "US500": "^GSPC",
}


class MarketLive:
    def __init__(self) -> None:
        self._mt5 = self._load_mt5()
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._yf_client: Any = None

    # ----------------------------------------------------------
    # CARGA DE PROVEDORES
    # ----------------------------------------------------------
    @staticmethod
    def _load_mt5():
        try:
            import MetaTrader5 as mt5

            if mt5.initialize():
                return mt5
            return None
        except Exception:
            return None

    # ----------------------------------------------------------
    # FALLBACK HTTP (sem pacote yfinance - funciona no executavel)
    # ----------------------------------------------------------
    def _quote_http(self, symbol: str) -> dict[str, Any] | None:
        """Busca cotacao via API HTTP do Yahoo Finance usando apenas `requests`.
        Usado quando o pacote yfinance NAO esta empacotado no executavel."""
        try:
            import requests
            ticker = YF_MAP.get(symbol.upper(), symbol)
            url = (
                "https://query1.finance.yahoo.com/v8/finance/chart/"
                + ticker
                + "?interval=1m&range=1d"
            )
            h = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=h, timeout=8)
            if r.status_code != 200:
                return None
            data = r.json()
            res = data["chart"]["result"][0]
            meta = res.get("meta", {})
            price = meta.get("regularMarketPrice")
            prev = meta.get("chartPreviousClose") or meta.get("previousClose") or price
            if not price:
                return None
            change = price - (prev or price)
            change_pct = (change / (prev or price) * 100) if prev else 0.0
            return {
                "symbol": symbol,
                "price": round(price, 5),
                "bid": round(price, 5),
                "ask": round(price, 5),
                "change": round(change, 5),
                "change_pct": round(change_pct, 3),
                "digits": 5,
                "point": 0.00001,
                "spread": 0.0,
                "source": "http",
                "time": datetime.now().strftime("%H:%M:%S"),
            }
        except Exception:
            return None

    def _get_yf(self):
        if self._yf_client is None:
            try:
                import yfinance as yf

                self._yf_client = yf
            except Exception:
                self._yf_client = False
        return self._yf_client if self._yf_client else None

    # ----------------------------------------------------------
    # MT5
    # ----------------------------------------------------------
    def _quote_mt5(self, symbol: str) -> dict[str, Any] | None:
        if not self._mt5:
            return None
        try:
            tick = self._mt5.symbol_info_tick(symbol)
            info = self._mt5.symbol_info(symbol)
            if tick is None or info is None:
                return None
            price = (tick.bid + tick.ask) / 2
            return {
                "symbol": symbol,
                "price": round(price, 5),
                "bid": tick.bid,
                "ask": tick.ask,
                "change": 0.0,
                "change_pct": 0.0,
                "digits": info.digits,
                "point": info.point,
                "spread": round((tick.ask - tick.bid) / info.point, 1)
                if info.point
                else 0.0,
                "source": "mt5",
                "time": datetime.now().strftime("%H:%M:%S"),
            }
        except Exception:
            return None

    # ----------------------------------------------------------
    # YFINANCE
    # ----------------------------------------------------------
    def _quote_yf(self, symbol: str) -> dict[str, Any] | None:
        yf = self._get_yf()
        if not yf:
            return None
        ticker = YF_MAP.get(symbol.upper(), symbol)
        try:
            ticker = yf.Ticker(ticker)
            hist = ticker.history(period="5d", interval="1d")
            if hist.empty:
                return None
            price = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
            change = price - prev
            change_pct = (change / prev * 100) if prev else 0.0
            return {
                "symbol": symbol,
                "price": round(price, 5),
                "bid": round(price, 5),
                "ask": round(price, 5),
                "change": round(change, 5),
                "change_pct": round(change_pct, 3),
                "digits": 5,
                "point": 0.00001,
                "spread": 0.0,
                "source": "yfinance",
                "time": datetime.now().strftime("%H:%M:%S"),
            }
        except Exception:
            return None

    # ----------------------------------------------------------
    # API PÚBLICA
    # ----------------------------------------------------------
    def get_quote(self, symbol: str) -> dict[str, Any] | None:
        cfg = get_api_config()
        provider = cfg.get("live_provider", "auto")
        symbol = symbol.strip()

        candidates: list[tuple[str, Any]] = []
        if provider == "mt5" or provider == "auto":
            candidates.append(("mt5", self._quote_mt5(symbol)))
        if provider == "yfinance" or provider == "auto":
            candidates.append(("yf", self._quote_yf(symbol)))
        # Fallback HTTP (funciona no executavel sem o pacote yfinance)
        if provider in ("yfinance", "auto"):
            candidates.append(("http", self._quote_http(symbol)))

        for name, quote in candidates:
            if quote:
                with self._lock:
                    self._cache[symbol] = quote
                return quote
        return None

    def get_many(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for s in symbols:
            q = self.get_quote(s)
            if q:
                result[s] = q
        return result

    def cached(self, symbol: str) -> dict[str, Any] | None:
        with self._lock:
            return self._cache.get(symbol)

    def provider_available(self, name: str) -> bool:
        if name == "mt5":
            return self._mt5 is not None
        if name == "yfinance":
            return self._get_yf() is not None
        return False

    def sync_robot_snapshot(self, magic: int = 2026001) -> dict[str, Any] | None:
        """Sincroniza o snapshot do robô (conta + posições) com o MT5 bridge."""
        try:
            import mt5_integration as mi

            info = mi.get_account_info()
            positions = mi.get_positions(magic=magic)
            return {
                "account": info,
                "positions": positions,
                "positions_count": len(positions),
            }
        except Exception:
            return None
