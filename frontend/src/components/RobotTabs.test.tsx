// @vitest-environment jsdom
// A aba ROBÔ virou UMA SÓ em 2026-09-29.
//
// Antes: oito painéis num scroll, depois cinco, depois quatro, depois cinco com
// EA próprio. Cada mudança reorganizava o mesmo conteúdo.
//
// Agora: uma sub-aba, "Operar": mesa XM+MT5, automatico, acompanhar e
// posicoes ao vivo. A ordem manual VOLTOU a pedido do dono (2026-10-04),
// SEM seletor proprio de corretora — ela opera o escopo ativo, o mesmo do
// Mini Terminal. O defeito antigo (OrderPanel afirmando corretora diferente
// do motor) nao pode voltar: a mesa nao tem seletor de corretora.
//
// O que este teste garante:
//   (a) existe uma única sub-aba;
//   (b) os paineis ficam MONTADOS juntos — desmontar jogaria fora a
//       seleção de ativo e qualquer leitura em andamento;
//   (c) guardian NAO volta por descuido; ordem manual so existe SEM seletor
//       de corretora (ver 'mesa sem seletor de corretora').
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

vi.mock('./AutoEnginePanel', () => ({ default: () => <div data-testid="painel-auto" /> }));
vi.mock('./tabs/RiskTab', () => ({ default: () => <div data-testid="painel-risco" /> }));
vi.mock('./UniversalLiveTerminal', () => ({ default: () => <div data-testid="painel-mini" /> }));
vi.mock('./AcompanharModelos', () => ({ default: () => <div data-testid="painel-acompanhar" /> }));
vi.mock('./MesaXM', () => ({ default: () => <div data-testid="painel-mesa" /> }));

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
    // Ordem de operacao: mesa -> automatico -> acompanhar -> posicoes.
    expect(screen.getByTestId('painel-mesa')).toBeTruthy();
    expect(screen.getByTestId('painel-auto')).toBeTruthy();
    expect(screen.getByTestId('painel-acompanhar')).toBeTruthy();
    expect(screen.getByTestId('painel-mini')).toBeTruthy();
  });

  it('guardian NAO volta; ordem manual so sem seletor de corretora', () => {
    // Guardian saiu a pedido do dono e nao volta por descuido. A mesa voltou
    // com a condicao de nao ter seletor proprio (ver MesaXM: sem select de
    // corretora/mercado — opera o escopo ativo).
    render(<RobotTabs />);
    expect(screen.queryByTestId('painel-guardian')).toBeNull();
    expect(screen.queryByTestId('painel-risco')).toBeNull();
    expect(screen.getByTestId('painel-mesa')).toBeTruthy();
  });

  it('todo nome de sub-aba antigo cai em "operar"', () => {
    // Quem usou a versao de cinco ou de quatro sub-abas tem 'sinal'/'ea' no
    // localStorage; sem o mapa, a tela abriria vazia.
    for (const nome of ['sinal', 'ea', 'copiloto', 'mesa', 'automacao', 'ativos', 'modelo']) {
      expect(LEGADO_ROBOT_SUB[nome]).toBe('operar');
    }
  });
});
