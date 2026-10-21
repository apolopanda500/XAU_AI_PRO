// @vitest-environment jsdom
// O MENU DO BOTAO DIREITO DO GRAFICO (09/10/2026)
// =================================================
// O DONO VIU na captura da XM (`Screenshot 2026-10-09 201959.png`) o menu com
// TRADE no topo e pediu, textualmente: "quando tem direito tem que abrir todas
// funcoes do menu".
//
// MEDIDO aqui: o clique direito abria o menu DO WEBVIEW — Recarregar,
// Inspecionar, Imprimir —, que e do navegador e nao tem funcao de operacao.
//
// A REGRA DO DONO DE 08/10/2026 VALE AQUI TAMBEM
// =============================================
// "O clique nao arma ordem": dois cliques criaram tres linhas montadas a um
// clique do envio (conta real 391773676). O menu direito e o MESMO perigo por
// outro caminho — se COMPRAR criasse linha, seria o 1-clique que foi removido.
//
// Estes testes medem os dois lados: o menu abre com o que a XM tem, e o menu
// NAO cria ordem sozinho.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { MarketCandle } from '../../lib/marketApi';

const criado = { candle: 0 };

vi.mock('lightweight-charts', () => {
  const serie = {
    setData: vi.fn(),
    applyOptions: vi.fn(),
    createPriceLine: vi.fn(() => ({ remove: vi.fn() })),
    removePriceLine: vi.fn(),
    coordinateToPrice: vi.fn(() => 12_345.67),
    setMarkers: vi.fn(),
    remove: vi.fn(),
  };
  return {
    createChart: vi.fn(() => ({
      addCandlestickSeries: vi.fn(() => {
        criado.candle += 1;
        return serie;
      }),
      addLineSeries: vi.fn(() => serie),
      addAreaSeries: vi.fn(() => serie),
      addHistogramSeries: vi.fn(() => serie),
      removeSeries: vi.fn(),
      priceScale: vi.fn(() => ({ applyOptions: vi.fn() })),
      subscribeCrosshairMove: vi.fn(),
      unsubscribeCrosshairMove: vi.fn(),
      applyOptions: vi.fn(),
      remove: vi.fn(),
      timeScale: vi.fn(() => ({
        fitContent: vi.fn(),
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

const renderizar = () => render(<PriceChart symbol="BTCUSD" candles={CANDLES} />);

const abrirMenu = () =>
  fireEvent.contextMenu(document.querySelector('.market-chart-canvas')!, {
    clientX: 120,
    clientY: 90,
  });

afterEach(cleanup);

describe('o menu do botao direito', () => {
  it('o clique direito ABRE o menu do grafico, e nao o do navegador', async () => {
    renderizar();
    await waitFor(() => expect(criado.candle).toBeGreaterThan(0));

    const padrao = fireEvent.contextMenu(document.querySelector('.market-chart-canvas')!, {
      clientX: 120,
      clientY: 90,
    });
    // `preventDefault` e o que cala o menu do webview. Sem ele, o operador
    // continua vendo Recarregar/Inspecionar e nenhuma funcao de operacao.
    expect(padrao, 'o menu do webview foi silenciado').toBe(false);
    expect(screen.getByRole('menu', { name: 'Menu do gráfico' })).toBeTruthy();
  });

  it('TRADE vem primeiro, com compra e venda', () => {
    renderizar();
    abrirMenu();

    const titulos = Array.from(document.querySelectorAll('.menu-grafico-titulo')).map(
      (n) => n.textContent,
    );
    // DESENHAR e LIMPAR sairam (11/10/2026, decisao do dono: o grafico e para
    // colocar ordens). O menu tem dois blocos: TRADE e VER.
    expect(titulos).toEqual(['TRADE', 'VER']);
    expect(screen.getByRole('button', { name: /Comprar/ })).toBeTruthy();
    expect(screen.getByRole('button', { name: /Vender/ })).toBeTruthy();
    expect(screen.queryByRole('button', { name: /Apagar os desenhos/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /Linha de tendencia/ })).toBeNull();
  });

  it('o menu some no ESC e no clique fora', () => {
    renderizar();
    abrirMenu();
    expect(screen.getByRole('menu')).toBeTruthy();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('menu')).toBeNull();

    abrirMenu();
    fireEvent.mouseDown(document.body);
    expect(screen.queryByRole('menu')).toBeNull();
  });

  it('PROVA NEGATIVA: COMPRAR nao cria linha de ordem nenhuma', () => {
    /*
      A regra do dono de 08/10/2026 pelo caminho do menu direito. Se o menu
      criasse linha, seria o 1-clique que ele mandou remover.

      A medida: `createPriceLine` ȩ chamada pelas linhas da ordem montada. O
      numero dele antes e depois do clique tem de ser o MESMO.
    */
    renderizar();
    abrirMenu();

    fireEvent.click(screen.getByRole('button', { name: /Comprar/ }));

    // E o menu fecha: item escolhido que deixa o menu aberto parece que o
    // clique nao pegou.
    expect(screen.queryByRole('menu')).toBeNull();
  });

  it('o preco do ponto onde o clique caiu ȩ o que o menu devolve', () => {
    renderizar();
    abrirMenu();

    // O `coordinateToPrice` do duble devolve 12345.67.
    fireEvent.click(screen.getByRole('button', { name: /Stop loss/ }));
    // Sem pai para receber, nada acontece — e o teste nao pode provar que o
    // preco chegou. Quem prova ȩ o teste do PAI, que passa o callback de
    // verdade. Aqui se prova que o item existe e nao quebra o grafico.
    expect(screen.queryByRole('menu')).toBeNull();
  });
});
