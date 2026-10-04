// @vitest-environment jsdom
// Painel de operação automática.
//
// O motor já aceitava `simbolo` e `timeframe` em `/api/auto/config`
// (auto_engine.MotorAuto.configurar) e o painel nunca mandava: a tela ficava
// presa em um unico par e período sem nenhuma opção. Aqui se fixa que (a) só aparecem pares
// COM modelo no disco — `_trava_instrumento()` recusa ciclo sem modelo, então
// um par sem `.pkl` deixaria o motor "ligado" que nunca opera —, (b) Aplicar
// manda ativo + período junto com os limites e (c) sobram três comandos
// (Aplicar, Ligar, Desligar), sem o "Rodar um ciclo" que repetia o loop.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

const E = vi.hoisted(() => ({
  data: {
    ativo: false,
    ciclo: 3,
    simbolo: 'ATIVOA',
    timeframe: 'H1',
    // O motor informa a corretora e o mercado que VAI usar. Sem eles no
    // mock, o painel comparava a tela (vazio) com o servidor (vazio) e o
    // botao caia em "Aplique antes de ligar" mesmo sem mudanca nenhuma.
    broker: 'mt5',
    market: 'metals',
    threads: 4,
    limites: {},
    decisoes: [],
  } as Record<string, unknown>,
  refetch: vi.fn(async () => ({})),
}));

vi.mock('../hooks/queries', () => ({
  useAutoState: () => ({ data: E.data, isError: false, refetch: E.refetch }),
}));
vi.mock('../lib/notify', () => ({ notify: vi.fn() }));

const MODELOS = [
  { id: 'ATIVO_A_60', symbol: 'ATIVOA', timeframe: 'H1', pkl_present: true },
  { id: 'ATIVO_A_240', symbol: 'ATIVOA', timeframe: 'H4', pkl_present: true },
  { id: 'ATIVOB_60', symbol: 'ATIVOB', timeframe: 'H1', pkl_present: true },
  { id: 'ATIVOC_60', symbol: 'ATIVOC', timeframe: 'H1', pkl_present: true },
  { id: 'GBPUSD_H1', symbol: 'GBPUSD', timeframe: 'H1', pkl_present: false },
];

const chamadas: Array<{ url: string; body: Record<string, unknown> }> = [];
const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
  const u = String(url);
  if (u.includes('/api/ai/trained')) {
    return { ok: true, json: async () => ({ models: MODELOS }) };
  }
  if (u.includes('/api/auto/')) {
    chamadas.push({
      url: u,
      body: init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : {},
    });
    return { ok: true, json: async () => ({ ok: true }) };
  }
  return { ok: true, json: async () => ({}) };
});

const { default: AutoEnginePanel } = await import('./AutoEnginePanel');

function ativo() {
  return screen.getByLabelText('Ativo do motor automatico') as HTMLSelectElement;
}

describe('AutoEnginePanel — par, comandos e config', () => {
  beforeEach(() => {
    chamadas.length = 0;
    fetchMock.mockClear();
    E.refetch.mockClear();
    E.data.ativo = false;
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('lista so os ativos que tem modelo, em ordem alfabetica', async () => {
    render(<AutoEnginePanel />);
    const sel = (await screen.findByLabelText('Ativo do motor automatico')) as HTMLSelectElement;
    await waitFor(() => expect(sel.options.length).toBe(3));
    expect(sel.value).toBe('ATIVOA');
    // GBPUSD tem `.pkl_present: false`: fica de fora, senão o motor liga e
    // nunca opera.
    expect([...sel.options].map((o) => o.value)).toEqual(['ATIVOA', 'ATIVOB', 'ATIVOC']);
  });

  it('o período acompanha o ativo escolhido', async () => {
    render(<AutoEnginePanel />);
    const sel = (await screen.findByLabelText('Ativo do motor automatico')) as HTMLSelectElement;
    await waitFor(() => expect(sel.options.length).toBe(3));

    const periodo = screen.getByLabelText('Periodo do motor automatico') as HTMLSelectElement;
    expect([...periodo.options].map((o) => o.value)).toEqual(['H1', 'H4']);

    fireEvent.change(sel, { target: { value: 'ATIVOB' } });
    await waitFor(() => {
      const p = screen.getByLabelText('Periodo do motor automatico') as HTMLSelectElement;
      expect([...p.options].map((o) => o.value)).toEqual(['H1']);
    });
  });

  it('Aplicar manda ativo, período e limites no mesmo POST', async () => {
    render(<AutoEnginePanel />);
    const sel = (await screen.findByLabelText('Ativo do motor automatico')) as HTMLSelectElement;
    await waitFor(() => expect(sel.options.length).toBe(3));

    fireEvent.change(sel, { target: { value: 'ATIVOB' } });
    fireEvent.click(screen.getByRole('button', { name: 'Aplicar so' }));

    await waitFor(() =>
      expect(chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(true),
    );
    const config = chamadas.find((c) => c.url.includes('/api/auto/config'));
    expect(config?.body.simbolo).toBe('ATIVOB');
    expect(config?.body.timeframe).toBe('H1');
    expect(config?.body.banca).toBe(20);
    expect(config?.body.risco_por_trade_pct).toBe(1);
    // O estado volta pelo mesmo hook que o Mini Terminal lê.
    expect(E.refetch).toHaveBeenCalled();
  });

  it('sem corretora o botao diz o que falta em vez de so falhar', async () => {
    // Trava de 2026-09-30: o backend recusa o "ligar" sem corretora
    // ("nenhuma corretora e caminho padrao") e o painel nao tinha onde
    // escolher. O operador recebia a recusa so depois do clique.
    //
    // O cenario e o motor recem-ligado, sem corretora: e o estado em que a
    // recusa acontece de verdade.
    E.data.broker = '';
    E.data.market = '';
    render(<AutoEnginePanel />);
    await screen.findByLabelText('Ativo do motor automatico');
    const botao = screen.getByRole('button', { name: 'Escolha a corretora' }) as HTMLButtonElement;
    expect(botao.disabled).toBe(true);
    E.data.broker = 'mt5';
    E.data.market = 'metals';
  });

  it('escolhendo a corretora o caminho feliz fica disponivel', async () => {
    render(<AutoEnginePanel />);
    const seletor = await screen.findByLabelText('Corretora do motor automatico');
    fireEvent.change(seletor, { target: { value: 'binance' } });
    const mercado = screen.getByLabelText('Mercado do motor automatico');
    // Binance so opera cripto: a lista de mercado tem de acompanhar a
    // corretora, senao o motor aceitaria "binance + forex" e so recusaria
    // no envio.
    expect(mercado.querySelector('option[value="forex"]')).toBeNull();
    expect(screen.getByRole('button', { name: /Aplicar e ligar|Aplique antes/ })).toBeTruthy();
  });

  it('botoes dizem o que FAZ: aplicar e ligar e um caminho so', async () => {
    render(<AutoEnginePanel />);
    await screen.findByLabelText('Ativo do motor automatico');
    fireEvent.change(await screen.findByLabelText('Corretora do motor automatico'), {
      target: { value: 'mt5' },
    });

    const nomes = screen.getAllByRole('button').map((b) => b.textContent ?? '');
    // "Aplicar e ligar" existe porque "Aplicar" e "Ligar" eram indistinguiveis:
    // o operador clicava em "Ligar" sem "Aplicar" e o motor seguia no par antigo.
    expect(nomes).toContain('Aplicar e ligar');
    expect(nomes).toContain('Aplicar so');
    expect(nomes).toContain('Parar motor');
    // E o seletor de modo manual saiu com a ordem manual.
    expect(nomes).not.toContain('Operar na mao');
    expect(nomes).not.toContain('Deixar o motor');
  });
  it('mostra o motor rodando e desabilita o comando que não faz sentido', async () => {
    E.data.ativo = true;
    render(<AutoEnginePanel />);

    // O rotulo do motor ficou "Automatico operando" (era "Operando") em
    // 2026-09-29: com os dois modos na mesma tela, "Operando" sozinho era
    // ambigo — parecia que a ordem manual tambem estava operando.
    expect(screen.getByText('Automatico operando')).toBeTruthy();
    // Ligar virou "Aplicar e ligar" (2026-09-30): os dois botoes antigos eram
    // indistinguiveis e o operador clicava em "Ligar" sem "Aplicar".
    // Com o motor ligado o botao muda de rotulo para "Operando" — e o que
    // impede o operador de achar que ainda ha algo a ligar.
    expect((screen.getByRole('button', { name: 'Operando' }) as HTMLButtonElement).disabled).toBe(
      true,
    );
    expect(
      (screen.getByRole('button', { name: 'Parar motor' }) as HTMLButtonElement).disabled,
    ).toBe(false);
  });
});
