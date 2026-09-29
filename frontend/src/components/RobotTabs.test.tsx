// @vitest-environment jsdom
// Sub-abas da aba Robô.
//
// Antes a aba devolvia oito painéis empilhados num único scroll; depois
// viraram cinco; depois quatro; agora cinco de novo, com EA proprio — Ordem e
// Ativos falavam do mesmo ativo, mas o Expert Advisor e outra responsabilidade
// (inventario do terminal + heartbeat + comando). O teste garante (a) que as
// cinco seções existem, (b) que só a ativa fica visível e (c) que os painéis
// escondidos CONTINUAM MONTADOS — desmontar jogaria fora a conversa do
// Copiloto e a seleção de ativo.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

vi.mock('./RobotModelPanel', () => ({ default: () => <div data-testid="painel-modelo" /> }));
vi.mock('./AutoEnginePanel', () => ({ default: () => <div data-testid="painel-auto" /> }));
vi.mock('./OrderPanel', () => ({ default: () => <div data-testid="painel-ordem" /> }));
vi.mock('./EAPanel', () => ({ default: () => <div data-testid="painel-ea" /> }));
vi.mock('./tabs/RiskTab', () => ({ default: () => <div data-testid="painel-risco" /> }));
vi.mock('./GuardianManager', () => ({ default: () => <div data-testid="painel-guardian" /> }));
vi.mock('./RobotAssetTableFixed', () => ({ default: () => <div data-testid="painel-ativos" /> }));
vi.mock('./CopilotPanel', () => ({ default: () => <div data-testid="painel-copiloto" /> }));
vi.mock('./UniversalLiveTerminalLatest', () => ({ default: () => <div data-testid="painel-mini" /> }));

const { default: RobotTabs } = await import('./RobotTabs');
const { useAppStore, ROBOT_SUBS } = await import('../hooks/useAppStore');

const visivel = (id: string) => {
  const painel = document.getElementById(id);
  expect(painel).not.toBeNull();
  return painel as HTMLElement;
};

describe('RobotTabs — sub-abas', () => {
  beforeEach(() => {
    useAppStore.setState({ robotSub: 'sinal' });
  });
  afterEach(() => cleanup());

  it('oferece as cinco seções aprovadas, nesta ordem', () => {
    render(<RobotTabs />);
    const tablist = screen.getByRole('tablist', { name: 'Seções do Robô' });
    const abas = Array.from(tablist.querySelectorAll('[role="tab"]')).map((b) => b.textContent);
    expect(abas).toEqual(['Sinal', 'Automação', 'Mesa', 'EA', 'Copiloto']);
    expect(ROBOT_SUBS).toEqual(['sinal', 'automacao', 'mesa', 'ea', 'copiloto']);
  });

  it('mostra só a seção ativa e mantém as demais montadas', () => {
    render(<RobotTabs />);
    expect(screen.getByTestId('painel-modelo')).toBeTruthy();
    expect(visivel('robot-panel-sinal').hidden).toBe(false);
    expect(visivel('robot-panel-mesa').hidden).toBe(true);
    expect(visivel('robot-panel-copiloto').hidden).toBe(true);
    // Montados, so escondidos.
    expect(screen.getByTestId('painel-ativos')).toBeTruthy();
    expect(screen.getByTestId('painel-copiloto')).toBeTruthy();
    expect(screen.getByTestId('painel-risco')).toBeTruthy();
    expect(screen.getByTestId('painel-ordem')).toBeTruthy();
    expect(screen.getByTestId('painel-ea')).toBeTruthy();
  });

  it('troca de seção e registra no store (persistindo a volta)', () => {
    render(<RobotTabs />);
    fireEvent.click(screen.getByRole('tab', { name: 'Mesa' }));
    expect(useAppStore.getState().robotSub).toBe('mesa');
    expect(visivel('robot-panel-mesa').hidden).toBe(false);
    expect(visivel('robot-panel-sinal').hidden).toBe(true);
    expect(screen.getByRole('tab', { name: 'Mesa' }).getAttribute('aria-selected')).toBe('true');
    expect(screen.getByRole('tab', { name: 'Sinal' }).getAttribute('aria-selected')).toBe('false');
  });

  it('Sinal junta modelo e ativos; Automação junta motor, risco e guardian', () => {
    render(<RobotTabs />);
    expect(screen.getByTestId('painel-modelo')).toBeTruthy();
    expect(screen.getByTestId('painel-ativos')).toBeTruthy();

    fireEvent.click(screen.getByRole('tab', { name: 'Automação' }));
    expect(screen.getByTestId('painel-auto')).toBeTruthy();
    expect(screen.getByTestId('painel-risco')).toBeTruthy();
    expect(screen.getByTestId('painel-guardian')).toBeTruthy();
    // Conferência, não comando: sempre visível, em qualquer sub-aba.
    expect(screen.getByTestId('painel-mini')).toBeTruthy();
  });

  it('abre na última seção usada quando o store já tem valor', () => {
    useAppStore.setState({ robotSub: 'copiloto' });
    render(<RobotTabs />);
    expect(visivel('robot-panel-copiloto').hidden).toBe(false);
    expect(screen.getByRole('tab', { name: 'Copiloto' }).getAttribute('aria-selected')).toBe('true');
  });

  it('nome antigo persistido (5 sub-abas) cai na sub-aba nova correspondente', async () => {
    const { LEGADO_ROBOT_SUB } = await import('../hooks/useAppStore');
    expect(LEGADO_ROBOT_SUB.ordem).toBe('mesa');
    expect(LEGADO_ROBOT_SUB.ativos).toBe('sinal');
    expect(LEGADO_ROBOT_SUB.operacao).toBe('automacao');
  });
});
