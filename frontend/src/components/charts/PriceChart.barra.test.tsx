// @vitest-environment jsdom
// A BARRA DO GRAFICO: tipo, indicadores, desfazer e refazer (06/10/2026).
//
// O DONO PEDIU
// ============
// A barra da XM: `1h · tipo de grafico · Indicadores · layout · + · desfazer ·
// refazer`. E o defeito que ele REPORTOU no mesmo ciclo e que motivou estes
// testes: "o botao EMA esta travado de cima azul, so funciona o de baixo".
//
// A ARMADILHA DESTES TESTES
// =========================
// `aria-pressed` NAO prova que um botao funciona. O botao EMA mudava
// `aria-pressed` e nao mudava a tela: o estado vivia no pai e o pai nunca era
// avisado. Estes testes medem o ESTADO que o grafico recebe, e nao o atributo.
//
// O mock do lightweight-charts registra QUAL SERIE foi criada. Trocar o tipo de
// grafico so e real se `addCandlestickSeries`/`addLineSeries`/`addAreaSeries`
// mudarem de verdade — e nao se a cor do botao mudar.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { MarketCandle } from '../../lib/marketApi';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

/* ---------------------------------------------------------------------------
   O DUBLE DO lightweight-charts.
   Registra as séries criadas, que é o que a troca de tipo de grafico produz.
--------------------------------------------------------------------------- */
const criado = { candle: 0, linha: 0, area: 0 };
const seriesAtual = { ref: null as unknown };
const seriesComDados: Array<{ setData: ReturnType<typeof vi.fn> }> = [];
/**
 * Quantas vezes o grafico foi ENQUADRADO.
 *
 * E a medicao do defeito "a visao volta sozinha": `fitContent` reenquadra, e ele
 * nao pode rodar a cada cotacao.
 */
const fitContentChamadas = { n: 0 };

vi.mock('lightweight-charts', () => {
  const criarSerie = (nome: 'candle' | 'linha' | 'area') => {
    criado[nome] += 1;
    const serie = {
      setData: vi.fn(),
      applyOptions: vi.fn(),
      createPriceLine: vi.fn(() => ({ remove: vi.fn() })),
      removePriceLine: vi.fn(),
      coordinateToPrice: vi.fn(() => 0),
      setMarkers: vi.fn(),
      remove: vi.fn(),
      __tipo: nome,
    };
    seriesAtual.ref = serie;
    seriesComDados.push(serie);
    return serie;
  };
  return {
    createChart: vi.fn(() => ({
      addCandlestickSeries: vi.fn(() => criarSerie('candle')),
      addLineSeries: vi.fn(() => criarSerie('linha')),
      addAreaSeries: vi.fn(() => criarSerie('area')),
      addHistogramSeries: vi.fn(() => criarSerie('candle')),
      removeSeries: vi.fn(),
      priceScale: vi.fn(() => ({ applyOptions: vi.fn() })),
      subscribeCrosshairMove: vi.fn(),
      unsubscribeCrosshairMove: vi.fn(),
      applyOptions: vi.fn(),
      remove: vi.fn(),
timeScale: vi.fn(() => ({
        fitContent: vi.fn(() => {
          fitContentChamadas.n += 1;
        }),
        scrollToPosition: vi.fn(),
        subscribeVisibleTimeRangeChange: vi.fn(() => ({ unsubscribe: vi.fn() })),
      })),
    })),
    ColorType: { Solid: 'solid', Vertical: 'vertical' },
    CrosshairMode: { Magnet: 0, Normal: 1 },
  };
});

vi.mock('../QuantumClock', () => ({ default: () => null }));
vi.mock('../SeletorFuso', () => ({ default: () => null }));

const { default: PriceChart } = await import('./PriceChart');

/**
 * 40 candles no formato COMPLETO de `MarketCandle`.
 *
 * Nao e `as never[]`: com esse cast o TypeScript impede o proprio teste de
 * mexer num candle (o `close` de `never[]` nao existe), e foi assim que a
 * construcao do candle com cotacao nova deixou de compilar. Tipar de verdade
 * deixa o teste montar o cenario que ele mede.
 */
const CANDLES: MarketCandle[] = Array.from({ length: 40 }, (_, i) => ({
  time: 1788000000 + i * 3600,
  open: 86000 + i,
  high: 86050 + i,
  low: 85950 + i,
  close: 86020 + i,
  volume: 12,
  broker: 'mt5' as MarketCandle['broker'],
  market: 'other' as MarketCandle['market'],
  symbol: 'BTCUSD',
  source: 'mt5_gateway',
  received_at: '2026-10-04T12:00:00.000Z',
  provider_timestamp: '2026-10-04T12:00:00.000Z',
  execucao: false,
  sinal: null,
}));

beforeEach(() => {
  criado.candle = 0;
  criado.linha = 0;
  criado.area = 0;
  seriesComDados.length = 0;
  fitContentChamadas.n = 0;
});

afterEach(() => cleanup());

const botao = (nome: string) => screen.getByRole('button', { name: nome });

/** O botao esta DESABILITADO de verdade, e nao so apagado. */
const desabilitado = (nome: string): boolean =>
  (screen.getByRole('button', { name: nome }) as HTMLButtonElement).disabled;

const setDataDe = (serie: unknown): ReturnType<typeof vi.fn> =>
  (serie as { setData: ReturnType<typeof vi.fn> }).setData;

/** A ultima chamada de `setData`, que e o desenho atual. */
const ultimoSetData = (serie: unknown): unknown[] => {
  const chamadas = setDataDe(serie).mock.calls;
  return chamadas[chamadas.length - 1][0] as unknown[];
};

describe('o grafico DESPINHA os dados na serie (o defeito do app instalado)', () => {
  /*
    MEDIDO (06/10/2026): com o app instalado, o grafico FICOU VAZIO — nenhuma
    vela, nenhuma linha, so o eixo.

    A CAUSA e um deadlock entre dois efeitos. A serie de preco e criada por um
    efeito que depende de `chartReady`. O efeito que chama `setData` dependia so
    de `chartReady` e `displayCandles`, e saia com `if (!series) return`. Na
    primeira passagem a serie ainda nao existia, ele saiu, e NAO VOLTOU a rodar —
    porque `displayCandles` nao tinha mudado. A serie ficava vazia para sempre.

    Este teste renderiza de verdade e mede a chamada de `setData`. Sem ele, a
    suite inteira passa com o grafico em branco — que e o estado que o dono viu.
  */
  it('os dados chegam a serie de preco, e nao ficam no vazio', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} />);
    // A serie de candle foi criada...
    expect(criado.candle).toBeGreaterThan(0);
    // ...e recebeu os 40 candles. Uma serie vazia e um grafico em branco.
    const serieDeCandle = seriesComDados.find((s) => (s as { __tipo?: string }).__tipo === 'candle');
    expect(serieDeCandle).toBeTruthy();
    expect(setDataDe(serieDeCandle)).toHaveBeenCalled();
    const recebido = ultimoSetData(serieDeCandle);
    expect(Array.isArray(recebido)).toBe(true);
    expect(recebido.length).toBe(CANDLES.length);
  });

  it('PROVA NEGATIVA: trocar o tipo redesenha os dados na serie NOVA', () => {
    /*
    Se a serie nova nascesse vazia, o operador trocaria de candle para linha e
    veria um grafico em branco — e o botao pareceria quebrado. E a mesma classe
    de defeito do efeito acima: criar a serie e desenhar nela sao dois passos, e
    o segundo precisa ser disparado pelo primeiro.
    */
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} />);
    const candlesAntes = seriesComDados.length;

    fireEvent.click(botao('Linha'));

    expect(seriesComDados.length).toBeGreaterThan(candlesAntes);
    const serieDeLinha = seriesComDados.filter((s) => (s as { __tipo?: string }).__tipo === 'linha').slice(-1)[0];
    expect(serieDeLinha).toBeTruthy();
    expect(setDataDe(serieDeLinha)).toHaveBeenCalled();
    expect(ultimoSetData(serieDeLinha).length).toBe(CANDLES.length);
  });
});

describe('a visao do operador NAO volta sozinha (defeito de 06/10/2026)', () => {
  /*
    MEDIDO NO APP INSTALADO: o dono reportou "quando eu desloco, depois ele volta
    para onde esta fixo sem eu apertar nada".

    A CAUSA: `timeScale().fitContent()` era chamado a CADA `setData`, e `setData`
    roda a cada candle novo — que chega a cada cotacao. O operador arrastava para
    ver um ponto, o proximo candle chegava, e a visao voltava para o fim.

    `fitContent` enquadra o grafico quando o CONJUNTO DE CANDLES MUDA (trocar de
    ativo, de timeframe, de tipo de grafico). Ele nao deve rodar quando so o
    ultimo candle mudou de preco.

    Este teste conta as chamadas: um `fitContent` por mudanca de conjunto, e NAO
    um por atualizacao de valor.
  */
  it('atualizar o ULTIMO candle nao reenquadra a visao', () => {
    const { rerender } = render(<PriceChart symbol="BTCUSD" candles={CANDLES} />);
    const enquadrarAntes = contagemFitContent();

    // Chega uma cotacao nova: o MESMO conjunto de horarios, o ultimo candle com
    // preco diferente. E o que chega a cada tick.
    const comCotacao = CANDLES.map((c, i) =>
      i === CANDLES.length - 1 ? { ...c, close: c.close + 25 } : c,
    ) as never[];
    rerender(<PriceChart symbol="BTCUSD" candles={comCotacao} />);

    // O grafico ATUALIZOU (o dado novo entrou)...
    expect(contagemFitContent()).toBe(enquadrarAntes);
    // ...e a visao NAO voltou sozinha.
  });

  it('PROVA NEGATIVA: trocar o timeframe REENQUADRA, porque e conjunto novo', () => {
    const { rerender } = render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M5" />);
    const antes = contagemFitContent();
    // Outro timeframe, outros candles: o operador pediu outro enquadramento.
    rerender(<PriceChart symbol="BTCUSD" candles={CANDLES.slice(0, 20)} timeframe="H1" />);
    expect(contagemFitContent()).toBeGreaterThan(antes);
  });
});

/** Quantas vezes o grafico foi reenquadrado desde o inicio do teste. */
function contagemFitContent(): number {
  return Object.values(fitContentChamadas).reduce((acc, n) => acc + n, 0);
}

describe('a barra do grafico — tipo de grafico', () => {
  it('comeca em CANDLES e mostra os tres tipos', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} />);
    expect(botao('Candles').getAttribute('aria-pressed')).toBe('true');
    expect(botao('Linha').getAttribute('aria-pressed')).toBe('false');
    expect(botao('Área').getAttribute('aria-pressed')).toBe('false');
    // E a serie de candle foi a primeira criada.
    expect(criado.candle).toBeGreaterThan(0);
    expect(criado.linha).toBe(0);
  });

  it('PROVA NEGATIVA: trocar para LINHA cria a serie de linha, e remove a de candle', () => {
    /*
    Este e o teste que impede o botao decorativo. Se a troca so mudasse a cor, o
    `aria-pressed` passaria e o grafico continuaria desenhando candle.

    `addCandlestickSeries` e `addLineSeries` sao METODOS DIFERENTES: nao ha
    `applyOptions` que transforme candle em linha. Por isso o grafico TEM de
    criar outra serie — e remover a antiga, senao a vela continua por cima da
    linha.
    */
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} />);
    const candlesAntes = criado.candle;
    expect(criado.linha).toBe(0);

    fireEvent.click(botao('Linha'));

    expect(criado.linha).toBeGreaterThan(0);
    expect(botao('Linha').getAttribute('aria-pressed')).toBe('true');
    expect(botao('Candles').getAttribute('aria-pressed')).toBe('false');
    // A serie de candle NAO pode continuar viva: seria o sintoma de "troquei
    // para linha e continuei vendo candle".
    expect(criado.candle).toBe(candlesAntes);
    expect((seriesAtual.ref as { __tipo: string }).__tipo).toBe('linha');
  });

  it('trocar para AREA cria a serie de area', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} />);
    fireEvent.click(botao('Área'));
    expect(criado.area).toBeGreaterThan(0);
    expect(botao('Área').getAttribute('aria-pressed')).toBe('true');
    expect((seriesAtual.ref as { __tipo: string }).__tipo).toBe('area');
  });
});

describe('a barra do grafico — desfazer e refazer', () => {
  it('comecam DESABILITADOS, porque nao ha nada para desfazer', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} />);
    // Botao que parece funcionar sem funcionar e o defeito do EMA. Sem passo,
    // o botao esta desabilitado e o `title` diz que nao ha o que desfazer.
    expect(desabilitado('Desfazer')).toBe(true);
    expect(desabilitado('Refazer')).toBe(true);
    expect(botao('Desfazer').getAttribute('title')).toBe('Nada para desfazer');
  });

  it('ligar um indicador HABILITA o desfazer, e ele volta o estado', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} />);
    expect(desabilitado('Desfazer')).toBe(true);

    fireEvent.click(botao('RSI'));
    expect(botao('RSI').getAttribute('aria-pressed')).toBe('true');

    // Agora ha o que desfazer, e o botao diz O QUE.
    const desfazer = botao('Desfazer');
    expect(desabilitado('Desfazer')).toBe(false);
    expect(desfazer.getAttribute('title')).toContain('ligar RSI');

    // E o efeito e real: o RSI DESLIGA.
    fireEvent.click(desfazer);
    expect(botao('RSI').getAttribute('aria-pressed')).toBe('false');
  });

  it('PROVA NEGATIVA: o desfazer volta o TIPO, nao so o indicador', () => {
    /*
    O teste que impede o desfazer de meio funcionar. Se ele so voltasse o
    indicador, trocar o tipo e desfazer deixaria o grafico em linha com o
    botao "Candles" marcado — e o operador veria um botao que mente.
    */
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} />);
    fireEvent.click(botao('Linha'));
    expect(botao('Linha').getAttribute('aria-pressed')).toBe('true');

    fireEvent.click(botao('Desfazer'));

    expect(botao('Candles').getAttribute('aria-pressed')).toBe('true');
    expect(botao('Linha').getAttribute('aria-pressed')).toBe('false');
  });

  it('refazer volta ao estado depois, e volta a desabilitar', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} />);
    fireEvent.click(botao('MACD'));
    fireEvent.click(botao('Desfazer'));
    expect(botao('MACD').getAttribute('aria-pressed')).toBe('false');
    expect(desabilitado('Refazer')).toBe(false);
    expect(botao('Refazer').getAttribute('title')).toContain('ligar MACD');

    fireEvent.click(botao('Refazer'));
    expect(botao('MACD').getAttribute('aria-pressed')).toBe('true');
    // E o refazer esgota: um segundo clique nao faz nada.
    expect(desabilitado('Refazer')).toBe(true);
  });

  it('PROVA NEGATIVA: mexer depois de desfazer DESCARTA o refazer', () => {
    // Sem isso, o "refazer" descreveria um caminho que deixou de existir: o
    // operador desfazia, ligava outro indicador, e o refazer pulava por cima.
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} />);
    fireEvent.click(botao('RSI'));
    fireEvent.click(botao('Desfazer'));
    expect(desabilitado('Refazer')).toBe(false);

    fireEvent.click(botao('EMA'));
    expect(desabilitado('Refazer')).toBe(true);
  });

  it('varios passos: desfazer volta um de cada vez, na ordem', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} />);
    fireEvent.click(botao('Linha'));
    fireEvent.click(botao('RSI'));
    fireEvent.click(botao('EMA'));
    expect(botao('EMA').getAttribute('aria-pressed')).toBe('true');
    expect(botao('RSI').getAttribute('aria-pressed')).toBe('true');

    fireEvent.click(botao('Desfazer'));
    expect(botao('EMA').getAttribute('aria-pressed')).toBe('false');
    expect(botao('RSI').getAttribute('aria-pressed')).toBe('true');
    expect(botao('Linha').getAttribute('aria-pressed')).toBe('true');

    fireEvent.click(botao('Desfazer'));
    expect(botao('RSI').getAttribute('aria-pressed')).toBe('false');
    expect(botao('Linha').getAttribute('aria-pressed')).toBe('true');

    fireEvent.click(botao('Desfazer'));
    expect(botao('Linha').getAttribute('aria-pressed')).toBe('false');
    expect(botao('Candles').getAttribute('aria-pressed')).toBe('true');
    expect(desabilitado('Desfazer')).toBe(true);
  });
});


