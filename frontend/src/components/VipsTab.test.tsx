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
  dias_ate_promocao: 1,
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

  it('avisa que a promocao nao e imediata', async () => {
    // Regra da IBKR: o nivel novo vale no dia seguinte, nao no instante em que
    // o limiar e cruzado. Sem isto na tela, o operador opera no ultimo minuto
    // achando que o desconto ja esta valendo.
    RESPOSTA.body = COMPLETO;
    render(<VipsTab />);
    await waitFor(() => expect(nivelRenderizado()).toBeTruthy());
    expect(screen.getByText(/promoção não é/)).toBeTruthy();
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

// A escada inteira. Antes a tela mostrava um degrau solto: o operador via
// "falta US$ 88.000" sem saber quantos degraus existem, onde ele esta, nem
// quanto ja fez do proximo. Estes testes fixam que a escada aparece inteira,
// que so um degrau e o proximo alvo, e que ela nunca promete desconto.
const ESCADA = {
  regular: { id: 'regular', nome: 'Regular', estado: 'alcancado', percentual: 100, minimo_por_grupo: { cripto: 0, forex_cfd: 0 } },
  vip1: { id: 'vip1', nome: 'VIP 1', estado: 'atual', percentual: 50, minimo_por_grupo: { cripto: 10_000, forex_cfd: 100_000 } },
  vip2: { id: 'vip2', nome: 'VIP 2', estado: 'futuro', percentual: 5, minimo_por_grupo: { cripto: 100_000, forex_cfd: 1_000_000 } },
  vip5: { id: 'vip5', nome: 'VIP 5', estado: 'futuro', percentual: 0, minimo_por_grupo: { cripto: 25_000_000, forex_cfd: 90_000_000 } },
};

function comEscada() {
  return {
    ...COMPLETO,
    nivel: 'regular',
    nivel_nome: 'Regular',
    volume_por_grupo: { cripto: 5_000, forex_cfd: 50_000 },
    escada: [ESCADA.regular, ESCADA.vip1, ESCADA.vip2, ESCADA.vip5],
    total_degraus: 4,
  };
}

describe('VipsTab — escada de niveis', () => {
  it('mostra a escada inteira, na ordem', async () => {
    RESPOSTA.body = comEscada();
    render(<VipsTab />);
    await waitFor(() => expect(nivelRenderizado()).toBeTruthy());
    const itens = document.querySelectorAll('.vips-degrau');
    expect(itens.length).toBe(4);
    expect(itens[0].textContent).toContain('Regular');
    expect(itens[1].textContent).toContain('VIP 1');
    expect(itens[2].textContent).toContain('VIP 2');
    expect(itens[3].textContent).toContain('VIP 5');
  });

  it('marca exatamente um degrau como proximo', async () => {
    // Cinco degraus marcados como proximo diriam que o operador precisa
    // trabalhar em cinco metas ao mesmo tempo — falso.
    RESPOSTA.body = comEscada();
    render(<VipsTab />);
    await waitFor(() => expect(nivelRenderizado()).toBeTruthy());
    expect(document.querySelectorAll('.vips-degrau.is-atual').length).toBe(1);
    expect(document.querySelectorAll('.vips-degrau.is-alcancado').length).toBe(1);
  });

  it('mostra o percentual de cada degrau', async () => {
    RESPOSTA.body = comEscada();
    render(<VipsTab />);
    await waitFor(() => expect(nivelRenderizado()).toBeTruthy());
    expect(screen.getByText('50.0%')).toBeTruthy();
    expect(screen.getByText('5.0%')).toBeTruthy();
  });

  it('nao quebra quando o backend ainda nao manda escada', async () => {
    // Um gateway antigo nao tem `escada`. A tela precisa continuar
    // mostrando nivel e "falta para o proximo" — degradar, nao quebrar.
    RESPOSTA.body = COMPLETO;
    render(<VipsTab />);
    await waitFor(() => expect(nivelRenderizado()).toBeTruthy());
    expect(document.querySelectorAll('.vips-degrau').length).toBe(0);
    expect(screen.getByText(/Falta para VIP 2/)).toBeTruthy();
  });

  it('a barra nunca passa de 100 por cento', async () => {
    // Um backend com volume muito acima do limiar produziria barra
    // estourada sem o teto em Math.min.
    RESPOSTA.body = {
      ...comEscada(),
      escada: [{ ...ESCADA.vip1, percentual: 250 }],
    };
    render(<VipsTab />);
    await waitFor(() => expect(nivelRenderizado()).toBeTruthy());
    const barra = document.querySelector('.vips-barra > span') as HTMLElement;
    expect(barra.style.width).toBe('100%');
  });
});
