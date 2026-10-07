// @vitest-environment jsdom
/*
  AS PONTAS, O ESTILO E O DESFAZER (06/10/2026)
  ===============================================
  MEDIDO nas capturas da XM (20:31, 20:33, 20:35, 20:36, 20:37):

    - 20:31 e 20:35  a linha de tendencia tem DOIS CIRCULOS nas pontas, e
                     arrastar um deles move a linha. Sem isso a linha existe mas
                     nao serve para AJUSTAR O STOP, que e o uso que o dono
                     descreveu.
    - 20:35 e 20:36  a paleta, a espessura (1 a 4 px) e o cadeado aparecem na
                     barra flutuante SOBRE o desenho escolhido.
    - 20:37          o `Ctrl + Z` desfaz e o botao ↶ acende.

  O DEFEITO QUE ESTES TESTES PROVAM QUE FOI CORRIGIDO
  ====================================================
  A camada dos desenhos renderizava SO com `ferramenta !== 'nenhuma'`, e o
  `aoClicar` desarma a ferramenta ao FECHAR o desenho. Ou seja: a linha que o
  operador acabava de clicar aparecia por um frame e SUMIA — enquanto o contador
  continuava dizendo "1 desenho".

  E o AGENTS.md 5 na sua forma mais cruel: o nome (contador) e a realidade
  (tela vazia) discordam, e o operador culparia o proprio clique. Marcaria o
  stop num desenho que o grafico jurava ter e que nao estava la.

  estes testes medem o DOM (o que o operador ve), nao o estado do React. Um
  `desenhos.length > 0` no estado passaria com a tela vazia.
*/
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { MarketCandle } from '../../lib/marketApi';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

/*
  O DUBLE DO lightweight-charts.

  A conversao preco <-> pixel e a MESMA conta nos dois sentidos e o ALCANCE E O
  MESMO, como em `PriceChart.ordem.test.tsx`: com limites diferentes em cada
  sentido, a ponta sairia `-9999` enquanto o clique naquele pixel ainda devolveria
  preco — e o teste passaria por um motivo errado.
*/
const TOPO = 86_100;
const BASE = 85_300;
const EIXO_MAX = 800;
const coordenadaDe = (preco: number) => TOPO - preco;
const precoDe = (coordenada: number) => TOPO - coordenada;
const dentroDaEscala = (v: number) => v >= 0 && v <= EIXO_MAX;

/**
  A ESCALA DE TEMPO do duble.
  MUDÁVEL pelo teste: e assim que se prova que a ponta e a linha andam JUNTAS no
  zoom. Dobrar a escala move o pixel de um mesmo `time`.
*/
const escala = { ganho: 1 };

vi.mock('lightweight-charts', () => {
  const criarSerie = () => ({
    setData: vi.fn(),
    applyOptions: vi.fn(),
    createPriceLine: vi.fn(() => ({ remove: vi.fn() })),
    removePriceLine: vi.fn(),
    coordinateToPrice: vi.fn((c: number) => (dentroDaEscala(c) ? precoDe(c) : null)),
    priceToCoordinate: vi.fn((p: number) => {
      const coord = coordenadaDe(p);
      return dentroDaEscala(coord) ? coord : null;
    }),
    setMarkers: vi.fn(),
    remove: vi.fn(),
  });
  return {
    createChart: vi.fn(() => ({
      addCandlestickSeries: vi.fn(() => criarSerie()),
      addLineSeries: vi.fn(() => criarSerie()),
      addAreaSeries: vi.fn(() => criarSerie()),
      addHistogramSeries: vi.fn(() => criarSerie()),
      removeSeries: vi.fn(),
      priceScale: vi.fn(() => ({ applyOptions: vi.fn() })),
      subscribeCrosshairMove: vi.fn(),
      unsubscribeCrosshairMove: vi.fn(),
      applyOptions: vi.fn(),
      remove: vi.fn(),
      timeScale: vi.fn(() => ({
        fitContent: vi.fn(),
        scrollToPosition: vi.fn(),
        subscribeVisibleLogicalRangeChange: vi.fn(() => ({ unsubscribe: vi.fn() })),
        unsubscribeVisibleLogicalRangeChange: vi.fn(),
        // `time` <-> `x`: a escala de tempo vira x pela metade de cada hora.
        timeToCoordinate: vi.fn((t: number) => ((t - 1788000000) / 3600) * 20 * escala.ganho),
        coordinateToTime: vi.fn((x: number) => 1788000000 + (x / (20 * escala.ganho)) * 3600),
      })),
    })),
    ColorType: { Solid: 'solid', Vertical: 'vertical' },
    CrosshairMode: { Magnet: 0, Normal: 1 },
  };
});

vi.mock('../QuantumClock', () => ({ default: () => null }));
vi.mock('../SeletorFuso', () => ({ default: () => null }));

const { default: PriceChart } = await import('./PriceChart');

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
  received_at: '2026-10-06T20:31:00Z',
  provider_timestamp: null,
}));

beforeEach(() => {
  escala.ganho = 1;
  // jsdom nao devolve rect: o `getBoundingClientRect` e o que converte
  // `clientX` em pixel do grafico. Sem isso todo clique cai em (0,0).
  Element.prototype.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: 800, height: 800, right: 800, bottom: 800, x: 0, y: 0, toJSON: () => ({}) } as DOMRect;
  };
});

afterEach(() => cleanup());

const canvas = () => screen.getByRole('img') as HTMLDivElement;

/** As PONTAIS visiveis: os circulos que o operador mira para arrastar. */
const pontas = () => document.querySelectorAll('circle[data-ponta]');
/** As LINHAS de desenho que o operador ve. */
const linhas = () => document.querySelectorAll('line[data-desenho]');

const clicarEm = (clientX: number, clientY: number) =>
  fireEvent.click(canvas(), { clientX, clientY });

/** Desenha uma tendencia de ponta a ponta com dois cliques. */
const desenharTendencia = (x1: number, y1: number, x2: number, y2: number) => {
  fireEvent.click(screen.getByRole('button', { name: /Linha de tendência/ }));
  clicarEm(x1, y1);
  clicarEm(x2, y2);
};

/** As coordenadas em pixel de um preco, na escala atual. */
const pxDe = (preco: number) => coordenadaDe(preco);

describe('o desenho fica na tela depois de desenhado', () => {
  it('PROVA: a linha continua visivel com a ferramenta DESARMADA', () => {
    /*
      Este e o defeito corrigido. Ao fechar a linha, `aoClicar` chama
      `setFerramenta('nenhuma')` — e a camada renderizava so com
      `ferramenta !== 'nenhuma'`. A linha sumia.
    */
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    expect(linhas().length).toBe(0);

    desenharTendencia(100, 400, 500, 200);

    // A linha existe…
    expect(linhas().length).toBe(1);
    // …e o contador concorda com a tela. Antes, o contador dizia "1 desenho"
    // com a tela vazia.
    expect(screen.getByText('1 desenho')).toBeTruthy();
  });

  it('PROVA NEGATIVA: sem nenhum desenho, a camada nao aparece', () => {
    // O contrario de "sempre renderizar": um SVG vazio sobre o grafico seria
    // uma camada invisivel capturando ponteiro.
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    expect(linhas().length).toBe(0);
    expect(pontas().length).toBe(0);
  });
});

describe('as pontas arrastaveis', () => {
  it('a tendencia desenhada tem DUAS pontas', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    desenharTendencia(100, 400, 500, 200);
    expect(pontas().length).toBe(2);
  });

  it('a horizontal desenhada tem UMA ponta', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    fireEvent.click(screen.getByRole('button', { name: /Linha horizontal/ }));
    clicarEm(100, 300);
    expect(pontas().length).toBe(1);
  });

  it('arrastar a ponta move a linha para o preco do cursor', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    desenharTendencia(100, 400, 500, 200);

    const ponta = pontas()[0] as unknown as SVGCircleElement;
    expect(ponta.getAttribute('cy')).toBe('400');

    // Arrasta a primeira ponta de y=400 (preco 85.700) ate y=600 (85.500).
    fireEvent.mouseDown(canvas(), { clientX: 100, clientY: 400 });
    fireEvent.mouseMove(window, { clientX: 100, clientY: 600 });
    fireEvent.mouseUp(window, { clientX: 100, clientY: 600 });

    // A ponta foi para o preco do cursor…
    const depois = document.querySelectorAll('circle[data-ponta]')[0] as unknown as SVGCircleElement;
    expect(Number(depois.getAttribute('cy'))).toBeCloseTo(600, 0);
    // …e a LINHA foi junto. Um "arrastou a ponta" que move so o circulo
    // deixaria o operador marcar o stop num lugar que a linha nao cobre.
    const linha = linhas()[0] as unknown as SVGLineElement;
    expect(Number(linha.getAttribute('y1'))).toBeCloseTo(600, 0);
  });

  it('PROVA: o preco da ponta e o do ARRASTE, e nao o pixel guardado', () => {
    /*
      O `rerender` e NECESSARIO, e e o que torna a prova valida.

      No app, o zoom do grafico muda o estado do lightweight-charts e dispara
      `subscribeVisibleLogicalRangeChange`, que reescreve os atributos direto no
      DOM. Aqui o duble nao avisa ninguem: entao sem re-render o componente nao
      le a escala nova, e o teste mediria o React parado, nao o desenho.

      Portanto este teste mede a CONSULTA a cada render: a ponta e lida do
      grafico com `tempoParaX`, e nao de um pixel guardado no estado.
    */
    const { rerender } = render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    desenharTendencia(100, 400, 500, 200);
    fireEvent.mouseDown(canvas(), { clientX: 100, clientY: 400 });
    fireEvent.mouseMove(window, { clientX: 100, clientY: 600 });
    fireEvent.mouseUp(window, { clientX: 100, clientY: 600 });

    expect(Number((pontas()[0] as unknown as SVGCircleElement).getAttribute('cx'))).toBeCloseTo(100, 0);

    // Dobrar a escala de TEMPO. O mesmo ponto vai de x=100 para x=200.
    escala.ganho = 2;
    rerender(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);

    // A ponta foi CONSULTADA de novo e mudou de lugar…
    expect(Number((pontas()[0] as unknown as SVGCircleElement).getAttribute('cx'))).toBeCloseTo(200, 0);
    // …e a LINHA junto. Um desenho preso em pixel deixaria a ponta parada em
    // 100, e o operador arrastaria a ponta errada achando que acertou.
    expect(Number((linhas()[0] as unknown as SVGLineElement).getAttribute('x1'))).toBeCloseTo(200, 0);
  });

  it('PROVA NEGATIVA: arrastar no VAZIO nao move linha nenhuma', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    desenharTendencia(100, 400, 500, 200);
    const antes = linhas()[0] as unknown as SVGLineElement;
    const y1Antes = antes.getAttribute('y1');

    // (700, 700) esta longe das duas pontas.
    fireEvent.mouseDown(canvas(), { clientX: 700, clientY: 700 });
    fireEvent.mouseMove(window, { clientX: 700, clientY: 100 });
    fireEvent.mouseUp(window, { clientX: 700, clientY: 100 });

    const depois = linhas()[0] as unknown as SVGLineElement;
    expect(depois.getAttribute('y1')).toBe(y1Antes);
  });
});

describe('o estilo do desenho escolhido', () => {
  it('a paleta so aparece com um desenho SELECIONADO', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    expect(screen.queryByRole('group', { name: 'Estilo do desenho' })).toBeNull();

    desenharTendencia(100, 400, 500, 200);
    // Nasce selecionado: o operador acabou de escolher ESTE desenho ao clicar.
    expect(screen.getByRole('group', { name: 'Estilo do desenho' })).toBeTruthy();
  });

  it('trocar a cor pinta a LINHA, nao so o botao', () => {
    // O defeito do botao EMA: `aria-pressed` mudava e a tela nao.
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    desenharTendencia(100, 400, 500, 200);

    fireEvent.click(screen.getByRole('button', { name: 'Cor #2ecc71' }));

    const linha = linhas()[0] as unknown as SVGLineElement;
    expect(linha.getAttribute('stroke')).toBe('#2ecc71');
  });

  it('trocar a espessura muda a linha desenhada', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    desenharTendencia(100, 400, 500, 200);

    fireEvent.click(screen.getByRole('button', { name: 'Espessura 4 px' }));

    const linha = linhas()[0] as unknown as SVGLineElement;
    expect(linha.getAttribute('stroke-width')).toBe('4');
  });

  it('a opacidade vai para a linha, e o valor e lido do controle', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    desenharTendencia(100, 400, 500, 200);

    const controle = screen.getByRole('slider', { name: /Opacidade do desenho/ }) as HTMLInputElement;
    expect(controle.value).toBe('100');
    fireEvent.change(controle, { target: { value: '40' } });

    const linha = linhas()[0] as unknown as SVGLineElement;
    expect(linha.getAttribute('opacity')).toBe('0.4');
  });

  it('PROVA NEGATIVA: a cor de um desenho NAO vaza para o proximo', () => {
    /*
      O estilo e DO DESENHO, nao global. Um estilo global obrigaria o operador
      a redesenhar a linha para trocar a cor — e a linha existe para marcar o
      stop no lugar certo. Perder o ponto marcado para mudar a cor e o oposto
      do que a ferramenta serve.
    */
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    desenharTendencia(100, 400, 500, 200);
    fireEvent.click(screen.getByRole('button', { name: 'Cor #2ecc71' }));

    // Agora um SEGUNDO desenho, sem tocar na cor.
    fireEvent.click(screen.getByRole('button', { name: /Linha horizontal/ }));
    clicarEm(100, 700);

    const linhasAgora = linhas();
    const primeira = linhasAgora[0] as unknown as SVGLineElement;
    const segunda = linhasAgora[1] as unknown as SVGLineElement;
    expect(primeira.getAttribute('stroke')).toBe('#2ecc71');
    // A nova nasce no padrao, e nao verde.
    expect(segunda.getAttribute('stroke')).not.toBe('#2ecc71');
  });
});

describe('travar o desenho', () => {
  it('travar esconde as pontas', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    desenharTendencia(100, 400, 500, 200);
    expect(pontas().length).toBe(2);

    fireEvent.click(screen.getByRole('button', { name: /Travar o desenho/ }));
    expect(pontas().length).toBe(0);
  });

  it('PROVA: com o desenho TRAVADO, arrastar a ponta NAO move a linha', () => {
    /*
      O guarda do `podeMoverPontos` no `mousemove`, e nao so no desenho das
      pontas. Sem ele, o circulo sumiria mas o `mousedown` continuaria pegando:
      o operador veria a tranca FECHADA com a linha andando, e marcaria o stop
      num nivel que ele nao escolheu.
    */
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    desenharTendencia(100, 400, 500, 200);
    fireEvent.click(screen.getByRole('button', { name: /Travar o desenho/ }));

    const antes = linhas()[0] as unknown as SVGLineElement;
    const y1Antes = antes.getAttribute('y1');

    fireEvent.mouseDown(canvas(), { clientX: 100, clientY: 400 });
    fireEvent.mouseMove(window, { clientX: 100, clientY: 600 });
    fireEvent.mouseUp(window, { clientX: 100, clientY: 600 });

    const depois = linhas()[0] as unknown as SVGLineElement;
    expect(depois.getAttribute('y1')).toBe(y1Antes);
  });

  it('destravar traz as pontas de volta', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    desenharTendencia(100, 400, 500, 200);
    fireEvent.click(screen.getByRole('button', { name: /Travar o desenho/ }));
    expect(pontas().length).toBe(0);
    fireEvent.click(screen.getByRole('button', { name: /Destravar o desenho/ }));
    expect(pontas().length).toBe(2);
  });
});

describe('desfazer e refazer', () => {
  it('desfazer remove a linha recem-criada', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    expect(screen.queryByRole('button', { name: /Desfazer a última/ })).toBeNull();

    desenharTendencia(100, 400, 500, 200);
    expect(linhas().length).toBe(1);

    fireEvent.click(screen.getByRole('button', { name: /Desfazer a última/ }));
    expect(linhas().length).toBe(0);
  });

  it('refazer traz a linha de volta', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    desenharTendencia(100, 400, 500, 200);
    fireEvent.click(screen.getByRole('button', { name: /Desfazer a última/ }));
    fireEvent.click(screen.getByRole('button', { name: /Refazer a mudança/ }));
    expect(linhas().length).toBe(1);
  });

  it('desfazer volta o ARRASTE da ponta, nao so a criacao', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    desenharTendencia(100, 400, 500, 200);
    fireEvent.mouseDown(canvas(), { clientX: 100, clientY: 400 });
    fireEvent.mouseMove(window, { clientX: 100, clientY: 600 });
    fireEvent.mouseUp(window, { clientX: 100, clientY: 600 });
    expect(Number((linhas()[0] as unknown as SVGLineElement).getAttribute('y1'))).toBeCloseTo(600, 0);

    fireEvent.click(screen.getByRole('button', { name: /Desfazer a última/ }));
    // Volta para 400: o ponto original, nao um desenho a menos.
    expect(Number((linhas()[0] as unknown as SVGLineElement).getAttribute('y1'))).toBeCloseTo(400, 0);
  });

  it('PROVA NEGATIVA: sem historico, o botao DESABILITADO — e nao so apagado', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    // Desenhando, o botao existe e nao esta desabilitado.
    desenharTendencia(100, 400, 500, 200);
    const b = screen.getByRole('button', { name: /Desfazer a última/ }) as HTMLButtonElement;
    expect(b.disabled).toBe(false);
  });

  it('Ctrl + Z desfaz, como na XM', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} timeframe="M15" />);
    desenharTendencia(100, 400, 500, 200);
    expect(linhas().length).toBe(1);

    fireEvent.keyDown(screen.getByRole('img').closest('.price-chart') as HTMLElement, { key: 'z', ctrlKey: true });
    expect(linhas().length).toBe(0);
  });
});