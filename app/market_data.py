"""
Provedores de dados de mercado para o app XAU_AI_PRO.
Suporta MT5 e HTTP (Yahoo Finance v8 via requests).
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.config_manager import get_config
from app.mt5_lock import mt5_lock


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


class MarketData:
    def __init__(self, provider: str = 'auto') -> None:
        self.provider = provider
        self._mt5: Any = None
        self._mt5_available = False
        self._cache: dict[str, Quote] = {}
        self._lock = threading.Lock()
        self._load_mt5()

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
        except Exception:
            self._mt5_available = False

    def _quote_mt5(self, symbol: str) -> Quote | None:
        if not self._mt5_available or self._mt5 is None:
            return None
        try:
            with mt5_lock:
                info = self._mt5.symbol_info(symbol)
                tick = self._mt5.symbol_info_tick(symbol)
            if info is None or tick is None:
                return None
            price = (tick.bid + tick.ask) / 2 if tick.bid and tick.ask else tick.last
            spread = round((tick.ask - tick.bid) / info.point, 1) if info.point else 0.0
            return Quote(
                symbol=symbol,
                price=round(price, info.digits),
                bid=round(tick.bid, info.digits),
                ask=round(tick.ask, info.digits),
                change=0.0, change_pct=0.0, spread=spread,
                digits=info.digits, point=info.point,
                volume=float(tick.volume) if hasattr(tick, 'volume') else 0.0,
                high=round(tick.high, info.digits) if hasattr(tick, 'high') else 0.0,
                low=round(tick.low, info.digits) if hasattr(tick, 'low') else 0.0,
                source='MT5', time=datetime.now().strftime('%H:%M:%S'),
                category=CATEGORY_MAP.get(symbol, 'forex'),
            )
        except Exception:
            return None

    def _quote_http(self, symbol: str) -> Quote | None:
        # Timeout generoso: Yahoo costuma responder em 1-3s; com 1s quase
        # tudo falhava e a aba Mercado ficava zerada sem MT5.
        try:
            import urllib.request
            ticker = YF_MAP.get(symbol.upper(), symbol)
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            result = data['chart']['result'][0]
            meta = result.get('meta', {})
            price = meta.get('regularMarketPrice')
            prev = meta.get('chartPreviousClose') or meta.get('previousClose') or price
            if price is None:
                return None
            change = price - prev
            change_pct = (change / prev * 100) if prev else 0.0
            digits = 5 if price < 1000 else 2
            return Quote(
                symbol=symbol, price=round(price, digits),
                bid=round(price, digits), ask=round(price, digits),
                change=round(change, digits), change_pct=round(change_pct, 3),
                spread=0.0, digits=digits, point=10 ** (-digits),
                volume=0.0, high=0.0, low=0.0,
                source='HTTP', time=datetime.now().strftime('%H:%M:%S'),
                category=CATEGORY_MAP.get(symbol, 'forex'),
            )
        except Exception:
            return None

    def _quote_exchange(self, symbol: str, exchange: str) -> Quote | None:
        pair = CRYPTO_EXCHANGE_MAP.get(symbol.upper())
        if not pair:
            return None
        try:
            import urllib.request
            if exchange == 'binance':
                url = f'https://api.binance.com/api/v3/ticker/24hr?symbol={pair}'
                source = 'Binance'
            elif exchange == 'mexc':
                url = f'https://api.mexc.com/api/v3/ticker/24hr?symbol={pair}'
                source = 'MEXC'
            else:
                return None
            req = urllib.request.Request(url, headers={'User-Agent': 'XAU-AI-PRO/1.2'})
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode('utf-8'))
            price = float(data['lastPrice'])
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
                source=source, time=datetime.now().strftime('%H:%M:%S'), category='crypto',
            )
        except Exception:
            return None

    def get_quote(self, symbol: str, provider: str | None = None) -> Quote | None:
        prov = provider or self.provider
        candidates: list[Quote | None] = []
        if prov in ('auto', 'mt5'):
            candidates.append(self._quote_mt5(symbol))
        if prov == 'auto' and symbol.upper() in CRYPTO_EXCHANGE_MAP:
            exchange = str(get_config().get('market', 'crypto_provider', default='binance')).lower()
            candidates.append(self._quote_exchange(symbol, exchange))
            if exchange != 'mexc':
                candidates.append(self._quote_exchange(symbol, 'mexc'))
        elif prov in ('binance', 'mexc'):
            candidates.append(self._quote_exchange(symbol, prov))
        if prov in ('auto', 'http'):
            candidates.append(self._quote_http(symbol))
        for q in candidates:
            if q is not None:
                with self._lock:
                    self._cache[symbol] = q
                return q
        return None

    def get_many(self, symbols: list[str], provider: str | None = None) -> dict[str, Quote]:
        result: dict[str, Quote] = {}
        for s in symbols:
            q = self.get_quote(s, provider)
            if q:
                result[s] = q
        return result

    def get_cached(self, symbol: str) -> Quote | None:
        with self._lock:
            return self._cache.get(symbol)

    def disconnect(self) -> None:
        # Nao chamamos mt5.shutdown(): a conexao IPC e compartilhada por todo
        # o processo (robot, graficos, busca) e o shutdown a derrubaria para todos.
        self._mt5_available = False
