import { useEffect, useMemo, useRef, useState } from 'react';
import { useAppStore } from '../hooks/useAppStore';
import { buildAssetRows, compatibleMarket, displayQuoteValue, marketsByBroker } from '../lib/robotAssets';

const API = 'http://127.0.0.1:9001';
const assetsBySource: Record<string, Record<string, string[]>> = {
  mt5: { forex: ['AUDCAD', 'EURUSD', 'GBPUSD', 'USDJPY'], metals: ['XAUUSD', 'XAGUSD'], indices: ['US30', 'US500', 'HK50'], 'crypto-spot': [], 'crypto-futures': [] },
  mexc: { 'crypto-spot': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'BNBUSDT', 'DOGEUSDT', 'ADAUSDT', 'TRXUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT', 'MATICUSDT', 'LTCUSDT', 'BCHUSDT', 'ETCUSDT'], 'crypto-futures': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'TRXUSDT', 'AVAXUSDT', 'LINKUSDT', 'LTCUSDT'], forex: [], metals: [], indices: [] },
  binance: { 'crypto-spot': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'TRXUSDT', 'AVAXUSDT', 'LINKUSDT'], 'crypto-futures': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'TRXUSDT', 'AVAXUSDT', 'LINKUSDT'], forex: [], metals: [], indices: [] },
};
const classify = (symbol: string) => {
  if (/^(XAU|XAG|XPT|XPD)/i.test(symbol)) return 'metals';
  if (/^(US30|US500|US2000|USTEC|USTECH|UK100|DE40|FRA40|GER40|HK50|JPN225|AUS200|CA60|CHINA50|CHINAH|ESP35|EUSTX50|IT40|NETH25|NOR25|SA40|SE30|SWI20|TECHDE30)/i.test(symbol)) return 'indices';
  return 'forex';
};

export default function RobotAssetTableFixed() {
  const quotes = useAppStore((s) => s.quotes);
  const selected = useAppStore((s) => s.selectedSymbol);
  const setSelected = useAppStore((s) => s.setSelectedSymbol);
  const addQuote = useAppStore((s) => s.addQuote);
  const [broker, setBroker] = useState('mt5');
  const [market, setMarket] = useState('forex');
  const [assets, setAssets] = useState(assetsBySource.mt5.forex);
  const [auto, setAuto] = useState(false);
  const [quoteBusy, setQuoteBusy] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);
  const [onlyWithQuote, setOnlyWithQuote] = useState(true);
  const quoteBusyRef = useRef(false);
  useEffect(() => {
    let active = true;
    const base = assetsBySource[broker]?.[market] ?? [];
    if (broker !== 'mt5') { setAssets(base); return () => { active = false; }; }
    fetch(`${API}/api/assets`, { signal: AbortSignal.timeout(5000) }).then((r) => r.json()).then((data: { symbols?: Array<{ symbol?: string } | string> }) => {
      const symbols = (data.symbols ?? []).map((x) => typeof x === 'string' ? x : (x.symbol ?? '')).filter(Boolean);
      if (active) setAssets([...new Set([...base, ...symbols.filter((symbol) => classify(symbol) === market)])]);
    }).catch(() => { if (active) setAssets(base); });
    return () => { active = false; };
  }, [broker, market]);
  useEffect(() => {
    if (!assets.length) return;
    let active = true;
    const read = async () => {
      if (quoteBusyRef.current) return;
      quoteBusyRef.current = true; setQuoteBusy(true);
      try {
        if (broker === 'mt5') {
          // Cotação em lote: um único endpoint para toda a lista (estilo Market Watch do MT5).
          const symbols = assets.slice(0, 24);
          const r = await fetch(`${API}/api/mt5/quotes?symbols=${encodeURIComponent(symbols.join(','))}`, { signal: AbortSignal.timeout(8000) });
          const data = await r.json() as { quotes?: Array<Record<string, unknown>> };
          for (const raw of data.quotes ?? []) {
            if (!active) break;
            const bid = Number(raw.bid ?? 0); const ask = Number(raw.ask ?? 0);
            if (!(bid > 0) && !(ask > 0)) continue; // sem informação real não entra
            const mid = (bid + ask) / 2;
            addQuote({ symbol: String(raw.symbol), bid, ask, last: Number(raw.last ?? mid), price: Number(raw.last ?? mid), volume: Number(raw.volume ?? 0), high: Number(raw.high ?? 0), low: Number(raw.low ?? 0), change: Number(raw.change_pct ?? 0), change_pct: Number(raw.change_pct ?? 0), spread: Number(raw.spread ?? (ask - bid || 0)), digits: Number(raw.digits ?? 5), point: Number(raw.point ?? 0.00001), timestamp: String(raw.timestamp ?? new Date().toISOString()), source: String(raw.source ?? 'mt5_gateway') });
          }
          return;
        }
        await Promise.all(assets.map(async (symbol) => {
          try { const r = await fetch(`${API}/api/universal/quote?broker=${broker}&market=${market}&symbol=${symbol}`); const q = await r.json(); if (active && r.ok && q.bid !== undefined) addQuote({ ...q, last: q.last ?? q.price, price: q.price ?? q.last, volume: 0, high: 0, low: 0, change: 0, change_pct: 0, digits: 8, point: 0.00000001, timestamp: q.timestamp ?? new Date().toISOString() }); } catch { /* fonte indisponível */ }
        }));
      } finally {
        quoteBusyRef.current = false; setQuoteBusy(false);
      }
    };
    void read();
    const timer = window.setInterval(read, 10000);
    return () => { active = false; window.clearInterval(timer); };
  }, [broker, market, assets, addQuote, refreshTick]);
  const rows = useMemo(() => {
    const base = buildAssetRows(assets, quotes);
    // Ativos sem informação de cotação não poluem a tela (padrão Market Watch).
    return onlyWithQuote ? base.filter(({ quote }) => quote && (Number(quote.bid) > 0 || Number(quote.ask) > 0)) : base;
  }, [assets, quotes, onlyWithQuote]);
  const changeBroker = (nextBroker: string) => {
    const nextMarket = compatibleMarket(nextBroker, market);
    setBroker(nextBroker);
    setMarket(nextMarket);
    setAssets(assetsBySource[nextBroker]?.[nextMarket] ?? []);
    setSelected('');
  };
  const changeMarket = (nextMarket: string) => {
    setMarket(nextMarket);
    setAssets(assetsBySource[broker]?.[nextMarket] ?? []);
    setSelected('');
  };
  return <div className="robot-operations">
    <div className="page-head"><div><h1>Robô</h1><span className="muted">Selecione origem, mercado e ativo para montar uma operação</span></div><div className="btn-row"><select value={broker} onChange={(e) => changeBroker(e.target.value)} aria-label="Origem"><option value="mt5">MT5</option><option value="mexc">MEXC</option><option value="binance">Binance</option></select><select value={market} onChange={(e) => changeMarket(e.target.value)} aria-label="Mercado">{marketsByBroker[broker].map((value) => <option key={value} value={value}>{{ 'crypto-spot': 'Spot', 'crypto-futures': 'Futuros', forex: 'Forex', metals: 'Metais', indices: 'Índices' }[value]}</option>)}</select></div></div>
    <div className="card compact-card"><div className="section-head"><div><h2>Ativos da origem selecionada</h2><span className="muted">{broker.toUpperCase()} · {market} · {assets.length} ativos compatíveis</span></div><div className="btn-row"><label className="chip" style={{ cursor: 'pointer' }}><input type="checkbox" checked={onlyWithQuote} onChange={(e) => setOnlyWithQuote(e.target.checked)} /> só com cotação</label><button type="button" className="btn sm primary" onClick={() => setRefreshTick((t) => t + 1)} disabled={quoteBusy}>{quoteBusy ? 'Atualizando…' : 'Atualizar agora'}</button></div></div><div className="table-scroll"><table className="tbl compact-table"><thead><tr><th>Usar</th><th>Ativo</th><th>Origem</th><th>Mercado</th><th>Preço</th><th>Bid</th><th>Ask</th><th>Spread</th></tr></thead><tbody>{rows.map(({ symbol, quote }) => <tr key={symbol} className={selected === symbol ? 'asset-row-selected' : ''}><td><input type="radio" name="robot-asset" checked={selected === symbol} onChange={() => setSelected(symbol)} aria-label={`Selecionar ${symbol}`} /></td><td><strong>◈ {symbol}</strong></td><td>{broker.toUpperCase()}</td><td>{classify(symbol) === 'metals' ? 'Metais' : classify(symbol) === 'indices' ? 'Índices' : broker === 'mt5' ? 'Forex' : market === 'crypto-futures' ? 'Futuros' : 'Spot'}</td><td className="num">{displayQuoteValue(quote?.price)}</td><td className="num">{displayQuoteValue(quote?.bid)}</td><td className="num">{displayQuoteValue(quote?.ask)}</td><td className="num">{displayQuoteValue(quote?.spread)}</td></tr>)}</tbody></table></div>{assets.length === 0 && <div className="empty-state">Nenhum ativo compatível disponível.</div>}</div>
    <div className="card compact-card"><div className="section-head"><div><h2>Ticket operacional</h2><span className="muted">{selected || 'Selecione um ativo'} · confirmação manual</span></div><span className="chip warn">Protegido</span></div><div className="btn-row"><button type="button" className={`btn sm ${auto ? 'primary' : 'ghost'}`} onClick={() => setAuto((v) => !v)}>Robô automático: {auto ? 'ON' : 'OFF'}</button><span className="chip">{broker.toUpperCase()} · {market}</span></div></div>
  </div>;
}
