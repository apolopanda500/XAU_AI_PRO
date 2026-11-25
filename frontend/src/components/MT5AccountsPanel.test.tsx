// @vitest-environment jsdom
// O separador da conta MT5 e texto, nao entidade HTML escrita à mao.
//
// MEDIDO no APK 1.2.191 em Conexões & Corretoras: a sessao detectada e a
// lista de contas vinculadas mostravam `&middot;` como texto. Dentro de
// template string o JSX nao interpreta entidade — o operador via o codigo
// html no lugar do ponto mediano.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

const MERCADOS_MT5 = [
  'forex',
  'metals',
  'indices',
  'stocks',
  'commodities',
  'bonds',
  'crypto-spot',
  'crypto-futures',
  'other',
];

const M = vi.hoisted(() => ({
  conexoes: [] as Array<{ id: string; broker: string; market: string }>,
  terminal: null as null | { login: number; server: string; name: string },
  salvas: [] as string[],
  testadas: [] as string[],
  escopo: [] as string[],
  falharTeste: [] as string[],
}));

vi.mock('../lib/connections', () => ({
  marketsFor: () => MERCADOS_MT5,
  requestConnection: async () => ({ connections: M.conexoes }),
  detectTerminal: async () => {
    if (!M.terminal) throw new Error('sem terminal');
    return M.terminal;
  },
  saveExchange: async (_broker: string, market: string) => {
    const id = `mt5:${market}:420750145`;
    M.salvas.push(id);
    return id;
  },
  connectionAction: vi.fn(async (id: string) => {
    M.testadas.push(id);
    if (M.falharTeste.includes(id)) throw new Error('leitura indisponivel');
  }),
}));

vi.mock('../lib/escopoAtivo', () => ({
  // O escopo ativo aponta para a conta MT5 realmente vinculada, nao para um
  // id fixo: assim o selo "EM USO" da lista e exercitado na prova negativa.
  contaAtivaId: () =>
    M.conexoes.find((conta) => conta.broker === 'mt5')?.id ?? '',
  definirEscopoAtivo: (broker: string, market: string, id: string) => {
    M.escopo.push(`${broker}:${market}:${id}`);
  },
}));

const { default: MT5AccountsPanel } = await import('./MT5AccountsPanel');

describe('MT5AccountsPanel — separador da sessao e das contas', () => {
  beforeEach(() => {
    M.conexoes = [];
    M.salvas = [];
    M.testadas = [];
    M.escopo = [];
    M.falharTeste = [];
    M.terminal = {
      login: 420750145,
      server: 'XMGlobal-MT5 17',
      name: 'Michele Dos Santos',
    };
  });
  afterEach(() => cleanup());

  it('sessao detectada mostra o separador real, nunca a entidade literal', async () => {
    render(<MT5AccountsPanel />);
    await waitFor(() => {
      expect(screen.getByText(/420750145/)).toBeTruthy();
    });
    const texto = document.body.textContent ?? '';
    expect(texto).toContain('·');
    expect(texto).not.toContain('&middot;');
  });

  it('PROVA NEGATIVA: a lista de contas vinculadas tambem nao mostra entidade', async () => {
    M.conexoes = [{ id: 'x:mt5:forex:420750145', broker: 'mt5', market: 'forex' }];
    render(<MT5AccountsPanel />);
    await waitFor(() => {
      expect(screen.getAllByText(/420750145/).length).toBeGreaterThan(1);
    });
    const texto = document.body.textContent ?? '';
    expect(texto).toContain('EM USO');
    expect(texto).not.toContain('&middot;');
  });

  it('UM CLIQUE sincroniza os nove mercados e grava um unico escopo ativo', async () => {
    render(<MT5AccountsPanel />);
    await waitFor(() => expect(screen.getByText(/420750145/)).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: /Sincronizar MT5/ }));
    await waitFor(() => expect(M.salvas).toHaveLength(MERCADOS_MT5.length));
    expect(M.testadas).toEqual(M.salvas);
    expect(M.escopo).toHaveLength(1);
    expect(M.escopo[0]).toBe('mt5:forex:mt5:forex:420750145');
    const texto = document.body.textContent ?? '';
    expect(texto).toContain('9/9 mercados registrados');
    expect(texto).toContain('crypto-spot');
    expect(texto).toContain('Nenhuma ordem foi enviada.');
  });

  it('PROVA NEGATIVA: falha em um mercado nao apaga os outros e e dita na tela', async () => {
    M.falharTeste = ['mt5:indices:420750145'];
    render(<MT5AccountsPanel />);
    await waitFor(() => expect(screen.getByText(/420750145/)).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: /Sincronizar MT5/ }));
    await waitFor(() => expect(M.salvas).toHaveLength(MERCADOS_MT5.length));
    const texto = document.body.textContent ?? '';
    expect(texto).toContain('8/9 leituras validadas');
    expect(texto).toContain('indices (leitura indisponivel)');
    expect(texto).not.toContain('9/9 leituras validadas');
  });
});
