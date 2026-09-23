// Tab de Analytics — XAU AI PRO.
// Fonte de verdade: deals reais de /api/universal/history (mt5/mexc/binance),
// mesmos dados do HistoryTab. Sem mock: sem histórico = "Sem dados".
import { fmtMoney, fmtPct, clsPnl } from '../../lib/format';
import { apiBase } from '../../lib/api';
import { calculateWinRate, calculateProfitFactor } from '../../lib/performanceMetrics';
import { useState, useMemo, useEffect, useCallback } from 'react';

type Deal = {
  id?: string | number; broker?: string; symbol?: string; side?: string;
  quantity?: number | string; volume?: number; price?: number | string;
  realizedPnl?: number | string; profit?: number;
  executedAt?: string; close_time?: string;
};

const toNum = (v: unknown): number => {
  if (typeof v === 'number') return v;
  if (typeof v !== 'string' || !v.trim()) return NaN;
  const c = v.replace(/\s/g, '');
  return Number(c.includes(',') ? c.replace(/\./g, '').replace(',', '.') : c);
};

const API = `${apiBase()}`;

export default function AnalyticsTab() {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [status, setStatus] = useState('Carregando histórico real...');
  const [filterSymbol, setFilterSymbol] = useState('all');
  const [filterPeriod, setFilterPeriod] = useState<'all' | '30d' | '7d' | 'today'>('all');

  const load = useCallback(async () => {
    setStatus('Carregando histórico real...');
    const settled = await Promise.allSettled(
      ['mt5'].map(async (b) => {
        const params = new URLSearchParams({ broker: b, market: 'other', days: '90' });
        const r = await fetch(`${API}/api/universal/history?${params}`, { signal: AbortSignal.timeout(15000) });
        const d = (await r.json()) as { deals?: Deal[]; error?: string };
        if (!r.ok) throw new Error(d.error || `${b} indisponível`);
        return d.deals ?? [];
      }),
    );
    const flat = settled.flatMap((s) => (s.status === 'fulfilled' ? s.value : []));
    setDeals(flat);
    setStatus(
      settled.some((s) => s.status === 'rejected')
        ? 'Gateway indisponível — conecte o MT5 para ver analytics reais.'
        : flat.length
          ? `${flat.length} deals reais (90 dias).`
          : 'Sem deals no período — nenhum trade fechado.',
    );
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const trades = useMemo(
    () =>
      deals.map((d, i) => ({
        id: String(d.id ?? i),
        symbol: d.symbol ?? '--',
        pnl: Number.isFinite(toNum(d.realizedPnl)) ? toNum(d.realizedPnl) : (d.profit ?? 0),
        timestamp: d.executedAt ?? d.close_time ?? '',
      })),
    [deals],
  );

  const filteredTrades = useMemo(() => {
    let result = trades;
    if (filterSymbol !== 'all') result = result.filter((t) => t.symbol === filterSymbol);
    const now = Date.now();
    if (filterPeriod === '30d') result = result.filter((t) => new Date(t.timestamp).getTime() > now - 30 * 24 * 3600000);
    else if (filterPeriod === '7d') result = result.filter((t) => new Date(t.timestamp).getTime() > now - 7 * 24 * 3600000);
    else if (filterPeriod === 'today') { const start = new Date(); start.setHours(0, 0, 0, 0); result = result.filter((t) => new Date(t.timestamp).getTime() > start.getTime()); }
    return result;
  }, [trades, filterSymbol, filterPeriod]);

  const metrics = useMemo(() => {
    if (filteredTrades.length === 0) return { totalTrades: 0, winRate: 0, profitFactor: 0, expectancy: 0, totalPnl: 0, bySymbol: {} as Record<string, { totalTrades: number; winRate: number; totalPnl: number; averagePnl: number; profitFactor: number }> };
    const asResults = filteredTrades.map((t) => ({ ...t, side: 'BUY' as const, volume: 0, entryPrice: 0, exitPrice: 0, pnlPercent: 0, commission: 0, swap: 0, holdingTimeMinutes: 0, ticket: 0 }));
    const wins = filteredTrades.filter((t) => t.pnl > 0);
    const losses = filteredTrades.filter((t) => t.pnl < 0);
    const totalPnl = filteredTrades.reduce((s, t) => s + t.pnl, 0);
    const bySymbol: Record<string, { totalTrades: number; winRate: number; totalPnl: number; averagePnl: number; profitFactor: number }> = {};
    const pnlsBySymbol: Record<string, number[]> = {};
    for (const t of filteredTrades) {
      const g = bySymbol[t.symbol] ?? { totalTrades: 0, winRate: 0, totalPnl: 0, averagePnl: 0, profitFactor: 0 };
      g.totalTrades += 1;
      g.totalPnl += t.pnl;
      bySymbol[t.symbol] = g;
      (pnlsBySymbol[t.symbol] ??= []).push(t.pnl);
    }
    for (const [sym, g] of Object.entries(bySymbol)) {
      const pnls = pnlsBySymbol[sym] ?? [];
      const w = pnls.filter((p) => p > 0).length;
      const gp = pnls.filter((p) => p > 0).reduce((s, p) => s + p, 0);
      const gl = Math.abs(pnls.filter((p) => p < 0).reduce((s, p) => s + p, 0));
      g.winRate = pnls.length ? (w / pnls.length) * 100 : 0;
      g.averagePnl = pnls.length ? g.totalPnl / pnls.length : 0;
      g.profitFactor = gl === 0 ? (gp > 0 ? Infinity : 0) : gp / gl;
    }
    return {
      totalTrades: filteredTrades.length,
      winRate: calculateWinRate(asResults),
      profitFactor: calculateProfitFactor(asResults),
      expectancy: wins.length > 0 && losses.length > 0 ? (wins.reduce((s, t) => s + t.pnl, 0) / wins.length * (wins.length / filteredTrades.length)) - (losses.reduce((s, t) => s + Math.abs(t.pnl), 0) / losses.length * (losses.length / filteredTrades.length)) : 0,
      totalPnl,
      bySymbol,
    };
  }, [filteredTrades]);

  const symbols = useMemo(() => ['all', ...new Set(trades.map((t) => t.symbol))], [trades]);
  const periodLabels = { all: 'Todos', '30d': '30 dias', '7d': '7 dias', today: 'Hoje' };
  
  if (metrics.totalTrades === 0) {
    return <div className="analytics-page"><div className="page-head"><div><h1>📈 Performance & Analytics</h1><span className="muted">{status}</span></div><button className="btn ghost" onClick={() => void load()}>Atualizar</button></div><div className="placeholder">Sem dados reais — nenhum trade fechado ou gateway offline.</div></div>;
  }

  return (
    <div className="analytics-page">
      <div className="page-head"><div><h1>📈 Performance & Analytics</h1><span className="muted">{status}</span></div><button className="btn ghost" onClick={() => void load()}>Atualizar</button></div>
      <div className="metrics-grid">
        <div className="card kpi-card"><span className="kpi-label">Win Rate</span><span className="kpi-value">{fmtPct(metrics.winRate)}</span><span className="kpi-sub">{metrics.totalTrades} trades</span></div>
        <div className="card kpi-card"><span className="kpi-label">Profit Factor</span><span className="kpi-value">{metrics.profitFactor > 0 ? metrics.profitFactor.toFixed(2) : 'N/A'}</span></div>
        <div className="card kpi-card"><span className="kpi-label">Expectativa</span><span className="kpi-value">{fmtMoney(metrics.expectancy, 'USD')}</span><span className="kpi-sub">Por trade</span></div>
        <div className="card kpi-card"><span className="kpi-label">PnL Total</span><span className={`kpi-value ${clsPnl(metrics.totalPnl)}`}>{fmtMoney(metrics.totalPnl, 'USD')}</span></div>
      </div>
      <div className="card">
        <div className="filter-row">
          <select value={filterSymbol} onChange={(e) => setFilterSymbol(e.target.value)}>{symbols.map(s => <option key={s} value={s}>{s === 'all' ? 'Todos' : s}</option>)}</select>
          <select value={filterPeriod} onChange={(e) => setFilterPeriod(e.target.value as typeof filterPeriod)}>{Object.entries(periodLabels).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
        </div>
      </div>
      <div className="card">
        <table className="tbl">
          <thead><tr><th>Símbolo</th><th>Trades</th><th>Win %</th><th>Total PnL</th><th>Avg PnL</th><th>PF</th></tr></thead>
          <tbody>{Object.entries(metrics.bySymbol).map(([symbol, data]) => (
            <tr key={symbol}><td><strong>{symbol}</strong></td><td className="num">{data.totalTrades}</td><td className={clsPnl(data.winRate - 50)}>{fmtPct(data.winRate)}</td><td className={clsPnl(data.totalPnl)}>{fmtMoney(data.totalPnl, 'USD')}</td><td className={clsPnl(data.averagePnl)}>{fmtMoney(data.averagePnl, 'USD')}</td><td className="num">{data.profitFactor > 0 ? data.profitFactor.toFixed(2) : 'N/A'}</td></tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}
