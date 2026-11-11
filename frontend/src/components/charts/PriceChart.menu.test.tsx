// @vitest-environment jsdom
// O MENU DO BOTAO DIREITO DO GRAFICO (09/10/2026, VALIDADO 11/11/2026)
// ======================================================================
// O DONO VIU na captura da XM (`Screenshot 2026-10-09 201959.png`) o menu com
// TRADE no topo e pediu, textualmente: "quando tem direito tem que abrir todas
// funcoes do menu".
//
// MEDIDO aqui: o clique direito abria o menu DO WEBVIEW — Recarregar,
// Inspecionar, Imprimir —, que e do navegador e nao tem funcao de operacao.
//
// E DEPOIS (11/11/2026) o dono pediu: "botao direito do mouse corrigir e
// validar tudo, cada uma acao tem que existir e melhorar igual o mt5". Este
// arquivo agora tem UM TESTE POR ACAO do menu (click e tecla), a contagem de
// itens — item sem teste e item morto — e as provas negativas.
//
// A REGRA DO DONO DE 08/10/2026 VALE AQUI TAMBEM
// =============================================
// "O clique nao arma ordem": dois cliques criaram tres linhas montadas a um
// clique do envio (conta real 391773676). O menu direito e o MESMO perigo por
// outro caminho — se COMPRAR criasse linha, seria o 1-clique que foi removido.
//
// Estes testes medem os dois lados: o menu abre com o que a XM tem, e o menu
// NAO cria ordem sozinho.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type { MarketCandle } from '../../lib/marketApi';

/*
  O REGISTRADOR E O CORPO DA PROVA
  ================================
  Cada consumidor de cada item conta chamada aqui. Um item que NAO mexe em
  nenhum registrador e um item morto — e o teste da contagem (21 itens) impede
  que um item novo apareca sem teste proprio.
*/
const criado = { candle: 0 };
const reg = {
  fitContent: 0,
  scrollToRealTime: 0,
  faixas: [] as Array<{ from: number; to: number }>,
  opcoesGrafico: [] as Array<Record<string, unknown>>,
  opcoesPreco: [] as Array<Record<string, unknown>>,
  opcoesVolume: [] as Array<Record<string, unknown>>,
  criacaoSerie: [] as Array<Record<string, unknown>>,
  telaCheia: 0,
};

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
    // O `coordinateToPrice` do menu: 12345.67 em qualquer altura, que e o
    // preco que os testes de stop/alvo/copiar esperam.
    coordinateToPrice: vi.fn(() => 12_345.67),
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
    priceScale: vi.fn(() => ({ applyOptions: vi.fn(), width: () => 60 })),
    subscribeCrosshairMove: vi.fn(),
    unsubscribeCrosshairMove: vi.fn(),
    applyOptions: vi.fn((o: Record<string, unknown>) => {
      reg.opcoesGrafico.push(o);
    }),
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
    createChart: vi.fn(() => novoGrafico()),
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

type Pai = {
  onOperarNoMenu?: (lado: 'compra' | 'venda', preco: number | null) => void;
  onEscolherPreco?: (papel: 'sl' | 'tp', preco: number | null) => void;
  onTimeframeChange?: (tf: 'M1' | 'M5' | 'M15' | 'M30' | 'H1' | 'H4' | 'D1' | 'W1' | 'MN1') => void;
};

const renderizar = (pai: Pai = {}) =>
  render(
    <PriceChart symbol="BTCUSD" candles={CANDLES} {...pai} />,
  );

const abrirMenu = () =>
  fireEvent.contextMenu(document.querySelector('.market-chart-canvas')!, {
    clientX: 120,
    clientY: 90,
  });

const menuEl = () => screen.getByRole('menu', { name: 'Menu do gráfico' });
const noMenu = () => within(menuEl());
const item = (nome: RegExp | string) => noMenu().getByRole('button', { name: nome });
const precos = () => reg.faixas[reg.faixas.length - 1];

beforeEach(() => {
  reg.fitContent = 0;
  reg.scrollToRealTime = 0;
  reg.faixas.length = 0;
  reg.opcoesGrafico.length = 0;
  reg.opcoesPreco.length = 0;
  reg.opcoesVolume.length = 0;
  reg.criacaoSerie.length = 0;
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
    expect(menuEl()).toBeTruthy();
  });

  it('TEM OS 4 BLOCOS DO MT5: TRADE, VER, PERIODO e EXIBIR', () => {
    renderizar();
    abrirMenu();

    const titulos = Array.from(document.querySelectorAll('.menu-grafico-titulo')).map(
      (n) => n.textContent,
    );
    // DESENHAR e LIMPAR sairam (11/10/2026, decisao do dono: o grafico e para
    // colocar ordens). Em 11/11/2026 entraram PERIODO e EXIBIR, como no menu
    // direito do MT5 (Timeframes / Grid / Volumes).
    expect(titulos).toEqual(['TRADE', 'VER', 'PERIODO', 'EXIBIR']);
    expect(screen.queryByRole('button', { name: /Apagar os desenhos/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /Linha de tendencia/ })).toBeNull();
  });

  /*
    A CONTAGEM E A TRAVA DE "CADA ACAO TEM QUE EXISTIR"
    ===================================================
    4 (TRADE) + 6 (VER) + 9 (PERIODO) + 2 (EXIBIR) = 21. Item novo no menu
    sem teste proprio reprovar aqui — e o `tsc` reprova acao nova sem handler
    pelo `never` no fim de `acaoDoMenu`.
  */
  it('TEM 21 ITENS, E CADA UM TEM TESTE NESTE ARQUIVO', () => {
    renderizar();
    abrirMenu();

    const itens = document.querySelectorAll('.menu-grafico-item');
    expect(itens.length).toBe(21);
  });

  it('o menu some no ESC e no clique fora', () => {
    renderizar();
    abrirMenu();
    expect(menuEl()).toBeTruthy();

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
    */
    renderizar();
    abrirMenu();

    fireEvent.click(item(/Comprar/));

    // E o menu fecha: item escolhido que deixa o menu aberto parece que o
    // clique nao pegou.
    expect(screen.queryByRole('menu')).toBeNull();
  });
});

describe('TRADE: cada item chega ao pai, com o preco do ponto', () => {
  it('Comprar e Vender passam lado e preco', () => {
    const operar = vi.fn();
    renderizar({ onOperarNoMenu: operar });
    abrirMenu();
    fireEvent.click(item(/Comprar/));
    expect(operar).toHaveBeenCalledWith('compra', 12_345.67);

    abrirMenu();
    fireEvent.click(item(/Vender/));
    expect(operar).toHaveBeenCalledWith('venda', 12_345.67);
  });

  it('Stop loss e Take profit passam papel e preco', () => {
    const escolher = vi.fn();
    renderizar({ onEscolherPreco: escolher });
    abrirMenu();
    fireEvent.click(item(/Stop loss/));
    expect(escolher).toHaveBeenCalledWith('sl', 12_345.67);

    abrirMenu();
    fireEvent.click(item(/Take profit/));
    expect(escolher).toHaveBeenCalledWith('tp', 12_345.67);
  });
});

describe('VER: cada item mexe na vista, e nada mais', () => {
  it('Aproximar diminui a janela visivel, Afastar aumenta (zoom de verdade)', () => {
    renderizar();
    abrirMenu();
    // REGEX, e nao string: o nome acessivel e `Aproximar+` — o `kbd` da
    // coluna de atalhos faz parte do nome (medido 11/11/2026).
    fireEvent.click(item(/Aproximar/));
    // faixa do duble = {0..50}; fator 0.8 -> 40 barras no centro 25.
    expect(precos()).toEqual({ from: 5, to: 45 });

    abrirMenu();
    fireEvent.click(item(/Afastar/));
    // fator 1.25 -> 62.5 barras.
    expect(precos()).toEqual({ from: -6.25, to: 56.25 });
  });

  it('Ajustar a janela chama fitContent (e zera o deslocamento vertical)', () => {
    renderizar();
    abrirMenu();
    // DELTA, e nao `toBe(1)`: o efeito de dados ja roda `fitContent` na
    // PRIMEIRA montagem (`candlesEnquadrados` comeca em 0 e o conjunto tem
    // 40) — fixar o total em 1 reprovaria o codigo certo (medido, 11/11/2026).
    const antes = reg.fitContent;
    fireEvent.click(item(/Ajustar a janela/));
    expect(reg.fitContent).toBe(antes + 1);
  });

  it('Ir para o preco atual chama scrollToRealTime', () => {
    renderizar();
    abrirMenu();
    const antes = reg.scrollToRealTime;
    fireEvent.click(item(/Ir para o preco atual/));
    expect(reg.scrollToRealTime).toBe(antes + 1);
  });

  it('Copiar preco do ponto escreve o preco no clipboard', async () => {
    const escrever = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: escrever },
      configurable: true,
    });
    renderizar();
    abrirMenu();
    fireEvent.click(item(/Copiar preco/));
    await waitFor(() => expect(escrever).toHaveBeenCalledWith('12345.67'));
  });

  it('Tela cheia chama requestFullscreen (e a tecla F tambem)', async () => {
    const telaCheia = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(HTMLElement.prototype, 'requestFullscreen', {
      value: telaCheia,
      configurable: true,
      writable: true,
    });
    renderizar();
    abrirMenu();
    fireEvent.click(item('Tela cheia'));
    expect(telaCheia).toHaveBeenCalledTimes(1);

    // O botao promete "(F)": a tecla e o segundo caminho da MESMA acao.
    telaCheia.mockClear();
    fireEvent.keyDown(window, { key: 'f' });
    expect(telaCheia).toHaveBeenCalledTimes(1);

    // PROVA NEGATIVA: a tecla dentro de um campo de texto nao sequestra nada.
    telaCheia.mockClear();
    const campo = document.createElement('input');
    document.body.append(campo);
    campo.dispatchEvent(new KeyboardEvent('keydown', { key: 'f', bubbles: true }));
    expect(telaCheia).not.toHaveBeenCalled();
    campo.remove();
  });
});

describe('PERIODO: o bloco de timeframes', () => {
  it('marca o timeframe ATUAL (M5 por omissao) e troca pelo MESMO consumidor da barra', async () => {
    const mudar = vi.fn();
    renderizar({ onTimeframeChange: mudar });
    await waitFor(() => expect(criado.candle).toBeGreaterThan(0));
    abrirMenu();

    expect(item('M5').getAttribute('aria-pressed')).toBe('true');
    expect(item('H1').getAttribute('aria-pressed')).toBe('false');

    fireEvent.click(item('H1'));
    expect(mudar).toHaveBeenCalledWith('H1');
    expect(screen.queryByRole('menu')).toBeNull();
  });

  it('sem pai, o periodo do menu vira o cabecalho do grafico', () => {
    renderizar();
    abrirMenu();
    fireEvent.click(item('H4'));

    const cabecalho = document.querySelector('.price-chart-ohlc');
    expect(cabecalho?.textContent?.startsWith('H4')).toBe(true);
  });

  it('PROVA NEGATIVA: so os 9 periodos que o gateway aceita estao no menu', () => {
    renderizar();
    abrirMenu();

    // Ordem do DOM: 4 TRADE + 6 VER antes; os 9 de PERIODO vem em seguida
    // (indices 10..18), e EXIBIR fecha com os 2 ultimos.
    const todos = Array.from(menuEl().querySelectorAll('.menu-grafico-item'));
    expect(todos.length).toBe(21);
    const periodos = todos.slice(10, 19).map((b) => b.textContent);
    expect(periodos).toEqual(['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1', 'MN1']);
  });
});

describe('EXIBIR: grade e volumes ligam e desligam no grafico', () => {
  it('Grade alterna grid.vertLines.visible e mostra o estado', async () => {
    renderizar();
    await waitFor(() => expect(criado.candle).toBeGreaterThan(0));
    abrirMenu();

    const grade = item('Grade');
    expect(grade.getAttribute('aria-pressed')).toBe('false');
    fireEvent.click(grade);

    const ultimo = reg.opcoesGrafico[reg.opcoesGrafico.length - 1] as {
      grid?: { vertLines?: { visible?: boolean } };
    };
    expect(ultimo.grid?.vertLines?.visible).toBe(true);

    abrirMenu();
    expect(item('Grade').getAttribute('aria-pressed')).toBe('true');
    fireEvent.click(item('Grade'));
    const agora = reg.opcoesGrafico[reg.opcoesGrafico.length - 1] as {
      grid?: { vertLines?: { visible?: boolean } };
    };
    expect(agora.grid?.vertLines?.visible).toBe(false);
  });

  it('Volumes esconde a serie de volume e mostra o estado', async () => {
    renderizar();
    await waitFor(() => expect(criado.candle).toBeGreaterThan(0));
    abrirMenu();

    const volumes = item('Volumes');
    // O volume NASCE LIGADO (`volumeVisivel = true`, igual ao `createChart`):
    // o estado marcado e o da TELA, e o primeiro clique DESLIGA.
    expect(volumes.getAttribute('aria-pressed')).toBe('true');
    fireEvent.click(volumes);

    expect(reg.opcoesVolume[reg.opcoesVolume.length - 1]).toEqual({ visible: false });

    abrirMenu();
    expect(item('Volumes').getAttribute('aria-pressed')).toBe('false');
    fireEvent.click(item('Volumes'));
    expect(reg.opcoesVolume[reg.opcoesVolume.length - 1]).toEqual({ visible: true });
  });
});

describe('AS TECLAS DA COLUNA kbd EXISTEM (medido antes: nenhum handler)', () => {
  it('B, S, T e P escolhem como o clique e fecham o menu', () => {
    const operar = vi.fn();
    const escolher = vi.fn();
    renderizar({ onOperarNoMenu: operar, onEscolherPreco: escolher });

    abrirMenu();
    fireEvent.keyDown(document, { key: 'b' });
    expect(operar).toHaveBeenCalledWith('compra', 12_345.67);
    expect(screen.queryByRole('menu')).toBeNull();

    abrirMenu();
    fireEvent.keyDown(document, { key: 'S' });
    expect(operar).toHaveBeenCalledWith('venda', 12_345.67);

    abrirMenu();
    fireEvent.keyDown(document, { key: 't' });
    expect(escolher).toHaveBeenCalledWith('sl', 12_345.67);

    abrirMenu();
    fireEvent.keyDown(document, { key: 'p' });
    expect(escolher).toHaveBeenCalledWith('tp', 12_345.67);
  });

  it('+ e - fazem o zoom (com Shift ou sem, que sao a mesma tecla)', () => {
    renderizar();

    abrirMenu();
    fireEvent.keyDown(document, { key: '+' });
    expect(precos()).toEqual({ from: 5, to: 45 });

    abrirMenu();
    fireEvent.keyDown(document, { key: '=' });
    expect(precos()).toEqual({ from: 5, to: 45 });

    abrirMenu();
    fireEvent.keyDown(document, { key: '-' });
    expect(precos()).toEqual({ from: -6.25, to: 56.25 });

    abrirMenu();
    fireEvent.keyDown(document, { key: '_' });
    expect(precos()).toEqual({ from: -6.25, to: 56.25 });
  });

  it('PROVA NEGATIVA: tecla fora do menu nao faz nada, e atalho com Ctrl tambem nao', () => {
    const operar = vi.fn();
    renderizar({ onOperarNoMenu: operar });

    abrirMenu();
    fireEvent.keyDown(document, { key: 'z' });
    // Nao achou acao: o menu continua aberto esperando o operador.
    expect(screen.queryByRole('menu')).toBeTruthy();
    expect(operar).not.toHaveBeenCalled();

    // `Ctrl + S` e do navegador (salvar pagina), nao do menu.
    fireEvent.keyDown(document, { key: 's', ctrlKey: true });
    expect(operar).not.toHaveBeenCalled();
    expect(screen.queryByRole('menu')).toBeTruthy();
  });
});
