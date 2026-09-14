import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';
import { useAppStore } from '../../hooks/useAppStore';

interface CandleData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

const SIMBOLOS = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD'];
const CORES_NEON = ['#f0b90b', '#4f7cff', '#22c55e', '#a855f7', '#ef4444'];

function gerarCandles(base: number, quantidade = 100): CandleData[] {
  const candles: CandleData[] = [];
  let preco = base;
  const agora = Math.floor(Date.now() / 1000);
  for (let i = quantidade; i >= 0; i--) {
    const variacao = (Math.random() - 0.5) * base * 0.002;
    const open = preco;
    const close = preco + variacao;
    const high = Math.max(open, close) + Math.random() * base * 0.001;
    const low = Math.min(open, close) - Math.random() * base * 0.001;
    const volume = Math.floor(Math.random() * 1000) + 100;
    candles.push({ time: agora - i * 60, open, high, low, close, volume });
    preco = close;
  }
  return candles;
}

export default function QuantumChart() {
  const quotes = useAppStore((s) => s.quotes);
  const selectedSymbol = useAppStore((s) => s.selectedSymbol);
  const setSelectedSymbol = useAppStore((s) => s.setSelectedSymbol);
  const [simboloAtivo, setSimboloAtivo] = useState(selectedSymbol);
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const candleSeriesRef = useRef<any>(null);
  const volumeSeriesRef = useRef<any>(null);
  const [candles, setCandles] = useState<CandleData[]>([]);

  const quoteAtual = quotes.find((q) => q.symbol === simboloAtivo);
  const basePrice = quoteAtual?.price ?? (simboloAtivo === 'XAUUSD' ? 2345 : simboloAtivo === 'BTCUSD' ? 43000 : 1.0850);

  useEffect(() => {
    setCandles(gerarCandles(basePrice));
  }, [simboloAtivo, basePrice]);

  useEffect(() => {
    if (!chartContainerRef.current) return;
    const chart = createChart(chartContainerRef.current, {
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: 'var(--text)' },
      grid: { vertLines: { color: 'rgba(255,255,255,0.05)' }, horzLines: { color: 'rgba(255,255,255,0.05)' } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: 'var(--border)' },
      timeScale: { borderColor: 'var(--border)', timeVisible: true },
      width: chartContainerRef.current.clientWidth,
      height: 400,
    });
    chartRef.current = chart;
    const candleSeries = (chart as any).addCandlestickSeries({
      upColor: '#22c55e', downColor: '#ef4444', borderUpColor: '#22c55e', borderDownColor: '#ef4444', wickUpColor: '#22c55e', wickDownColor: '#ef4444',
    });
    candleSeriesRef.current = candleSeries;
    const volumeSeries = (chart as any).addHistogramSeries({
      color: '#4f7cff', priceFormat: { type: 'volume' }, priceScaleId: 'volume',
    });
    volumeSeriesRef.current = volumeSeries;
    return () => chart.remove();
  }, [simboloAtivo]);

  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current || candles.length === 0) return;
    candleSeriesRef.current.setData(candles.map((c) => ({ time: c.time as any, open: c.open, high: c.high, low: c.low, close: c.close })));
    volumeSeriesRef.current.setData(candles.map((c) => ({ time: c.time as any, value: c.volume, color: c.close >= c.open ? 'rgba(34,197,94,0.4)' : 'rgba(239,68,68,0.4)' })));
  }, [candles]);

  useEffect(() => {
    if (!quoteAtual || !candleSeriesRef.current || candles.length === 0) return;
    const ultimoCandle = candles[candles.length - 1];
    const novoCandle = { ...ultimoCandle, close: quoteAtual.price, high: Math.max(ultimoCandle.high, quoteAtual.price), low: Math.min(ultimoCandle.low, quoteAtual.price) };
    candleSeriesRef.current.update({ time: novoCandle.time as any, open: novoCandle.open, high: novoCandle.high, low: novoCandle.low, close: novoCandle.close });
  }, [quoteAtual?.price]);

  return (
    <div>
      <div className="page-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Gráfico Quântico</h1>
          <span className="muted">Multi-ativo com candles em tempo real</span>
        </div>
        <div className="btn-row">
          {SIMBOLOS.map((s, i) => (
            <button key={s} className={simboloAtivo === s ? 'btn sm primary' : 'btn sm ghost'}
              onClick={() => { setSimboloAtivo(s); setSelectedSymbol(s); }}
              style={simboloAtivo === s ? { borderColor: CORES_NEON[i], boxShadow: `0 0 8px ${CORES_NEON[i]}40` } : {}}>
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="card" style={{ padding: 10, marginBottom: 14 }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
          <span className="muted" style={{ marginLeft: 'auto', fontSize: 12 }}>Ativo: <strong>{simboloAtivo}</strong> | Preço: <strong>{quoteAtual?.price.toFixed(2) ?? '--'}</strong></span>
        </div>
        <div ref={chartContainerRef} style={{ width: '100%', height: 400, borderRadius: 8, overflow: 'hidden' }} />
      </div>

      <div className="grid cols-4">
        <div className="card"><div className="kpi-label">Abertura</div><div className="kpi-value mono">{candles.length > 0 ? candles[candles.length - 1].open.toFixed(2) : '--'}</div></div>
        <div className="card"><div className="kpi-label">Máxima 20p</div><div className="kpi-value mono">{candles.length > 0 ? Math.max(...candles.slice(-20).map(c => c.high)).toFixed(2) : '--'}</div></div>
        <div className="card"><div className="kpi-label">Mínima 20p</div><div className="kpi-value mono">{candles.length > 0 ? Math.min(...candles.slice(-20).map(c => c.low)).toFixed(2) : '--'}</div></div>
        <div className="card"><div className="kpi-label">Volume</div><div className="kpi-value mono">{candles.length > 0 ? candles[candles.length - 1].volume : '--'}</div></div>
      </div>
    </div>
  );
}