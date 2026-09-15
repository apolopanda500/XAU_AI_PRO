import { useEffect, useMemo, useState } from 'react';
import { useAppStore, Quote } from '../../hooks/useAppStore';

const MT5 = 'http://127.0.0.1:9001';
const WATCHLIST = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD'];

export default function MarketTab() {
  const quotes = useAppStore((s) => s.quotes);
  const selectedSymbol = useAppStore((s) => s.selectedSymbol);
  const setSelectedSymbol = useAppStore((s) => s.setSelectedSymbol);
  const addQuote = useAppStore((s) => s.addQuote);
  const wsConnected = useAppStore((s) => s.wsConnected);
  const account = useAppStore((s) => s.account);
  const positions = useAppStore((s) => s.positions);
  const [filter, setFilter] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const fmt = (v: number | undefined | null, d = 2) => v == null ? '--' : v.toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d });
  const visibleQuotes = useMemo(() => quotes.filter((q) => q.symbol.toLowerCase().includes(filter.toLowerCase())), [quotes, filter]);
  const selected = quotes.find((q) => q.symbol === selectedSymbol) ?? visibleQuotes[0];

  const realRefresh = async () => {
    setRefreshing(true); setError('');
    try {
      const response = await fetch(`${MT5}/api/mt5/quotes?symbols=${WATCHLIST.join(',')}`, { signal: AbortSignal.timeout(5000) });
      if (!response.ok) throw new Error(`MT5 HTTP ${response.status}`);
      const data = await response.json() as { quotes?: Array<Record<string, unknown>>; errors?: string[] };
      (data.quotes ?? []).forEach((raw) => {
        const bid = Number(raw.bid ?? 0); const ask = Number(raw.ask ?? 0);
        const q: Quote = { symbol: String(raw.symbol), bid, ask, last: Number(raw.last ?? 0), price: Number(raw.last ?? 0) || (bid + ask) / 2, volume: Number(raw.volume ?? 0), high: Number(raw.high ?? 0), low: Number(raw.low ?? 0), change: Number(raw.change_pct ?? 0), change_pct: Number(raw.change_pct ?? 0), spread: ask - bid, digits: 2, point: 0.01, timestamp: String(raw.timestamp ?? new Date().toISOString()), source: String(raw.source ?? 'mt5_gateway') };
        addQuote(q);
      });
      if ((data.errors ?? []).length && !(data.quotes ?? []).length) setError('Nenhum ativo da lista está disponível no MT5.');
    } catch (err) { setError(err instanceof Error ? err.message : 'Fonte MT5 indisponível'); }
    finally { setRefreshing(false); }
  };

  useEffect(() => { void realRefresh(); const timer = window.setInterval(() => void realRefresh(), 2000); return () => window.clearInterval(timer); }, []);

  return <div>
    <div className="page-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
      <div><h1>Mercado</h1><span className="muted">Cotações reais sincronizadas por MT5 + WebSocket Core</span></div>
      <div className="btn-row"><span className={`chip ${wsConnected ? 'ok' : 'danger'}`}>WS {wsConnected ? 'Online' : 'Offline'}</span><button className="btn primary" type="button" onClick={realRefresh} disabled={refreshing}>{refreshing ? 'Atualizando...' : 'Atualizar MT5'}</button></div>
    </div>

    <div className="card" style={{ marginBottom: 14 }}><div className="btn-row" style={{ justifyContent: 'space-between' }}><input aria-label="Buscar ativo" className="input" placeholder="Buscar símbolo..." value={filter} onChange={(e) => setFilter(e.target.value)} /><div className="btn-row">{WATCHLIST.map((symbol) => <button key={symbol} className={`btn xs ${selectedSymbol === symbol ? 'primary' : 'ghost'}`} type="button" onClick={() => setSelectedSymbol(symbol)}>{symbol}</button>)}</div></div></div>

    {error && <div className="placeholder" role="alert"><strong>Dados reais indisponíveis</strong><span className="muted">{error}. Dados simulados estão bloqueados.</span></div>}

    {selected && <div className="grid cols-4" style={{ marginBottom: 14 }}><div className="card"><div className="kpi-label">Ativo selecionado</div><div className="kpi-value">{selected.symbol}</div><div className="kpi-sub">Fonte: {selected.source}</div></div><div className="card"><div className="kpi-label">Preço médio</div><div className="kpi-value mono">{fmt(selected.price, selected.digits)}</div><div className="kpi-sub">Bid {fmt(selected.bid, selected.digits)} · Ask {fmt(selected.ask, selected.digits)}</div></div><div className="card"><div className="kpi-label">Spread</div><div className="kpi-value mono">{fmt(selected.spread, selected.digits)}</div><div className="kpi-sub">Atualização por MT5</div></div><div className="card"><div className="kpi-label">Variação</div><div className={`kpi-value ${selected.change_pct >= 0 ? 'pos' : 'neg'}`}>{selected.change_pct >= 0 ? '▲' : '▼'} {fmt(selected.change_pct, 2)}%</div><div className="kpi-sub">Máx {fmt(selected.high, selected.digits)} · Mín {fmt(selected.low, selected.digits)}</div></div></div>}

    {visibleQuotes.length === 0 ? <div className="placeholder"><span>Aguardando cotações reais.</span><span className="muted">Abra o MT5, mantenha o símbolo disponível e atualize.</span></div> : <div className="tbl-wrap"><table className="tbl"><thead><tr><th>Símbolo</th><th>Preço</th><th>Bid</th><th>Ask</th><th>Spread</th><th>Var %</th><th>Volume</th><th>Fonte</th><th>Atualizado</th><th></th></tr></thead><tbody>{visibleQuotes.map((q) => <tr key={q.symbol} className={selectedSymbol === q.symbol ? 'selected' : ''}><td><strong>{q.symbol}</strong></td><td className="mono">{fmt(q.price, q.digits)}</td><td className="mono">{fmt(q.bid, q.digits)}</td><td className="mono">{fmt(q.ask, q.digits)}</td><td className="mono">{fmt(q.spread, q.digits)}</td><td className={`mono ${q.change_pct >= 0 ? 'pos' : 'neg'}`}>{q.change_pct >= 0 ? '▲' : '▼'} {fmt(q.change_pct, 2)}%</td><td className="mono">{fmt(q.volume, 2)}</td><td><span className="chip ok">{q.source}</span></td><td className="mono">{new Date(q.timestamp).toLocaleTimeString('pt-BR')}</td><td><button className={`btn xs ${selectedSymbol === q.symbol ? 'primary' : 'ghost'}`} type="button" onClick={() => setSelectedSymbol(q.symbol)}>{selectedSymbol === q.symbol ? 'Selecionado' : 'Detalhes'}</button></td></tr>)}</tbody></table></div>}

    <div className="grid cols-2" style={{ marginTop: 14 }}>
      <div className="card"><h2>Terminal MT5</h2><div className="tbl-wrap"><table className="tbl"><tbody>
        <tr><td>Conexão de mercado</td><td><span className={`chip ${wsConnected ? 'ok' : 'danger'}`}>{wsConnected ? 'Core/WS online' : 'WS offline'}</span></td></tr>
        <tr><td>Conta</td><td className="mono">{account ? `${account.login} · ${account.server}` : 'Aguardando MT5'}</td></tr>
        <tr><td>Negociação</td><td><span className={`chip ${account?.trade_allowed ? 'ok' : 'warn'}`}>{account ? (account.trade_allowed ? 'Permitida' : 'Bloqueada') : 'Sem estado'}</span></td></tr>
        <tr><td>Posições abertas</td><td className="mono">{positions.length}</td></tr>
      </tbody></table></div></div>
      <div className="card"><h2>Eventos e erros reais</h2><div className="placeholder" style={{ minHeight: 120, alignItems: 'flex-start' }}>
        {error ? <><strong className="neg">ERRO MT5</strong><span className="muted">{error}</span></> : <><strong className="pos">SEM ERROS DE MERCADO</strong><span className="muted">Última leitura confirmada por MT5. Símbolos indisponíveis aparecem na resposta da fonte.</span></>}
      </div></div>
    </div>
  </div>;
}
