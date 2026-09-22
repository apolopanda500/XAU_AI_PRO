// Gráfico de candles OHLC reais do MT5 (lightweight-charts v4).
// Dados exclusivamente do gateway (/api/mt5/candles via copy_rates) — sem dado simulado.
import { useEffect, useRef, useState } from 'react';
import { createChart, type CandlestickSeriesOptions, type IChartApi, type ISeriesApi, type CandlestickData, type UTCTimestamp, ColorType, CrosshairMode } from 'lightweight-charts';
import { apiBase } from '../../lib/api';

const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'] as const;
type Timeframe = (typeof TIMEFRAMES)[number];

type Candle = { time: number; open: number; high: number; low: number; close: number; volume: number };

export default function PriceChart({ symbol = 'XAUUSD', height = 360 }: { symbol?: string; height?: number }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const [timeframe, setTimeframe] = useState<Timeframe>('M5');
  const [candles, setCandles] = useState<Candle[]>([]);
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(true);

  // Criação única do gráfico + série
  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      height,
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#8b93a7' },
      grid: { vertLines: { color: 'rgba(139,147,167,.08)' }, horzLines: { color: 'rgba(139,147,167,.08)' } },
      timeScale: { timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: 'rgba(139,147,167,.2)' },
      crosshair: { mode: CrosshairMode.Magnet },
    });
    const serie = chart.addCandlestickSeries({
      upColor: '#2ecc71', downColor: '#e74c3c', borderUpColor: '#2ecc71', borderDownColor: '#e74c3c',
      wickUpColor: '#2ecc71', wickDownColor: '#e74c3c',
    } as CandlestickSeriesOptions);
    chartRef.current = chart;
    seriesRef.current = serie;
    const obs = new ResizeObserver(() => chart.applyOptions({ width: containerRef.current?.clientWidth ?? 0 }));
    obs.observe(containerRef.current);
    return () => { obs.disconnect(); chart.remove(); chartRef.current = null; seriesRef.current = null; };
  }, [height]);

  // Busca dos candles no gateway (http-polling; refetch ao trocar timeframe)
  useEffect(() => {
    let ativo = true;
    const carregar = async () => {
      setCarregando(true);
      try {
        const r = await fetch(`${apiBase()}/api/mt5/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&count=300`, { signal: AbortSignal.timeout(10000) });
        const d = await r.json() as { ok?: boolean; candles?: Candle[]; error?: string };
        if (!ativo) return;
        if (r.ok && d.ok && Array.isArray(d.candles) && d.candles.length) {
          setCandles(d.candles);
          setErro('');
        } else {
          setErro(d.error || `sem candles (${r.status})`);
        }
      } catch {
        if (ativo) setErro('gateway indisponível');
      } finally {
        if (ativo) setCarregando(false);
      }
    };
    void carregar();
    const timer = window.setInterval(carregar, 30_000); // atualização de fundo a cada 30s
    return () => { ativo = false; window.clearInterval(timer); };
  }, [symbol, timeframe]);

  // Aplica os dados na série
  useEffect(() => {
    const serie = seriesRef.current;
    if (!serie || !candles.length) return;
    const dados: CandlestickData[] = candles.map((c) => ({
      time: c.time as UTCTimestamp,
      open: c.open, high: c.high, low: c.low, close: c.close,
    }));
    serie.setData(dados);
    chartRef.current?.timeScale().fitContent();
  }, [candles]);

  return (
    <div className="card compact-card price-chart">
      <div className="section-head">
        <div>
          <h2>{symbol}</h2>
          <span className="muted">Candles OHLC reais · atualização a cada 30s · gateway MT5</span>
        </div>
        <div className="btn-row" role="group" aria-label="Timeframe">
          {TIMEFRAMES.map((tf) => (
            <button key={tf} type="button" className={`btn sm ${tf === timeframe ? 'primary' : ''}`} onClick={() => setTimeframe(tf)}>{tf}</button>
          ))}
        </div>
      </div>
      {erro && <div className="hint" role="alert">Gráfico indisponível: {erro}</div>}
      {carregando && !candles.length && <div className="hint">Carregando candles…</div>}
      <div ref={containerRef} style={{ width: '100%', height }} />
    </div>
  );
}