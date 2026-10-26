// @vitest-environment jsdom
/*
  POSICOES COM OS DOIS NOMES DO MESMO DADO (25/10/2026)
  =====================================================
  MEDIDO na DEMO 113568614, app 1.2.9: a tabela "Terminal ao vivo" mostrava
  ticket e ativo, e TODA a fila de dados `--` (Vol, Abertura, Atual, SL, TP,
  PnL). Causa: `_universal_positions` devolve para MT5 as linhas LEGADO
  (`volume`, `open_price`, `price_current`, `sl`, `tp`, `profit`, `type`)
  e a traducao so lia os nomes do contrato universal (`quantity`, ...).
  Dois lados do mesmo dado divergindo do nome (AGENTS.md 5).

  Este teste monta cada cenario (universal e legado) e exige a MESMA tabela
  preenchida — exercitando o caminho inteiro do componente, nao a funcao de
  traducao isolada (AGENTS.md 6).
*/
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';

const estado = vi.hoisted(() => ({
  posicoes: [] as Array<Record<string, unknown>>,
}));

vi.mock('../hooks/queries', () => ({
  useCoreStatus: () => ({ data: { pronto: true, ligado: false } }),
  useAccount: () => ({ data: { login: 113568614, balance: 10021.59, equity: 10009.71, margin: 206.79, margin_free: 9802.92, level: 4841 },
  }),
  usePositions: () => ({ data: { positions: [] } }),
  useJournal: () => ({ data: { lines: [] }, isFetching: false }),
  useAllCryptoAccounts: () => ({ data: [] }),
  useAutoState: () => ({ data: null }),
  useUniversalOverview: () => ({ data: { connections: [] } }),
  useUniversalAccount: () => ({ data: {} }),
  useUniversalPositions: () => ({ data: { positions: estado.posicoes } }),
}));

import UniversalLiveTerminal from './UniversalLiveTerminal';

const celulaDaLinha = (trecho: string, indice: number): string => {
  const linha = Array.from(document.querySelectorAll('tr')).find((tr) =>
    (tr.textContent ?? '').includes(trecho),
  );
  if (!linha) throw new Error(`linha nao encontrada na tela: ${trecho}`);
  const colunas = Array.from(linha.querySelectorAll('td'));
  return colunas[indice]?.textContent ?? '';
};

afterEach(cleanup);

describe('as colunas de posicao vem, venham os nomes que vierem', () => {
  it('nomes universais (exchange) preenchem a tabela', () => {
    estado.posicoes = [
      {
        ticket: '9001',
        symbol: 'BTCUSDT',
        side: 'BUY',
        quantity: 0.01,
        entry_price: 60000,
        mark_price: 60500,
        stop_loss: 59000,
        take_profit: 62000,
        unrealized_pnl: 5.0,
      },
    ];
    render(<UniversalLiveTerminal />);
    const linha = Array.from(document.querySelectorAll('tr')).find((tr) =>
      (tr.textContent ?? '').includes('9001'),
    );
    expect(linha).toBeTruthy();
    // Tipos segue a ordem do JSX: Ticket, Ativo, Lado, Vol, Abertura, Atual, SL, TP, Swap, PnL.
    expect(celulaDaLinha('9001', 3)).toContain('0,01');
    expect(celulaDaLinha('9001', 4)).toContain('60\.000');
    expect(celulaDaLinha('9001', 5)).toContain('60\.500');
    expect(celulaDaLinha('9001', 6)).toContain('59\.000');
    expect(celulaDaLinha('9001', 7)).toContain('62\.000');
    expect(celulaDaLinha('9001', 9)).toContain('5,00');
  });

  it('nomes legados (payload cru do MT5) preenchem a MESMA tabela', () => {
    estado.posicoes = [
      {
        ticket: '11079037885',
        symbol: 'USDCHF',
        type: 'BUY',
        volume: 0.2,
        open_price: 0.82092,
        price_current: 0.8215,
        sl: 0.81890,
        tp: 0.82500,
        profit: 1.41,
      },
    ];
    render(<UniversalLiveTerminal />);
    expect(celulaDaLinha('11079037885', 1)).toContain('USDCHF');
    expect(celulaDaLinha('11079037885', 2)).toContain('BUY');
    expect(celulaDaLinha('11079037885', 3)).toContain('0,20');
    expect(celulaDaLinha('11079037885', 4)).toContain('0,82');
    expect(celulaDaLinha('11079037885', 5)).toContain('0,82');
    expect(celulaDaLinha('11079037885', 6)).toContain('0,82');
    expect(celulaDaLinha('11079037885', 7)).toContain('0,83');
    expect(celulaDaLinha('11079037885', 9)).toContain('1,41');
  });

  it('PROVA NEGATIVA: sem dados, a celula continua -- (e nao 0,00 nem vazia)', () => {
    estado.posicoes = [{ ticket: '777', symbol: 'XAUUSD' }];
    render(<UniversalLiveTerminal />);
    expect(celulaDaLinha('777', 3)).toContain('--');
    expect(celulaDaLinha('777', 9)).toContain('--');
  });
});
