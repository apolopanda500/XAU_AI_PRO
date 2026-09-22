import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiBase } from '../../lib/api';
import { useAppStore, type Quote } from '../../hooks/useAppStore';
import MiniPriceChart from '../charts/MiniPriceChart';
import PriceChart from '../charts/PriceChart';
import { assetIcon } from '../../lib/assetIcons';

const API = apiBase();
const STALE_AFTER_MS = 15_000;
const REQUEST_TIMEOUT_MS = 8_000;

type RequestedSource = { broker: string; market: string; label: string } | null;
type Connection = { broker?: string; market?: string; active?: boolean; status?: string; error?: string | null };
type Overview = { ok?: boolean; connections?: Connection[]; error?: string };
type QuoteResponse = { ok?: boolean; quotes?: Array<Record<string, unknown>>; errors?: Array<{ symbol?: string; error?: string }>; error?: string };

export function isQuoteStale(lastSync: number | null, now = Date.now()): boolean {
  return lastSync !== null && now - lastSync > STALE_AFTER_MS;
}

async function fetchWithTimeout(input: RequestInfo | URL, timeoutMs = REQUEST_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { signal: controller.signal });
  } finally {
    window.clearTimeout(timer);
  }
}

function readRequestedSource(): RequestedSource {
  try {
    const [rawBroker, rawMarket] = (window.localStorage.getItem('xau-active-account') ?? '').split(':');
    const broker = rawBroker?.trim().toLowerCase() ?? '';
    const market = rawMarket?.trim().toLowerCase() ?? '';
    if (broker && market && broker !== 'all' && market !== 'all') return { broker, market, label: `${broker.toUpperCase()} · ${market}` };
  } catch {
    // Storage pode estar indisponível em modo privado.
  }
  return null;
}

function sameSource(quote: Quote, source: RequestedSource): boolean {
  return Boolean(source && quote.broker?.toLowerCase() === source.broker && quote.market?.toLowerCase() === source.market);
}

function normalizeQuote(raw: Record<string, unknown>, source: NonNullable<RequestedSource>): Quote | null {
  const symbol = String(raw.symbol ?? '').trim().toUpperCase();
  if (!symbol) return null;
  const number = (value: unknown): number => Number.isFinite(Number(value)) ? Number(value) : 0;
  const now = new Date().toISOString();
  return {
    broker: String(raw.broker ?? source.broker).toLowerCase(), market: String(raw.market ?? source.market).toLowerCase(), symbol,
    price: number(raw.price ?? raw.last), bid: number(raw.bid), ask: number(raw.ask), last: number(raw.last ?? raw.price),
    volume: number(raw.volume), high: number(raw.high), low: number(raw.low), change: number(raw.change), change_pct: number(raw.change_pct),
    spread: number(raw.spread), digits: Math.max(0, number(raw.digits) || 2), point: number(raw.point),
    timestamp: String(raw.timestamp ?? now), received_at: String(raw.received_at ?? now), source: String(raw.source ?? `${source.broker}_gateway`),
  };
}

export default function MarketTab() {
  const quotes = useAppStore((state) => state.quotes);
  const selectedSymbol = useAppStore((state) => state.selectedSymbol);
  const setSelectedSymbol = useAppStore((state) => state.setSelectedSymbol);
  const watchlist = useAppStore((state) => state.marketWatchlist);
  const setWatchlist = useAppStore((state) => state.setMarketWatchlist);
  const setSubscribeSymbols = useAppStore((state) => state.setSubscribeSymbols);
  const addQuote = useAppStore((state) => state.addQuote);
  const marketAutoRefresh = useAppStore((state) => state.settings.marketAutoRefresh);
  const marketRefreshMs = useAppStore((state) => state.settings.marketRefreshMs);
  const [source, setSource] = useState<RequestedSource>(() => readRequestedSource());
  const [connection, setConnection] = useState<Connection | null>(null);
  const [filter, setFilter] = useState('');
  const [symbolInput, setSymbolInput] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [sourceErrors, setSourceErrors] = useState<Array<{ symbol?: string; error?: string }>>([]);
  const [lastSync, setLastSync] = useState<number | null>(null);
  const [clock, setClock] = useState(Date.now());
  const requestInFlight = useRef(false);

  const visibleQuotes = useMemo(() => quotes.filter((quote) => sameSource(quote, source)).filter((quote) => quote.symbol.toLowerCase().includes(filter.trim().toLowerCase())), [filter, quotes, source]);
  const selected = visibleQuotes.find((quote) => quote.symbol === selectedSymbol) ?? visibleQuotes[0];
  const sourceConnected = connection?.active === true && connection?.status === 'conectada';
  const isStale = isQuoteStale(lastSync, clock);

  const refresh = useCallback(async () => {
    if (requestInFlight.current) return;
    const requested = readRequestedSource();
    setSource(requested); setConnection(null); setSourceErrors([]);
    if (!requested) { setError('Selecione uma corretora ativa para receber cotações reais.'); setLastSync(null); return; }
    requestInFlight.current = true; setRefreshing(true); setError('');
    try {
      const overviewResponse = await fetchWithTimeout(`${API}/api/universal/overview`);
      const overview = await overviewResponse.json() as Overview;
      if (!overviewResponse.ok || overview.ok === false) throw new Error(overview.error || `Gateway HTTP ${overviewResponse.status}`);
      const activeConnection = (overview.connections ?? []).find((item) => item.broker?.toLowerCase() === requested.broker && item.market?.toLowerCase() === requested.market) ?? null;
      setConnection(activeConnection);
      if (!activeConnection || activeConnection.active !== true || activeConnection.status !== 'conectada') { setLastSync(null); setError(activeConnection?.error || `A fonte ${requested.label} não está conectada.`); return; }
      const symbols = Array.from(new Set([selectedSymbol, ...watchlist].map((item) => item.trim().toUpperCase()).filter(Boolean))).slice(0, 24);
      setSubscribeSymbols(symbols);
      if (!symbols.length) { setLastSync(null); setError('Adicione ao menos um símbolo à watchlist.'); return; }
      const params = new URLSearchParams({ broker: requested.broker, market: requested.market, symbols: symbols.join(',') });
      const quoteResponse = await fetchWithTimeout(`${API}/api/universal/quotes?${params.toString()}`);
      const payload = await quoteResponse.json() as QuoteResponse;
      if (!quoteResponse.ok || payload.ok === false) throw new Error(payload.error || `Fonte HTTP ${quoteResponse.status}`);
      (payload.quotes ?? []).map((item) => normalizeQuote(item, requested)).filter((item): item is Quote => Boolean(item)).forEach(addQuote);
      setSourceErrors(payload.errors ?? []); setLastSync(Date.now());
    } catch (reason) {
      setLastSync(null); setError(reason instanceof Error ? reason.message : 'Não foi possível consultar a fonte de mercado.');
    } finally {
      requestInFlight.current = false; setRefreshing(false);
    }
  }, [addQuote, selectedSymbol, setSubscribeSymbols, watchlist]);

  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => { const timer = window.setInterval(() => setClock(Date.now()), 1_000); return () => window.clearInterval(timer); }, []);
  useEffect(() => {
    if (!marketAutoRefresh || !sourceConnected) return undefined;
    const timer = window.setInterval(() => void refresh(), Math.max(5_000, marketRefreshMs));
    return () => window.clearInterval(timer);
  }, [marketAutoRefresh, marketRefreshMs, refresh, sourceConnected]);

  const addSymbol = () => { const next = symbolInput.trim().toUpperCase(); if (!next) return; setWatchlist([...watchlist, next]); setSymbolInput(''); };
  const removeSymbol = (symbol: string) => setWatchlist(watchlist.filter((item) => item !== symbol));
  const fmt = (value: number | undefined | null, digits = 2) => value == null ? '--' : value.toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits });

  return <div className="market-page">
    <div className="page-head"><div><h1>Mercado</h1><span className="muted">Cotações exclusivamente da corretora conectada e confirmada pelo gateway.</span></div><div className="btn-row"><span className={`chip ${sourceConnected && !isStale ? 'ok' : 'warn'}`}>{sourceConnected ? (isStale ? 'Cotação vencida' : `Conectada · ${source?.label}`) : 'Fonte não conectada'}</span><button className="btn primary" type="button" onClick={() => void refresh()} disabled={refreshing}>{refreshing ? 'Atualizando…' : 'Atualizar'}</button></div></div>
    <div className="card compact-card"><div className="section-head"><div><h2>Watchlist</h2><span className="muted">Lista local; não garante disponibilidade na fonte.</span></div><div className="btn-row"><input aria-label="Novo símbolo" value={symbolInput} onChange={(event) => setSymbolInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') addSymbol(); }} placeholder="Ex.: BTCUSDT" /><button className="btn sm" type="button" onClick={addSymbol}>Adicionar</button></div></div><div className="chip-row">{watchlist.map((symbol) => <span className="chip" key={symbol}>{assetIcon(symbol)} {symbol}<button type="button" aria-label={`Remover ${symbol}`} onClick={() => removeSymbol(symbol)}>×</button></span>)}</div></div>
    <div className="card compact-card"><div className="section-head"><div><h2>Cotações</h2><span className="muted">Fonte selecionada: {source?.label ?? 'nenhuma'}</span></div><input aria-label="Filtrar símbolos" value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Filtrar símbolo" /></div>
      {!source ? <div className="placeholder" role="status">Selecione uma corretora em Contas ativas. Nenhuma cotação será solicitada ou exibida sem uma fonte ativa.</div> : !sourceConnected ? <div className="placeholder" role="status">{error || `A fonte ${source.label} precisa estar conectada antes de exibir preços reais.`}</div> : visibleQuotes.length === 0 ? <div className="placeholder" role="status">{error || 'A fonte conectada ainda não retornou cotações reais para a watchlist.'}</div> : <div className="tbl-wrap"><table className="tbl"><thead><tr><th>Símbolo</th><th>Preço</th><th>Bid</th><th>Ask</th><th>Spread</th><th>Fonte</th><th>Atualizado</th><th></th></tr></thead><tbody>{visibleQuotes.map((quote) => <tr key={`${quote.broker}:${quote.market}:${quote.symbol}`} className={selectedSymbol === quote.symbol ? 'selected' : ''}><td><strong>{quote.symbol}</strong></td><td className="mono">{fmt(quote.price, quote.digits)}</td><td className="mono">{fmt(quote.bid, quote.digits)}</td><td className="mono">{fmt(quote.ask, quote.digits)}</td><td className="mono">{fmt(quote.spread, quote.digits)}</td><td><span className="chip ok">{quote.source}</span></td><td className={`mono ${isStale ? 'neg' : ''}`}>{isStale ? 'VENCIDA' : new Date(quote.received_at ?? quote.timestamp).toLocaleTimeString('pt-BR')}</td><td><button className={`btn xs ${selectedSymbol === quote.symbol ? 'primary' : 'ghost'}`} type="button" onClick={() => setSelectedSymbol(quote.symbol)}>{selectedSymbol === quote.symbol ? 'Selecionado' : 'Detalhes'}</button></td></tr>)}</tbody></table></div>}
      {sourceErrors.length > 0 && <div className="hint" role="alert">Símbolos indisponíveis: {sourceErrors.map((item) => `${item.symbol ?? 'símbolo'} · ${item.error ?? 'erro da fonte'}`).join(' | ')}</div>}
    </div>
    {selected && sourceConnected && <div className="grid cols-2"><MiniPriceChart quote={selected} symbol={selected.symbol} /><PriceChart symbol={selected.symbol} /></div>}
    <div className="card compact-card"><h2>Estado da fonte</h2><div className="tbl-wrap"><table className="tbl"><tbody><tr><td>Conta selecionada</td><td>{source?.label ?? 'Nenhuma'}</td></tr><tr><td>Confirmação do gateway</td><td><span className={`chip ${sourceConnected ? 'ok' : 'warn'}`}>{sourceConnected ? 'Conectada' : connection?.status ?? 'Não confirmada'}</span></td></tr><tr><td>Última sincronização</td><td className={`mono ${isStale ? 'neg' : ''}`}>{lastSync ? (isStale ? `Vencida há ${Math.floor((clock - lastSync) / 1000)}s` : new Date(lastSync).toLocaleTimeString('pt-BR')) : '--'}</td></tr><tr><td>Erro da fonte</td><td>{error || connection?.error || 'Nenhum'}</td></tr></tbody></table></div></div>
  </div>;
}