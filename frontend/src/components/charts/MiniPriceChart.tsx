import { memo, useMemo } from 'react';

type MiniPoint = { time: number; price: number | null };
type MiniQuote = { last?: number | null; price?: number | null; source?: string | null };

type MiniPriceChartProps = {
  quote?: MiniQuote;
  values?: MiniPoint[];
  symbol: string;
  sourceLabel?: string;
};

function MiniPriceChart({ quote, values = [], symbol, sourceLabel }: MiniPriceChartProps) {
  const points = useMemo(() => values.filter((point): point is { time: number; price: number } => point.price !== null && Number.isFinite(point.price)).slice(-60), [values]);
  const chart = useMemo(() => {
    if (points.length < 2) return null;
    const prices = points.map((point) => point.price);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || Math.max(max * 0.0001, 0.01);
    const width = 640;
    const height = 180;
    const pad = 12;
    const line = points.map((point, index) => `${(pad + (index / (points.length - 1)) * (width - pad * 2)).toFixed(1)},${(height - pad - ((point.price - min) / range) * (height - pad * 2)).toFixed(1)}`).join(' ');
    const first = prices[0];
    const last = prices[prices.length - 1];
    const change = first === 0 ? null : ((last - first) / first) * 100;
    return { line, min, max, last, change, width, height };
  }, [points]);
  const last = quote?.last ?? quote?.price ?? null;
  const source = sourceLabel ?? quote?.source ?? 'fonte da seleção';
  return <div className="mini-price-chart" aria-label={`Mini gráfico real de ${symbol}`}>
    <div className="mini-chart-head"><div><strong>{symbol}</strong><span className="muted"> · {source}</span></div>{chart?.change != null && <div className={`mono ${chart.change >= 0 ? 'pos' : 'neg'}`}>{chart.change >= 0 ? '▲' : '▼'} {chart.change.toFixed(3)}%</div>}</div>
    {!chart ? <div className="placeholder mini-chart-empty"><span>Candles reais insuficientes para a linha.</span><span className="muted">Nenhum valor é inventado para preencher o gráfico.</span></div> : <svg className="mini-chart-svg" viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label={`Movimentação real de ${symbol}`} preserveAspectRatio="none"><line x1="12" y1="24" x2="628" y2="24" stroke="var(--border)" /><line x1="12" y1="90" x2="628" y2="90" stroke="var(--border)" /><line x1="12" y1="168" x2="628" y2="168" stroke="var(--border)" /><polyline points={chart.line} fill="none" stroke="var(--primary)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" /><text x="14" y="15" fill="var(--muted)" fontSize="12">máx {chart.max.toFixed(2)}</text><text x="14" y="178" fill="var(--muted)" fontSize="12">mín {chart.min.toFixed(2)}</text></svg>}
    <div className="mini-chart-foot"><span className="muted">Amostra: {points.length} candles · fonte explícita</span>{last !== null && <span className="mono">Último {last.toFixed(2)}</span>}</div>
  </div>;
}

export default memo(MiniPriceChart);
