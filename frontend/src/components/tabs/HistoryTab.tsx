import { useCallback, useEffect, useRef, useState } from 'react';
import '../../theme/history.css';
const API = 'http://127.0.0.1:9001';
type Deal = { id?: string | number; broker?: string; market?: string; symbol?: string; side?: string; quantity?: number | string; volume?: number; price?: number | string; realizedPnl?: number | string; profit?: number; executedAt?: string; close_time?: string; comment?: string; position_id?: number | string };
const limits: Record<string, number> = { '1': 100, '7': 200, '15': 300, '30': 500, '90': 500, '365': 500, '0': 500 };
const periods: Record<string, string> = { '1': 'Hoje', '7': '7 dias', '15': '15 dias', '30': '30 dias', '90': '90 dias', '365': '1 ano', '0': 'Tudo' };
const num = (v: unknown, d = 2) => {
  const normalized = typeof v === 'string' ? v.replace(/\s/g, '').replace(/(\d)\.(\d{3})(?=\D|$)/g, '$1$2').replace(',', '.') : v;
  const n = Number(normalized);
  return Number.isFinite(n) ? n.toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d }) : '--';
};
const toNumber = (v: unknown): number => {
  if (typeof v === 'number') return v;
  if (typeof v !== 'string' || !v.trim()) return NaN;
  const cleaned = v.replace(/\s/g, '');
  const normalized = cleaned.includes(',') ? cleaned.replace(/\./g, '').replace(',', '.') : cleaned;
  return Number(normalized);
};
const money = (v: unknown) => { const n = toNumber(v); return Number.isFinite(n) ? `${n >= 0 ? '' : '−'}$${Math.abs(n).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '--'; };
const cls = (v: number) => (v > 0 ? 'acum-pos' : v < 0 ? 'acum-neg' : '');
const date = (v?: string) => { if (!v) return '--'; const d = new Date(v); return Number.isNaN(d.getTime()) ? v : d.toLocaleString('pt-BR'); };
export default function HistoryTab() {
  const [broker, setBroker] = useState('all');
  const [symbol, setSymbol] = useState('');
  const [days, setDays] = useState('1');
  const [rows, setRows] = useState<Deal[]>([]);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('Aguardando consulta…');
  const [updatedAt, setUpdatedAt] = useState('--:--:--');
  const [selected, setSelected] = useState<number[]>([]);
  const busyRef = useRef(false);
  const load = useCallback(async () => {
    if (busyRef.current) return;
    busyRef.current = true;
    setError(''); setSelected([]);
    const list = broker === 'all' ? ['mt5', 'mexc', 'binance'] : [broker];
    const settled = await Promise.allSettled(list.map(async (b) => {
      if (b !== 'mt5' && !symbol.trim()) return { broker: b, deals: [] as Deal[], skipped: true };
      const params = new URLSearchParams({ broker: b, market: b === 'mt5' ? 'other' : 'crypto-spot', days });
      if (symbol.trim()) params.set('symbol', symbol.trim());
      const r = await fetch(`${API}/api/universal/history?${params}`, { signal: AbortSignal.timeout(15000) });
      const d = await r.json() as { deals?: Deal[]; error?: string };
      if (!r.ok) throw new Error(d.error || `${b} indisponível`);
      return { broker: b, deals: d.deals ?? [] as Deal[] };
    }));
    const fetched: Array<{ broker: string; deals: Deal[] }> = [];
    const failures: string[] = [];
    settled.forEach((result, index) => {
      if (result.status === 'fulfilled') {
        if (!result.value.skipped) fetched.push({ broker: result.value.broker, deals: result.value.deals });
      } else {
        failures.push(`${list[index]}: ${result.reason instanceof Error ? result.reason.message : 'indisponível'}`);
      }
    });
    try {
      const flat = fetched.flatMap(({ broker: b, deals }) => deals.map((deal) => ({ ...deal, broker: deal.broker ?? b })));
      setRows(flat.sort((a, b) => date(b.executedAt ?? b.close_time).localeCompare(date(a.executedAt ?? a.close_time))).slice(0, limits[days] ?? 500));
      const base = fetched.length ? `${fetched.map((f) => `${f.broker}: ${f.deals.length}`).join(' · ')}${flat.length > (limits[days] ?? 500) ? ` · exibindo ${limits[days] ?? 500} mais recentes` : ''}` : 'Sem fontes para o filtro atual';
      setStatus(failures.length ? `${base} · falhas parciais: ${failures.join(' | ')}` : base);
      if (!fetched.length && failures.length) setError(failures.join(' | '));
      setUpdatedAt(new Date().toLocaleTimeString('pt-BR'));
    } catch (e) {
      setRows([]); setStatus('Aguardando consulta…');
      setError(e instanceof Error ? e.message : 'Histórico indisponível');
    } finally { busyRef.current = false; }
  }, [broker, symbol, days]);
  useEffect(() => { void load(); }, [load]);
  const toggleSel = (i: number) => setSelected((cur) => cur.includes(i) ? cur.filter((x) => x !== i) : [...cur, i]);
  const acc = (pool: Deal[]) => {
    const wins = pool.filter((d) => toNumber(d.realizedPnl) > 0).length;
    const losses = pool.filter((d) => toNumber(d.realizedPnl) < 0).length;
    const grossWin = pool.filter((d) => toNumber(d.realizedPnl) > 0).reduce((s, d) => s + toNumber(d.realizedPnl), 0);
    const grossLoss = Math.abs(pool.filter((d) => toNumber(d.realizedPnl) < 0).reduce((s, d) => s + toNumber(d.realizedPnl), 0));
    const closed = wins + losses;
    return { total: pool.reduce((s, d) => s + (toNumber(d.realizedPnl) || 0), 0), wins, losses, closed, wr: closed ? (wins / closed) * 100 : 0, pf: grossLoss > 0 ? grossWin / grossLoss : (grossWin > 0 ? Infinity : 0), grossWin, grossLoss, qty: pool.length };
  };
  const tot = acc(rows);
  const sel = acc(selected.map((i) => rows[i]).filter(Boolean));
  const byAsset = new Map<string, Deal[]>();
  for (const d of rows) { const k = String(d.symbol ?? '--'); byAsset.set(k, [...(byAsset.get(k) ?? []), d]); }
  const perPeriod = Object.keys(periods).filter((k) => k !== days && k !== '0').map((k) => {
    const ini = new Date(Date.now() - Number(k) * 86400000).toISOString();
    const pool = rows.filter((d) => { const when = d.executedAt ?? d.close_time; if (!when) return false; const t = new Date(when); return !Number.isNaN(t.getTime()) && t >= new Date(ini); });
    return { key: k, label: periods[k], ...acc(pool) };
  });
  const exportCsv = () => {
    const csv = [['ID/Ticket', 'Corretora', 'Ativo', 'Lado', 'Quantidade', 'Preco', 'PNL', 'Data'], ...rows.map((r) => [r.id, r.broker, r.symbol, r.side, r.quantity ?? r.volume, r.price, r.realizedPnl, r.executedAt ?? r.close_time])].map((r) => r.join(';')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'historico-universal.csv'; a.click(); URL.revokeObjectURL(url);
  };

  return <main className="history-page quantum-history">
    <div className="page-head"><div><span className="eyebrow">REGISTRO UNIVERSAL</span><h1>Histórico</h1><span className="muted">Execuções reais por corretora · PnL acumulado e seleção</span></div>
      <div className="btn-row"><button className="btn ghost" onClick={exportCsv} disabled={!rows.length}>Exportar CSV</button><button className="btn primary" type="button" onClick={() => void load()} disabled={busyRef.current}>Atualizar</button></div></div>
    <div className="card compact-card history-filter-card"><div className="history-filters">
      <label className="field">Corretora<select value={broker} onChange={(e) => setBroker(e.target.value)}><option value="all">Todas</option><option value="mt5">MT5</option><option value="mexc">MEXC</option><option value="binance">Binance</option></select></label>
      <label className="field">Ativo<input value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} placeholder={broker === 'mt5' ? 'Opcional (ex.: XAUUSD)' : 'Escolha manualmente'} /></label>
      <label className="field">Período<select value={days} onChange={(e) => setDays(e.target.value)}><option value="1">Hoje</option><option value="7">7 dias</option><option value="15">15 dias</option><option value="30">30 dias</option><option value="90">90 dias</option><option value="365">1 ano</option><option value="0">Tudo</option></select></label>
      <div className="history-count"><span className="muted">Exibindo</span><strong>{rows.length}</strong><span className="muted">{updatedAt !== '--:--:--' ? `· ${updatedAt}` : ''}</span></div>
    </div></div>
    {error && <div className="placeholder">{error}</div>}
    <div className="history-status-row"><span className="muted">Fontes: {status}</span></div>
    <div className="metrics-grid">
      <div className="card metric-card"><span className="muted">PnL acumulado do período</span><strong className={cls(tot.total)}>{money(tot.total)}</strong><small>{tot.qty} operações</small></div>
      <div className="card metric-card"><span className="muted">Ganhos / Perdas</span><strong>{tot.wins} / {tot.losses}</strong><small>Taxa de acerto {tot.wr.toFixed(1)}%</small></div>
      <div className="card metric-card"><span className="muted">Lucro / Prejuízo bruto</span><strong>{money(tot.grossWin)} / {money(-tot.grossLoss)}</strong><small>{tot.pf === Infinity ? 'Sem perdas no período' : `Fator de lucro ${tot.pf.toFixed(2)}`}</small></div>
      <div className="card metric-card"><span className="muted">Seleção atual</span><strong className={cls(sel.total)}>{selected.length ? money(sel.total) : '--'}</strong><small>{selected.length} operação(ões) marcada(s)</small></div>
    </div>
    <div className="card compact-card acum-table-card"><h2>PnL acumulado por período</h2>
      <div className="table-scroll"><table className="tbl compact-table"><thead><tr><th>Período</th><th>Operações</th><th>PnL acumulado</th><th>Ganhos</th><th>Perdas</th><th>Acerto</th><th>Fator de lucro</th></tr></thead>
        <tbody>{perPeriod.filter((p) => p.qty > 0).map((p) => <tr key={p.key}><td>{p.label}</td><td className="num">{p.qty}</td><td className={`num ${cls(p.total)}`}>{money(p.total)}</td><td className="num acum-pos">{p.wins}</td><td className="num acum-neg">{p.losses}</td><td className="num">{p.wr.toFixed(0)}%</td><td className="num">{p.pf === Infinity ? '∞' : p.pf.toFixed(2)}</td></tr>)}
          {perPeriod.every((p) => p.qty === 0) && <tr><td colSpan={7}>Sem operações nos demais períodos.</td></tr>}</tbody></table></div>
      <p className="csv-note">Períodos calculados sobre os registros retornados pelo filtro atual. Use o período "Tudo" para o acumulado completo.</p></div>
    <div className="card compact-card history-selection-card"><div className="section-head"><div><h2>PnL da seleção</h2><span className="muted">Clique em uma operação para somar ou remover da seleção</span></div><div className="history-selection-list">
      {Array.from(byAsset.keys()).slice(0, 8).map((k) => { const a = acc(byAsset.get(k) ?? []); return <button key={k} type="button" className="sel-chip" onClick={() => { const idx = rows.map((r, i) => (r.symbol ?? '--') === k ? i : -1).filter((i) => i >= 0); setSelected((cur) => cur.length === idx.length && cur.every((v, j) => cur.includes(idx[j])) ? [] : idx); }}><input type="checkbox" readOnly checked={selected.length > 0 && selected.length === (byAsset.get(k) ?? []).length} tabIndex={-1} />{k}<span className={`sum ${cls(a.total)}`}>{money(a.total)}</span></button>; })}
      <button type="button" className="btn xs ghost" onClick={() => setSelected([])} disabled={!selected.length}>Limpar seleção</button>
    </div></div></div>
    <div className="card compact-card table-scroll history-table-card"><table className="tbl compact-table"><thead><tr><th>ID/Ticket</th><th>Corretora</th><th>Ativo</th><th>Lado</th><th>Quantidade</th><th>Preço</th><th>PNL</th><th>Data</th></tr></thead>
      <tbody>{rows.map((r, i) => { const p = toNumber(r.realizedPnl); const value = Number.isFinite(p) ? p : 0; const on = selected.includes(i); return <tr key={`${r.id}-${i}`} className={`${on ? 'asset-row-selected' : ''} ${value > 0 ? 'history-row-positive' : value < 0 ? 'history-row-negative' : 'history-row-neutral'}`} onClick={() => toggleSel(i)} style={{ cursor: 'pointer' }}>
        <td className="mono">{r.id ?? '--'}</td><td><span className={`chip ${r.broker === 'mt5' ? 'mt5' : r.broker === 'mexc' ? 'ok' : r.broker === 'binance' ? 'warn' : 'neutral'}`}>{(r.broker ?? '--').toUpperCase()}</span></td>
        <td><strong>{r.symbol ?? '--'}</strong></td><td>{r.side ?? '--'}</td><td className="num">{num(r.quantity ?? r.volume, 4)}</td><td className="num">{num(r.price, 5)}</td>
        <td className={`num ${value > 0 ? 'pos' : value < 0 ? 'neg' : ''}`}>{num(r.realizedPnl, 2)}</td><td>{date(r.executedAt ?? r.close_time)}</td></tr>; })}
        {!rows.length && !error && <tr><td colSpan={8}>Nenhum registro no período.</td></tr>}</tbody></table></div>
  </main>;
}
