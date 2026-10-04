// Performance & Analytics, lido da MESMA fonte da aba Historico.
//
// POR QUE E PROPS E NAO UM HOOK PROPRIO
// =====================================
// Cada aba chamava `useHistorico` com filtros diferentes — Historico com
// broker/ativo/periodo (padrao "Hoje") e Analytics fixo em mt5/90 dias. As
// duas secoes ficavam lado a lado no mesmo scroll mostrando numeros
// diferentes para a mesma conta, e o botao Atualizar de uma nao mexia na
// outra. Agora HistoryTab monta o hook UMA vez e repassa deals/status/
// loading/recarregar: um fetch, um filtro, um numero.
//
// As classes de tabela e de card sao as mesmas do Historico
// (history-grid + metric-card), que sao as unicas com CSS de largura e
// numeracao tabular — as antigas kpi-card/filter-row nao tinham nenhuma
// regra e ficavam sem caixa, sem gap e com os numeros colidindo.
import { fmtMoney, fmtPct, clsPnl } from '../../lib/format';
import { resumir, type Deal } from '../../lib/historico';
import { useMemo } from 'react';

type Props = {
  deals: Deal[];
  status: string;
  loading: boolean;
  recarregar: () => void;
};

export default function AnalyticsTab({ deals, status, loading, recarregar }: Props) {
  const metrics = useMemo(() => {
    const geral = resumir(deals);
    const porSimbolo: Record<
      string,
      {
        totalTrades: number;
        winRate: number;
        totalPnl: number;
        averagePnl: number;
        profitFactor: number;
      }
    > = {};
    const grupos = new Map<string, Deal[]>();
    for (const deal of deals) {
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
    const expectativa =
      geral.closed > 0
        ? (geral.winRate / 100) * mediaGanho - (1 - geral.winRate / 100) * mediaPerda
        : 0;
    return { ...geral, expectancy: expectativa, bySymbol: porSimbolo };
  }, [deals]);

  const cabecalho = (
    <div className="page-head">
      <div>
        <span className="eyebrow">DESEMPENHO</span>
        <h1>Performance &amp; Analytics</h1>
        <span className="muted">{loading ? 'Atualizando operacoes…' : status}</span>
      </div>
      <button className="btn ghost" type="button" onClick={recarregar} disabled={loading}>
        {loading ? 'Atualizando…' : 'Atualizar'}
      </button>
    </div>
  );

  if (metrics.qty === 0) {
    return (
      <div className="analytics-page">
        {cabecalho}
        <div className="placeholder" role="status">
          {loading
            ? 'Carregando operacoes…'
            : 'Nenhuma operacao fechada no periodo do filtro do Historico acima.'}
        </div>
      </div>
    );
  }

  return (
    <div className="analytics-page">
      {cabecalho}
      <div className="metrics-grid">
        <div className="card metric-card">
          <span className="muted">Win Rate</span>
          <strong>{fmtPct(metrics.winRate)}</strong>
          <small>{metrics.qty} trades</small>
        </div>
        <div className="card metric-card">
          <span className="muted">Profit Factor</span>
          <strong>
            {Number.isFinite(metrics.profitFactor) ? metrics.profitFactor.toFixed(2) : 'N/A'}
          </strong>
          <small>Fator de lucro</small>
        </div>
        <div className="card metric-card">
          <span className="muted">Expectativa</span>
          <strong className={clsPnl(metrics.expectancy)}>
            {fmtMoney(metrics.expectancy, 'USD')}
          </strong>
          <small>Por trade</small>
        </div>
        <div className="card metric-card">
          <span className="muted">PnL Total</span>
          <strong className={clsPnl(metrics.total)}>{fmtMoney(metrics.total, 'USD')}</strong>
          <small>{metrics.closed} fechadas</small>
        </div>
      </div>
      <div className="card compact-card table-scroll">
        <table className="tbl compact-table history-grid">
          <caption className="sr-only">Desempenho por ativo no periodo filtrado</caption>
          <thead>
            <tr>
              <th>Simbolo</th>
              <th className="num">Trades</th>
              <th className="num">Win %</th>
              <th className="num">Total PnL</th>
              <th className="num">Avg PnL</th>
              <th className="num">PF</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(metrics.bySymbol).map(([symbol, data]) => (
              <tr key={symbol}>
                <td>
                  <strong>{symbol}</strong>
                </td>
                <td className="num">{data.totalTrades}</td>
                <td className="num">{fmtPct(data.winRate)}</td>
                <td className="num">{fmtMoney(data.totalPnl, 'USD')}</td>
                <td className="num">{fmtMoney(data.averagePnl, 'USD')}</td>
                <td className="num">
                  {data.profitFactor > 0 ? data.profitFactor.toFixed(2) : 'N/A'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
