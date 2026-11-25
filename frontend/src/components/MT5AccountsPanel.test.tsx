// @vitest-environment jsdom
// O separador da conta MT5 e texto, nao entidade HTML escrita à mao.
//
// MEDIDO no APK 1.2.191 em Conexões & Corretoras: a sessao detectada e a
// lista de contas vinculadas mostravam `&middot;` como texto. Dentro de
// template string o JSX nao interpreta entidade — o operador via o codigo
// html no lugar do ponto mediano.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';

const M = vi.hoisted(() => ({
  conexoes: [] as Array<{ id: string; broker: string; market: string }>,
  terminal: null as null | { login: number; server: string; name: string },
}));

vi.mock('../lib/connections', () => ({
  marketsFor: () => ['forex'],
  requestConnection: async () => ({ connections: M.conexoes }),
  detectTerminal: async () => {
    if (!M.terminal) throw new Error('sem terminal');
    return M.terminal;
  },
  saveExchange: async () => 'id-mt5-1',
  connectionAction: async () => {},
}));

vi.mock('../lib/escopoAtivo', () => ({
  // O escopo ativo aponta para a conta MT5 realmente vinculada, nao para um
  // id fixo: assim o selo "EM USO" da lista e exercitado na prova negativa.
  contaAtivaId: () =>
    M.conexoes.find((conta) => conta.broker === 'mt5')?.id ?? '',
  definirEscopoAtivo: () => {},
}));

const { default: MT5AccountsPanel } = await import('./MT5AccountsPanel');

describe('MT5AccountsPanel — separador da sessao e das contas', () => {
  beforeEach(() => {
    M.conexoes = [];
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
});
