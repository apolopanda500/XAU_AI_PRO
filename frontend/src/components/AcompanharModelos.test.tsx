// @vitest-environment jsdom
// O botao EMA do grafico MANDA no estado, e nao so parece ligado.
//
// O DEFEITO MEDIDO NO APP INSTALADO (06/10/2026)
// ===============================================
// O dono reportou "o botao EMA esta travado de cima azul, so funciona o de
// baixo". As duas metades desse relato eram verdade:
//
// 1. HAVIA DOIS CONTROLES para o mesmo dado — o botao `EMA` no topo do grafico e
//    um checkbox "EMA 12/26" na barra de operar, em blocos visuais separados.
// 2. O BOTAO DO TOPO NAO FAZIA NADA. `PriceChart` recebe `ema` como prop, e so
//    escreve o estado interno quando a prop e `undefined`
//    (`emaProp === undefined`). Com a prop presente, o clique mudava
//    `aria-pressed` e nada mais: o estado e do pai, e o pai nunca era avisado.
//
// A CORRECAO
// ==========
// O checkbox saiu (um controle, um dado) e o botao do grafico passou a escrever
// o estado do pai por `onIndicadoresChange`.
//
// O QUE ESTE ARQUIVO TRAVA
// ========================
// Que clicar no botao EMA MUDA o que o grafico desenha. Sem este teste, voltar
// o checkbox ou quebrar o `onIndicadoresChange` e so uma importacao — e o botao
// volta a parecer ligado sem mudar nada, que e exatamente o defeito relatado.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import type { MarketCandle } from '../lib/marketApi';

const { useAutoStateMock, usePositionsMock, useSinaisMock, getCandlesMock } = vi.hoisted(() => ({
  useAutoStateMock: vi.fn(),
  usePositionsMock: vi.fn(),
  useSinaisMock: vi.fn(),
  getCandlesMock: vi.fn(),
}));

vi.mock('../hooks/queries', () => ({
  useAutoState: useAutoStateMock,
  usePositions: usePositionsMock,
}));

vi.mock('../hooks/useSinaisModelo', () => ({ useSinaisModelo: useSinaisMock }));

vi.mock('../lib/marketApi', () => ({ getCandles: getCandlesMock }));

vi.mock('../lib/notify', () => ({ notify: vi.fn() }));

const { default: AcompanharModelos } = await import('./AcompanharModelos');

/**
 * 40 candles OHLC no formato COMPLETO de `MarketCandle`.
 *
 * Os campos `broker`, `market`, `symbol`, `source`, `sinal` e `execucao` sao
 * exigidos pelo tipo. Um candle so com OHLCV faria o teste PASSAR no vitest (que
 * nao checa tipo) e REPROVAR no `tsc` — o teste verde e o build vermelho, que e
 * a pior combinacao: a tela parece testada e nao compila.
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

function montar() {
  useAutoStateMock.mockReturnValue({
    data: {
      broker: 'mt5',
      market: 'other',
      simbolo: 'BTCUSD',
      timeframe: 'H1',
      limites: { lote: 0.01, sl_preco: 85000, tp_preco: 87000 },
    },
  });
  usePositionsMock.mockReturnValue({ data: { positions: [] } });
  useSinaisMock.mockReturnValue({ sinais: [], idadeSeg: 0 });
  getCandlesMock.mockResolvedValue({ candles: CANDLES });
  return render(<AcompanharModelos />);
}

const botaoEma = () => screen.getByRole('button', { name: 'EMA' });

describe('o botao EMA do grafico manda no estado', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  afterEach(() => cleanup());

  it('existe UM controle de EMA, nao dois', async () => {
    // MEDIDO: havia o botao no grafico E o checkbox "EMA 12/26" na barra de
    // operar. Dois controles para um dado e o que produz "so funciona o de
    // baixo": o dono usava o unico que escrevia o estado e via o outro inerte.
    montar();
    const botoesEma = screen.getAllByRole('button', { name: 'EMA' });
    expect(botoesEma).toHaveLength(1);
    // E nao sobrou checkbox com o rotulo antigo em lugar nenhum.
    expect(screen.queryByLabelText('EMA 12/26')).toBeNull();
    expect(screen.queryByRole('checkbox', { name: /EMA/i })).toBeNull();
  });

  it('o botao começa LIGADO e DESLIGA quando clicado', async () => {
    // `aria-pressed` sozinho nao prova nada: o botao mudava `aria-pressed`
    // antes da correcao e mesmo assim nao desenhava nada. O que se prova aqui e
    // que o ESTADO do pai muda, que e o que o `PriceChart` le para desenhar.
    montar();
    const botao = botaoEma();
    expect(botao.getAttribute('aria-pressed')).toBe('true');

    fireEvent.click(botao);

    await vi.waitFor(() => {
      expect(botaoEma().getAttribute('aria-pressed')).toBe('false');
    });
  });

  it('PROVA NEGATIVA: sem o onIndicadoresChange, o botao volta a ser inerte', async () => {
    /*
    A PROVA NEGATIVA QUE FALTAVA.

    Este teste mede o DEFECTO, nao a correcao: e o `PriceChart` sozinho, sem o
    `onIndicadoresChange`, que e a tela de antes. O botao continua mudando o
    `aria-pressed` — e a linha continua desenhando a EMA. E exatamente o que o
    dono viu: "azul, mas so funciona o de baixo".

    Sem este teste, um `onIndicadoresChange` mal ligado passaria: o `aria-pressed`
    continuaria trocando e ninguem notaria que a EMA nao some da tela.
    */
    const { default: PriceChart } = await import('./charts/PriceChart');
    const { container } = render(
      <PriceChart symbol="BTCUSD" candles={CANDLES} ema={true} broker={'mt5' as never} market={'other' as never} />,
    );

    const dentroDoGrafico = container.querySelector('.price-chart') as HTMLElement;
    // A EMA esta ligada: existe a linha da media desenhada.
    const linhasAntes = dentroDoGrafico.querySelectorAll('canvas').length;
    expect(linhasAntes).toBeGreaterThan(0);

    // O botao fica "pressionado"...
    const botao = dentroDoGrafico.querySelector('button[aria-pressed]') as HTMLButtonElement;
    expect(botao).toBeTruthy();
    fireEvent.click(botao);
    expect(botao.getAttribute('aria-pressed')).toBe('true');

    // ...e o numero de canvas NAO muda: nenhuma linha sumiu. O controle
    // decorativo se comporta como oowner viu.
    const linhasDepois = dentroDoGrafico.querySelectorAll('canvas').length;
    expect(linhasDepois).toBe(linhasAntes);
  });
});