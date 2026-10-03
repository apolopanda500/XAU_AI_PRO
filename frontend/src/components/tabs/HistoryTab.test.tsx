// @vitest-environment jsdom
// Uma fonte só de histórico para Histórico + Performance & Analytics.
//
// O bug corrigido aqui: as duas seções chamavam `useHistorico` com filtros
// diferentes (Histórico: broker/ativo/período, padrão "Hoje"; Analytics fixo
// em mt5/90 dias) e ficavam lado a lado no mesmo scroll com números
// diferentes para a mesma conta, e o Atualizar de uma não movia a outra.
// Agora HistoryTab monta o hook UMA vez e repassa deals/status/loading.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';

const { useHistoricoMock } = vi.hoisted(() => ({ useHistoricoMock: vi.fn() }));

vi.mock('../../lib/historico', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/historico')>();
  return { ...actual, useHistorico: useHistoricoMock };
});

const { default: HistoryTab } = await import('./HistoryTab');

const DEALS = [
  {
    id: 'd1', broker: 'mt5', symbol: 'XAUUSD', side: 'buy',
    quantity: 0.1, price: 2400, realizedPnl: 100, executedAt: '2026-09-28T10:00:00Z',
  },
  {
    id: 'd2', broker: 'mt5', symbol: 'XAUUSD', side: 'sell',
    quantity: 0.1, price: 2410, realizedPnl: -50, executedAt: '2026-09-28T11:00:00Z',
  },
];

function devolver(extra: Record<string, unknown> = {}) {
  useHistoricoMock.mockReturnValue({
    deals: DEALS,
    loading: false,
    erro: '',
    status: 'mt5 ok',
    updatedAt: '10:30:00',
    recarregar: vi.fn(),
    ...extra,
  });
}

describe('HistoryTab — histórico e analytics compartilham a mesma fonte', () => {
  beforeEach(() => devolver());
  afterEach(() => cleanup());

  it('monta useHistorico uma unica vez', () => {
    render(<HistoryTab />);
    expect(useHistoricoMock).toHaveBeenCalledTimes(1);
  });

  it('mostra a mesma quantidade de operacoes nas duas secoes', () => {
    const { container } = render(<HistoryTab />);
    // Historico: "PnL do período" conta as 2 operacoes.
    const cards = container.querySelectorAll('.metrics-grid .metric-card');
    expect([...cards].some((c) => c.textContent?.includes('2 operações'))).toBe(true);
    // Analytics: mesmo conjunto (2 trades, 50% de acerto) no card Win Rate.
    const analytics = container.querySelector('.analytics-page');
    expect(analytics).not.toBeNull();
    expect(analytics?.textContent).toContain('2 trades');
    expect(analytics?.textContent).toContain('50.00%');
    expect(analytics?.textContent).toContain('50,00 USD');
  });

  it('recarregar do analytics usa o hook do historico', () => {
    const recarregar = vi.fn();
    devolver({ recarregar });
    const { container } = render(<HistoryTab />);
    const analytics = container.querySelector('.analytics-page');
    const botao = within(analytics as HTMLElement).getByRole('button', { name: 'Atualizar' });
    fireEvent.click(botao);
    expect(recarregar).toHaveBeenCalledTimes(1);
    expect(useHistoricoMock).toHaveBeenCalledTimes(1);
  });

  it('botao de atualizar desabilita com texto de progresso nas duas secoes', () => {
    devolver({ loading: true });
    const { container } = render(<HistoryTab />);
    const historico = container.querySelector('.history-page');
    const analytics = container.querySelector('.analytics-page');
    const b1 = within(historico as HTMLElement).getByRole('button', { name: 'Atualizando…' });
    const b2 = within(analytics as HTMLElement).getByRole('button', { name: 'Atualizando…' });
    expect((b1 as HTMLButtonElement).disabled).toBe(true);
    expect((b2 as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryAllByText('Atualizar')).toHaveLength(0);
  });

  it('Analytics explica o vazio usando o filtro do Historico', () => {
    devolver({ deals: [], loading: false });
    const { container } = render(<HistoryTab />);
    expect(container.querySelector('.analytics-page')?.textContent)
      .toContain('Nenhuma operacao fechada no periodo do filtro do Historico acima.');
  });
});
