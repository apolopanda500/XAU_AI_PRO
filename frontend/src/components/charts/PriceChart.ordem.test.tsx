// @vitest-environment jsdom
// A ORDEM ARMADA PELO GRAFICO (06/10/2026)
// ==========================================
// MEDIDO nas capturas da XM: o clique ARMA a ordem e nao envia. As tres linhas
// (`entrada`, `stop`, `alvo`) aparecem com rotulo em dinheiro e um `x` cada, e
// sao arrastaveis.
//
// A ARMADILHA DESTES TESTES
// =========================
// `createPriceLine` ser CHAMADO nao prova que a linha esta na tela: prova que
// alguem pediu. Como o efeito recria as linhas a cada render, o log de chamadas
// conta o mesmo requisito duas vezes. Por isso estes testes medem as LINHAS
// VIVAS (`criadas − removidas`), que e o que o operador ve.
//
// E o `x` nao existe no lightweight-charts: o `title` da price line e TEXTO no
// canvas e nao recebe clique. Um `x` desenhado como texto seria o botao que
// parece funcionar e nao funciona — o defeito do botao EMA.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { MarketCandle } from '../../lib/marketApi';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

/*
  O EIXO DO DOUBLE, coerente POR CONSTRUCAO.

  Antes o duble tinha uma tabela `{preco: pixel}` escrita a mao, e ela nao
  cobria os precos das linhas: o `x` do stop saia `-9999px` e o teste "acertava"
  por um motivo errado — era o duble quebrado, nao o codigo. AGENTS.md 6: um
  duble que le o campo errado faz o teste passar calado.

  Aqui a conversao e a MESMA conta nos dois sentidos, e o ALCANCE E O MESMO:

      coordenada  = 86.100 − preco        (0 px em 86.100, 800 px em 85.300)
      preco       = 86.100 − coordenada

  O alcance unico importa: com limites diferentes em cada sentido, o `x` do
  alvo saia `-9999px` enquanto o clique naquele pixel ainda devolvia preco — e o
  teste passaria por um motivo errado.

  85.510,25 -> 589,75 px   (a entrada)
  85.710,25 -> 389,75 px   (o stop)
  85.310,25 -> 789,75 px   (o alvo)
  85.000,00 -> 1.100 px    (fora: `null`)
*/
const TOPO = 86_100;
const BASE = 85_300;
/** O eixo do duble vai de 0 a 800 px. Fora disso, `null` — como a biblioteca. */
const EIXO_MAX = 800;
const coordenadaDe = (preco: number) => TOPO - preco;
const precoDe = (coordenada: number) => TOPO - coordenada;
const dentroDaEscala = (v: number) => v >= 0 && v <= EIXO_MAX;

/** Contadores de price line, para medir as VIAS e nao as chamadas. */
const contadores = { criadas: 0, removidas: 0 };
/** Todas as `createPriceLine` pedidas: o que o app QUIS. */
const pedidos: Array<{ price: number; title: string; color: string }> = [];

vi.mock('lightweight-charts', () => {
  const criarSerie = (_nome: string) => ({
    setData: vi.fn(),
    applyOptions: vi.fn(),
    createPriceLine: vi.fn((opts: any) => {
      contadores.criadas += 1;
      pedidos.push({ price: opts.price, title: opts.title, color: opts.color });
      return { remove: vi.fn() };
    }),
    removePriceLine: vi.fn(() => {
      contadores.removidas += 1;
    }),
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
      addCandlestickSeries: vi.fn(() => criarSerie('candle')),
      addLineSeries: vi.fn(() => criarSerie('linha')),
      addAreaSeries: vi.fn(() => criarSerie('area')),
      addHistogramSeries: vi.fn(() => criarSerie('histograma')),
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
  market: 'forex' as MarketCandle['market'],
  symbol: 'BTCUSD',
  source: 'mt5_gateway',
  received_at: '2026-10-06T14:12:39Z',
  provider_timestamp: null,
}));

const ENTRADA = 85_510.25;
const STOP = 85_710.25;
const ALVO = 85_310.25;

/** Os tres niveis da captura 141239: entrada, stop acima, alvo abaixo (VENDA). */
const ORDEM = [
  { papel: 'entrada' as const, preco: ENTRADA, rotulo: '0,01 | −2,00 USD', cor: 'rgba(139,147,167,.9)' },
  { papel: 'sl' as const, preco: STOP, rotulo: '0,01 | −2,00 USD', cor: '#e8a33d' },
  { papel: 'tp' as const, preco: ALVO, rotulo: '0,01 | +2,00 USD', cor: '#2ecc71' },
];

/** As linhas VIVAS: o que o operador ve, depois de criadas e removidas. */
const linhasVivas = () => contadores.criadas - contadores.removidas;

/** O `div` do canvas, onde os cliques do grafico acontecem. */
const canvas = () => screen.getByRole('img') as HTMLDivElement;

beforeEach(() => {
  contadores.criadas = 0;
  contadores.removidas = 0;
  pedidos.length = 0;
});

afterEach(() => cleanup());

describe('o clique ARMA a ordem, no preco clicado', () => {
  it('manda o preco de coordinateToPrice para o pai', () => {
    const armar = vi.fn();
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={ORDEM} onArmarOrdem={armar} />);
    fireEvent.click(canvas(), { clientY: coordenadaDe(ENTRADA) });
    expect(armar).toHaveBeenCalledWith(ENTRADA);
  });

  it('o preco vai CRU: quem arredonda e o pai, que tem a ficha do ativo', () => {
    /*
    O grafico nao sabe o `point` do ativo. Arredondar aqui com 2 casasaria
    85.000,00 virando 85.000 num forex de 5 casas — e o `point` vem da
    corretora, nao de uma constante (AGENTS.md 3).
    */
    const armar = vi.fn();
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={ORDEM} onArmarOrdem={armar} />);
    // 85.900 e 200 px, longe das duas linhas: a tolerancia de arraste e 0,2%
    // (171 pontos em BTCUSD), e um preco perto do stop seria corretamente
    // tratado como "clicar sobre a linha".
    fireEvent.click(canvas(), { clientY: coordenadaDe(85_900.37) });
    expect(armar).toHaveBeenCalledWith(85_900.37);
  });

  it('PROVA NEGATIVA: sem modoOrdem o clique nao arma nada', () => {
    const armar = vi.fn();
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} ordem={ORDEM} onArmarOrdem={armar} />);
    fireEvent.click(canvas(), { clientY: coordenadaDe(ENTRADA) });
    expect(armar).not.toHaveBeenCalled();
  });

  it('PROVA NEGATIVA: clicar SOBRE o stop nao arma — e o inicio do arraste', () => {
    /*
    Clicar na linha e o primeiro pedaco do ARRASTE, nao uma ordem nova. Se
    armasse aqui, cada ajuste fino do stop criaria uma ordem sem querer.
    */
    const armar = vi.fn();
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={ORDEM} onArmarOrdem={armar} />);
    fireEvent.click(canvas(), { clientY: coordenadaDe(STOP) });
    expect(armar).not.toHaveBeenCalled();
  });

  it('PROVA NEGATIVA: preco fora da escala nao arma — o app nao decide o preco', () => {
    const armar = vi.fn();
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={ORDEM} onArmarOrdem={armar} />);
    fireEvent.click(canvas(), { clientY: 999 });
    expect(armar).not.toHaveBeenCalled();
  });
});

describe('AS TRES LINHAS, com o rotulo em dinheiro', () => {
  it('as tres ficam vivas, cada uma com o rotulo que a XM escreve', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={ORDEM} />);
    // Vivas, e nao "chamadas": o efeito recria as linhas a cada render, e o
    // log contaria a mesma linha duas vezes.
    expect(linhasVivas()).toBe(3);
    const titulos = pedidos.slice(-3).map((l) => l.title);
    expect(titulos).toContain('0,01 | −2,00 USD');
    expect(titulos).toContain('0,01 | +2,00 USD');
    expect(pedidos.slice(-3).map((l) => l.price)).toEqual(
      expect.arrayContaining([ENTRADA, STOP, ALVO]),
    );
  });

  it('o stop e o alvo tem cores DIFERENTES: e assim que se distingue de relance', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={ORDEM} />);
    const ultimas = pedidos.slice(-3);
    const sl = ultimas.find((l) => l.price === STOP)!;
    const tp = ultimas.find((l) => l.price === ALVO)!;
    expect(sl.color).toBe('#e8a33d');
    expect(tp.color).toBe('#2ecc71');
    expect(sl.color).not.toBe(tp.color);
  });

  it('PROVA NEGATIVA: stop apagado SOME, e nao vira preco zero', () => {
    /*
    O `x` apaga o stop. A linha some — e o que resta e entrada e alvo. Um `0`
    aqui seria uma linha no chao mandando ordem com sl=0, que o gateway recusa
    com um motivo generico.
    */
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={[ORDEM[0], ORDEM[2]]} />);
    expect(linhasVivas()).toBe(2);
    expect(pedidos.some((l) => l.price === STOP)).toBe(false);
    expect(pedidos.map((l) => l.price)).not.toContain(0);
  });

  it('PROVA NEGATIVA: sem ordem armada NAO ha linha nenhuma', () => {
    // Um painel de ordem sem clique nao pode deixar veizinho de nada no grafico.
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={[]} />);
    expect(linhasVivas()).toBe(0);
  });
});

describe('o `x` de cada linha', () => {
  it('o botao EXISTE no DOM, e nao e texto no canvas', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={ORDEM} />);
    // Sem estes, o controle que o dono mediu na captura nao existe.
    expect(screen.getByLabelText('Apagar stop')).toBeTruthy();
    expect(screen.getByLabelText('Apagar alvo')).toBeTruthy();
  });

  it('a posicao vem de priceToCoordinate, e nao de conta propria', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={ORDEM} />);
    const stop = screen.getByLabelText('Apagar stop') as HTMLButtonElement;
    // Um `top` calculado pelo app sairia errado no primeiro zoom, e o operador
    // apagaria a linha errada acreditando no que ve.
    expect(stop.style.top).toBe(`${coordenadaDe(STOP)}px`);
    const alvo = screen.getByLabelText('Apagar alvo') as HTMLButtonElement;
    expect(alvo.style.top).toBe(`${coordenadaDe(ALVO)}px`);
  });

  it('a entrada NAO tem `x`: apagar a ordem recem armada e um engano de um clique', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={ORDEM} />);
    expect(screen.queryByLabelText('Apagar entrada')).toBeNull();
  });

  it('o clique no `x` chama o pai com o PAPEL, e nao com o preco', () => {
    const remover = vi.fn();
    render(
      <PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={ORDEM} onRemoverLinha={remover} />,
    );
    fireEvent.click(screen.getByLabelText('Apagar stop'));
    expect(remover).toHaveBeenCalledWith('sl');
  });

  it('o `x` NAO arma outra ordem ao ser clicado', () => {
    /*
    O `x` esta dentro da area do grafico. Sem o `stopPropagation`, apagar o stop
    viraria "armar ordem nova" — e o operador perderia a ordem que estava
    armando.
    */
    const armar = vi.fn();
    const remover = vi.fn();
    render(
      <PriceChart
        symbol="BTCUSD"
        candles={CANDLES}
        modoOrdem
        ordem={ORDEM}
        onArmarOrdem={armar}
        onRemoverLinha={remover}
      />,
    );
    fireEvent.click(screen.getByLabelText('Apagar alvo'));
    expect(remover).toHaveBeenCalledWith('tp');
    expect(armar).not.toHaveBeenCalled();
  });

  it('preco fora da escala nao deixa `x` parado no topo da tela', () => {
    // Um `x` visivel e sem linha parece clicavel; ele some.
    render(
      <PriceChart
        symbol="BTCUSD"
        candles={CANDLES}
        modoOrdem
        ordem={[ORDEM[0], { ...ORDEM[2], preco: 90_000 }]}
      />,
    );
    const alvo = screen.getByLabelText('Apagar alvo') as HTMLButtonElement;
    expect(alvo.style.top).toBe('-9999px');
  });

  it('PROVA NEGATIVA: sem modoOrdem nao ha `x` nenhum', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} ordem={ORDEM} />);
    expect(screen.queryByLabelText('Apagar stop')).toBeNull();
    expect(screen.queryByLabelText('Apagar alvo')).toBeNull();
  });

  it('PROVA NEGATIVA: linha apagada nao deixa `x` orfao', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={[ORDEM[0], ORDEM[1]]} />);
    expect(screen.queryByLabelText('Apagar stop')).toBeTruthy();
    expect(screen.queryByLabelText('Apagar alvo')).toBeNull();
  });
});

describe('arrastar a linha devolve o PAPEL e o preco', () => {
  it('soltar o stop longe devolve `sl` e o preco novo', () => {
    const mover = vi.fn();
    render(
      <PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={ORDEM} onMoverLinhaOrdem={mover} />,
    );
    fireEvent.mouseDown(canvas(), { clientY: coordenadaDe(STOP) });
    fireEvent.mouseMove(window, { clientY: coordenadaDe(STOP) });
    fireEvent.mouseUp(window, { clientY: coordenadaDe(86_000) });
    // O preco vai CRU: quem converte distancia em dinheiro e o pai, que tem o
    // contract_size. O grafico nao tem como saber quanto o preco vale em USD.
    expect(mover).toHaveBeenCalledWith('sl', 86_000);
  });

  it('arrastar o alvo devolve `tp`, e nao `sl`', () => {
    const mover = vi.fn();
    render(
      <PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={ORDEM} onMoverLinhaOrdem={mover} />,
    );
    fireEvent.mouseDown(canvas(), { clientY: coordenadaDe(ALVO) });
    fireEvent.mouseUp(window, { clientY: coordenadaDe(85_600) });
    expect(mover).toHaveBeenCalledWith('tp', 85_600);
  });

  it('PROVA NEGATIVA: a entrada nao arrasta — o preco dela e o que foi clicado', () => {
    const mover = vi.fn();
    render(
      <PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={ORDEM} onMoverLinhaOrdem={mover} />,
    );
    fireEvent.mouseDown(canvas(), { clientY: coordenadaDe(ENTRADA) });
    fireEvent.mouseUp(window, { clientY: coordenadaDe(85_400) });
    expect(mover).not.toHaveBeenCalled();
  });

  it('PROVA NEGATIVA: sem onMoverLinhaOrdem o arraste nao quebra a tela', () => {
    render(<PriceChart symbol="BTCUSD" candles={CANDLES} modoOrdem ordem={ORDEM} />);
    expect(() => {
      fireEvent.mouseDown(canvas(), { clientY: coordenadaDe(STOP) });
      fireEvent.mouseUp(window, { clientY: coordenadaDe(86_000) });
    }).not.toThrow();
  });
});