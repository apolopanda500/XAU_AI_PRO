// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { getCapabilities, getDepth, getQuotes, getStats24h, MarketApiError } from './marketApi';

const values = new Map<string, string>();
Object.defineProperty(window, 'localStorage', {
  configurable: true,
  value: {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => { values.set(key, value); },
    removeItem: (key: string) => { values.delete(key); },
    clear: () => { values.clear(); },
  },
});

function response(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

const base = {
  ok: true,
  broker: 'binance',
  market: 'crypto-spot',
  source: 'binance_api',
  received_at: '2026-09-24T12:00:00.000Z',
  provider_timestamp: '2026-09-24T12:00:00.000Z',
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe('marketApi', () => {
  it('normaliza quotes e restringe ao conjunto solicitado', async () => {
    const fetcher = vi.fn().mockResolvedValue(response({
      ...base,
      quotes: [
        { symbol: 'BTCUSDT', bid: 99, ask: 101, last: 100 },
        { symbol: 'ETHUSDT', bid: 9, ask: 11, last: 10 },
      ],
      errors: [],
    }));
    const result = await getQuotes({ broker: 'binance', market: 'crypto-spot' }, ['BTCUSDT'], { fetcher });
    expect(result.quotes.map((quote) => quote.symbol)).toEqual(['BTCUSDT']);
    expect(fetcher).toHaveBeenCalledWith(expect.stringContaining('symbols=BTCUSDT'), expect.objectContaining({ method: 'GET' }));
  });

  it('normaliza estatísticas aninhadas sem trocar identidade', async () => {
    const fetcher = vi.fn().mockResolvedValue(response({
      ...base,
      symbol: 'BTCUSDT',
      stats: { last: 100, high: 110, low: 90, trades_count: 8 },
    }));
    const result = await getStats24h({ broker: 'binance', market: 'crypto-spot', symbol: 'BTCUSDT' }, { fetcher });
    expect(result.stats?.trades_count).toBe(8);
    expect(result.stats?.broker).toBe('binance');
  });

  it('rejeita resposta de outra corretora', async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ ...base, broker: 'mexc', symbol: 'BTCUSDT', stats: { last: 100 } }));
    await expect(getStats24h({ broker: 'binance', market: 'crypto-spot', symbol: 'BTCUSDT' }, { fetcher })).rejects.toMatchObject({ code: 'identity' });
  });

  it('rejeita fonte simulada', async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ ...base, source: 'mock_market', symbol: 'BTCUSDT', stats: { last: 100 } }));
    await expect(getStats24h({ broker: 'binance', market: 'crypto-spot', symbol: 'BTCUSDT' }, { fetcher })).rejects.toBeInstanceOf(MarketApiError);
  });

  it('carrega a matriz canônica de capacidades', async () => {
    const fetcher = vi.fn().mockResolvedValue(response({
      ok: true,
      source: 'fastapi_gateway',
      received_at: '2026-09-24T12:00:00.000Z',
      matrix: [{ broker: 'binance', market: 'crypto-spot', status: 'active', read_only: true, capabilities: ['quotes'], execution: [], withdrawals: false, transfers: false }],
    }));
    const result = await getCapabilities({ fetcher });
    expect(result.matrix).toHaveLength(1);
    expect(result.matrix[0].withdrawals).toBe(false);
  });

  it('propaga limite de depth e usa somente GET', async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ ...base, symbol: 'BTCUSDT', bids: [], asks: [] }));
    await getDepth({ broker: 'binance', market: 'crypto-spot', symbol: 'BTCUSDT' }, 7, { fetcher });
    const [url, init] = fetcher.mock.calls[0];
    expect(String(url)).toContain('limit=7');
    expect(init.method).toBe('GET');
    expect(init.body).toBeUndefined();
  });
});
