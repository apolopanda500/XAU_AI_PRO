// @vitest-environment jsdom
// Progressão VIP: o que a tela NÃO pode fazer.
//
// A tela mostra nível por volume. O risco aqui não é quebrar o layout — é
// exibir uma promessa que o sistema não pode cumprir. Estes testes fixam duas
// coisas: que a trava de dinheiro real aparece na tela (o operador precisa
// ver que saque está desligado), e que volume ausente vira "--", nunca 0
// fingido ou NaN quebrando a tabela.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';

const RESPOSTA = vi.hoisted(() => ({ body: null as unknown }));

vi.mock('../../lib/api', () => ({ apiBase: () => 'http://127.0.0.1:9001' }));

vi.stubGlobal('fetch', vi.fn(async () => ({
  ok: true,
  status: 200,
  json: async () => RESPOSTA.body,
})));

const { default: VipsTab } = await import('./VipsTab');

const COMPLETO = {
  nivel: 'vip1',
  nivel_nome: 'VIP 1',
  beneficios: ['Spread reduzido'],
  janela_dias: 30,
  trava_dias: 30,
  volume_por_grupo: { cripto: 12_000, forex_cfd: 150_000 },
  proximo: { id: 'vip2', nome: 'VIP 2', falta_por_grupo: { cripto: 88_000, forex_cfd: 850_000 } },
  live_execution: false,
  withdrawals_enabled: false,
};

afterEach(() => cleanup());

// "VIP 1" aparece duas vezes na tela — no chip do cabecalho e no nome do
// nivel. `findByText` exige unicidade, entao os testes usam o chip como
// ancora: e o ponto unico que so muda quando a rota responde.
function nivelRenderizado(): HTMLElement {
  return document.querySelector('.vips-nivel strong') as HTMLElement;
}

describe('VipsTab', () => {
  it('mostra o nivel e o que falta para o proximo', async () => {
    RESPOSTA.body = COMPLETO;
    render(<VipsTab />);
    await waitFor(() => expect(nivelRenderizado()).toBeTruthy());
    expect(nivelRenderizado().textContent).toBe('VIP 1');
    expect(screen.getByText(/Falta para VIP 2/)).toBeTruthy();
  });

  it('declara saque e execucao real desligados', async () => {
    RESPOSTA.body = COMPLETO;
    render(<VipsTab />);
    // A tela precisa MOSTRAR a trava, nao so obedecer a ela: um operador
    // que acredite ter liberado saque por subir de nivel e o pior desfecho.
    await waitFor(() => expect(nivelRenderizado()).toBeTruthy());
    expect(screen.getByText('desativados')).toBeTruthy();
    expect(screen.getByText('desativada')).toBeTruthy();
  });

  it('formata volume em milhar e milhao', async () => {
    RESPOSTA.body = { ...COMPLETO, volume_por_grupo: { cripto: 12_000, forex_cfd: 2_500_000 } };
    render(<VipsTab />);
    await waitFor(() => expect(nivelRenderizado()).toBeTruthy());
    expect(screen.getByText('$12.0k')).toBeTruthy();
    expect(screen.getByText('$2.5M')).toBeTruthy();
  });

  it('avisa que limiar nao e promessa de desconto', async () => {
    RESPOSTA.body = COMPLETO;
    render(<VipsTab />);
    await waitFor(() => expect(nivelRenderizado()).toBeTruthy());
    expect(screen.getByText(/limiares são de estrutura/)).toBeTruthy();
  });

  it('trata volume ausente como -- e nao como zero', async () => {
    // Zero e um dado valido ("operou nada"); ausente e falta de dado. A tela
    // nao pode confundir os dois.
    RESPOSTA.body = { ...COMPLETO, volume_por_grupo: {} };
    render(<VipsTab />);
    await waitFor(() => expect(nivelRenderizado()).toBeTruthy());
    expect(screen.getAllByText('--').length).toBeGreaterThan(0);
  });
});
