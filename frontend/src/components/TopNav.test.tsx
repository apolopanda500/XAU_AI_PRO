// @vitest-environment jsdom
// O cabeçalho não pode afirmar o contrário do que está medido. (05/10/2026)
//
// O DEFEITO
// ==========
// A tela mostrava `EA: Desconectado` e `AI: Inativo` **com o EA ligado**.
//
// MEDIDO no heartbeat lido do disco, na conta 391773676:
//     state RUNNING · autotrading true · login 391773676
//     server XMGlobal-MT5 14 · symbol ETHUSD · write_count 19027
//
// CAUSA, no código (não na tela):
//   - `useAppStore.ts:309` nasce com `robotStatus: 'Desconectado'`
//   - `useAppStore.ts:313` nasce com `aiStatus: 'Inativo'`
//   - o único escritor de `robotStatus` é `useAICommunication`, que **ninguém
//     chama** — então os dois campos ficavam nos padrões de fábrica para sempre
//   - `useInferenciaIA(timeframe, enabled)` recebia `enabled` e **não o usava**:
//     inferia sempre, sem interruptor
//
// Um rótulo que nega o estado real é pior que rótulo nenhum: o operador vai ao
// terminal conferir e perde a confiança na tela inteira.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';

const H = vi.hoisted(() => ({
  runtime: null as unknown,
  status: 'Inativo',
  aiCalls: 0,
}));

vi.mock('../hooks/queries', () => ({
  useEaRuntime: () => ({ data: H.runtime, isLoading: false }),
}));

const { default: TopNav } = await import('./TopNav');
const { useInferenciaIA } = await import('../hooks/useAICommunication');

// O store precisa ser o de verdade, para o teste ler o mesmo campo que a tela.
const { useAppStore } = await import('../hooks/useAppStore');

/** O heartbeat como o gateway devolve em `/api/ea/status`. */
const HEARTBEAT_VIVO = {
  ok: true,
  live: true,
  terminal_connected: true,
  autotrading: true,
  ea_heartbeat: {
    live: true,
    state: 'RUNNING',
    age_sec: 3,
    symbol: 'ETHUSD',
    timeframe: 'H1',
    source: 'XAU_AI_PRO_heartbeat.json',
  },
};

describe('TopNav — o rótulo do EA vem do heartbeat, não de um texto fixo', () => {
  beforeEach(() => {
    H.runtime = HEARTBEAT_VIVO;
    useAppStore.setState({ robotStatus: 'Desconectado', aiStatus: 'Inativo' });
  });
  afterEach(() => cleanup());

  it('com o EA VIVO, a tela NÃO diz "Desconectado"', async () => {
    render(<TopNav />);
    await waitFor(() => {
      expect(screen.getByText(/EA:/).textContent).not.toContain('Desconectado');
    });
    // E diz o que está de fato: vivo, no gráfico, com par e período.
    const texto = screen.getByText(/EA:/).textContent ?? '';
    expect(texto).toContain('ETHUSD');
    expect(texto).toContain('H1');
  });

  it('com o heartbeat VELHO, a tela diz "sem sinal há N" e não "desconectado"', () => {
    // São coisas diferentes e exigem ações diferentes: o EA parado precisa de
    // reanexar; heartbeat velho é o arquivo que parou de ser escrito. Dizer
    // "desconectado" nos dois casos manda o operador caçar o problema errado.
    H.runtime = {
      ...HEARTBEAT_VIVO,
      live: false,
      ea_heartbeat: { ...HEARTBEAT_VIVO.ea_heartbeat, live: false, age_sec: 640 },
    };
    render(<TopNav />);
    const texto = screen.getByText(/EA:/).textContent ?? '';
    expect(texto).toContain('sem sinal há');
    expect(texto).not.toContain('Desconectado');
  });

  it('sem leitura do gateway, a tela diz "sem leitura" — não "desconectado"', () => {
    H.runtime = null;
    render(<TopNav />);
    const texto = screen.getByText(/EA:/).textContent ?? '';
    expect(texto).toContain('sem leitura');
    expect(texto).not.toContain('Desconectado');
  });

  it('o rótulo do EA é escrito no store, para os outros paineis lerem', async () => {
    // O store é a fonte compartilhada. Se a tela calcula e não publica, os
    // outros painéis continuam vendo o padrão de fábrica.
    render(<TopNav />);
    await waitFor(() => {
      expect(useAppStore.getState().robotStatus).toContain('ETHUSD');
    });
  });
});

describe('useInferenciaIA — o interruptor enabled passou a valer', () => {
  beforeEach(() => {
    H.status = 'Inativo';
    useAppStore.setState({ aiStatus: 'Inativo' });
  });
  afterEach(() => {
    H.aiCalls = 0;
    cleanup();
  });

  it('desligada NÃO escreve nada e devolve o motivo', async () => {
    /*
      Este é o D5. Antes: `enabled` era parâmetro sem uso, o hook inferia
      sempre, e o cabeçalho ficava em "Inativo" porque o hook não era chamado.
    */
    const { result } = renderHook(() => useInferenciaIA('H1', false));
    const r = await result.current.inferir('BTCUSD');
    expect(r.disponivel).toBe(false);
    expect(r.motivo).toContain('desligada');
  });

  it('desligada NÃO apaga o último sinal que o operador viu', () => {
    // Ligar e desligar a IA não pode limpar a tela: o último sinal real
    // continua valendo enquanto o operador olha para ele.
    const { result } = renderHook(() => useInferenciaIA('H1', false));
    expect(result.current.sinal).toBeNull();
  });

  it('o interruptor escreve o estado da IA no cabeçalho', () => {
    const { result } = renderHook(() => useInferenciaIA('H1', true));
    result.current.ativar(true);
    expect(useAppStore.getState().aiStatus).toBe('Ativa');
    result.current.ativar(false);
    expect(useAppStore.getState().aiStatus).toBe('Inativa');
  });
});

// ---------------------------------------------------------------------------
// `renderHook` local, por um `Harness` renderizado — sem `require`, que o `tsc`
// acusa neste projeto por falta de `@types/node`.
// ---------------------------------------------------------------------------
function renderHook<T>(useHook: () => T): { result: { current: T } } {
  const box: { current: T } = { current: undefined as unknown as T };
  function Harness() {
    box.current = useHook();
    return null;
  }
  render(<Harness />);
  return { result: box };
}