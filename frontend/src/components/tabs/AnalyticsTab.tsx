// Tab de Analytics - XAU AI PRO
import { useAppStore } from '../../hooks/useAppStore';
import { fmtMoney, fmtPct, fmtNum, clsPnl } from '../../lib/format';
import { calculateWinRate, calculateProfitFactor, calculatePerformanceBySymbol, type TradeResult } from '../../lib/performanceMetrics';
import { useState, useMemo } from 'react';

const generateMockTrades = (): TradeResult[] => {
  const symbols = ['XAUUSD', 'BTCUSDT', 'EURUSD', 'GBPUSD', 'SOLUSDT'];
  const trades: TradeResult[] = [];
  for (let i = 0; i < 150; i++) {
    const symbol = symbols[Math.floor(Math.random() * symbols.length)];
    const side = Math.random() > 0.5 ? 'BUY' as const : 'SELL' as const;
    const entryPrice = 95000 + Math.random() * 5000;
    const exitPrice = entryPrice + (Math.random() - 0.45) * entryPrice * 0.02;
    const pnl = (exitPrice - entryPrice) * (side === 'BUY' ? 1 : -1) * 0.1;
    trades.push({
      id: `trade-${i}`, ticket: 100000 + i, symbol, side,
      volume: 0.1 + Math.random() * 0.5, entryPrice, exitPrice, pnl,
      pnlPercent: (pnl / 10000) * 100, commission: Math.abs(pnl) * 0.02, swap: 0,
      holdingTimeMinutes: Math.floor(Math.random() * 480),
      timestamp: new Date(Date.now() - i * 3600000).toISOString(),
    });
  }
  return trades;
};

export default function AnalyticsTab() {
  const [trades] = useState(() => generateMockTrades());
  const [filterSymbol, setFilterSymbol] = useState('all');
  const [filterPeriod, setFilterPeriod] = useState<'all' | '30d' | '7d' | 'today'>('all');
  
  const filteredTrades = useMemo(() => {
    let result = trades;
    if (filterSymbol !== 'all') result = result.filter(t => t.symbol === filterSymbol);
    const now = Date.now();
    if (filterPeriod === '30d') result = result.filter(t => new Date(t.timestamp).getTime() > now - 30 * 24 * 3600000);
    else if (filterPeriod === '7d') result = result.filter(t => new Date(t.timestamp).getTime() > now - 7 * 24 * 3600000);
    else if (filterPeriod === 'today') { const start = new Date(); start.setHours(0, 0, 0, 0); result = result.filter(t => new Date(t.timestamp).getTime() > start.getTime()); }
    return result;
  }, [trades, filterSymbol, filterPeriod]);
  
  const metrics = useMemo(() => {
    if (filteredTrades.length === 0) return { totalTrades: 0, winRate: 0, profitFactor: 0, expectancy: 0, totalPnl: 0, bySymbol: {} };
    const wins = filteredTrades.filter(t => t.pnl > 0);
    const losses = filteredTrades.filter(t => t.pnl < 0);
    const totalPnl = filteredTrades.reduce((s, t) => s + t.pnl, 0);
    return {
      totalTrades: filteredTrades.length,
      winRate: calculateWinRate(filteredTrades),
      profitFactor: calculateProfitFactor(filteredTrades),
      expectancy: wins.length > 0 && losses.length > 0 ? (wins.reduce((s, t) => s + t.pnl, 0) / wins.length * (wins.length / filteredTrades.length)) - (losses.reduce((s, t) => s + Math.abs(t.pnl), 0) / losses.length * (losses.length / filteredTrades.length)) : 0,
      totalPnl,
      bySymbol: calculatePerformanceBySymbol(filteredTrades),
    };
  }, [filteredTrades]);
  
  const recentTrades = useMemo(() => [...filteredTrades].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()).slice(0, 20), [filteredTrades]);
  const symbols = useMemo(() => ['all', ...new Set(trades.map(t => t.symbol))], [trades]);
  const periodLabels = { all: 'Todos', '30d': '30 dias', '7d': '7 dias', today: 'Hoje' };
  
  if (metrics.totalTrades === 0) {
    return <div className="analytics-page"><div className="page-head"><h1>📈 Performance & Analytics</h1></div><div className="placeholder">Sem dados</div></div>;
  }
  
  return (
    <div className="analytics-page">
      <div className="page-head"><h1>📈 Performance & Analytics</h1><span className="muted">{metrics.totalTrades} trades</span></div>
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
