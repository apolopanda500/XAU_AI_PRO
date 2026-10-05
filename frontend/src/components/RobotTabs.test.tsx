// @vitest-environment jsdom
// A aba ROBO tem DUAS sub-abas desde 2026-10-04 (antes: tudo empilhado, depois
// tres — a automacao duplicava os comandos da mesa).
//
//   Mesa       → comandos simples + lista de modelos + AUTO SIM/NAO
//   Acompanhar → grafico ao vivo operavel (1-clique, TP/SL arrastavel)
//
// O Mini Terminal fica sempre visivel no fim (conferencia).
//
// O que este teste garante:
//   (a) as duas sub-abas existem;
//   (b) os paineis ficam MONTADOS juntos — desmontar jogaria fora a
//       seleção de ativo e qualquer leitura em andamento;
//   (c) guardian e painel de automacao separado NAO voltam por descuido.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

vi.mock('./AutoEnginePanel', () => ({ default: () => <div data-testid="painel-auto" /> }));
vi.mock('./tabs/RiskTab', () => ({ default: () => <div data-testid="painel-risco" /> }));
vi.mock('./UniversalLiveTerminal', () => ({ default: () => <div data-testid="painel-mini" /> }));
vi.mock('./AcompanharModelos', () => ({ default: () => <div data-testid="painel-acompanhar" /> }));
vi.mock('./MesaXM', () => ({ default: () => <div data-testid="painel-mesa" /> }));
vi.mock('./RobotModelPanel', () => ({ default: () => <div data-testid="painel-modelos" /> }));

const { default: RobotTabs } = await import('./RobotTabs');
const { useAppStore, ROBOT_SUBS, LEGADO_ROBOT_SUB } = await import('../hooks/useAppStore');

const visivel = (id: string) => {
  const painel = document.getElementById(id);
  expect(painel).not.toBeNull();
  return painel as HTMLElement;
};

describe('RobotTabs — duas sub-abas', () => {
  beforeEach(() => {
    useAppStore.setState({ robotSub: 'mesa' });
  });
  afterEach(() => cleanup());

  it('oferece Mesa e Acompanhar', () => {
    render(<RobotTabs />);
    const tablist = screen.getByRole('tablist', { name: 'Seções de operação' });
    const abas = Array.from(tablist.querySelectorAll('[role="tab"]')).map((b) => b.textContent);
    expect(abas).toEqual(['Mesa', 'Acompanhar']);
    expect(ROBOT_SUBS).toEqual(['mesa', 'acompanhar']);
  });

  it('a mesa inteira esta montada na mesma tela', () => {
    render(<RobotTabs />);
    // Mesa ativa por padrao; Acompanhar escondida com hidden, sem desmontar.
    expect(visivel('robot-panel-mesa').hidden).toBe(false);
    expect(visivel('robot-panel-acompanhar').hidden).toBe(true);
    expect(screen.getByTestId('painel-mesa')).toBeTruthy();
    expect(screen.getByTestId('painel-modelos')).toBeTruthy();
    expect(screen.getByTestId('painel-acompanhar')).toBeTruthy();
    // Mini Terminal sempre visivel no fim (conferencia).
    expect(screen.getByTestId('painel-mini')).toBeTruthy();
  });

  it('automacao separada e guardian NAO voltam', () => {
    // A automacao fundiu na Mesa (mesmo LOTE/SL/TP, AUTO SIM/NAO). Painel
    // separado mandando no motor era comando repetido.
    render(<RobotTabs />);
    expect(screen.queryByTestId('painel-auto')).toBeNull();
    expect(screen.queryByTestId('painel-guardian')).toBeNull();
    expect(screen.queryByTestId('painel-risco')).toBeNull();
    expect(screen.getByTestId('painel-mesa')).toBeTruthy();
  });

  it('todo nome de sub-aba antigo cai numa valida', () => {
    // Quem usou versao antiga tem 'sinal'/'ea'/'operar'/'auto' no
    // localStorage; sem o mapa, a tela abriria vazia.
    expect(LEGADO_ROBOT_SUB['operar']).toBe('mesa');
    expect(LEGADO_ROBOT_SUB['auto']).toBe('mesa');
    for (const nome of ['sinal', 'ea', 'copiloto', 'automacao', 'mesa']) {
      expect(['mesa', 'acompanhar']).toContain(LEGADO_ROBOT_SUB[nome]);
    }
  });
});
