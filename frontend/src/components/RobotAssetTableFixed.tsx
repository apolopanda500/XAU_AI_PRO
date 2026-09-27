import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';
import {
  BROKERS,
  MARKET_LABELS,
  MARKETS_BY_BROKER,
  brokerLabel,
  compatibleMarket,
  isTradable,
  normalizeSymbol,
  parseAssetCatalog,
  restrictionLabel,
  type AssetRow,
} from '../lib/brokerCatalog';
import { AssetIcon } from './AssetIcon';

type Quote = {
  symbol: string;
  bid: number;
  ask: number;
  last: number;
  price: number;
  volume: number;
  high: number;
  low: number;
  change: number;
  change_pct: number;
  spread: number;
  digits: number;
  point: number;
  timestamp: string;
  source: string;
};

type CatalogState = {
  rows: AssetRow[];
  source: string | null;
  error: string | null;
  loading: boolean;
};

const MAX_BATCH = 30;

function lerPreco(valor: unknown, padrao: number): number {
  const n = Number(valor);
  return Number.isFinite(n) ? n : padrao;
}

export default function RobotAssetTableFixed() {
  const addQuote = useAppStore((s) => s.addQuote);
  const quotes = useAppStore((s) => s.quotes);
  const selected = useAppStore((s) => s.selectedSymbol);
  const setSelected = useAppStore((s) => s.setSelectedSymbol);

  const [broker, setBroker] = useState('mt5');
  const [market, setMarket] = useState('forex');
  const [catalog, setCatalog] = useState<CatalogState>({ rows: [], source: null, error: null, loading: true });
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const [quoteBusy, setQuoteBusy] = useState(false);
  const [onlyTradable, setOnlyTradable] = useState(false);
  const [auto, setAuto] = useState(false);
  const [tick, setTick] = useState(0);
  const busyRef = useRef(false);

  // Catálogo real: vem da corretora, nunca de uma lista fixa no front.
  useEffect(() => {
    let alive = true;
    setCatalog((prev) => ({ ...prev, loading: true, error: null }));
    const url = `${apiBase()}/api/universal/assets?broker=${encodeURIComponent(broker)}&market=${encodeURIComponent(market)}`;
    fetch(url, { signal: AbortSignal.timeout(12000) })
      .then(async (r) => ({ ok: r.ok, status: r.status, body: await r.json().catch(() => ({})) }))
      .then(({ ok, status, body }) => {
        if (!alive) return;
        const data = body as { assets?: unknown; source?: string; error?: string };
        if (!ok) {
          setCatalog({ rows: [], source: null, error: data?.error || `HTTP ${status}`, loading: false });
          return;
        }
        setCatalog({ rows: parseAssetCatalog(body), source: data?.source ?? null, error: null, loading: false });
      })
      .catch((err: unknown) => {
        if (!alive) return;
        setCatalog({ rows: [], source: null, error: `Catálogo indisponível: ${String(err)}`, loading: false });
      });
    return () => {
      alive = false;
    };
  }, [broker, market]);

  const symbols = useMemo(() => {
    const base = catalog.rows.map((row) => row.symbol);
    return onlyTradable ? base.filter((s) => isTradable(catalog.rows.find((r) => r.symbol === s)!)) : base;
  }, [catalog.rows, onlyTradable]);

  const lerQuotes = useCallback(async () => {
    if (busyRef.current || !symbols.length) return;
    busyRef.current = true;
    setQuoteBusy(true);
    try {
      const alvo = symbols.slice(0, MAX_BATCH);
      const path = broker === 'mt5'
        ? `/api/mt5/quotes?symbols=${encodeURIComponent(alvo.join(','))}`
        : `/api/universal/quotes?broker=${encodeURIComponent(broker)}&market=${encodeURIComponent(market)}&symbols=${encodeURIComponent(alvo.join(','))}`;
      const r = await fetch(`${apiBase()}${path}`, { signal: AbortSignal.timeout(12000) });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        setQuoteError((body as { error?: string })?.error || `HTTP ${r.status}`);
        return;
      }
      const data = body as { quotes?: unknown[]; errors?: unknown[] };
      setQuoteError(Array.isArray(data.errors) && data.errors.length ? 'Alguns ativos não responderam.' : null);
      let recebidas = 0;
      for (const item of data.quotes ?? []) {
        if (!item || typeof item !== 'object') continue;
        const raw = item as Record<string, unknown>;
        const bid = Number(raw.bid);
        const ask = Number(raw.ask);
        // Sem bid/ask real não entra na tela: preço zero é dado inventado.
        if (!(bid > 0) && !(ask > 0)) continue;
        const mid = (bid + ask) / 2;
        const last = lerPreco(raw.last ?? raw.price, mid);
        recebidas += 1;
        addQuote({
          symbol: normalizeSymbol(String(raw.symbol ?? '')),
          bid: bid > 0 ? bid : mid,
          ask: ask > 0 ? ask : mid,
          last,
          price: last,
          volume: lerPreco(raw.volume, 0),
          high: lerPreco(raw.high, 0),
          low: lerPreco(raw.low, 0),
          change: lerPreco(raw.change, 0),
          change_pct: lerPreco(raw.change_pct, 0),
          spread: lerPreco(raw.spread, ask > 0 && bid > 0 ? ask - bid : 0),
          digits: lerPreco(raw.digits, 5),
          point: lerPreco(raw.point, 0.00001),
          timestamp: String(raw.timestamp ?? new Date().toISOString()),
          source: String(raw.source ?? `${broker}_api`),
        });
      }
      if (!recebidas) setQuoteError('A corretora não devolveu cotação para os ativos listados.');
    } catch (err) {
      setQuoteError(`Cotações indisponíveis: ${String(err)}`);
    } finally {
      busyRef.current = false;
      setQuoteBusy(false);
    }
  }, [addQuote, broker, market, symbols]);

  useEffect(() => {
    void lerQuotes();
    const timer = window.setInterval(() => void lerQuotes(), 15000);
    return () => window.clearInterval(timer);
    // `tick` e o disparo manual do botao "Atualizar agora".
  }, [lerQuotes, tick]);

  const porSimbolo = useMemo(() => {
    const map = new Map<string, Quote>();
    for (const q of quotes) map.set(normalizeSymbol(q.symbol), q);
    return map;
  }, [quotes]);

  const infoPorSimbolo = useMemo(() => {
    const map = new Map<string, AssetRow>();
    for (const row of catalog.rows) map.set(row.symbol, row);
    return map;
  }, [catalog.rows]);

  const trocarBroker = (next: string) => {
    setBroker(next);
    setMarket(compatibleMarket(next, market));
    setSelected('');
  };

  return (
    <div className="robot-operations">
      <div className="page-head">
        <div>
          <h1>Robô</h1>
          <span className="muted">Catálogo e cotações vindos da corretora selecionada</span>
        </div>
        <div className="btn-row">
          <select value={broker} onChange={(e) => trocarBroker(e.target.value)} aria-label="Origem">
            {BROKERS.map((item) => (
              <option key={item.id} value={item.id}>{item.label}</option>
            ))}
          </select>
          <select value={market} onChange={(e) => { setMarket(e.target.value); setSelected(''); }} aria-label="Mercado">
            {(MARKETS_BY_BROKER[broker] ?? []).map((value) => (
              <option key={value} value={value}>{MARKET_LABELS[value] ?? value}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="card compact-card">
        <div className="section-head">
          <div>
            <h2>Ativos da corretora</h2>
            <span className="muted">
              {brokerLabel(broker)} · {MARKET_LABELS[market] ?? market} · {symbols.length} ativos
              {catalog.source ? ` · fonte ${catalog.source}` : ''}
            </span>
          </div>
          <div className="btn-row">
            <label className="chip" style={{ cursor: 'pointer' }}>
              <input type="checkbox" checked={onlyTradable} onChange={(e) => setOnlyTradable(e.target.checked)} />
              apenas operáveis
            </label>
            <button type="button" className="btn sm primary" onClick={() => setTick((t) => t + 1)} disabled={quoteBusy}>
              {quoteBusy ? 'Atualizando…' : 'Atualizar agora'}
            </button>
          </div>
        </div>

        {catalog.error && <div className="hint warn" role="alert">{catalog.error}</div>}
        {quoteError && <div className="hint warn" role="status">{quoteError}</div>}
        {catalog.loading && <div className="hint">Carregando catálogo…</div>}

        <div className="table-scroll">
          <table className="tbl compact-table">
            <thead>
              <tr>
                <th>Usar</th><th>Ativo</th><th>Mercado</th><th className="num">Preço</th>
                <th>Bid</th><th>Ask</th><th>Spread</th><th>Fonte</th><th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {symbols.map((symbol) => {
                const quote = porSimbolo.get(symbol);
                const info = infoPorSimbolo.get(symbol);
                const tradable = info ? isTradable(info) : false;
                const preco = quote?.price;
                return (
                  <tr key={symbol} className={selected === symbol ? 'asset-row-selected' : ''}>
                    <td>
                      <input
                        type="radio"
                        name="robot-asset"
                        checked={selected === symbol}
                        disabled={!tradable}
                        onChange={() => setSelected(symbol)}
                        aria-label={`Selecionar ${symbol}`}
                      />
                    </td>
                    <td className="asset-cell">
                      <AssetIcon symbol={symbol} broker={broker} />
                      <strong>{symbol}</strong>
                    </td>
                    <td>{MARKET_LABELS[market] ?? market}</td>
                    <td className="num">{typeof preco === 'number' && Number.isFinite(preco) ? preco : '--'}</td>
                    <td className="num">{quote && Number.isFinite(quote.bid) ? quote.bid : '--'}</td>
                    <td className="num">{quote && Number.isFinite(quote.ask) ? quote.ask : '--'}</td>
                    <td className="num">{quote && Number.isFinite(quote.spread) ? quote.spread : '--'}</td>
                    <td className="muted">{quote?.source ?? 'sem cotação'}</td>
                    <td>
                      {tradable
                        ? <span className="chip ok">operável</span>
                        : <span className="chip warn" title={(info?.restrictions ?? []).map(restrictionLabel).join(', ')}>
                            {(info?.restrictions ?? []).map(restrictionLabel).join(', ') || info?.availability || 'indisponível'}
                          </span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {!catalog.loading && !symbols.length && (
          <div className="empty-state">
            A corretora não expôs ativos para {brokerLabel(broker)} em {MARKET_LABELS[market] ?? market}.
          </div>
        )}
        {symbols.length > MAX_BATCH && (
          <p className="hint">Exibindo e consultando os {MAX_BATCH} primeiros ativos do catálogo.</p>
        )}
      </div>

      <div className="card compact-card">
        <div className="section-head">
          <div>
            <h2>Ticket operacional</h2>
            <span className="muted">{selected || 'Selecione um ativo'} · confirmação manual</span>
          </div>
          <span className="chip warn">Protegido</span>
        </div>
        <div className="btn-row">
          <button type="button" className={`btn sm ${auto ? 'primary' : 'ghost'}`} onClick={() => setAuto((v) => !v)}>
            Robô automático: {auto ? 'ON' : 'OFF'}
          </button>
          <span className="chip">{brokerLabel(broker)} · {MARKET_LABELS[market] ?? market}</span>
        </div>
      </div>
    </div>
  );
}
