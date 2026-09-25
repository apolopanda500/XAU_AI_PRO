export const marketsByBroker: Record<string, string[]> = {
  mt5: ['forex', 'metals', 'indices', 'stocks', 'commodities', 'bonds', 'crypto-spot', 'other'],
  mexc: ['crypto-spot', 'crypto-futures'],
  binance: ['crypto-spot', 'crypto-futures', 'stocks'],
  bybit: ['crypto-spot', 'crypto-futures', 'options'],
  okx: ['crypto-spot', 'crypto-futures', 'stocks', 'commodities', 'bonds'],
};

export function compatibleMarket(broker: string, current: string): string {
  const markets = marketsByBroker[broker] ?? [];
  return markets.includes(current) ? current : (markets[0] ?? '');
}

/** Mantém o catálogo visível mesmo antes de chegar a primeira cotação. */
export function buildAssetRows<T extends { symbol: string }>(assets: string[], quotes: T[]) {
  const normalize = (symbol: string) => symbol.toUpperCase().replace(/[/:_-]/g, '').replace(/\.P$/, '');
  const bySymbol = new Map<string, T>();
  for (const quote of quotes) {
    const key = normalize(quote.symbol);
    if (!bySymbol.has(key)) bySymbol.set(key, quote);
  }
  return assets.map((symbol) => ({ symbol, quote: bySymbol.get(normalize(symbol)) }));
}

/** Ausência e valores inválidos não são preços zero. */
export function displayQuoteValue(value: unknown): number | '--' {
  if (typeof value !== 'number' && typeof value !== 'string') return '--';
  if (typeof value === 'string' && !value.trim()) return '--';
  const number = Number(value);
  return Number.isFinite(number) ? number : '--';
}
