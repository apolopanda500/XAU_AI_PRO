// @vitest-environment jsdom
// Configurações → Plano (11/10/2026).
//
// O QUE ESTE ARQUIVO TRAVA
// ========================
// O 403 `PLAN_REQUIRED` do motor automático chegava na tela como um erro
// mudo, enquanto o gateway já expunha as três rotas de assinatura e o
// frontend não tinha UM consumidor delas. `PlanoConfig` é o desbloqueio:
//
//   - os nomes vêm do CATÁLOGO que o gateway devolve, nunca do componente;
//   - "Ativar" faz POST `/api/subscriptions/activate` (local, sem cobrança)
//     e depois REPERGUNTA `/api/subscriptions/me` — a tela mostra o que o
//     gateway respondeu, não o que o botão acreditou ter feito;
//   - a trava de dinheiro real (`withdrawals_enabled`) é declaração na tela,
//     não interruptor (AGENTS.md 2).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const estado = vi.hoisted(() => ({
  chamadas: [] as string[],
  planoAtivo: 'free',
  recusarAtivacao: null as string | null,
}));

const mockFetch = async (url: string, init?: RequestInit) => {
  estado.chamadas.push(String(url));
  if (String(url).includes('/api/subscriptions/me')) {
    return {
      ok: true,
      json: async () => ({
        ok: true,
        subscription: {
          plan_id: estado.planoAtivo,
          effective_plan_id: estado.planoAtivo,
          active: true,
          plan: {
            id: estado.planoAtivo,
            name: estado.planoAtivo === 'free' ? 'Free' : 'Ouro',
            description: 'Plano lido do gateway.',
          },
          live_execution: false,
          withdrawals_enabled: false,
        },
      }),
    };
  }
  if (String(url).includes('/api/subscriptions/plans')) {
    return {
      ok: true,
      json: async () => ({
        ok: true,
        plans: [
          { id: 'free', name: 'Free', description: 'Operação local básica.', features: ['Paper/demo'] },
          { id: 'ouro', name: 'Ouro', description: 'Automacao completa.', features: ['Motor automatico'] },
        ],
        withdrawals_enabled: false,
      }),
    };
  }
  if (String(url).includes('/api/subscriptions/activate')) {
    if (estado.recusarAtivacao) {
      return { ok: false, status: 422, json: async () => ({ ok: false, error: estado.recusarAtivacao }) };
    }
    const corpo = JSON.parse(String(init?.body ?? '{}')) as { plan_id?: string };
    estado.planoAtivo = String(corpo.plan_id ?? '');
    return { ok: true, json: async () => ({ ok: true }) };
  }
  return { ok: true, json: async () => ({ ok: true }) };
};

const { default: PlanoConfig } = await import('./PlanoConfig');

function renderPlano() {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <PlanoConfig />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  estado.chamadas = [];
  estado.planoAtivo = 'free';
  estado.recusarAtivacao = null;
  // Reinstala A CADA teste: o `afterEach` desfaz o stub global, e o segundo
  // teste nasceria sem fetch nenhum — falha de harness, não de produto.
  vi.stubGlobal('fetch', mockFetch);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('Configurações → Plano — o desbloqueio do 403 PLAN_REQUIRED', () => {
  it('mostra os planos que o GATEWAY devolveu, com o atual destacado', async () => {
    renderPlano();
    // Nomes vindos do payload: "Ouro" não é escrito no componente, então se
    // ele aparecer é porque o catálogo foi lido (prova contra plano fixo).
    await waitFor(() => expect(screen.getByText('Ouro')).toBeTruthy());
    // "Free" aparece DUAS vezes de propósito: no chip do plano atual e no
    // item do catálogo — o mesmo dado nos dois lugares, com o mesmo nome.
    expect(screen.getAllByText('Free').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByTestId('plano-atual').textContent).toContain('Free');
    expect(document.querySelector('.plano-item.ativo')?.textContent).toContain('Free');
  });

  it('Ativar faz POST /api/subscriptions/activate e repergunta o /me', async () => {
    renderPlano();
    await waitFor(() => expect(screen.getByText('Ouro')).toBeTruthy());
    const botao = screen.getByRole('button', { name: 'Ativar' });
    fireEvent.click(botao);
    await waitFor(() =>
      expect(estado.chamadas.some((u) => u.includes('/api/subscriptions/activate'))).toBe(true),
    );
    await waitFor(() =>
      expect(screen.getByTestId('plano-status').textContent).toContain('ativado neste dispositivo'),
    );
    // A tela passa a mostrar o que o gateway responde, depois da ativação.
    await waitFor(() => expect(screen.getByTestId('plano-atual').textContent).toContain('Ouro'));
    expect(document.querySelector('.plano-item.ativo')?.textContent).toContain('Ouro');
  });

  it('a ativação NÃO encaminha ordem nem dinheiro para fora', async () => {
    // PROVA NEGATIVA (AGENTS.md 2): ativar plano não é caminho para ordem,
    // saque nem transferência. O único POST é o de ativação local.
    renderPlano();
    await waitFor(() => expect(screen.getByText('Ouro')).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'Ativar' }));
    await waitFor(() =>
      expect(estado.chamadas.some((u) => u.includes('/api/subscriptions/activate'))).toBe(true),
    );
    expect(estado.chamadas.some((u) => u.includes('/api/trade/order'))).toBe(false);
    expect(estado.chamadas.some((u) => /withdraw|transfer/i.test(u))).toBe(false);
    // E a tela declara isso ao operador, sem prometer execução real.
    const corpo = document.body.textContent ?? '';
    expect(corpo).toContain('sem saque e sem transferência');
    expect(corpo).toContain('a trava de dinheiro real não muda em nenhum deles');
  });

  it('recusa do gateway (422) aparece como recusa, sem "ativado"', async () => {
    estado.recusarAtivacao = 'plano inválido: xyz';
    renderPlano();
    await waitFor(() => expect(screen.getByText('Ouro')).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'Ativar' }));
    await waitFor(() =>
      expect(screen.getByTestId('plano-status').textContent).toContain('não ativado'),
    );
    expect(screen.getByTestId('plano-status').textContent).toContain('plano inválido');
    // PROVA NEGATIVA: o botão não pode afirmar sucesso depois de 422.
    expect(screen.getByTestId('plano-status').textContent).not.toContain('ativado neste');
  });
});
