// Fonte de verdade: deals reais de /api/universal/history, via lib/historico.
// Compartilha o mesmo hook e os mesmos calculos com HistoryTab, entao as duas
// abas leem exatamente os mesmos registros e nao podem divergir em numero.
import { fmtMoney, fmtPct, clsPnl } from '../../lib/format';
import { useHistorico, resumir, dealPnl, dealDate, type Deal } from '../../lib/historico';
import { useMemo, useState } from 'react';

export default function AnalyticsTab() {
  const [filterSymbol, setFilterSymbol] = useState('all');
  const [filterPeriod, setFilterPeriod] = useState<'all' | '30d' | '7d' | 'today'>('all');

  // Mesma fonte da aba Historico. Antes cada aba tinha seu proprio fetch e
  // sua propria conta de win-rate/PF, o que permitia numeros diferentes.
  const { deals, status, recarregar } = useHistorico({ broker: 'mt5', days: '90' });

  const filtrados = useMemo(() => {
    let result = deals;
    if (filterSymbol !== 'all') {
      result = result.filter((d) => (d.symbol ?? '--') === filterSymbol);
    }
    if (filterPeriod !== 'all') {
      const now = Date.now();
      const desde =
        filterPeriod === 'today'
          ? new Date(new Date().setHours(0, 0, 0, 0)).getTime()
          : now - Number(filterPeriod.replace('d', '')) * 24 * 3600000;
      result = result.filter((d) => {
        const quando = dealDate(d);
        if (!quando) return false;
        const tempo = new Date(quando).getTime();
        return !Number.isNaN(tempo) && tempo > desde;
      });
    }
    return result;
  }, [deals, filterSymbol, filterPeriod]);

  const metrics = useMemo(() => {
    const geral = resumir(filtrados);
    const porSimbolo: Record<string, {
      totalTrades: number; winRate: number; totalPnl: number;
      averagePnl: number; profitFactor: number;
    }> = {};
    const grupos = new Map<string, Deal[]>();
    for (const deal of filtrados) {
      const simbolo = deal.symbol ?? '--';
      grupos.set(simbolo, [...(grupos.get(simbolo) ?? []), deal]);
    }
    for (const [simbolo, lista] of grupos) {
      const r = resumir(lista);
      porSimbolo[simbolo] = {
        totalTrades: r.qty,
        winRate: r.winRate,
        totalPnl: r.total,
        averagePnl: r.qty ? r.total / r.qty : 0,
        profitFactor: Number.isFinite(r.profitFactor) ? r.profitFactor : 0,
      };
    }
    // Expectativa: media ponderada de ganho e perda por trade.
    const mediaGanho = geral.wins > 0 ? geral.grossWin / geral.wins : 0;
    const mediaPerda = geral.losses > 0 ? geral.grossLoss / geral.losses : 0;
    const expectativa = geral.closed > 0
      ? (geral.winRate / 100) * mediaGanho - (1 - geral.winRate / 100) * mediaPerda
      : 0;
    return { ...geral, expectancy: expectativa, bySymbol: porSimbolo };
  }, [filtrados]);

  const symbols = useMemo(
    () => ['all', ...new Set(deals.map((d) => d.symbol ?? '--'))],
    [deals],
  );
  const periodLabels = { all: 'Todos', '30d': '30 dias', '7d': '7 dias', today: 'Hoje' };

  const cabecalho = (
    <div className="page-head">
      <div>
        <h1>📈 Performance &amp; Analytics</h1>
        <span className="muted">{status}</span>
      </div>
      <button className="btn ghost" onClick={recarregar}>Atualizar</button>
    </div>
  );

  if (metrics.qty === 0) {
    return (
      <div className="analytics-page">
        {cabecalho}
        <div className="placeholder">Sem dados reais — nenhum trade fechado ou gateway offline.</div>
      </div>
    );
  }

  return (
    <div className="analytics-page">
      {cabecalho}
      <div className="metrics-grid">
        <div className="card kpi-card"><span className="kpi-label">Win Rate</span><span className="kpi-value">{fmtPct(metrics.winRate)}</span><span className="kpi-sub">{metrics.qty} trades</span></div>
        <div className="card kpi-card"><span className="kpi-label">Profit Factor</span><span className="kpi-value">{Number.isFinite(metrics.profitFactor) ? metrics.profitFactor.toFixed(2) : 'N/A'}</span></div>
        <div className="card kpi-card"><span className="kpi-label">Expectativa</span><span className="kpi-value">{fmtMoney(metrics.expectancy, 'USD')}</span><span className="kpi-sub">Por trade</span></div>
        <div className="card kpi-card"><span className="kpi-label">PnL Total</span><span className={`kpi-value ${clsPnl(metrics.total)}`}>{fmtMoney(metrics.total, 'USD')}</span></div>
      </div>
      <div className="card">
        <div className="filter-row">
          <select value={filterSymbol} onChange={(e) => setFilterSymbol(e.target.value)}>{symbols.map(s => <option key={s} value={s}>{s === 'all' ? 'Todos' : s}</option>)}</select>
          <select value={filterPeriod} onChange={(e) => setFilterPeriod(e.target.value as typeof filterPeriod)}>{Object.entries(periodLabels).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
        </div>
      </div>
      <div className="card">
        <table className="tbl">
          <thead><tr><th>Símbolo</th><th className="num">Trades</th><th className="num">Win %</th><th className="num">Total PnL</th><th className="num">Avg PnL</th><th className="num">PF</th></tr></thead>
          <tbody>{Object.entries(metrics.bySymbol).map(([symbol, data]) => (
            <tr key={symbol}><td><strong>{symbol}</strong></td><td className="num">{data.totalTrades}</td><td className={clsPnl(data.winRate - 50)}>{fmtPct(data.winRate)}</td><td className={clsPnl(data.totalPnl)}>{fmtMoney(data.totalPnl, 'USD')}</td><td className={clsPnl(data.averagePnl)}>{fmtMoney(data.averagePnl, 'USD')}</td><td className="num">{data.profitFactor > 0 ? data.profitFactor.toFixed(2) : 'N/A'}</td></tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}
