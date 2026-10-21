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
    // Todos os limites nascem em ZERO. O painel nao preenche
    // nada por conta propria: o que o operador nao digitar continua zero, e o
    // backend recusa o motor nomeando o campo que falta. Painel simples:
    // so lote, stop e alvo.
    expect(config?.body.lote).toBe(0);
    expect(config?.body.sl_preco).toBe(0);
    expect(config?.body.tp_preco).toBe(0);
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


/** Os inputs DO BLOCO DE RISCO, e nao os do painel inteiro.
 *
 * `screen.getAllByRole('spinbutton')` sem escopo medido em 04/10/2026: 117
 * elementos, nao 13 — o painel renderiza outros formularios. A contagem
 * ingenua passava a provar nada, e a falha apareceu como "expected 117 to be
 * 13". O que este teste precisa e do conjunto que o motor le.
 */
function dentroDoBlocoDeRisco(raiz: HTMLElement = document.body): HTMLInputElement[] {
  // Escopo pelo CONTAINER do render, nao por `document`. Medido em
  // 04/10/2026: `screen.getByRole('group', ...)` achou varios elementos e
  // reprovou com "Found multiple elements" — o `cleanup` roda no fim do
  // teste, entao o DOM de um teste ainda coexiste com o seguinte dentro do
  // mesmo arquivo.
  const bloco = raiz.querySelector<HTMLElement>('.auto-engine-bloco:last-of-type');
  return Array.from(
    (bloco ?? raiz).querySelectorAll<HTMLInputElement>('input[type="number"]'),
  );
}

describe('Todo limite que o backend exige tem campo na tela (2026-10-04)', () => {
  // SINTOMA MEDIDO
  // -------------
  // O painel mostrava so `lote`, `sl_preco` e `tp_preco`, mas `LimitesAuto`
  // tem TREZE campos e `valido()` exige os dez primeiros. Faltava
  // `confianca_minima`: o gate que decide se a ordem sai.
  //
  // O operador digitava 36, apertava "Aplicar", e o motor recusava com
  // "confianca 38.0% abaixo do minimo 55.0%" — o 55 era o ultimo valor gravado
  // no servidor, nunca escolhido naquela tela. A tela affirmava uma coisa e o
  // motor operava outra.
  //
  // Este teste compara a lista da tela com a dataclass do backend. Sem ele, a
  // lista pode encolher de novo em silencio — e o backend continua aceitando,
  // porque o campo opcional e apenas ignorado.

  beforeEach(() => {
    E.data.limites = {};
    E.data.ativo = false;
  });

  const ESPERADOS = [
    'Confianca minima',
    'Edge minimo',
    'Banca',
    'Risco por operacao',
    'Perda diaria maxima',
    'Maximo de posicoes',
    'Operacoes por dia',
    'Intervalo entre avaliacoes',
  ];

  it.each(ESPERADOS)('exibe o campo "%s"', async (rotulo) => {
    render(<AutoEnginePanel />);
    await waitFor(() => expect(screen.getAllByLabelText('Corretora do motor automatico').length).toBeGreaterThan(0));
    // `getByText` falha com "Found multiple elements": o rotulo aparece no
    // `<span>` do campo E dentro do `<label>`. O que importa e que exista
    // pelo menos um, nao que exista exatamente um.
    expect(screen.getAllByText(new RegExp(rotulo, 'i')).length).toBeGreaterThan(0);
  });

  it('os campos de risco nascem zerados: zero e "nao declarado", nao um padrao', async () => {
    // Se um campo nascesse com valor, o operador nao saberia que o motor esta
    // usando um risco que ele nao escolheu.
    render(<AutoEnginePanel />);
    await waitFor(() => expect(screen.getAllByLabelText('Corretora do motor automatico').length).toBeGreaterThan(0));
    const numeros = dentroDoBlocoDeRisco();
    // 10 = os 10 campos que `LimitesAuto.valido()` exige.
    expect(numeros.length).toBe(10);
    const naoZerados = numeros.filter((i) => i.value !== '' && Number(i.value) !== 0);
    expect(naoZerados.map((i) => i.value)).toEqual([]);
  });

  it('editar a confianca minima manda o valor digitado, nao um padrao', async () => {
    const cfg = vi.fn(async (_corpo: Record<string, unknown>) => ({ ok: true }));
    (globalThis as unknown as { fetch: unknown }).fetch = vi.fn(
      async (url: string, init?: RequestInit) => {
        if (String(url).includes('/api/auto/config')) {
          return { ok: true, json: async () => cfg(JSON.parse(String(init?.body ?? '{}'))) } as unknown as Response;
        }
        return { ok: true, json: async () => ({ ok: true }) } as unknown as Response;
      });
    // `render` devolve o container do PROPRIO render. `screen` ve o
    // `document` inteiro, e dentro do mesmo arquivo o DOM do teste anterior
    // ainda esta la — medido: "Found multiple elements with the role button".
    const { container } = render(<AutoEnginePanel />);
    await waitFor(() =>
      expect(container.querySelectorAll('select').length).toBeGreaterThan(0));

    const confianca = dentroDoBlocoDeRisco(container).find((c) =>
      /confianca/i.test(c.closest('label')?.textContent ?? ''));
    expect(confianca).toBeTruthy();
    fireEvent.change(confianca!, { target: { value: '36' } });

    const botao = Array.from(container.querySelectorAll('button')).find((b) =>
      /Aplicar e ligar/i.test(b.textContent ?? ''));
    expect(botao).toBeTruthy();
    await waitFor(() => expect(botao!.hasAttribute('disabled')).toBe(false));
    fireEvent.click(botao!);
    await waitFor(() => expect(cfg).toHaveBeenCalled());
    expect(cfg.mock.calls[0][0].confianca_minima).toBe(36);
  });
});

