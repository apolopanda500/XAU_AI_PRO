import { useEffect, useRef } from 'react';
import { createChart, type IChartApi, type ISeriesApi, type UTCTimestamp } from 'lightweight-charts';
import type { MarketCandle } from '../../lib/marketApi';
import { rsiValores, macdValores } from './PriceChart';

/*
  PAINEL DE INDICADOR ABAIXO DO PRECO (05/10/2026)
  ==================================================
  MEDIDO: `lightweight-charts` esta na **4.2.3**, e pane (varias series em
  quadros empilhados dentro do mesmo chart) so existe a partir da **v5**. Entao
  RSI e MACD nao podem virar pane aqui sem trocar a biblioteca no meio do
  ciclo.

  A solucao medida e a mesma do MT5: um segundo canvas DEBAIXO do preco, com o
  proprio eixo. Sem depender de recurso inexistente, e sem subir a dependencia
  como efeito colateral de um item de tela.

  Os valores vem das MESMAS funcoes puras que os testes exercitam
  (`rsiValores` / `macdValores`), e dos CANDLES REAIS EXIBIDOS: nada de
  indicador vindo de servidor. `null` vira buraco, nunca zero.
*/

export type IndicadorId = 'rsi' | 'macd';

type Props = {
  candles: MarketCandle[];
  /** `rsi` desenha uma linha 0..100; `macd` desenha macd, sinal e histograma. */
  indicador: IndicadorId;
  altura?: number;
};

/** Ponto de serie alinhado pelo indice do candle. `null` fica `null`. */
function paraSerie(candles: MarketCandle[], valor: number | null, i: number) {
  return {
    time: Math.floor(candles[i].time) as UTCTimestamp,
    value: valor,
  };
}

export function GraficoIndicador({ candles, indicador, altura = 132 }: Props) {
  const alvoRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const alvo = alvoRef.current;
    if (!alvo || candles.length < 2) return undefined;

    const chart = createChart(alvo, {
      height: altura,
      layout: {
        background: { color: 'transparent' },
        textColor: '#8b98a9',
        fontSize: 10,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: 'rgba(139,152,169,0.12)' },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, visible: false },
      crosshair: { mode: 0 },
      handleScale: { axisPressedMouseMove: false },
    });
    chartRef.current = chart;

    const fecha = candles.map((c) => c.close);

    if (indicador === 'rsi') {
      const serie: ISeriesApi<'Line'> = chart.addLineSeries({
        color: '#5aa9e6',
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: true,
      });
      const rsi = rsiValores(fecha, 14);
      serie.setData(
        rsi
          .map((v, i) => paraSerie(candles, v, i))
          .filter((p) => p.value !== null) as never,
      );
      // As faixas 70 e 30 sao o que da leitura ao numero. Um RSI sem elas e
      // um numero solto na tela.
      serie.createPriceLine({
        price: 70,
        color: 'rgba(214,106,106,0.5)',
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: 'sobrecomprado',
      });
      serie.createPriceLine({
        price: 30,
        color: 'rgba(106,190,150,0.5)',
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: 'sobrevendido',
      });
    } else {
      const histo: ISeriesApi<'Histogram'> = chart.addHistogramSeries({
        priceFormat: { type: 'price', precision: 5, minMove: 0.00001 },
        priceLineVisible: false,
        lastValueVisible: false,
      });
      const macd = macdValores(fecha);
      histo.setData(
        macd.histograma
          .map((v, i) =>
            v === null
              ? null
              : {
                  time: Math.floor(candles[i].time) as UTCTimestamp,
                  value: v,
                  color: v >= 0 ? 'rgba(106,190,150,0.55)' : 'rgba(214,106,106,0.55)',
                },
          )
          .filter(Boolean) as never,
      );
      const linhaMacd: ISeriesApi<'Line'> = chart.addLineSeries({
        color: '#5aa9e6',
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      const linhaSinal: ISeriesApi<'Line'> = chart.addLineSeries({
        color: '#e6a54a',
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      linhaMacd.setData(
        macd.macd.map((v, i) => paraSerie(candles, v, i)).filter((p) => p.value !== null) as never,
      );
      linhaSinal.setData(
        macd.sinal.map((v, i) => paraSerie(candles, v, i)).filter((p) => p.value !== null) as never,
      );
    }

    chart.timeScale().fitContent();
    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [candles, indicador, altura]);

  /*
    QUANTOS CANDLES CADA INDICADOR EXIGE — e o piso, nunca a diferenca.

    A primeira versao escrevia `candles.length - 35`, que com 0 candles
    imprimia "precisa de -35 candles": numero negativo num texto de interface.
    O teste chegou a cravar esse defeito como se fosse o esperado. O requisito
    e uma CONSTANTE do indicador, e ele nao muda conforme o que chegou.
  */
  const rotulo = indicador === 'rsi' ? 'RSI (14)' : 'MACD (12, 26, 9)';
  const minimo = indicador === 'rsi' ? 15 : 35;
  const semDados = candles.length < minimo;

  return (
    <div className="market-subchart" data-indicador={indicador}>
      <div className="market-subchart-head">
        <span className="mono">{rotulo}</span>
        {indicador === 'macd' && (
          <span className="muted">
            <span style={{ color: '#5aa9e6' }}>macd</span>
            {' · '}
            <span style={{ color: '#e6a54a' }}>sinal</span>
            {' · '}
            <span className="muted">histograma</span>
          </span>
        )}
      </div>
      {semDados ? (
        <div className="market-subchart-vazio muted">
          {rotulo} precisa de {minimo} candles; há {candles.length}.
        </div>
      ) : (
        <div ref={alvoRef} className="market-subchart-canvas" />
      )}
    </div>
  );
}

export default GraficoIndicador;