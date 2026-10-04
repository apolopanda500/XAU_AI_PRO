import { useEffect, useRef, useState } from 'react';
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type UTCTimestamp,
  ColorType,
  CrosshairMode,
} from 'lightweight-charts';
import {
  getCandles,
  type MarketBroker,
  type MarketCandle,
  type MarketKind,
} from '../../lib/marketApi';

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
  // Marcadores de sinal do modelo (BUY abaixo da barra, SELL acima).
  // Tempo em segundos (mesma base dos candles) e texto curto com a
  // confianca — o operador ve ONDE o modelo decidiu, nao so o numero.
  markers?: Array<{ time: number; signal: string; text?: string }>;
  // Linhas de preco (posicoes abertas: entrada, SL, TP). So leitura: o
  // grafico mostra onde esta protegido, nao edita a ordem por arrasto.
  // Com `ticket` + `kind` + `onMoveLine`, SL/TP viram arrastaveis estilo
  // MT5: soltar aplica na hora via /api/trade/modify-position.
  lines?: Array<{ price: number; color: string; title: string; ticket?: number | string; kind?: 'sl' | 'tp' | 'entrada' }>;
  onMoveLine?: (ticket: number | string, kind: 'sl' | 'tp', price: number) => void;
  // Medias moveis exponenciais 12/26 calculadas DOS candles reais exibidos.
  // Indicador derivavel, sem fonte externa: se faltar candle, some a linha.
  ema?: boolean;
};

export function emaValores(fechamentos: number[], periodo: number): Array<number | null> {
  if (periodo < 2 || !fechamentos.length) return fechamentos.map(() => null);
  const k = 2 / (periodo + 1);
  const saida: Array<number | null> = [];
  let anterior: number | null = null;
  fechamentos.forEach((preco, i) => {
    if (i < periodo - 1) {
      saida.push(null);
    } else if (i === periodo - 1) {
      const soma = fechamentos.slice(0, periodo).reduce((s, v) => s + v, 0);
      anterior = soma / periodo;
      saida.push(anterior);
    } else {
      anterior = preco * k + (anterior ?? preco) * (1 - k);
      saida.push(anterior);
    }
  });
  return saida;
}

function defaultMarket(broker: MarketBroker): MarketKind {
  return broker === 'mt5' ? 'forex' : 'crypto-spot';
}

export default function PriceChart({
  symbol = '',
  broker = 'mt5',
  market,
  height = 360,
  candles,
  timeframe,
  onTimeframeChange,
  loading = false,
  error = '',
  sourceLabel,
  markers = [],
  lines = [],
  ema = false,
  onMoveLine,
}: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'>>(null);
  const linhasRef = useRef<Array<ReturnType<ISeriesApi<'Candlestick'>['createPriceLine']>>>([]);
  const emaRef = useRef<Array<ISeriesApi<'Line'>>>([]);
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
      grid: {
        vertLines: { color: 'rgba(139,147,167,.08)' },
        horzLines: { color: 'rgba(139,147,167,.08)' },
      },
      timeScale: { timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: 'rgba(139,147,167,.2)' },
      crosshair: { mode: CrosshairMode.Magnet },
    });
    const series = chart.addCandlestickSeries({
      upColor: '#2ecc71',
      downColor: '#e74c3c',
      borderUpColor: '#2ecc71',
      borderDownColor: '#e74c3c',
      wickUpColor: '#2ecc71',
      wickDownColor: '#e74c3c',
    });
    chartRef.current = chart;
    seriesRef.current = series;
    setChartReady(true);
    const observer =
      typeof ResizeObserver !== 'undefined'
        ? new ResizeObserver(() =>
            chart.applyOptions({ width: containerRef.current?.clientWidth ?? 0 }),
          )
        : null;
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
        const result = await getCandles(
          { broker, market: activeMarket, symbol: symbol.toUpperCase() },
          activeTimeframe,
          300,
          { signal: controller.signal },
        );
        if (active) {
          setLoadedCandles(result.candles);
          setLoadedError('');
        }
      } catch (reason) {
        if (
          active &&
          !(
            reason instanceof Error &&
            reason.name === 'MarketApiError' &&
            reason.message === 'Requisição cancelada.'
          )
        )
          setLoadedError(
            reason instanceof Error ? reason.message : 'Candles indisponíveis para esta fonte.',
          );
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
    // Sinais do modelo sobre as barras. So BUY/SELL entram; NEUTRAL e
    // recusa nao marcam o grafico (marcador sem decisao e ruido).
    const times = new Set(data.map((d) => d.time));
    series.setMarkers(
      markers
        .filter((m) => (m.signal === 'BUY' || m.signal === 'SELL') && times.has(m.time as UTCTimestamp))
        .map((m) => ({
          time: m.time as UTCTimestamp,
          position: m.signal === 'BUY' ? 'belowBar' : 'aboveBar',
          color: m.signal === 'BUY' ? '#2ecc71' : '#e74c3c',
          shape: m.signal === 'BUY' ? 'arrowUp' : 'arrowDown',
          text: m.text ?? m.signal,
        })),
    );
    // Linhas de posicao: recriadas a cada render (a API nao atualiza em
    // lote — remover e recriar e o caminho documentado).
    for (const antiga of linhasRef.current) {
      try {
        series.removePriceLine(antiga);
      } catch {
        /* linha de serie anterior, ja descartada */
      }
    }
    linhasRef.current = lines
      .filter((l) => Number.isFinite(l.price))
      .map((l) =>
        series.createPriceLine({
          price: l.price,
          color: l.color,
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: l.title,
        }),
      );
    const emaSerie = emaRef.current;
    if (ema && chartRef.current) {
      const fechas = data.map((d) => d.close);
      const pares: Array<number[]> = [
        emaValores(fechas, 12),
        emaValores(fechas, 26),
      ];
      const cores = ['#f0b90b', '#a78bfa'];
      pares.forEach((valores, idx) => {
        const pontos = data
          .map((d, i) => (valores[i] === null ? null : { time: d.time, value: valores[i] as number }))
          .filter((p): p is { time: UTCTimestamp; value: number } => p !== null);
        const existente = emaSerie[idx];
        if (existente) {
          existente.setData(pontos);
        } else if (pontos.length) {
          emaSerie[idx] = chartRef.current!.addLineSeries({
            color: cores[idx],
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
          });
          emaSerie[idx].setData(pontos);
        }
      });
    } else {
      for (const s of emaSerie) {
        try {
          chartRef.current?.removeSeries(s);
        } catch {
          /* ja removida */
        }
      }
      emaRef.current = [];
    }
    if (data.length) chartRef.current?.timeScale().fitContent();
  }, [chartReady, displayCandles, markers, lines, ema]);

  // Arrastar SL/TP estilo MT5. So linhas com ticket+kind sao moveis; a
  // entrada nunca arrasta. O preco segue o mouse via rAF (sem travar) e
  // SOLTAR aplica via onMoveLine — igual ao terminal, sem modal no meio.
  useEffect(() => {
    const el = containerRef.current;
    const series = seriesRef.current;
    if (!el || !series || !chartReady || !onMoveLine) return undefined;
    const moveis = lines.filter(
      (l): l is { price: number; color: string; title: string; ticket: number | string; kind: 'sl' | 'tp' } =>
        (l.kind === 'sl' || l.kind === 'tp') && l.ticket !== undefined,
    );
    if (!moveis.length) return undefined;
    let alvo: { ticket: number | string; kind: 'sl' | 'tp' } | null = null;
    let precoSessao = 0;
    let frame = 0;
    const yParaPreco = (clientY: number): number | null => {
      const rect = el.getBoundingClientRect();
      try {
        const p = series.coordinateToPrice(clientY - rect.top);
        return typeof p === 'number' && Number.isFinite(p) ? p : null;
      } catch {
        return null;
      }
    };
    const perto = (clientY: number) => {
      const p = yParaPreco(clientY);
      if (p === null) return null;
      let melhor: typeof alvo & { dist: number } | null = null;
      for (const l of moveis) {
        const dist = Math.abs(l.price - p);
        const tol = Math.max(Math.abs(p) * 0.002, 0.01);
        if (dist <= tol && (!melhor || dist < melhor.dist)) melhor = { ticket: l.ticket, kind: l.kind, dist };
      }
      return melhor;
    };
    const redesenhar = () => {
      frame = 0;
      if (!alvo) return;
      for (let i = 0; i < linhasRef.current.length; i++) {
        const base = moveis[i];
        if (!base || base.ticket !== alvo.ticket || base.kind !== alvo.kind) continue;
        try {
          series.removePriceLine(linhasRef.current[i]);
        } catch {
          /* serie anterior */
        }
        try {
          linhasRef.current[i] = series.createPriceLine({
            price: precoSessao,
            color: base.color,
            lineWidth: 2,
            lineStyle: 0,
            axisLabelVisible: true,
            title: base.title,
          });
        } catch {
          /* fora da escala visivel */
        }
      }
    };
    const aoMover = (e: MouseEvent) => {
      if (!alvo) {
        el.style.cursor = perto(e.clientY) ? 'ns-resize' : '';
        return;
      }
      const p = yParaPreco(e.clientY);
      if (p === null) return;
      precoSessao = p;
      if (!frame) frame = window.requestAnimationFrame(redesenhar);
    };
    const aoSoltar = (e: MouseEvent) => {
      if (!alvo) return;
      const final = alvo;
      alvo = null;
      el.style.cursor = '';
      if (frame) {
        window.cancelAnimationFrame(frame);
        frame = 0;
      }
      const p = yParaPreco(e.clientY);
      if (p !== null) onMoveLine(final.ticket, final.kind, Math.round(p * 100) / 100);
    };
    const aoPressionar = (e: MouseEvent) => {
      const achou = perto(e.clientY);
      if (achou) {
        alvo = { ticket: achou.ticket, kind: achou.kind };
        const atual = moveis.find((l) => l.ticket === achou.ticket && l.kind === achou.kind);
        precoSessao = atual ? atual.price : 0;
        el.style.cursor = 'ns-resize';
        e.preventDefault();
      }
    };
    el.addEventListener('mousedown', aoPressionar);
    window.addEventListener('mousemove', aoMover);
    window.addEventListener('mouseup', aoSoltar);
    return () => {
      el.removeEventListener('mousedown', aoPressionar);
      window.removeEventListener('mousemove', aoMover);
      window.removeEventListener('mouseup', aoSoltar);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, [chartReady, lines, onMoveLine]);

  const changeTimeframe = (next: ChartTimeframe) => {
    if (onTimeframeChange) onTimeframeChange(next);
    else setInternalTimeframe(next);
  };

  return (
    <div className="card compact-card price-chart" aria-busy={loading}>
      <div className="section-head">
        <div>
          <h2>{symbol || 'Selecione um ativo'}</h2>
          <span className="muted">
            Candles OHLC reais · {sourceLabel ?? `${broker.toUpperCase()} · ${activeMarket}`}
          </span>
        </div>
        <div className="btn-row" role="group" aria-label="Timeframe do gráfico">
          {TIMEFRAMES.map((value) => (
            <button
              key={value}
              type="button"
              className={`btn sm ${value === activeTimeframe ? 'primary' : 'ghost'}`}
              aria-pressed={value === activeTimeframe}
              onClick={() => changeTimeframe(value)}
            >
              {value}
            </button>
          ))}
        </div>
      </div>
      {displayError && (
        <div className="hint" role="alert">
          Gráfico indisponível: {displayError}
        </div>
      )}
      {loading && !displayCandles.length && (
        <div className="hint" role="status">
          Carregando candles…
        </div>
      )}
      {!displayCandles.length && !loading && !displayError && (
        <div className="hint" role="status">
          Candles reais indisponíveis para esta fonte.
        </div>
      )}
      <p id="price-chart-summary" className="sr-only">
        {chartSummary}
      </p>
      <div
        ref={containerRef}
        className="market-chart-canvas"
        style={{ height }}
        aria-label={`Gráfico de candles de ${symbol || 'ativo'}`}
        aria-describedby="price-chart-summary"
        role="img"
        tabIndex={0}
      />
      {displayCandles.length > 0 && (
        <details className="market-chart-data">
          <summary>Ver dados em tabela</summary>
          <div
            className="table-scroll market-focus-scroll"
            role="region"
            aria-label="Candles em formato tabular"
            tabIndex={0}
          >
            <table className="tbl">
              <caption className="sr-only">Últimos candles reais em formato tabular</caption>
              <thead>
                <tr>
                  <th scope="col">Data</th>
                  <th scope="col">Abertura</th>
                  <th scope="col">Máxima</th>
                  <th scope="col">Mínima</th>
                  <th scope="col">Fechamento</th>
                  <th scope="col">Volume</th>
                </tr>
              </thead>
              <tbody>
                {displayCandles
                  .slice(-20)
                  .reverse()
                  .map((candle) => (
                    <tr key={candle.time}>
                      <td>{new Date(candle.time * 1000).toLocaleString('pt-BR')}</td>
                      <td>{candle.open}</td>
                      <td>{candle.high}</td>
                      <td>{candle.low}</td>
                      <td>{candle.close}</td>
                      <td>{candle.volume ?? '—'}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  );
}
