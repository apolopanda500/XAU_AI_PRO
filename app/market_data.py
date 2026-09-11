# -*- coding: utf-8 -*-
"""
Proveedores de datos de mercado para el app XAU_AI_PRO.

Cadena de resiliencia por simbolo (provider='auto'), evaluada en lazy (se
detiene en el primer exito, sin gastar HTTP cuando MT5 responde):
  1) MT5 local (terminal conectado, simbolo publicado);
  2) Exchange publico de cripto (binance/mexc) cuando aplica;
  3) Yahoo Finance chart (fallback HTTP);
  4) Stooq CSV (ultimo recurso, sin API key, determinista).

Reglas de produccion:
  - Lecturas PARALELAS: get_many usa ThreadPoolExecutor (stdlib) con
    timeouts cortos (4 s) -> la lista completa resuelve en pocos segundos
    aunque un proveedor este caido (antes: ~96 s secuencial).
  - Error UNICO por simbolo: get_quote registra la causa final solo cuando
    TODOS los proveedores fallan (nada de errores fantasma de proveedores
    que ni se usaron).
  - Solo stdlib (urllib/threading/concurrent.futures): la GUI no arrastra
    pandas/numpy/sklearn al runtime (tecnologias livianas a proposito).
"""
from __future__ import annotations

import json
import os
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.config_manager import get_config
from app.mt5_lock import mt5_lock

# Timeouts cortos de red: la GUI debe responder aunque el proveedor falle.
HTTP_TIMEOUT = 4.0
MAX_WORKERS = 6


@dataclass
class Quote:
    symbol: str
    price: float
    bid: float
    ask: float
    change: float
    change_pct: float
    spread: float
    digits: int
    point: float
    volume: float = 0.0
    high: float = 0.0
    low: float = 0.0
    source: str = ''
    time: str = ''
    category: str = 'forex'

    def to_dict(self) -> dict[str, Any]:
        return {
            'symbol': self.symbol, 'price': self.price, 'bid': self.bid, 'ask': self.ask,
            'change': self.change, 'change_pct': self.change_pct, 'spread': self.spread,
            'digits': self.digits, 'point': self.point, 'volume': self.volume,
            'high': self.high, 'low': self.low, 'source': self.source,
            'time': self.time, 'category': self.category,
        }


YF_MAP: dict[str, str] = {
    'XAUUSD': 'GC=F', 'XAUUSDc': 'GC=F',
    'BTCUSD': 'BTC-USD', 'BTCUSDc': 'BTC-USD',
    'ETHUSD': 'ETH-USD', 'ETHUSDc': 'ETH-USD',
    'EURUSD': 'EURUSD=X', 'GBPUSD': 'GBPUSD=X',
    'USDJPY': 'JPY=X', 'AUDUSD': 'AUDUSD=X',
    'USDCAD': 'CAD=X', 'NZDUSD': 'NZDUSD=X', 'USDCHF': 'CHF=X',
    'US30': '^DJI', 'SPX500': '^GSPC', 'NAS100': '^NDX',
    'BTC=F': 'BTC=F', 'ES=F': 'ES=F', 'NQ=F': 'NQ=F', 'YM=F': 'YM=F', 'GC=F': 'GC=F',
}

# Stooq: solo simbolos FX/metales/indices con cobertura publica gratuita.
# (cripto no esta cubierta de forma fiable sin API key -> se omite).
STOOQ_MAP: dict[str, str] = {
    'XAUUSD': 'gold', 'XAUUSDc': 'gold',
    'EURUSD': 'eurusd', 'GBPUSD': 'gbpusd', 'USDJPY': 'usdjpy',
    'AUDUSD': 'audusd', 'USDCAD': 'usdcad', 'NZDUSD': 'nzdusd',
    'USDCHF': 'usdchf', 'SPX500': 'spx', 'NAS100': 'ndx', 'US30': 'dji',
}

CATEGORY_MAP: dict[str, str] = {
    'XAUUSD': 'forex', 'XAUUSDc': 'forex',
    'BTCUSD': 'crypto', 'BTCUSDc': 'crypto',
    'ETHUSD': 'crypto', 'ETHUSDc': 'crypto',
    'EURUSD': 'forex', 'GBPUSD': 'forex',
    'USDJPY': 'forex', 'AUDUSD': 'forex',
    'USDCAD': 'forex', 'NZDUSD': 'forex', 'USDCHF': 'forex',
    'US30': 'index', 'SPX500': 'index', 'NAS100': 'index',
    'BTC=F': 'futures', 'ES=F': 'futures', 'NQ=F': 'futures', 'YM=F': 'futures', 'GC=F': 'futures',
}

CRYPTO_EXCHANGE_MAP: dict[str, str] = {
    'BTCUSD': 'BTCUSDT', 'BTCUSDc': 'BTCUSDT',
    'ETHUSD': 'ETHUSDT', 'ETHUSDc': 'ETHUSDT',
}

# Hosts publicos con nombre fiable (sin API key).
YAHOO_HOSTS = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")
BINANCE_URL_LEGACY = "https://api.binance.com/api/v1/ticker/24hr"  # publico (deprecado pero vivo)
MEXC_URL = "https://api.mexc.com/api/v3/ticker/24hr"


def _now_ts() -> str:
    return datetime.now().strftime('%H:%M:%S')


class MarketData:
    def __init__(self, provider: str = 'auto') -> None:
        self.provider = provider
        self._mt5: Any = None
        self._mt5_available = False
        self._cache: dict[str, Quote] = {}
        self._lock = threading.Lock()
        # Errores por simbolo del ultimo ciclo (visible en la GUI).
        self._errors: dict[str, str] = {}
        # Timeout de socket global para no colgar los requests en maquinas sin red.
        socket.setdefaulttimeout(HTTP_TIMEOUT)
        self._load_mt5()

    # ---------------------------------------------------------------- estado
    def errors(self) -> dict[str, str]:
        """Causas de fallo del ultimo ciclo (symbol -> motivo concreto)."""
        with self._lock:
            return dict(self._errors)

    def clear_errors(self) -> None:
        with self._lock:
            self._errors = {}

    def _set_error(self, symbol: str, reason: str) -> None:
        with self._lock:
            self._errors[symbol] = reason

    def _clear_error(self, symbol: str) -> None:
        with self._lock:
            self._errors.pop(symbol, None)

    # ---------------------------------------------------------------- MT5
    def _load_mt5(self) -> None:
        try:
            import MetaTrader5 as mt5
            with mt5_lock:
                cfg_path = get_config().get("mt5", "terminal_path", default="")
                if cfg_path and os.path.exists(cfg_path):
                    ok = mt5.initialize(path=cfg_path)
                else:
                    ok = mt5.initialize()
            if ok:
                self._mt5 = mt5
                self._mt5_available = True
            else:
                # Ya inicializado por MT5Robot (mismo proceso): la conexion IPC
                # es compartida; la API no exige reinicializar.
                self._mt5 = mt5
                self._mt5_available = True
        except Exception:
            self._mt5_available = False

    def _quote_mt5(self, symbol: str) -> Quote | None:
        if not self._mt5_available or self._mt5 is None:
            return None
        try:
            with mt5_lock:
                info = self._mt5.symbol_info(symbol)
                tick = self._mt5.symbol_info_tick(symbol)
            if info is None or tick is None or tick.bid is None or tick.ask is None:
                return None
            price = (tick.bid + tick.ask) / 2
            spread = round((tick.ask - tick.bid) / info.point, 1) if info.point else 0.0
            return Quote(
                symbol=symbol,
                price=round(price, info.digits),
                bid=round(tick.bid, info.digits),
                ask=round(tick.ask, info.digits),
                change=0.0, change_pct=0.0, spread=spread,
                digits=info.digits, point=info.point,
                volume=float(tick.volume) if getattr(tick, 'volume', None) else 0.0,
                high=round(float(tick.high), info.digits) if getattr(tick, 'high', 0) else 0.0,
                low=round(float(tick.low), info.digits) if getattr(tick, 'low', 0) else 0.0,
                source='MT5', time=_now_ts(),
                category=CATEGORY_MAP.get(symbol, 'forex'),
            )
        except Exception:
            return None

    # ---------------------------------------------------------------- cripto
    def _quote_exchange(self, symbol: str, exchange: str) -> Quote | None:
        pair = CRYPTO_EXCHANGE_MAP.get(symbol.upper())
        if not pair:
            return None
        try:
            import urllib.request
            if exchange == 'binance':
                url = f"{BINANCE_URL_LEGACY}?symbol={pair}"
                source = 'Binance'
            elif exchange == 'mexc':
                url = f"{MEXC_URL}?symbol={pair}"
                source = 'MEXC'
            else:
                return None
            req = urllib.request.Request(url, headers={'User-Agent': 'XAU-AI-PRO/1.2'})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as response:
                data = json.loads(response.read().decode('utf-8', errors='replace'))
            price = float(data.get('lastPrice') or 0)
            if price <= 0:
                return None
            bid = float(data.get('bidPrice') or data.get('bid1Price') or price)
            ask = float(data.get('askPrice') or data.get('ask1Price') or price)
            change = float(data.get('priceChange') or 0.0)
            change_pct = float(data.get('priceChangePercent') or 0.0)
            return Quote(
                symbol=symbol, price=round(price, 2), bid=round(bid, 2), ask=round(ask, 2),
                change=round(change, 2), change_pct=round(change_pct, 3),
                spread=round(ask - bid, 2), digits=2, point=0.01,
                volume=float(data.get('volume') or 0.0),
                high=round(float(data.get('highPrice') or 0.0), 2),
                low=round(float(data.get('lowPrice') or 0.0), 2),
                source=source, time=_now_ts(), category='crypto',
            )
        except Exception:
            return None

    # ---------------------------------------------------------------- HTTP
    def _fetch_json(self, url: str, headers: dict[str, str]) -> Any:
        """GET con UA propio y timeout corto; lanza si no hay JSON valido."""
        import urllib.request
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as response:
            return json.loads(response.read().decode('utf-8', errors='replace'))

    def _quote_http(self, symbol: str) -> Quote | None:
        """Yahoo Finance chart (fallback). Host 2 como respaldo anti rate-limit."""
        ticker = YF_MAP.get(symbol.upper(), symbol)
        for host in YAHOO_HOSTS:
            url = f'https://{host}/v8/finance/chart/{ticker}?interval=1d&range=5d'
            try:
                data = self._fetch_json(url, {'User-Agent': 'Mozilla/5.0'})
                result = data.get('chart', {}).get('result') or []
                if not result:
                    continue
                meta = result[0].get('meta', {})
                price = meta.get('regularMarketPrice')
                prev = meta.get('chartPreviousClose') or meta.get('previousClose') or price
                if price is None or prev is None:
                    continue
                change = price - prev
                change_pct = (change / prev * 100) if prev else 0.0
                digits = 5 if price < 1000 else 2
                return Quote(
                    symbol=symbol, price=round(price, digits),
                    bid=round(price, digits), ask=round(price, digits),
                    change=round(change, digits), change_pct=round(change_pct, 3),
                    spread=0.0, digits=digits, point=10 ** (-digits),
                    volume=0.0, high=0.0, low=0.0,
                    source='Yahoo', time=_now_ts(),
                    category=CATEGORY_MAP.get(symbol, 'forex'),
                )
            except Exception:
                continue
        return None

    def _quote_stooq(self, symbol: str) -> Quote | None:
        """Stooq CSV (ultimo recurso, sin API key). Simbolos FX/metales/indices."""
        st = STOOQ_MAP.get(symbol.upper())
        if not st:
            return None
        try:
            import urllib.request
            url = f'https://stooq.com/q/l/?s={st}&f=sd2t2ohlcv&h&e=csv'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as response:
                raw = response.read().decode('utf-8', errors='replace')
            lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            if len(lines) < 2:
                return None
            cols = lines[1].split(',')
            if len(cols) < 6 or cols[4] in ('', 'N/D'):
                return None
            price = float(cols[4])
            digits = 5 if price < 1000 else 2
            return Quote(
                symbol=symbol, price=round(price, digits),
                bid=round(price, digits), ask=round(price, digits),
                change=0.0, change_pct=0.0,
                spread=0.0, digits=digits, point=10 ** (-digits),
                volume=0.0, high=0.0, low=0.0,
                source='Stooq', time=_now_ts(),
                category=CATEGORY_MAP.get(symbol, 'forex'),
            )
        except Exception:
            return None

    # ---------------------------------------------------------------- API
    def _candidates(self, symbol: str, prov: str) -> list[tuple[str, str | None]]:
        """Lista (etiqueta, exchange) de proveedores a intentar, en orden."""
        plan: list[tuple[str, str | None]] = []
        if prov in ('auto', 'mt5'):
            plan.append(("mt5", None))
        if symbol.upper() in CRYPTO_EXCHANGE_MAP:
            if prov in ('auto', 'binance', 'mexc'):
                exchange = str(get_config().get('market', 'crypto_provider', default='binance')).lower()
                plan.append(("exchange", exchange))
                if prov == 'auto' and exchange != 'mexc':
                    plan.append(("exchange", 'mexc'))
        if prov in ('auto', 'http'):
            plan.append(("http", None))
            if prov == 'auto':
                plan.append(("stooq", None))
        return plan

    def get_quote(self, symbol: str, provider: str | None = None) -> Quote | None:
        """Evaluacion lazy: detiene la cadena en el PRIMER proveedor con datos.

        El error se registra UNA vez por simbolo y solo si todos fallaron, con
        las causas separadas por ' | ' para diagnosticar en la GUI.
        """
        prov = provider or self.provider
        reasons: list[str] = []

        for kind, exchange in self._candidates(symbol, prov):
            if kind == 'mt5':
                q = self._quote_mt5(symbol)
                if q is not None:
                    self._clear_error(symbol)
                    with self._lock:
                        self._cache[symbol] = q
                    return q
                if self._mt5_available:
                    reasons.append("MT5 sin tick")
                else:
                    reasons.append("MT5 no conectado")
            elif kind == 'exchange':
                q = self._quote_exchange(symbol, exchange or '')
                if q is not None:
                    self._clear_error(symbol)
                    with self._lock:
                        self._cache[symbol] = q
                    return q
                reasons.append(f"{exchange} sin datos")
            elif kind == 'http':
                q = self._quote_http(symbol)
                if q is not None:
                    self._clear_error(symbol)
                    with self._lock:
                        self._cache[symbol] = q
                    return q
                reasons.append("Yahoo sin datos")
            elif kind == 'stooq':
                q = self._quote_stooq(symbol)
                if q is not None:
                    self._clear_error(symbol)
                    with self._lock:
                        self._cache[symbol] = q
                    return q
                reasons.append("Stooq sin datos")

        self._set_error(symbol, " | ".join(dict.fromkeys(reasons)) or "sin proveedores")
        return None

    def get_many(self, symbols: list[str], provider: str | None = None) -> dict[str, Quote]:
        """Consulta paralela con pool stdlib; cada simbolo con timeout propio.

        Sin paralelismo la lista completa tardaba hasta ~96 s (secuencial con
        timeouts de 8 s) y la GUI quedaba 'trabada' en _busy=True.
        """
        symbols = [s for s in symbols if s]
        if not symbols:
            return {}
        result: dict[str, Quote] = {}
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(self.get_quote, s, provider): s for s in symbols}
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    quote = future.result()
                except Exception:
                    self._set_error(symbol, "worker fallido")
                    continue
                if quote is not None:
                    result[symbol] = quote
        return result

    def get_cached(self, symbol: str) -> Quote | None:
        with self._lock:
            return self._cache.get(symbol)

    def disconnect(self) -> None:
        # No usamos mt5.shutdown(): la conexion IPC es compartida por todo el
        # proceso (robot, graficos, busqueda) y apagarla los derribaria a todos.
        self._mt5_available = False