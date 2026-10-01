// @vitest-environment jsdom
// A aba ROBÔ virou UMA SÓ em 2026-09-29.
//
// Antes: oito painéis num scroll, depois cinco, depois quatro, depois cinco com
// EA próprio. Cada mudança reorganizava o mesmo conteúdo.
//
// Agora: uma sub-aba, "Operar", com DOIS painéis — automático e posições ao
// vivo (2026-09-30). Ordem manual e guardian SAÍRAM a pedido do dono:
// "operacao automatica, terminal, posicoes abertas so isso".
//
// A ordem manual saía principalmente por duplicar o seletor de corretora: o
// OrderPanel mantem o proprio `Broker`/`MERCADOS`, e a tela podia afirmar uma
// corretora enquanto o motor operava outra.
//
// O que este teste garante:
//   (a) existe uma única sub-aba;
//   (b) os dois painéis ficam MONTADOS juntos — desmontar jogaria fora a
//       seleção de ativo e qualquer leitura em andamento;
//   (c) ordem manual e guardian NAO voltam por descuido.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

vi.mock('./AutoEnginePanel', () => ({ default: () => <div data-testid="painel-auto" /> }));
vi.mock('./tabs/RiskTab', () => ({ default: () => <div data-testid="painel-risco" /> }));
vi.mock('./UniversalLiveTerminal', () => ({ default: () => <div data-testid="painel-mini" /> }));

const { default: RobotTabs } = await import('./RobotTabs');
const { useAppStore, ROBOT_SUBS, LEGADO_ROBOT_SUB } = await import('../hooks/useAppStore');

const visivel = (id: string) => {
  const painel = document.getElementById(id);
  expect(painel).not.toBeNull();
  return painel as HTMLElement;
};

describe('RobotTabs — sub-aba unica', () => {
  beforeEach(() => {
    useAppStore.setState({ robotSub: 'operar' });
  });
  afterEach(() => cleanup());

  it('oferece uma unica sub-aba, "Operar"', () => {
    render(<RobotTabs />);
    const tablist = screen.getByRole('tablist', { name: 'Seções de operação' });
    const abas = Array.from(tablist.querySelectorAll('[role="tab"]')).map((b) => b.textContent);
    expect(abas).toEqual(['Operar']);
    expect(ROBOT_SUBS).toEqual(['operar']);
  });

  it('a mesa inteira esta montada na mesma tela', () => {
    render(<RobotTabs />);
    expect(visivel('robot-panel-operar').hidden).toBe(false);
    // Ordem de operacao: decide -> acompanha -> envia -> protege.
    // O Risco saiu daqui em 2026-09-29: ele trazia a parada de emergencia,
    // que ja existia tambem no OrderPanel. Dois botoes de corte na mesma tela
    // e o risco real de o operador clicar no errado; ficou so o do OrderPanel.
    expect(screen.getByTestId('painel-auto')).toBeTruthy();
    expect(screen.getByTestId('painel-mini')).toBeTruthy();
  });

  it('ordem manual e guardian NAO estao mais na aba Robo', () => {
    // Regressao de 2026-09-30: o dono pediu "so isso" e a tela ainda tinha os
    // quatro blocos. Este teste existe para o bloco nao voltar por engano.
    render(<RobotTabs />);
    expect(screen.queryByTestId('painel-ordem')).toBeNull();
    expect(screen.queryByTestId('painel-guardian')).toBeNull();
    expect(screen.queryByTestId('painel-risco')).toBeNull();
  });

  it('todo nome de sub-aba antigo cai em "operar"', () => {
    // Quem usou a versao de cinco ou de quatro sub-abas tem 'sinal'/'ea' no
    // localStorage; sem o mapa, a tela abriria vazia.
    for (const nome of ['sinal', 'ea', 'copiloto', 'mesa', 'automacao', 'ativos', 'modelo']) {
      expect(LEGADO_ROBOT_SUB[nome]).toBe('operar');
    }
  });
});
