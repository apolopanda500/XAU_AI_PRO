// @vitest-environment jsdom
// A aba ROBÔ virou UMA SÓ em 2026-09-29.
//
// Antes: oito painéis num scroll, depois cinco, depois quatro, depois cinco com
// EA próprio. Cada mudança reorganizava o mesmo conteúdo.
//
// Agora: uma sub-aba, "Operar", com a mesa inteira na ordem em que se opera —
// automático, posições ao vivo, risco, ordem manual e guardian. "Sinal" e "EA"
// saíram porque obrigavam a trocar de tela para responder "qual ativo e modelo?"
// e "quanto posso arriscar?", que são a mesma pergunta.
//
// O que este teste garante:
//   (a) existe uma única sub-aba;
//   (b) os cinco painéis ficam MONTADOS juntos — desmontar jogaria fora a
//       seleção de ativo e qualquer leitura em andamento.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

vi.mock('./AutoEnginePanel', () => ({ default: () => <div data-testid="painel-auto" /> }));
vi.mock('./OrderPanel', () => ({ default: () => <div data-testid="painel-ordem" /> }));
vi.mock('./tabs/RiskTab', () => ({ default: () => <div data-testid="painel-risco" /> }));
vi.mock('./GuardianManager', () => ({ default: () => <div data-testid="painel-guardian" /> }));
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
    expect(screen.getByTestId('painel-ordem')).toBeTruthy();
    expect(screen.getByTestId('painel-guardian')).toBeTruthy();
    // E o Risco NAO esta mais aqui.
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
