import { memo, useEffect, useMemo, useState } from 'react';
import type { Quote } from '../../hooks/useAppStore';

type Point = { time: number; price: number };

function MiniPriceChart({ quote, symbol }: { quote?: Quote; symbol: string }) {
  const [points, setPoints] = useState<Point[]>([]);
  useEffect(() => { setPoints([]); }, [symbol]);
  useEffect(() => {
    if (!quote || !Number.isFinite(quote.price) || quote.price <= 0) return;
    setPoints((current) => [...current, { time: Date.now(), price: quote.price }].slice(-60));
  }, [quote?.price, quote?.timestamp]);
  const chart = useMemo(() => {
    if (points.length < 2) return null;
    const prices = points.map((p) => p.price); const min = Math.min(...prices); const max = Math.max(...prices); const range = max - min || Math.max(max * 0.0001, 0.01); const width = 640; const height = 180; const pad = 12;
    const line = points.map((p, i) => `${(pad + (i / (points.length - 1)) * (width - pad * 2)).toFixed(1)},${(height - pad - ((p.price - min) / range) * (height - pad * 2)).toFixed(1)}`).join(' '); const last = prices[prices.length - 1]; const first = prices[0];
    return { line, min, max, last, change: ((last - first) / first) * 100, width, height };
  }, [points]);
  return <div className="mini-price-chart" aria-label={`Mini gráfico real de ${symbol}`}>
    <div className="mini-chart-head"><div><strong>{symbol}</strong><span className="muted"> · movimentação recebida do MT5</span></div>{chart && <div className={`mono ${chart.change >= 0 ? 'pos' : 'neg'}`}>{chart.change >= 0 ? '▲' : '▼'} {chart.change.toFixed(3)}%</div>}</div>
    {!chart ? <div className="placeholder mini-chart-empty"><span>Aguardando pelo menos duas cotações reais.</span><span className="muted">Nenhuma linha ou valor simulado é desenhado.</span></div> : <svg className="mini-chart-svg" viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label={`Movimentação de ${symbol}`} preserveAspectRatio="none"><line x1="12" y1="24" x2="628" y2="24" stroke="var(--border)" /><line x1="12" y1="90" x2="628" y2="90" stroke="var(--border)" /><line x1="12" y1="168" x2="628" y2="168" stroke="var(--border)" /><polyline points={chart.line} fill="none" stroke="var(--primary)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" /><text x="14" y="15" fill="var(--muted)" fontSize="11">máx {chart.max.toFixed(2)}</text><text x="14" y="178" fill="var(--muted)" fontSize="11">mín {chart.min.toFixed(2)}</text></svg>}
    <div className="mini-chart-foot"><span className="muted">Amostra: {points.length} leituras · janela local</span>{chart && <span className="mono">Último {chart.last.toFixed(2)}</span>}</div>
  </div>;
}

export default memo(MiniPriceChart);
