"""Cliente Binance Spot/Futures somente leitura."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class BinanceError(RuntimeError):
    pass


class BinanceClient:
    def __init__(self, market: str = 'spot') -> None:
        if market not in {'spot', 'futures'}: raise ValueError('market deve ser spot ou futures')
        self.market = market; self.api_key = os.getenv(f'BINANCE_{market.upper()}_API_KEY', '').strip(); self.secret = os.getenv(f'BINANCE_{market.upper()}_API_SECRET', '').strip()
        self.base = os.getenv(f'BINANCE_{market.upper()}_BASE_URL', 'https://api.binance.com' if market == 'spot' else 'https://fapi.binance.com').rstrip('/')

    @property
    def configured(self) -> bool: return bool(self.api_key and self.secret)

    def _get(self, path: str, params: dict[str, object] | None = None, signed: bool = False) -> object:
        query = dict(params or {})
        if signed:
            if not self.configured: raise BinanceError(f'credenciais Binance {self.market} não configuradas')
            query['timestamp'] = int(time.time() * 1000); payload = urlencode(query); query['signature'] = hmac.new(self.secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        url = f'{self.base}{path}' + (f'?{urlencode(query)}' if query else '')
        try:
            with urlopen(Request(url, headers={'X-MBX-APIKEY': self.api_key, 'Accept': 'application/json'}, method='GET'), timeout=10) as response: data = json.loads(response.read().decode())
        except Exception as exc: raise BinanceError(f'Binance {self.market} indisponível: {exc}') from exc
        if isinstance(data, dict) and 'code' in data and int(data['code']) < 0: raise BinanceError(str(data))
        return data

    def exchange_info(self) -> object: return self._get('/api/v3/exchangeInfo') if self.market == 'spot' else self._get('/fapi/v1/exchangeInfo')
    def account(self) -> object: return self._get('/api/v3/account', signed=True) if self.market == 'spot' else self._get('/fapi/v2/account', signed=True)
    def history(self, symbol: str = '', limit: int = 100) -> object:
        params: dict[str, object] = {'limit': min(max(limit, 1), 1000)}
        if symbol.strip(): params['symbol'] = symbol.strip().upper()
        return self._get('/api/v3/myTrades' if self.market == 'spot' else '/fapi/v1/userTrades', params, signed=True)
    def depth(self, symbol: str, limit: int = 20) -> object:
        params = {'symbol': symbol.strip().upper(), 'limit': min(max(limit, 5), 100)}
        return self._get('/api/v3/depth' if self.market == 'spot' else '/fapi/v1/depth', params)
    def trades(self, symbol: str, limit: int = 20) -> object:
        return self._get('/api/v3/trades' if self.market == 'spot' else '/fapi/v1/trades', {'symbol': symbol.upper(), 'limit': min(max(limit, 5), 100)})
