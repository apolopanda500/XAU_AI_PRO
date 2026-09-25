// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

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

const now = '2026-09-24T12:00:00.000Z';

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

function envelope(broker: string, market: string) {
  return {
    ok: true,
    broker,
    market,
    source: `${broker}_api`,
    received_at: now,
    provider_timestamp: now,
  };
}

function payloadFor(input: RequestInfo | URL): unknown {
  const url = new URL(String(input), 'http://localhost');
  const broker = url.searchParams.get('broker') ?? 'binance';
  const market = url.searchParams.get('market') ?? 'crypto-spot';
  const symbol = url.searchParams.get('symbol') ?? 'BTCUSDT';
  const base = envelope(broker, market);
  if (url.pathname === '/api/capabilities') {
    return {
      ok: true,
      source: 'fastapi_gateway',
      received_at: now,
      matrix: [
        { broker: 'mt5', market: 'forex', status: 'active', read_only: true, capabilities: ['quotes'], execution: [], withdrawals: false, transfers: false },
        { broker: 'mt5', market: 'metals', status: 'active', read_only: true, capabilities: ['quotes'], execution: [], withdrawals: false, transfers: false },
        { broker: 'binance', market: 'crypto-spot', status: 'active', read_only: true, capabilities: ['quotes'], execution: [], withdrawals: false, transfers: false },
        { broker: 'binance', market: 'crypto-futures', status: 'active', read_only: true, capabilities: ['quotes'], execution: [], withdrawals: false, transfers: false },
        { broker: 'mexc', market: 'crypto-spot', status: 'active', read_only: true, capabilities: ['quotes'], execution: [], withdrawals: false, transfers: false },
        { broker: 'mexc', market: 'crypto-futures', status: 'active', read_only: true, capabilities: ['quotes'], execution: [], withdrawals: false, transfers: false },
        { broker: 'bybit', market: 'crypto-spot', status: 'code_only', read_only: true, capabilities: ['quotes'], execution: [], withdrawals: false, transfers: false },
      ],
    };
  }
  if (url.pathname === '/api/universal/overview') {
    return { ...base, source: 'universal_gateway', mt5_required: false, connected: 1, connections: [{ id: `${broker}:${market}:active`, broker, market, active: true, status: 'conectada', account: null, positions: [], pnl: null, error: null, source: 'universal_gateway' }] };
  }
  if (url.pathname === '/api/universal/assets') {
    return { ...base, assets: [{ symbol, display_name: symbol, asset_type: 'crypto', base_asset: 'BTC', quote_asset: 'USDT', enabled: true }], symbols: [], errors: [] };
  }
  if (url.pathname === '/api/universal/quotes') {
    return { ...base, quotes: [{ symbol, bid: 99, ask: 101, last: 100, price: 100, spread: 2, high: 110, low: 90, change: 1, change_pct: 1, volume: 10, timestamp: now, source: `${broker}_api`, received_at: now }], errors: [] };
  }
  if (url.pathname === '/api/universal/stats24h') {
    return { ...base, symbol, stats: { symbol, last: 100, bid: 99, ask: 101, high: 110, low: 90, change: 1, change_pct: 1, volume: 10, quote_volume: 1000, trades_count: 5, spread: 2 } };
  }
  if (url.pathname === '/api/universal/candles') {
    return { ...base, symbol, timeframe: url.searchParams.get('timeframe') ?? 'M5', candles: [{ time: 1_789_000_000, open: 99, high: 102, low: 98, close: 101, volume: 10 }] };
  }
  if (url.pathname === '/api/universal/depth') {
    return { ...base, symbol, bids: [[99, 2]], asks: [[101, 3]] };
  }
  if (url.pathname === '/api/universal/trades') {
    return { ...base, symbol, trades: [{ id: '1', symbol, side: 'BUY', price: 100, quantity: 1, timestamp: now, provider_timestamp: now, source: `${broker}_public_trades` }] };
  }
  if (url.pathname === '/api/status') {
    return { ...base, broker: 'mt5', market: 'metals', source: 'mt5_gateway', gateway: 'online', mt5_connected: true, account: null, positions: [], ea_heartbeat: { live: true, age_sec: 2, symbol: 'XAUUSD', autotrading: true, source: 'EA FILE_COMMON' } };
  }
  return { ...base, error: 'not_found' };
}

function installFetch() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => response(payloadFor(input), String(input).includes('/not-found') ? 404 : 200));
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

beforeEach(() => {
  storage.clear();
  localStorageStub.setItem('xau-market-source', 'binance:crypto-spot');
  useAppStore.setState((state) => ({
    quotes: [],
    selectedSymbol: '',
    marketWatchlist: ['BTCUSDT'],
    subscribeSymbols: [],
    settings: { ...state.settings, marketAutoRefresh: false },
  }));
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('MarketTab', () => {
  it('carrega mercado público somente por GET e sem conta ativa', async () => {
    const fetchMock = installFetch();
    render(<MarketTab />);
    expect((await screen.findAllByText('binance_api')).length).toBeGreaterThan(0);
    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(7);
    fetchMock.mock.calls.forEach(([, init]) => expect(init?.method).toBe('GET'));
    fetchMock.mock.calls.forEach(([input]) => expect(String(input)).toMatch(/\/api\/(capabilities|universal\/(overview|assets|quotes|stats24h|candles|depth|trades)|status)/));
  });

  it('não oferece controles acionáveis de trading', async () => {
    installFetch();
    render(<MarketTab />);
    await screen.findAllByText('binance_api');
    const controls = screen.getAllByRole('button').map((control) => control.textContent ?? '');
    expect(controls.some((label) => /comprar|vender|fechar|ordem|executarPosição/i.test(label))).toBe(false);
  });

  it('descarta dados da corretora anterior ao trocar a fonte', async () => {
    installFetch();
    render(<MarketTab />);
    expect((await screen.findAllByText('binance_api')).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText('Selecionar fonte do mercado'), { target: { value: 'mexc' } });
    expect((await screen.findAllByText('mexc_api')).length).toBeGreaterThan(0);
    expect(screen.queryByText('binance_api')).toBeNull();
  });

  it('limpa a seleção ao remover o último ativo', async () => {
    localStorageStub.setItem('xau-market-watchlist:binance:crypto-spot', JSON.stringify(['BTCUSDT']));
    installFetch();
    render(<MarketTab />);
    fireEvent.click(await screen.findByRole('button', { name: 'Remover BTCUSDT da lista' }));
    await waitFor(() => expect(useAppStore.getState().selectedSymbol).toBe(''));
    expect(screen.getByText(/Watchlist vazia|Lista vazia/i)).toBeTruthy();
  });

  it('não solicita capacidades públicas não expostas pelo MT5', async () => {
    localStorageStub.setItem('xau-market-source', 'mt5:metals');
    localStorageStub.setItem('xau-market-watchlist:mt5:metals', JSON.stringify(['XAUUSD']));
    const fetchMock = installFetch();
    render(<MarketTab />);
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/api/status'))).toBe(true));
    const paths = fetchMock.mock.calls.map(([input]) => String(input));
    expect(paths.some((path) => path.includes('/api/universal/stats24h'))).toBe(false);
    expect(paths.some((path) => path.includes('/api/universal/depth'))).toBe(false);
    expect(paths.some((path) => path.includes('/api/universal/trades'))).toBe(false);
  });

  it('considera quote vencida somente depois de 15 segundos', () => {
    const syncedAt = 1_000_000;
    expect(isQuoteStale(null, syncedAt + 99_999)).toBe(false);
    expect(isQuoteStale(syncedAt, syncedAt + 15_000)).toBe(false);
    expect(isQuoteStale(syncedAt, syncedAt + 15_001)).toBe(true);
  });
});
