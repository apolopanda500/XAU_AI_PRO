// @vitest-environment jsdom
// OS DESLOCAMENTOS DO GRAFICO, VALIDADOS COM NUMERO (11/11/2026)
// ===============================================================
// O DONO PEDIU: "melhorar deslocamentos do grafico mais soltos, poder rolar com
// botao do meio do mouse, rolar na barra lateral direita com valores igual no
// TradingView, tudo livre e solto, ficar mais rapido".
//
// O QUE FOI MEDIDO NO FONTE da lightweight-charts 4.2.3 (dev build), e que estes
// testes fixam como contrato:
//
//   - a roda NATIVA so fazia zoom (`handleScale.mouseWheel`, deltaY) e o
//     deltaX rolava com coeficiente 0,8px por unidade — com roda comum (só
//     deltaY) NAO existia como rolar o grafico;
//   - `kineticScroll.mouse` nasce `false` (arraste sem inercia);
//   - nao existe pan vertical publico: o unico ponto e o
//     `autoscaleInfoProvider` da serie, chamado a cada recalculo da escala;
//   - o `button === 1` (meio) e ignorado pela biblioteca.
//
// Estes testes provam: roda rola tempo, roda na ESCALA rola preco (via o
// provedor, com o numero certo), Ctrl+roda da zoom, o MEIO arrasta os dois eicos
// solta, duplo clique na escala zera o deslocamento — e as provas negativas de
// que nada disso acontece no lugar errado.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, waitFor } from '@testing-library/react';
import type { MarketCandle } from '../../lib/marketApi';

const criado = { candle: 0 };
const reg = {
  faixas: [] as Array<{ from: number; to: number }>,
  criacaoGrafico: [] as Array<Record<string, unknown>>,
  criacaoSerie: [] as Array<Record<string, unknown>>,
  opcoesPreco: [] as Array<Record<string, unknown>>,
  opcoesVolume: [] as Array<Record<string, unknown>>,
  fitContent: 0,
  scrollToRealTime: 0,
};

// O PRECO POR PIXEL do duble: 0,5 por px (2000 em cima, desce 0,5 por pixel).
const PRECO_POR_PX = 0.5;
const LARGURA_ESCALA = 60;

vi.mock('lightweight-charts', () => {
  const base = {
    setData: vi.fn(),
    createPriceLine: vi.fn(() => ({ remove: vi.fn() })),
    removePriceLine: vi.fn(),
    setMarkers: vi.fn(),
    remove: vi.fn(),
  };
  const serie = {
    ...base,
    applyOptions: vi.fn((o: Record<string, unknown>) => {
      reg.opcoesPreco.push(o);
    }),
    coordinateToPrice: vi.fn((y: number) => 2000 - y * 0.5),
  };
  const volume = {
    ...base,
    applyOptions: vi.fn((o: Record<string, unknown>) => {
      reg.opcoesVolume.push(o);
    }),
    coordinateToPrice: vi.fn(() => 1),
  };
  const novoGrafico = () => ({
    addCandlestickSeries: vi.fn((o: Record<string, unknown>) => {
      criado.candle += 1;
      reg.criacaoSerie.push(o);
      return serie;
    }),
    addLineSeries: vi.fn((o: Record<string, unknown>) => {
      reg.criacaoSerie.push(o);
      return serie;
    }),
    addAreaSeries: vi.fn((o: Record<string, unknown>) => {
      reg.criacaoSerie.push(o);
      return serie;
    }),
    addHistogramSeries: vi.fn((o: Record<string, unknown>) => {
      reg.criacaoSerie.push(o);
      return volume;
    }),
    removeSeries: vi.fn(),
    priceScale: vi.fn(() => ({ applyOptions: vi.fn(), width: () => LARGURA_ESCALA })),
    subscribeCrosshairMove: vi.fn(),
    unsubscribeCrosshairMove: vi.fn(),
    applyOptions: vi.fn(),
    resize: vi.fn(),
    remove: vi.fn(),
    timeScale: vi.fn(() => ({
      fitContent: vi.fn(() => {
        reg.fitContent += 1;
      }),
      scrollToPosition: vi.fn(),
      scrollToRealTime: vi.fn(() => {
        reg.scrollToRealTime += 1;
      }),
      subscribeVisibleTimeRangeChange: vi.fn(() => ({ unsubscribe: vi.fn() })),
      getVisibleLogicalRange: vi.fn(() => ({ from: 0, to: 50 })),
      setVisibleLogicalRange: vi.fn((r: { from: number; to: number }) => {
        reg.faixas.push({ from: r.from, to: r.to });
      }),
      options: vi.fn(() => ({ barSpacing: 6 })),
    })),
  });
  return {
    createChart: vi.fn((_el: unknown, o: Record<string, unknown>) => {
      reg.criacaoGrafico.push(o);
      return novoGrafico();
    }),
    ColorType: { Solid: 'solid', Vertical: 'vertical' },
    CrosshairMode: { Magnet: 0, Normal: 1 },
  };
});

vi.mock('../QuantumClock', () => ({ default: () => null }));
vi.mock('../SeletorFuso', () => ({ default: () => null }));

const { default: PriceChart } = await import('./PriceChart');

const CANDLES: MarketCandle[] = Array.from({ length: 40 }, (_, i) => ({
  time: 1_700_000_000 + i * 3600,
  open: 100 + i,
  high: 101 + i,
  low: 99 + i,
  close: 100.5 + i,
  volume: 1000,
  broker: 'mt5' as MarketCandle['broker'],
  market: 'other' as MarketCandle['market'],
  symbol: 'BTCUSD',
  source: 'mt5_gateway',
  received_at: '2026-10-04T12:00:00.000Z',
  provider_timestamp: '2026-10-04T12:00:00.000Z',
  execucao: false,
  sinal: null,
}));

/** O provedor da escala, tal qual a serie nasceu com ele. */
type Info = { priceRange: { minValue: number; maxValue: number } };
const provedor = (): ((base: () => Info) => Info) => {
  const opcoes = reg.criacaoSerie.find((o) => o.autoscaleInfoProvider);
  return opcoes?.autoscaleInfoProvider as (base: () => Info) => Info;
};
const faixaBase = (): Info => ({ priceRange: { minValue: 1000, maxValue: 2000 } });

/** jsdom nao tem layout: a janela e 800x600 e a escala de precos tem 60px. */
const esticar = (el: HTMLElement) => {
  el.getBoundingClientRect = () =>
    ({
      width: 800,
      height: 600,
      left: 0,
      top: 0,
      right: 800,
      bottom: 600,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    }) as DOMRect;
  return el;
};

const renderarEPronto = async (): Promise<HTMLElement> => {
  render(<PriceChart symbol="BTCUSD" candles={CANDLES} />);
  await waitFor(() => expect(criado.candle).toBeGreaterThan(0));
  const el = document.querySelector('.market-chart-canvas') as HTMLElement;
  return esticar(el);
};

const rolar = (el: HTMLElement, init: WheelEventInit) => {
  const ev = new WheelEvent('wheel', { bubbles: true, cancelable: true, ...init });
  el.dispatchEvent(ev);
  return ev;
};

const precos = () => reg.faixas[reg.faixas.length - 1];

beforeEach(() => {
  reg.faixas.length = 0;
  reg.criacaoGrafico.length = 0;
  reg.criacaoSerie.length = 0;
  reg.opcoesPreco.length = 0;
  reg.opcoesVolume.length = 0;
  reg.fitContent = 0;
  reg.scrollToRealTime = 0;
  criado.candle = 0;
});

afterEach(cleanup);

describe('as opcoes que deixam o grafico SOLTO', () => {
  it('a roda nativa fica DESLIGADA (a nossa roda assume) e a inercia do mouse LIGA', async () => {
    await renderarEPronto();
    const opcoes = reg.criacaoGrafico[0];

    expect((opcoes.handleScroll as { mouseWheel: boolean }).mouseWheel).toBe(false);
    expect((opcoes.handleScale as { mouseWheel: boolean }).mouseWheel).toBe(false);
    // O arraste com botao esquerdo continua de fabrica…
    expect((opcoes.handleScroll as { pressedMouseMove: boolean }).pressedMouseMove).toBe(true);
    // …e e ele que ganha inercia: `kineticScroll.mouse` nasce false na 4.2.3.
    expect((opcoes.kineticScroll as { mouse: boolean }).mouse).toBe(true);
  });
});

describe('a roda sobre o GRAFICO: rolagem do tempo, rapida', () => {
  it('deltaY rola 25 barras por passada (1,5px/unidade contra 0,8px do nativo)', async () => {
    const el = await renderarEPronto();
    const ev = rolar(el, { deltaY: 100, clientX: 400, clientY: 300 });
    // Sem preventDefault a pagina rola junto com o grafico.
    expect(ev.defaultPrevented).toBe(true);
    // 100 * 1.5 / barSpacing(6) = 25 barras a mais (pra frente no tempo).
    expect(precos()).toEqual({ from: 25, to: 75 });
  });

  it('deltaX (touchpad) rola o mesmo eixo, com o sinal natural', async () => {
    const el = await renderarEPronto();
    rolar(el, { deltaX: -60, deltaY: 0, clientX: 400, clientY: 300 });
    // 60 * 1.5 / 6 = 15 barras.
    expect(precos()).toEqual({ from: 15, to: 65 });
  });

  it('PROVA NEGATIVA: rolar o grafico NAO mexe na escala vertical', async () => {
    const el = await renderarEPronto();
    rolar(el, { deltaY: 100, clientX: 400, clientY: 300 });
    expect(provedor()(() => faixaBase())).toEqual(faixaBase());
  });
});

describe('a roda sobre a BARRA LATERAL: rolagem vertical dos precos', () => {
  it('roda pra baixo desce 50 unidades de preco (deltaY * preco por pixel)', async () => {
    const el = await renderarEPronto();
    // 760 >= 800 - 60 = 740: por cima da escala de precos.
    rolar(el, { deltaY: 100, clientX: 760, clientY: 300 });

    const info = provedor()(() => faixaBase());
    // 100 * 0.5 = 50; rola pra baixo = faixa desce = valores menores.
    expect(info.priceRange.minValue).toBeCloseTo(950, 6);
    expect(info.priceRange.maxValue).toBeCloseTo(1950, 6);
  });

  it('e OBRIGA o grafico a reler a escala (setVisibleLogicalRange = recalculo)', async () => {
    const el = await renderarEPronto();
    const antes = reg.faixas.length;
    rolar(el, { deltaY: 100, clientX: 760, clientY: 300 });
    expect(reg.faixas.length).toBe(antes + 1);
    // O tempo nao andou: o recolocar devolve a MESMA faixa.
    expect(precos()).toEqual({ from: 0, to: 50 });
  });

  it('PROVA NEGATIVA: rola a escala sem rolar o tempo do grafico', async () => {
    const el = await renderarEPronto();
    rolar(el, { deltaY: 100, clientX: 760, clientY: 300 });
    // A faixa empurrada e a mesma de antes (releitura), nunca deslocada.
    expect(precos()).toEqual({ from: 0, to: 50 });
  });

  it('duplo clique na barra ZERA o deslocamento (reset nativo preservado)', async () => {
    const el = await renderarEPronto();
    rolar(el, { deltaY: 100, clientX: 760, clientY: 300 });
    expect(provedor()(() => faixaBase()).priceRange.minValue).toBeCloseTo(950, 6);

    fireEvent.dblClick(el, { clientX: 760, clientY: 300 });
    expect(provedor()(() => faixaBase())).toEqual(faixaBase());
  });
});

describe('Ctrl + roda: o zoom em torno do ponteiro', () => {
  it('aproxima a janela (50 -> 44.5 barras) sem tocar na escala vertical', async () => {
    const el = await renderarEPronto();
    rolar(el, { deltaY: -100, ctrlKey: true, clientX: 200, clientY: 300 });

    const f = precos();
    expect(f.to - f.from).toBeCloseTo(44.5, 6);
    expect(provedor()(() => faixaBase())).toEqual(faixaBase());
  });

  it('PROVA NEGATIVA: Ctrl + roda NAO rola o tempo (o ponto ANCORADO fica)', async () => {
    /*
      O erro de desenho deste teste (medido 11/11/2026): zoom no ponteiro NAO
      preserva o CENTRO — ele preserva o ponto SOB O MOUSE. Com o mouse em
      200/740 da largura util, o centro anda de 25 para ~23,74 e um assert no
      centro reprovaria o zoom correto.

      O que nao se move e a ancora: `from + rel*(to-from)` tem de continuar
      13,5135 (= 0 + 0,2703 * 50) antes e depois — e o tempo nao rolou, que e
      o que este caso prova.
    */
    const el = await renderarEPronto();
    rolar(el, { deltaY: -100, ctrlKey: true, clientX: 200, clientY: 300 });

    const f = precos();
    const rel = 200 / (800 - LARGURA_ESCALA);
    const ancora = 0 + rel * 50;
    expect(f.from + rel * (f.to - f.from)).toBeCloseTo(ancora, 6);
    // A janela encolheu (zoom) — mas nao DESLOCOU para frente: o minimo
    // continua perto de onde estava, so a largura mudou.
    expect(f.from).toBeGreaterThan(-1);
    expect(f.to).toBeLessThan(51);
  });
});

describe('O BOTAO DO MEIO: arrastar o grafico inteiro', () => {
  it('arrasta tempo e preco juntos, e previne o autoscroll do Windows', async () => {
    const el = await renderarEPronto();

    const mousedown = new MouseEvent('mousedown', {
      button: 1,
      clientX: 400,
      clientY: 300,
      bubbles: true,
      cancelable: true,
    });
    el.dispatchEvent(mousedown);
    expect(mousedown.defaultPrevented, 'autoscroll do sistema contido').toBe(true);
    expect(el.style.cursor).toBe('grabbing');

    window.dispatchEvent(new MouseEvent('mousemove', { clientX: 480, clientY: 340 }));
    // -80px / barSpacing 6 = -13.333 barras.
    expect(precos().from).toBeCloseTo(-13.333333, 5);
    expect(precos().to).toBeCloseTo(36.666667, 5);
    // 40px * 0.5 = 20 unidades de preco pra cima (arraste pra baixo).
    expect(provedor()(() => faixaBase()).priceRange.minValue).toBeCloseTo(1020, 6);

    window.dispatchEvent(new MouseEvent('mouseup'));
    expect(el.style.cursor).toBe('');
    const antes = reg.faixas.length;
    window.dispatchEvent(new MouseEvent('mousemove', { clientX: 500, clientY: 400 }));
    expect(reg.faixas.length, 'soltou, parou de arrastar').toBe(antes);
  });

  it('PROVA NEGATIVA: o botao ESQUERDO nao arrasta por aqui (e nao e preenchido)', async () => {
    const el = await renderarEPronto();
    const mousedown = new MouseEvent('mousedown', {
      button: 0,
      clientX: 400,
      clientY: 300,
      bubbles: true,
      cancelable: true,
    });
    el.dispatchEvent(mousedown);
    expect(mousedown.defaultPrevented).toBe(false);

    window.dispatchEvent(new MouseEvent('mousemove', { clientX: 480, clientY: 340 }));
    expect(reg.faixas.length).toBe(0);
  });
});
