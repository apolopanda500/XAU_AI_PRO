// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

const storage = new Map<string, string>();
const localStorageStub = {
  getItem: (key: string) => storage.get(key) ?? null,
  setItem: (key: string, value: string) => { storage.set(key, value); },
  removeItem: (key: string) => { storage.delete(key); },
  clear: () => { storage.clear(); },
};

Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: localStorageStub });

const { default: MarketTab, isQuoteStale } = await import('./MarketTab');
const { useAppStore } = await import('../../hooks/useAppStore');

vi.mock('../charts/MiniPriceChart', () => ({ default: () => <div data-testid="mini-chart" /> }));
vi.mock('../charts/PriceChart', () => ({ default: () => <div data-testid="price-chart" /> }));

const response = (body: unknown, ok = true) => ({ ok, status: ok ? 200 : 503, json: async () => body }) as Response;
const connectedOverview = { ok: true, connections: [{ broker: 'binance', market: 'crypto-spot', active: true, status: 'conectada' }] };

beforeEach(() => {
  storage.clear();
  useAppStore.setState({ quotes: [], selectedSymbol: '', marketWatchlist: ['BTCUSDT'], subscribeSymbols: [] });
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); });

describe('MarketTab', () => {
  it('não solicita cotações quando não há corretora ativa', async () => {
    const fetchMock = vi.fn(); vi.stubGlobal('fetch', fetchMock); render(<MarketTab />);
    expect(await screen.findByText(/Selecione uma corretora em Contas ativas/i)).toBeTruthy();
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it('não solicita cotações quando a corretora selecionada está offline', async () => {
    localStorageStub.setItem('xau-active-account', 'binance:crypto-spot');
    const fetchMock = vi.fn().mockResolvedValue(response({ ok: true, connections: [{ broker: 'binance', market: 'crypto-spot', active: true, status: 'offline', error: 'API indisponível' }] }));
    vi.stubGlobal('fetch', fetchMock); render(<MarketTab />);
    expect((await screen.findAllByText('API indisponível')).length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/universal/overview');
  });
  it('consulta fonte conectada e oculta quote de broker anterior', async () => {
    localStorageStub.setItem('xau-active-account', 'binance:crypto-spot');
    useAppStore.setState({ quotes: [{ broker: 'mexc', market: 'crypto-spot', symbol: 'BTCUSDT', price: 1, bid: 1, ask: 1, last: 1, volume: 0, high: 0, low: 0, change: 0, change_pct: 0, spread: 0, digits: 2, point: 0, timestamp: new Date().toISOString(), source: 'mexc_api' }] });
    const fetchMock = vi.fn().mockResolvedValueOnce(response(connectedOverview)).mockResolvedValueOnce(response({ ok: true, quotes: [{ broker: 'binance', market: 'crypto-spot', symbol: 'BTCUSDT', bid: 100, ask: 101, last: 100.5, price: 100.5, spread: 1, source: 'binance_api', timestamp: '2026-09-21T00:00:00Z', received_at: '2026-09-21T00:00:00Z' }], errors: [] }));
    vi.stubGlobal('fetch', fetchMock); render(<MarketTab />);
    expect(await screen.findByText('binance_api')).toBeTruthy();
    expect(screen.queryByText('mexc_api')).toBeNull();
    expect(String(fetchMock.mock.calls[1][0])).toContain('/api/universal/quotes?broker=binance&market=crypto-spot&symbols=BTCUSDT');
  });
  it('consulta o endpoint universal da MEXC quando a fonte está conectada', async () => {
    localStorageStub.setItem('xau-active-account', 'mexc:crypto-spot');
    const fetchMock = vi.fn().mockResolvedValueOnce(response({ ok: true, connections: [{ broker: 'mexc', market: 'crypto-spot', active: true, status: 'conectada' }] })).mockResolvedValueOnce(response({ ok: true, quotes: [], errors: [] }));
    vi.stubGlobal('fetch', fetchMock); render(<MarketTab />);
    await screen.findByText(/ainda não retornou cotações reais/i);
    expect(String(fetchMock.mock.calls[1][0])).toContain('/api/universal/quotes?broker=mexc&market=crypto-spot&symbols=BTCUSDT');
  });
  it('considera quote vencida somente depois de 15 segundos', () => {
    const syncedAt = 1_000_000;
    expect(isQuoteStale(null, syncedAt + 99_999)).toBe(false);
    expect(isQuoteStale(syncedAt, syncedAt + 15_000)).toBe(false);
    expect(isQuoteStale(syncedAt, syncedAt + 15_001)).toBe(true);
  });
});