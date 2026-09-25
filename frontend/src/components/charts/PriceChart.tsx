import { useEffect, useRef, useState } from 'react';
import { createChart, type IChartApi, type ISeriesApi, type CandlestickData, type UTCTimestamp, ColorType, CrosshairMode } from 'lightweight-charts';
import { getCandles, type MarketBroker, type MarketCandle, type MarketKind } from '../../lib/marketApi';

export const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'] as const;
export type ChartTimeframe = (typeof TIMEFRAMES)[number];

type PriceChartProps = {
  symbol?: string;
  broker?: MarketBroker;
  market?: MarketKind;
  height?: number;
  candles?: MarketCandle[];
  timeframe?: ChartTimeframe;
  onTimeframeChange?: (timeframe: ChartTimeframe) => void;
  loading?: boolean;
  error?: string;
  sourceLabel?: string;
};

function defaultMarket(broker: MarketBroker): MarketKind {
  return broker === 'mt5' ? 'forex' : 'crypto-spot';
}

export default function PriceChart({ symbol = '', broker = 'mt5', market, height = 360, candles, timeframe, onTimeframeChange, loading = false, error = '', sourceLabel }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'>>(null);
  const [chartReady, setChartReady] = useState(false);
  const [internalTimeframe, setInternalTimeframe] = useState<ChartTimeframe>('M5');
  const [loadedCandles, setLoadedCandles] = useState<MarketCandle[]>([]);
  const [loadedError, setLoadedError] = useState('');
  const activeTimeframe = timeframe ?? internalTimeframe;
  const activeMarket = market ?? defaultMarket(broker);
  const displayCandles = candles ?? loadedCandles;
  const displayError = error || loadedError;
  const latestCandle = displayCandles[displayCandles.length - 1] ?? null;
  const chartSummary = latestCandle
    ? `${symbol || 'Ativo'}: ${displayCandles.length} candles no timeframe ${activeTimeframe}. Último fechamento ${latestCandle.close}, abertura ${latestCandle.open}, máxima ${latestCandle.high} e mínima ${latestCandle.low}.`
    : `${symbol || 'Ativo'} sem candles reais para ${activeTimeframe}.`;

  useEffect(() => {
    if (!containerRef.current) return undefined;
    const chart = createChart(containerRef.current, {
      height,
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#8b93a7' },
      grid: { vertLines: { color: 'rgba(139,147,167,.08)' }, horzLines: { color: 'rgba(139,147,167,.08)' } },
      timeScale: { timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: 'rgba(139,147,167,.2)' },
      crosshair: { mode: CrosshairMode.Magnet },
    });
    const series = chart.addCandlestickSeries({
      upColor: '#2ecc71', downColor: '#e74c3c', borderUpColor: '#2ecc71', borderDownColor: '#e74c3c',
      wickUpColor: '#2ecc71', wickDownColor: '#e74c3c',
    });
    chartRef.current = chart;
    seriesRef.current = series;
    setChartReady(true);
    const observer = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(() => chart.applyOptions({ width: containerRef.current?.clientWidth ?? 0 })) : null;
    observer?.observe(containerRef.current);
    return () => {
      observer?.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [height]);

  useEffect(() => {
    if (candles !== undefined || !symbol) return undefined;
    const controller = new AbortController();
    let active = true;
    const load = async () => {
      try {
        const result = await getCandles({ broker, market: activeMarket, symbol: symbol.toUpperCase() }, activeTimeframe, 300, { signal: controller.signal });
        if (active) {
          setLoadedCandles(result.candles);
          setLoadedError('');
        }
      } catch (reason) {
        if (active && !(reason instanceof Error && reason.name === 'MarketApiError' && reason.message === 'Requisição cancelada.')) setLoadedError(reason instanceof Error ? reason.message : 'Candles indisponíveis para esta fonte.');
      }
    };
    void load();
    const timer = window.setInterval(load, 30_000);
    return () => {
      active = false;
      controller.abort();
      window.clearInterval(timer);
    };
  }, [activeMarket, activeTimeframe, broker, candles, symbol]);

  useEffect(() => {
    const series = seriesRef.current;
    if (!series || !chartReady) return;
    const data: CandlestickData[] = displayCandles.map((candle) => ({
      time: candle.time as UTCTimestamp,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));
    series.setData(data);
    if (data.length) chartRef.current?.timeScale().fitContent();
  }, [chartReady, displayCandles]);

  const changeTimeframe = (next: ChartTimeframe) => {
    if (onTimeframeChange) onTimeframeChange(next);
    else setInternalTimeframe(next);
  };

  return (
    <div className="card compact-card price-chart" aria-busy={loading}>
      <div className="section-head">
        <div>
          <h2>{symbol || 'Selecione um ativo'}</h2>
          <span className="muted">Candles OHLC reais · {sourceLabel ?? `${broker.toUpperCase()} · ${activeMarket}`}</span>
        </div>
        <div className="btn-row" role="group" aria-label="Timeframe do gráfico">
          {TIMEFRAMES.map((value) => (
            <button key={value} type="button" className={`btn sm ${value === activeTimeframe ? 'primary' : 'ghost'}`} aria-pressed={value === activeTimeframe} onClick={() => changeTimeframe(value)}>{value}</button>
          ))}
        </div>
      </div>
      {displayError && <div className="hint" role="alert">Gráfico indisponível: {displayError}</div>}
      {loading && !displayCandles.length && <div className="hint" role="status">Carregando candles…</div>}
      {!displayCandles.length && !loading && !displayError && <div className="hint" role="status">Candles reais indisponíveis para esta fonte.</div>}
      <p id="price-chart-summary" className="sr-only">{chartSummary}</p>
      <div ref={containerRef} className="market-chart-canvas" style={{ height }} aria-label={`Gráfico de candles de ${symbol || 'ativo'}`} aria-describedby="price-chart-summary" role="img" tabIndex={0} />
      {displayCandles.length > 0 && <details className="market-chart-data"><summary>Ver dados em tabela</summary><div className="table-scroll market-focus-scroll" role="region" aria-label="Candles em formato tabular" tabIndex={0}><table className="tbl"><caption className="sr-only">Últimos candles reais em formato tabular</caption><thead><tr><th scope="col">Data</th><th scope="col">Abertura</th><th scope="col">Máxima</th><th scope="col">Mínima</th><th scope="col">Fechamento</th><th scope="col">Volume</th></tr></thead><tbody>{displayCandles.slice(-20).reverse().map((candle) => <tr key={candle.time}><td>{new Date(candle.time * 1000).toLocaleString('pt-BR')}</td><td>{candle.open}</td><td>{candle.high}</td><td>{candle.low}</td><td>{candle.close}</td><td>{candle.volume ?? '—'}</td></tr>)}</tbody></table></div></details>}
    </div>
  );
}
