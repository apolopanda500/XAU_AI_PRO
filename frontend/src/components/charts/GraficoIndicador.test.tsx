import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

/*
  O PAINEL DE INDICADOR TEM CONSUMIDOR? (05/10/2026)
  ===================================================
  Função pura sem consumidor é controle morto: a regra do projeto trata isso
  como pior que a ausência. Este arquivo prova que o painel LIGA, que some
  quando ninguem liga, e que sem candles suficientes ele DIZ QUANTOS FALTAM em
  vez de mostrar eixo vazio (eixo vazio parece "o indicador nao achou nada").

  `lightweight-charts` e mockado porque o jsdom nao tem canvas: createChart
  real lancaria. O mock registra o que a biblioteca receberia — que e o que
  interessa: as series e os valores.
*/

const seriesSetData = vi.fn();
const createLineSeries = vi.fn(() => ({ setData: seriesSetData, createPriceLine: vi.fn() }));
const createHistogramSeries = vi.fn(() => ({ setData: seriesSetData }));
let fitContent = vi.fn();

vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addLineSeries: createLineSeries,
    addHistogramSeries: createHistogramSeries,
    timeScale: () => ({ fitContent: () => fitContent() }),
    remove: vi.fn(),
  })),
}));

import { GraficoIndicador } from './GraficoIndicador';
import type { MarketCandle } from '../../lib/marketApi';

function candle(i: number, close: number): MarketCandle {
  return {
    time: 1767225600 + i * 3600,
    open: close,
    high: close + 1,
    low: close - 1,
    close,
    volume: 1000,
  } as MarketCandle;
}

const candles = (n: number) => Array.from({ length: n }, (_, i) => candle(i, 100 + i));

describe('GraficoIndicador — o painel', () => {
  beforeEach(() => {
    seriesSetData.mockClear();
    createLineSeries.mockClear();
    createHistogramSeries.mockClear();
  });

  it('com candles suficientes, monta o canvas do indicador', () => {
    const { container } = render(<GraficoIndicador candles={candles(60)} indicador="rsi" />);
    expect(container.querySelector('[data-indicador="rsi"]')).toBeTruthy();
    expect(container.querySelector('.market-subchart-canvas')).toBeTruthy();
    expect(screen.queryByText(/precisa de/)).toBeNull();
  });

  it('PROVA NEGATIVA: sem candles suficientes, DIZ quantos faltam', () => {
    const { container } = render(<GraficoIndicador candles={candles(10)} indicador="rsi" />);
    expect(container.querySelector('.market-subchart-canvas')).toBeNull();
    // RSI(14) precisa de 15 candles: o texto tem que dizer isso, com o numero.
    expect(screen.getByText(/RSI \(14\) precisa de 15 candles; h\u00e1 10\./)).toBeTruthy();
  });

  it('PROVA NEGATIVA: sem candles nenhum, nao inventa grafico', () => {
    const { container } = render(<GraficoIndicador candles={[]} indicador="macd" />);
    expect(container.querySelector('.market-subchart-canvas')).toBeNull();
    // O requisito e uma CONSTANTE do indicador. A primeira versao imprimia
    // "precisa de -35 candles" (candles.length - 35) e este teste gravou esse
    // numero negativo como esperado. Numero negativo em texto de interface e
    // defeito, nao formato.
    expect(screen.getByText(/MACD \(12, 26, 9\) precisa de 35 candles; h\u00e1 0\./)).toBeTruthy();
    expect(screen.queryByText(/-\d+ candles/)).toBeNull();
  });

  it('MACD incompleto tambem diz o que falta, com o total certo', () => {
    // MACD 12/26/9 precisa de 26 + 9 = 35 candles.
    render(<GraficoIndicador candles={candles(20)} indicador="macd" />);
    expect(screen.getByText(/precisa de 35 candles; h\u00e1 20\./)).toBeTruthy();
  });

  it('RSI manda a serie COM VALORES e sem null no meio', () => {
    render(<GraficoIndicador candles={candles(60)} indicador="rsi" />);
    expect(createLineSeries).toHaveBeenCalled();
    const dados = seriesSetData.mock.calls[0][0] as Array<{ value: number }>;
    expect(dados.length).toBeGreaterThan(0);
    for (const p of dados) expect(p.value).not.toBeNull();
  });

  it('MACD desenha as tres series: histograma, macd e sinal', () => {
    render(<GraficoIndicador candles={candles(80)} indicador="macd" />);
    expect(createHistogramSeries).toHaveBeenCalledTimes(1);
    expect(createLineSeries).toHaveBeenCalledTimes(2);
    // 1a serie = macd, 2a = sinal, e o histograma ja foi montado antes.
    expect(seriesSetData).toHaveBeenCalledTimes(3);
  });

  it('o rotulo do RSI diz o periodo', () => {
    const { container } = render(<GraficoIndicador candles={candles(60)} indicador="rsi" />);
    expect(container.querySelector('.market-subchart-head')?.textContent).toContain('RSI (14)');
  });

  it('o rotulo do MACD diz os tres periodos, porque o numero muda com eles', () => {
    const { container } = render(<GraficoIndicador candles={candles(80)} indicador="macd" />);
    const head = container.querySelector('.market-subchart-head')?.textContent ?? '';
    expect(head).toContain('MACD (12, 26, 9)');
    // e nomeia as tres series, senao tres linhas coloridas nao dizem nada
    expect(head).toContain('macd');
    expect(head).toContain('sinal');
    expect(head).toContain('histograma');
  });
});