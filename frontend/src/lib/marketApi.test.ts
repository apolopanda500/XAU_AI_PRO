// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { getCapabilities, getCandles, getDepth, getQuotes, getStats24h, MarketApiError } from './marketApi';

const values = new Map<string, string>();
Object.defineProperty(window, 'localStorage', {
  configurable: true,
  value: {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => {
      values.set(key, value);
    },
    removeItem: (key: string) => {
      values.delete(key);
    },
    clear: () => {
      values.clear();
    },
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
    const fetcher = vi.fn().mockResolvedValue(
      response({
        ...base,
        quotes: [
          { symbol: 'BTCUSDT', bid: 99, ask: 101, last: 100 },
          { symbol: 'ETHUSDT', bid: 9, ask: 11, last: 10 },
        ],
        errors: [],
      }),
    );
    const result = await getQuotes({ broker: 'binance', market: 'crypto-spot' }, ['BTCUSDT'], {
      fetcher,
    });
    expect(result.quotes.map((quote) => quote.symbol)).toEqual(['BTCUSDT']);
    expect(fetcher).toHaveBeenCalledWith(
      expect.stringContaining('symbols=BTCUSDT'),
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('normaliza estatísticas aninhadas sem trocar identidade', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      response({
        ...base,
        symbol: 'BTCUSDT',
        stats: { last: 100, high: 110, low: 90, trades_count: 8 },
      }),
    );
    const result = await getStats24h(
      { broker: 'binance', market: 'crypto-spot', symbol: 'BTCUSDT' },
      { fetcher },
    );
    expect(result.stats?.trades_count).toBe(8);
    expect(result.stats?.broker).toBe('binance');
  });

  it('rejeita resposta de outra corretora', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(
        response({ ...base, broker: 'mexc', symbol: 'BTCUSDT', stats: { last: 100 } }),
      );
    await expect(
      getStats24h({ broker: 'binance', market: 'crypto-spot', symbol: 'BTCUSDT' }, { fetcher }),
    ).rejects.toMatchObject({ code: 'identity' });
  });

  it('rejeita fonte simulada', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(
        response({ ...base, source: 'mock_market', symbol: 'BTCUSDT', stats: { last: 100 } }),
      );
    await expect(
      getStats24h({ broker: 'binance', market: 'crypto-spot', symbol: 'BTCUSDT' }, { fetcher }),
    ).rejects.toBeInstanceOf(MarketApiError);
  });

  it('carrega a matriz canônica de capacidades', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      response({
        ok: true,
        source: 'fastapi_gateway',
        received_at: '2026-09-24T12:00:00.000Z',
        matrix: [
          {
            broker: 'binance',
            market: 'crypto-spot',
            status: 'active',
            read_only: true,
            capabilities: ['quotes'],
            execution: [],
            withdrawals: false,
            transfers: false,
          },
        ],
      }),
    );
    const result = await getCapabilities({ fetcher });
    expect(result.matrix).toHaveLength(1);
    expect(result.matrix[0].withdrawals).toBe(false);
  });

  it('propaga limite de depth e usa somente GET', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(response({ ...base, symbol: 'BTCUSDT', bids: [], asks: [] }));
    await getDepth({ broker: 'binance', market: 'crypto-spot', symbol: 'BTCUSDT' }, 7, { fetcher });
    const [url, init] = fetcher.mock.calls[0];
    expect(String(url)).toContain('limit=7');
    expect(init.method).toBe('GET');
    expect(init.body).toBeUndefined();
  });
});

/*
  A PROCEDENCIA PUBLICA VIAJA ATE A TELA (12/10/2026)
  ===================================================
  MEDIDO no app instalado: com a corretora fora, o gateway preenchia com
  fonte publica (`fonte`, `fallback_publico`, `execucao: False`) — e a tela
  continuava escrevendo o nome da CORRETORA no cabecalho, porque a
  procedencia so lia `source` (quem montou a resposta). `source` nao muda
  (identidade do gateway); `fonte` viaja ao lado para o cabecalho mostrar.
*/
describe('marketApi — procedencia da fonte publica', () => {
  const vela = (time: number) => ({
    time,
    open: 85000,
    high: 85100,
    low: 84900,
    close: 85050,
    volume: 12,
  });

  it('PROVA: `fonte`, `fallback_publico` e `execucao` chegam em getCandles', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      response({
        ...base,
        symbol: 'BTCUSDT',
        candles: [vela(1788000000), vela(1788003600)],
        fonte: 'binance',
        fallback_publico: true,
        execucao: false,
      }),
    );
    const result = await getCandles(
      { broker: 'binance', market: 'crypto-spot', symbol: 'BTCUSDT' },
      'M15',
      300,
      { fetcher },
    );
    expect(result.candles).toHaveLength(2);
    expect(result.fonte).toBe('binance');
    expect(result.fallback_publico).toBe(true);
    expect(result.execucao).toBe(false);
    // E `source` continua sendo a identidade do gateway, nao a venue.
    expect(result.source).toBe('binance_api');
  });

  it('PROVA: sem fallback, os tres vem vazios — e nada e inventado', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      response({ ...base, symbol: 'BTCUSDT', candles: [vela(1788000000)] }),
    );
    const result = await getCandles(
      { broker: 'binance', market: 'crypto-spot', symbol: 'BTCUSDT' },
      'M15',
      300,
      { fetcher },
    );
    expect(result.candles).toHaveLength(1);
    expect(result.fonte ?? null).toBeNull();
    expect(result.fallback_publico ?? false).toBe(false);
    expect(result.execucao ?? null).toBeNull();
  });
});
