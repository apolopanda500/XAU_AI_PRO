import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useAppStore } from '../../hooks/useAppStore';
import { atr, macd, rsi } from '../../lib/technical';
import { getAssets, getCapabilities, getCandles, getDepth, getOverview, getQuotes, getStats24h, getTrades, MARKET_SOURCES, normalizeMarketSource, type MarketAsset, type MarketCandle, type MarketConnection, type MarketIdentity, type MarketKind, type MarketOverview, type MarketQuote, type MarketSource, type MarketSourceOption, type MarketStats24h } from '../../lib/marketApi';
import MiniPriceChart from '../charts/MiniPriceChart';
import PriceChart, { type ChartTimeframe } from '../charts/PriceChart';
import { normalizeSymbols } from '../../lib/constants';
import { formatNumber, formatSigned, formatTime, formatDateTime, receivedTimestamp, isMarketStale, STALE_AFTER_MS } from '../../lib/marketFormat';
import '../../theme/market.css';
import '../../theme/market-quotes-compact.css';

export const REFRESH_MIN_MS = 2_000;
export const REFRESH_MAX_MS = 10_000;
export const OVERVIEW_REFRESH_MS = 15_000;
// O catalogo de ativos muda pouco: 60s evita hammering na exchange.
export const ASSETS_REFRESH_MS = 60_000;
// Candles, stats, depth e trades usavam 15s, o que deixava o grafico
// visivelmente atrasado em relacao a cotacao (que vai a 2-10s). O operador
// via o preco andar e a vela nao. Alinhado ao mesmo intervalo das cotacoes.
export const SELECTED_REFRESH_MS = REFRESH_MIN_MS;

type EndpointKey = 'capabilities' | 'overview' | 'assets' | 'quotes' | 'stats24h' | 'candles' | 'depth' | 'trades' | 'status';
type ErrorState = Partial<Record<EndpointKey, string>>;
type Settled<T> = { value: T | null; error: string | null };
type RequestEntry = { controller: AbortController; promise: Promise<unknown> };

type KpiProps = {
  label: string;
  value: number | null;
  suffix?: string;
  digits?: number;
  tone?: 'positive' | 'negative' | 'neutral';
};

const DEFAULT_WATCHLISTS: Record<string, string[]> = {
  'mt5:forex': ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY'],
  'mt5:metals': ['XAUUSD', 'XAGUSD'],
  'mt5:indices': ['US30', 'NAS100'],
  'mt5:other': ['XAUUSD'],
  'binance:crypto-spot': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
  'binance:crypto-futures': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
  'mexc:crypto-spot': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
  'mexc:crypto-futures': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
};

const ERROR_LABELS: Record<EndpointKey, string> = {
  capabilities: 'Capacidades',
  overview: 'Contas',
  assets: 'Catálogo',
  quotes: 'Cotações',
  stats24h: 'Estatísticas',
  candles: 'Candles',
  depth: 'Livro de ofertas',
  trades: 'Negócios',
  status: 'MT5',
};

const sourceKey = (source: MarketSource): string => `${source.broker}:${source.market}`;

function useReadGate() {
  const active = useRef<RequestEntry | null>(null);
  const run = useCallback(function runRequest<T>(loader: (signal: AbortSignal) => Promise<T>): Promise<T> {
    const current = active.current;
    if (current && !current.controller.signal.aborted) return current.promise as Promise<T>;
    const controller = new AbortController();
    let entry: RequestEntry;
    const promise = (async () => {
      try {
        return await loader(controller.signal);
      } finally {
        if (active.current === entry) active.current = null;
      }
    })();
    entry = { controller, promise };
    active.current = entry;
    return promise;
  }, []);
  const cancel = useCallback(() => {
    active.current?.controller.abort();
    active.current = null;
  }, []);
  useEffect(() => cancel, [cancel]);
  return { run, cancel };
}

function readStorage(key: string): string | null {
  try {
    return typeof window !== 'undefined' ? window.localStorage.getItem(key) : null;
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string): void {
  try {
    if (typeof window !== 'undefined') window.localStorage.setItem(key, value);
  } catch {
    return;
  }
}

function removeStorage(key: string): void {
  try {
    if (typeof window !== 'undefined') window.localStorage.removeItem(key);
  } catch {
    return;
  }
}

function readSource(): MarketSource {
  const explicit = readStorage('xau-market-source')?.split(':');
  const active = readStorage('xau-active-account')?.split(':');
  const candidate = explicit?.[0] && explicit[1] ? explicit : active?.[0] && active[1] ? active : ['binance', 'crypto-spot'];
  return normalizeMarketSource(candidate[0], candidate[1]) ?? { broker: 'binance', market: 'crypto-spot' };
}

function readWatchlist(source: MarketSource): string[] {
  const key = `xau-market-watchlist:${sourceKey(source)}`;
  try {
    const raw = readStorage(key);
    if (raw) {
      const parsed: unknown = JSON.parse(raw);
      if (Array.isArray(parsed)) return normalizeSymbols(parsed);
    }
  } catch {
    return normalizeSymbols(DEFAULT_WATCHLISTS[sourceKey(source)] ?? []);
  }
  return normalizeSymbols(DEFAULT_WATCHLISTS[sourceKey(source)] ?? []);
}

function readSelectedSymbol(source: MarketSource, watchlist: string[]): string {
  const stored = readStorage(`xau-market-selected:${sourceKey(source)}`);
  return stored && watchlist.includes(stored) ? stored : watchlist[0] ?? '';
}

// normalizeSymbols agora vem de lib/constants.ts (fonte única). Esta cópia
// local era a 3ª implementação e divergia das outras duas.

function sourceLabel(source: MarketSource, sources: readonly MarketSourceOption[] = MARKET_SOURCES): string {
  const broker = sources.find((item) => item.broker === source.broker)?.label ?? source.broker.toUpperCase();
  const market = source.market === 'crypto-spot' ? 'Spot' : source.market === 'crypto-futures' ? 'Futuros' : source.market;
  return `${broker} · ${market}`;
}

function marketLabel(market: string): string {
  return market === 'crypto-spot' ? 'Spot' : market === 'crypto-futures' ? 'Futuros' : market;
}

function readError(reason: unknown): string {
  if (reason instanceof Error && reason.message) return reason.message;
  return 'A fonte não respondeu.';
}

function isAborted(reason: unknown): boolean {
  return reason instanceof Error && reason.name === 'AbortError';
}

async function settle<T>(promise: Promise<T>): Promise<Settled<T>> {
  try {
    return { value: await promise, error: null };
  } catch (reason) {
    return { value: null, error: isAborted(reason) ? null : readError(reason) };
  }
}


export const isQuoteStale = isMarketStale;

function Kpi({ label, value, suffix, digits = 2, tone = 'neutral' }: KpiProps) {
  const className = tone === 'positive' ? 'pos' : tone === 'negative' ? 'neg' : '';
  return <div className="market-kpi"><span className="kpi-label">{label}</span><strong className={`market-kpi-value ${className}`}>{formatNumber(value, digits)}{suffix && value !== null ? ` ${suffix}` : ''}</strong></div>;
}

function connectionFor(overview: MarketOverview | null, source: MarketSource): MarketConnection | null {
  return overview?.connections.find((connection) => connection.broker.toLowerCase() === source.broker && connection.market === source.market) ?? null;
}

function identityFor(source: MarketSource, symbol: string): MarketIdentity {
  return { ...source, symbol: symbol.toUpperCase() };
}

function partialErrorMessage(errors: ErrorState): string {
  return Object.entries(errors)
    .filter((entry): entry is [EndpointKey, string] => Boolean(entry[1]))
    .map(([key, value]) => `${ERROR_LABELS[key]}: ${value}`)
    .join(' · ');
}

function KpiGrid({ stats, quote }: { stats: MarketStats24h | null; quote: MarketQuote | null }) {
  const last = stats?.last ?? quote?.last ?? null;
  const bid = stats?.bid ?? quote?.bid ?? null;
  const ask = stats?.ask ?? quote?.ask ?? null;
  const spread = stats?.spread ?? quote?.spread ?? (bid !== null && ask !== null ? ask - bid : null);
  const spreadBps = bid !== null && ask !== null && bid + ask !== 0 ? ((ask - bid) / ((ask + ask) / 2)) * 10_000 : null;
  const change = stats?.change ?? quote?.change ?? null;
  const changePct = stats?.change_pct ?? quote?.change_pct ?? null;
  const tone = change === null ? 'neutral' : change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral';
  return <div className="market-kpis" role="group" aria-label="Indicadores da cotação">
    <Kpi label="Ãšltimo" value={last} />
    <Kpi label="Compra" value={bid} />
    <Kpi label="Venda" value={ask} />
    <Kpi label="Spread" value={spread} />
    <Kpi label="Spread bps" value={spreadBps} digits={3} />
    <Kpi label="Máxima 24h" value={stats?.high ?? quote?.high ?? null} />
    <Kpi label="Mínima 24h" value={stats?.low ?? quote?.low ?? null} />
    <Kpi label="Variação" value={change} tone={tone} />
    <Kpi label="Variação %" value={changePct} digits={3} tone={tone} />
    <Kpi label="Volume" value={stats?.volume ?? quote?.volume ?? null} digits={4} />
    <div className="market-kpi"><span className="kpi-label">Provedor</span><strong className="market-kpi-timestamp">{formatDateTime(stats?.provider_timestamp ?? quote?.provider_timestamp)}</strong><small>Recebido: {formatDateTime(stats?.received_at ?? quote?.received_at)}</small></div>
  </div>;
}

export default function MarketTab() {
  const [source, setSource] = useState<MarketSource>(() => readSource());
  const [marketSources, setMarketSources] = useState<MarketSourceOption[]>(() => MARKET_SOURCES.map((item) => ({ ...item, markets: [...item.markets] })));
  const [watchlist, setWatchlist] = useState<string[]>(() => readWatchlist(source));
  const [selectedSymbol, setSelectedSymbol] = useState<string>(() => readSelectedSymbol(source, watchlist));
  const [search, setSearch] = useState('');
  const [timeframe, setTimeframe] = useState<ChartTimeframe>('M5');
  const [assets, setAssets] = useState<MarketAsset[]>([]);
  const [quotes, setQuotes] = useState<Record<string, MarketQuote>>({});
  const [overview, setOverview] = useState<MarketOverview | null>(null);
  const [stats, setStats] = useState<MarketStats24h | null>(null);
  const [candles, setCandles] = useState<MarketCandle[]>([]);
  const [depth, setDepth] = useState<{ bids: Array<{ price: number | null; quantity: number | null }>; asks: Array<{ price: number | null; quantity: number | null }>; source: string } | null>(null);
  const [trades, setTrades] = useState<{ trades: Array<{ id: string | null; side: 'BUY' | 'SELL' | null; price: number | null; quantity: number | null; provider_timestamp: string | null; source: string }>; source: string } | null>(null);
  const [errors, setErrors] = useState<ErrorState>({});
  const [capabilitiesLoading, setCapabilitiesLoading] = useState(true);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [assetsLoading, setAssetsLoading] = useState(true);
  const [quotesLoading, setQuotesLoading] = useState(true);
  const [selectedLoading, setSelectedLoading] = useState(() => Boolean(selectedSymbol));
  const [overviewReceivedAt, setOverviewReceivedAt] = useState<number | null>(null);
  const [quotesReceivedAt, setQuotesReceivedAt] = useState<number | null>(null);
  const [selectedReceivedAt, setSelectedReceivedAt] = useState<number | null>(null);
  const [instrumentKey, setInstrumentKey] = useState('');
  const [now, setNow] = useState(() => Date.now());
  const capabilitiesGate = useReadGate();
  const overviewGate = useReadGate();
  const assetsGate = useReadGate();
  const quotesGate = useReadGate();
  const selectedGate = useReadGate();
  const setStoreSelectedSymbol = useAppStore((state) => state.setSelectedSymbol);
  const setMarketWatchlist = useAppStore((state) => state.setMarketWatchlist);
  const setSubscribeSymbols = useAppStore((state) => state.setSubscribeSymbols);
  const marketAutoRefresh = useAppStore((state) => state.settings.marketAutoRefresh);
  const setSettings = useAppStore((state) => state.setSettings);
  const marketRefreshMs = useAppStore((state) => state.settings.marketRefreshMs);

  const refreshMs = Math.min(REFRESH_MAX_MS, Math.max(REFRESH_MIN_MS, Number(marketRefreshMs) || 5_000));
  const quoteSymbols = useMemo(() => normalizeSymbols([selectedSymbol, ...watchlist]), [selectedSymbol, watchlist]);
  const catalogSymbols = useMemo(() => normalizeSymbols([...watchlist, ...assets.map((asset) => asset.symbol)]), [assets, watchlist]);
  // Sem termo de busca a tabela mostra SO a lista do operador, como o Market
  // Watch do MT5. Antes ela reunia lista + catalogo inteiro, o que fazia o
  // botao de remover nao ter efeito visivel (o ativo continuava vindo de
  // `assets`) e despejava centenas de linhas. Com busca, o catalogo inteiro
  // volta para permitir escolher o que adicionar.
  const termoBusca = search.trim().toLowerCase();
  const filteredSymbols = useMemo(
    () => (termoBusca ? catalogSymbols.filter((symbol) => symbol.toLowerCase().includes(termoBusca)) : watchlist),
    [catalogSymbols, watchlist, termoBusca],
  );
  const selectedQuote = selectedSymbol ? quotes[selectedSymbol.toUpperCase()] ?? null : null;
  const connection = connectionFor(overview, source);
  const currentInstrumentKey = `${sourceKey(source)}:${selectedSymbol}:${timeframe}`;
  const instrumentVisible = instrumentKey === currentInstrumentKey;
  const visibleStats = instrumentVisible ? stats : null;
  const visibleCandles = instrumentVisible ? candles : [];
  const visibleDepth = instrumentVisible ? depth : null;
  const visibleTrades = instrumentVisible ? trades : null;
  const marketStale = isMarketStale(quotesReceivedAt, now);
  const selectedStale = isMarketStale(selectedReceivedAt, now);
  const errorSummary = partialErrorMessage(errors);
  const hasMarketData = assets.length > 0 || Object.keys(quotes).length > 0;
  const hasInstrumentData = Boolean(visibleStats || visibleCandles.length || visibleDepth || visibleTrades);
  const marketLoading = assetsLoading || quotesLoading;

  const clearInstrument = useCallback(() => {
    setStats(null);
    setCandles([]);
    setDepth(null);
    setTrades(null);
    setInstrumentKey('');
    setSelectedReceivedAt(null);
    setSelectedLoading(false);
  }, []);

  const refreshCapabilities = useCallback(async () => {
    let requestSignal: AbortSignal | null = null;
    setCapabilitiesLoading(true);
    setErrors((current) => ({ ...current, capabilities: '' }));
    try {
      const result = await capabilitiesGate.run((signal) => {
        requestSignal = signal;
        return getCapabilities({ signal });
      });
      if (requestSignal?.aborted) return;
      const grouped = new Map<MarketSourceOption['broker'], MarketSourceOption>();
      result.matrix.forEach((row) => {
        if (row.withdrawals || row.transfers) return;
        const fallback = MARKET_SOURCES.find((item) => item.broker === row.broker);
        const current = grouped.get(row.broker) ?? { broker: row.broker, label: fallback?.label ?? row.broker.toUpperCase(), markets: [], enabled: false };
        if (!current.markets.includes(row.market)) current.markets.push(row.market);
        current.enabled = current.enabled || row.status === 'active';
        grouped.set(row.broker, current);
      });
      const next = [...grouped.values()].filter((item) => item.markets.length > 0);
      if (!next.length) throw new Error('Matriz de capacidades vazia ou insegura.');
      setMarketSources(next);
    } catch (reason) {
      if (!requestSignal?.aborted && !isAborted(reason)) setErrors((current) => ({ ...current, capabilities: readError(reason) }));
    } finally {
      if (!requestSignal?.aborted) setCapabilitiesLoading(false);
    }
  }, [capabilitiesGate.run]);

  const refreshOverview = useCallback(async () => {
    let requestSignal: AbortSignal | null = null;
    setOverviewLoading(true);
    setErrors((current) => ({ ...current, overview: '' }));
    try {
      const result = await overviewGate.run((signal) => {
        requestSignal = signal;
        return getOverview({ signal });
      });
      if (requestSignal?.aborted) return;
      setOverview(result);
      setOverviewReceivedAt(Date.now());
      setNow(Date.now());
    } catch (reason) {
      if (!requestSignal?.aborted && !isAborted(reason)) setErrors((current) => ({ ...current, overview: readError(reason) }));
    } finally {
      if (!requestSignal?.aborted) setOverviewLoading(false);
    }
  }, [overviewGate.run]);

  const refreshAssets = useCallback(async () => {
    let requestSignal: AbortSignal | null = null;
    setAssetsLoading(true);
    setErrors((current) => ({ ...current, assets: '' }));
    try {
      const result = await assetsGate.run((signal) => {
        requestSignal = signal;
        return getAssets(source, { signal });
      });
      if (requestSignal?.aborted) return;
      setAssets(result.assets);
      setErrors((current) => ({
        ...current,
        assets: result.errors.length ? result.errors.map((item) => `${item.symbol ?? 'ativo'}: ${item.error}`).join(' · ') : '',
      }));
    } catch (reason) {
      if (!requestSignal?.aborted && !isAborted(reason)) setErrors((current) => ({ ...current, assets: readError(reason) }));
    } finally {
      if (!requestSignal?.aborted) setAssetsLoading(false);
    }
  }, [assetsGate.run, source]);

  const refreshQuotes = useCallback(async () => {
    let requestSignal: AbortSignal | null = null;
    setQuotesLoading(true);
    setErrors((current) => ({ ...current, quotes: '' }));
    try {
      if (!quoteSymbols.length) {
        setQuotes({});
        setQuotesReceivedAt(Date.now());
        return;
      }
      const result = await quotesGate.run((signal) => {
        requestSignal = signal;
        return getQuotes(source, quoteSymbols, { signal });
      });
      if (requestSignal?.aborted) return;
      setQuotes(Object.fromEntries(result.quotes.map((quote) => [quote.symbol, quote])));
      setQuotesReceivedAt(Date.now());
      setNow(Date.now());
      setErrors((current) => ({
        ...current,
        quotes: result.errors.length ? result.errors.map((item) => `${item.symbol ?? 'ativo'}: ${item.error}`).join(' · ') : '',
      }));
    } catch (reason) {
      if (!requestSignal?.aborted && !isAborted(reason)) setErrors((current) => ({ ...current, quotes: readError(reason) }));
    } finally {
      if (!requestSignal?.aborted) setQuotesLoading(false);
    }
  }, [quoteSymbols, quotesGate.run, source]);

  const refreshSelected = useCallback(async () => {
    if (!selectedSymbol) {
      clearInstrument();
      return;
    }
    const requestKey = currentInstrumentKey;
    const identity = identityFor(source, selectedSymbol);
    let requestSignal: AbortSignal | null = null;
    setSelectedLoading(true);
    setErrors((current) => ({ ...current, stats24h: '', candles: '', depth: '', trades: '', status: '' }));
    try {
      const result = await selectedGate.run(async (signal) => {
        requestSignal = signal;
        const statsRequest: Promise<Settled<MarketStats24h | null>> = source.broker === 'mt5'
          ? Promise.resolve({ value: null, error: null })
          : settle(getStats24h(identity, { signal }).then((response) => response.stats));
        const candlesRequest = settle(getCandles(identity, timeframe, 300, { signal }).then((response) => response.candles));
        const depthRequest: Promise<Settled<typeof depth>> = source.broker === 'mt5'
          ? Promise.resolve({ value: null, error: null })
          : settle(getDepth(identity, 20, { signal }));
        const tradesRequest: Promise<Settled<typeof trades>> = source.broker === 'mt5'
          ? Promise.resolve({ value: null, error: null })
          : settle(getTrades(identity, 20, { signal }));
        const [statsResult, candlesResult, depthResult, tradesResult] = await Promise.all([
          statsRequest,
          candlesRequest,
          depthRequest,
          tradesRequest,
        ]);
        return { statsResult, candlesResult, depthResult, tradesResult };
      });
      if (requestSignal?.aborted) return;
      setStats(result.statsResult.value);
      setCandles(result.candlesResult.value ?? []);
      setDepth(result.depthResult.value);
      setTrades(result.tradesResult.value);
      setInstrumentKey(requestKey);
      if ([result.statsResult, result.candlesResult, result.depthResult, result.tradesResult].some((item) => item.value !== null)) {
        setSelectedReceivedAt(Date.now());
        setNow(Date.now());
      }
      setErrors((current) => ({
        ...current,
        stats24h: result.statsResult.error ?? '',
        candles: result.candlesResult.error ?? '',
        depth: result.depthResult.error ?? '',
        trades: result.tradesResult.error ?? '',
      }));
    } catch (reason) {
      if (!requestSignal?.aborted && !isAborted(reason)) setErrors((current) => ({ ...current, candles: readError(reason) }));
    } finally {
      if (!requestSignal?.aborted) setSelectedLoading(false);
    }
  }, [clearInstrument, currentInstrumentKey, selectedGate.run, selectedSymbol, source, timeframe]);

  useEffect(() => {
    void refreshCapabilities();
    return () => capabilitiesGate.cancel();
  }, [capabilitiesGate.cancel, refreshCapabilities]);

  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    const poll = async () => {
      if (document.visibilityState === 'visible') await refreshOverview();
      if (active && marketAutoRefresh) timer = window.setTimeout(() => { void poll(); }, OVERVIEW_REFRESH_MS);
    };
    void poll();
    return () => {
      active = false;
      if (timer !== undefined) window.clearTimeout(timer);
      overviewGate.cancel();
    };
  }, [marketAutoRefresh, overviewGate.cancel, refreshOverview]);

  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    const poll = async () => {
      if (document.visibilityState === 'visible') await refreshAssets();
      if (active && marketAutoRefresh) timer = window.setTimeout(() => { void poll(); }, ASSETS_REFRESH_MS);
    };
    void poll();
    return () => {
      active = false;
      if (timer !== undefined) window.clearTimeout(timer);
      assetsGate.cancel();
    };
  }, [assetsGate.cancel, marketAutoRefresh, refreshAssets]);

  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    const poll = async () => {
      if (document.visibilityState === 'visible') await refreshQuotes();
      if (active && marketAutoRefresh) timer = window.setTimeout(() => { void poll(); }, refreshMs);
    };
    void poll();
    return () => {
      active = false;
      if (timer !== undefined) window.clearTimeout(timer);
      quotesGate.cancel();
    };
  }, [marketAutoRefresh, quotesGate.cancel, refreshQuotes, refreshMs]);

  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    const poll = async () => {
      if (document.visibilityState === 'visible') await refreshSelected();
      if (active && marketAutoRefresh) timer = window.setTimeout(() => { void poll(); }, SELECTED_REFRESH_MS);
    };
    void poll();
    return () => {
      active = false;
      if (timer !== undefined) window.clearTimeout(timer);
      selectedGate.cancel();
    };
  }, [marketAutoRefresh, refreshSelected, selectedGate.cancel]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 5_000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    writeStorage(`xau-market-watchlist:${sourceKey(source)}`, JSON.stringify(watchlist));
    setMarketWatchlist(watchlist);
    setSubscribeSymbols(watchlist);
  }, [setMarketWatchlist, setSubscribeSymbols, source, watchlist]);

  useEffect(() => {
    if (selectedSymbol) {
      writeStorage(`xau-market-selected:${sourceKey(source)}`, selectedSymbol);
      setStoreSelectedSymbol(selectedSymbol);
    } else {
      removeStorage(`xau-market-selected:${sourceKey(source)}`);
      setStoreSelectedSymbol('');
    }
  }, [selectedSymbol, setStoreSelectedSymbol, source]);

  useEffect(() => {
    if (watchlist.length && !watchlist.includes(selectedSymbol)) setSelectedSymbol(watchlist[0]);
    if (!watchlist.length && selectedSymbol) setSelectedSymbol('');
  }, [selectedSymbol, watchlist]);

  useEffect(() => {
    document.getElementById('market-title')?.focus();
  }, []);

  const changeSource = (next: MarketSource) => {
    if (next.broker === source.broker && next.market === source.market) return;
    const nextWatchlist = readWatchlist(next);
    setSource(next);
    setWatchlist(nextWatchlist);
    setSelectedSymbol(readSelectedSymbol(next, nextWatchlist));
    setSearch('');
    setAssets([]);
    setQuotes({});
    setOverview(null);
    setErrors({});
    setOverviewReceivedAt(null);
    setQuotesReceivedAt(null);
    clearInstrument();
    writeStorage('xau-market-source', sourceKey(next));
  };

  const changeBroker = (broker: string) => {
    const option = marketSources.find((item) => item.broker === broker);
    if (!option?.enabled || !option.markets.length) return;
    const nextMarket = option.markets.includes(source.market) ? source.market : option.markets[0];
    changeSource({ broker: option.broker, market: nextMarket });
  };

  const addSymbol = () => {
    const next = normalizeSymbols([search]);
    if (!next.length) return;
    const nextWatchlist = normalizeSymbols([...watchlist, next[0]]);
    setWatchlist(nextWatchlist);
    setSelectedSymbol(next[0]);
    setSearch('');
  };

  const removeSymbol = (symbol: string) => {
    const nextWatchlist = watchlist.filter((item) => item !== symbol);
    setWatchlist(nextWatchlist);
    if (selectedSymbol === symbol) {
      setSelectedSymbol(nextWatchlist[0] ?? '');
      if (!nextWatchlist.length) clearInstrument();
    }
  };

  const refreshAll = () => {
    void refreshCapabilities();
    void refreshOverview();
    void refreshAssets();
    void refreshQuotes();
    void refreshSelected();
  };

  const rsiValue = useMemo(() => rsi(visibleCandles as never), [visibleCandles]);
  const macdValue = useMemo(() => macd(visibleCandles as never), [visibleCandles]);
  const atrValue = useMemo(() => atr(visibleCandles as never), [visibleCandles]);
  const publicStatus = marketLoading && !hasMarketData ? 'Consultando' : hasMarketData ? marketStale ? 'Dados vencidos' : 'Dados reais' : errors.assets || errors.quotes ? 'Indisponível' : 'Aguardando';
  const sourceLabelText = sourceLabel(source, marketSources);
  const statusTone = publicStatus === 'Dados reais' ? 'ok' : publicStatus === 'Indisponível' ? 'danger' : 'warn';
  const chartValues = useMemo(() => visibleCandles.map((candle) => ({ time: candle.time, price: candle.close })), [visibleCandles]);

  return <section className="market-page" aria-labelledby="market-title" aria-busy={capabilitiesLoading || marketLoading || selectedLoading || overviewLoading}>
    <div className="page-head market-page-head"><div><span className="eyebrow">LEITURA UNIVERSAL</span><h1 id="market-title" tabIndex={-1}>Mercado</h1><span className="muted">Preços, histórico e livro público em tempo real. A ordem sai em Robô → Mesa.</span></div><div className="btn-row"><span className={`chip ${statusTone}`} role="status">{publicStatus} · {sourceLabelText}</span><button className="btn" type="button" onClick={() => setSettings({ marketAutoRefresh: !marketAutoRefresh })}>{marketAutoRefresh ? 'Pausar atualização' : 'Retomar atualização'}</button><button className="btn primary" type="button" onClick={refreshAll} disabled={capabilitiesLoading || marketLoading || selectedLoading || overviewLoading}>{capabilitiesLoading || marketLoading || selectedLoading || overviewLoading ? 'Atualizando…' : 'Atualizar agora'}</button></div></div>
    <div className="market-security-banner" role="status"><strong>Esta aba é leitura</strong><span>Dados de mercado são independentes do status da conta. A ordem sai em Robô → Mesa, nas corretoras MT5, MEXC, Binance, Bybit e OKX.</span></div>
    <section className="card market-source-panel" aria-labelledby="market-source-title"><div className="section-head"><div><h2 id="market-source-title">Fonte e mercado</h2><span className="muted">A identidade da leitura é corretora + mercado + ativo.</span></div><span className="chip primary">Público</span></div><div className="market-source-controls"><label className="field"><span>Fonte</span><select aria-label="Selecionar fonte do mercado" value={source.broker} onChange={(event) => changeBroker(event.target.value)}>{marketSources.map((item) => <option key={item.broker} value={item.broker} disabled={!item.enabled}>{item.label}{item.enabled ? '' : ' · homologação, desativado'}</option>)}</select></label><label className="field"><span>Mercado</span><select aria-label="Selecionar mercado" value={source.market} onChange={(event) => changeSource({ ...source, market: event.target.value as MarketKind })}>{marketSources.find((item) => item.broker === source.broker)?.markets.map((market) => <option key={market} value={market}>{marketLabel(market)}</option>)}</select></label><label className="field market-search-field"><span>Buscar ativo</span><input aria-label="Buscar ativo" value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') addSymbol(); }} placeholder="Ex.: BTCUSDT" /></label><button className="btn sm" type="button" onClick={addSymbol}>Adicionar ativo</button></div><div className="market-source-meta"><span>Status público: <strong>{publicStatus}</strong></span><span>Recebido: <strong>{formatTime(overview?.received_at)}</strong></span><span>Fonte: <strong>{overview?.source ?? '—'}</strong></span></div></section>
    {errorSummary && <p className="market-partial-note" role="status">{errorSummary}</p>}
    {!marketLoading && !hasMarketData && <div className="market-offline-state" role="status"><strong>Gateway indisponível</strong><span>Não há dados de mercado para exibir. Nenhum valor simulado foi usado.</span></div>}
    <section className="card market-quotes-panel" aria-labelledby="market-quotes-title" aria-busy={quotesLoading}><div className="section-head"><div><h2 id="market-quotes-title">Cotações</h2><span className="muted">{marketStale ? 'Dados vencidos; aguardando nova leitura.' : `Atualização automática a cada ${Math.round(refreshMs / 1000)}s`}</span></div><span className={`chip ${marketStale ? 'warn' : hasMarketData ? 'ok' : 'warn'}`}>{marketStale ? 'Vencida' : hasMarketData ? 'Atualizada' : 'Aguardando'}</span></div>{quotesLoading && !hasMarketData ? <div className="market-state" role="status">Carregando cotações reais…</div> : filteredSymbols.length ? <div className="table-scroll market-focus-scroll" role="region" aria-label="Tabela de cotações reais" tabIndex={0}><table className="tbl market-quotes-table"><caption className="sr-only">Cotações reais por ativo e fonte</caption><thead><tr><th scope="col">Ativo</th><th scope="col" className="num">Último</th><th scope="col" className="num">Compra</th><th scope="col" className="num">Venda</th><th scope="col" className="num">Spread</th><th scope="col">Leitura</th><th scope="col"></th></tr></thead><tbody>{filteredSymbols.map((symbol) => { const quote = quotes[symbol] ?? null; const quoteStale = quote ? isMarketStale(receivedTimestamp(quote.received_at), now) : false; const quoteHasValues = Boolean(quote && (quote.last !== null || quote.bid !== null || quote.ask !== null)); const dica = quote ? `${quote.source ?? ''}${quote.provider_timestamp ? ' · ' + formatTime(quote.provider_timestamp) : ''}${quote.received_at ? ' · recebido ' + formatTime(quote.received_at) : ''}` : 'sem retorno'; return <tr key={symbol} className={selectedSymbol === symbol ? 'selected' : ''} title={dica}><th scope="row"><button type="button" className="market-table-symbol" aria-pressed={selectedSymbol === symbol} onClick={() => setSelectedSymbol(symbol)}>{symbol}</button></th><td className="num">{formatNumber(quote?.last)}</td><td className="num">{formatNumber(quote?.bid)}</td><td className="num">{formatNumber(quote?.ask)}</td><td className="num">{formatNumber(quote?.spread)}</td><td><span className={`chip ${quoteHasValues && !quoteStale ? 'ok' : 'warn'}`}>{quoteHasValues ? (quoteStale ? 'vencida' : 'real') : 'sem retorno'}</span></td><td><button type="button" className="market-remove-symbol" aria-label={`Remover ${symbol} da lista`} onClick={() => removeSymbol(symbol)}>x</button></td></tr>; })}</tbody></table></div> : <div className="market-state" role="status">{search ? 'Nenhum ativo corresponde à busca.' : 'Nenhum ativo disponível nesta fonte.'}</div>}</section>
    <section className="card market-instrument-panel" aria-labelledby="market-instrument-title" aria-busy={selectedLoading}><div className="section-head"><div><h2 id="market-instrument-title">{selectedSymbol || 'Ativo'}</h2><span className="muted">Mesma fonte: {sourceLabelText} · campos ausentes permanecem indisponíveis</span></div><span className={`chip ${selectedStale ? 'warn' : 'primary'}`}>{selectedStale ? 'Leitura vencida' : 'Leitura do mercado'}</span></div>{selectedLoading && !hasInstrumentData ? <div className="market-state" role="status">Carregando detalhes reais…</div> : <KpiGrid stats={visibleStats} quote={selectedQuote} />}</section>
    <div className="market-charts-grid"><MiniPriceChart quote={selectedQuote} values={chartValues} symbol={selectedSymbol || '—'} sourceLabel={sourceLabelText} /><PriceChart symbol={selectedSymbol} broker={source.broker} market={source.market} candles={visibleCandles} timeframe={timeframe} onTimeframeChange={setTimeframe} loading={selectedLoading} error={errors.candles ?? ''} sourceLabel={sourceLabelText} /></div>
    <div className="market-indicator-strip" role="group" aria-label="Indicadores"><div className="market-indicator-grid"><div><span>RSI</span><strong>{rsiValue === null ? 'Indisponível' : formatNumber(rsiValue, 2)}</strong></div><div><span>MACD</span><strong>{macdValue === null ? 'Indisponível' : formatNumber(macdValue.macd, 4)}</strong></div><div><span>ATR</span><strong>{atrValue === null ? 'Indisponível' : formatNumber(atrValue, 4)}</strong></div><div><span>Candles</span><strong>{visibleCandles.length || '—'}</strong></div></div></div>
    <div className="market-secondary-grid"><section className="card market-depth-panel" aria-labelledby="market-depth-title"><div className="section-head"><div><h2 id="market-depth-title">Livro de ofertas</h2><span className="muted">{selectedSymbol || '—'} · {visibleDepth?.source ?? sourceLabelText}</span></div><span className="chip">{visibleDepth ? 'leitura' : 'indisponível'}</span></div>{selectedLoading && !visibleDepth ? <div className="market-state" role="status">Carregando livro de ofertas…</div> : source.broker === 'mt5' ? <div className="market-state" role="status">O adaptador MT5 não expõe DOM público.</div> : visibleDepth && (visibleDepth.bids.length || visibleDepth.asks.length) ? <div className="market-depth-grid"><DepthTable title="Compras" levels={visibleDepth.bids} /><DepthTable title="Vendas" levels={visibleDepth.asks} /></div> : <div className="market-state" role="status">Livro de ofertas real indisponível para esta fonte.</div>}</section><section className="card market-trades-panel" aria-labelledby="market-trades-title"><div className="section-head"><div><h2 id="market-trades-title">Negócios públicos</h2><span className="muted">{selectedSymbol || '—'} · {visibleTrades?.source ?? sourceLabelText}</span></div><span className="chip">{visibleTrades ? 'leitura' : 'indisponível'}</span></div>{selectedLoading && !visibleTrades ? <div className="market-state" role="status">Carregando negócios…</div> : source.broker === 'mt5' ? <div className="market-state" role="status">O adaptador MT5 não expõe tape público.</div> : visibleTrades?.trades.length ? <div className="table-scroll market-focus-scroll" role="region" aria-label="Negócios públicos normalizados" tabIndex={0}><table className="tbl market-trades-table"><caption className="sr-only">Negócios públicos normalizados</caption><thead><tr><th scope="col">Hora</th><th scope="col">Lado</th><th scope="col">Preço</th><th scope="col">Quantidade</th><th scope="col">Fonte</th></tr></thead><tbody>{visibleTrades.trades.slice(0, 12).map((trade, index) => <tr key={`${trade.id ?? 'trade'}-${index}`}><td>{formatTime(trade.provider_timestamp)}</td><td>{trade.side ?? '—'}</td><td>{formatNumber(trade.price, 6)}</td><td>{formatNumber(trade.quantity, 6)}</td><td>{trade.source}</td></tr>)}</tbody></table></div> : <div className="market-state" role="status">Negócios públicos reais indisponíveis para esta fonte.</div>}</section></div>
  </section>;
}

function DepthTable({ title, levels }: { title: string; levels: Array<{ price: number | null; quantity: number | null }> }) {
  return <div className="market-depth-table"><h3>{title}</h3><div className="table-scroll market-focus-scroll" role="region" aria-label={`Níveis de ${title}`} tabIndex={0}><table className="tbl"><caption className="sr-only">Níveis de {title} do livro público</caption><thead><tr><th scope="col">Preço</th><th scope="col">Quantidade</th></tr></thead><tbody>{levels.slice(0, 8).map((level, index) => <tr key={`${title}-${index}`}><td>{formatNumber(level.price, 8)}</td><td>{formatNumber(level.quantity, 8)}</td></tr>)}</tbody></table></div></div>;
}

