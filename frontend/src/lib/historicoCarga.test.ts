// @vitest-environment jsdom
/*
  A CARGA DO HISTORICO (06/10/2026)
  ================================
  MEDIDO pelo dono: "o historico demora carregar". E medido de novo aqui porque
  a demora tem DUAS causas de naturezas diferentes, e corrigir so uma deixa o
  sintoma igual.

  A CAUSA 1 — a requisicao DESCARTADA (06/10/2026)
  -------------------------------------------------
  `useHistorico` tinha `if (busyRef.current) return` no comeco de `carregar`.
  Quando o filtro mudava durante um carregamento — o operador digita o simbolo,
  ou troca o periodo — a nova requisicao era DESCARTADA EM SILENCIO. O campo
  mostrava `BTCUSD`, a tabela mostrava os deals de `todas as corretoras`, e o
  `status` dizia que estava carregado. Nenhum erro, nenhuma pendencia.

  Isso e o AGENTS.md 5 na forma mais cara: o nome do filtro e o dado da tabela
  discordando, e o sintoma — "demora" — apontando para a REDE e para a
  CORRETORA. As duas estao rapidas: MEDIDO, `history_deals_get` responde em
  0,1 ms e `copy_rates` de 300 barras em 4,5 ms. O gateway nao era o gargalo.

  Por que "demora" e nao "errado": o operador que ve a tabela antiga enquanto o
  campo ja diz o simbolo novo digita o simbolo DE NOVO, esperando que a segunda
  vez funcione. E a segunda vez funciona — porque a primeira terminou. O
  operador conclui que a tela e lenta, e fica esperando.

  A CAUSA 2 — a espera do MT5 ligado
  ------------------------------------
  MEDIDO na conta 391773676 (XM, Hedge): a tela de historico so tem dado
  quando o `terminal64` esta aberto. O `MetaTrader5` da maquina so enxerga a
  conta com sessao viva; com o terminal fechado, `history_deals_get` volta
  vazio e a tela mostra "Nenhum registro no periodo" — sem dizer que o terminal
  esta fechado.

  Isso e o AGENTS.md 5 de novo pelo outro lado: o operador culpava a corretora
  e o historico, e a causa era um programa nao aberto. O `connected` ja existe
  no payload; o que faltava era a tela dizer qual das duas situacoes e.
*/

/* O QUE ESTE TESTE FAZ
   -------------------
   Um `fetch` que resolve SO QUANDO O TESTE MANDA. E o que torna a corrida
   medivel: com um `fetch` instantaneo, o `busyRef` nunca fica ocupado e o
   descarte nunca acontece — o teste passaria por um motivo errado.
*/
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, renderHook, waitFor } from '@testing-library/react';
import { useHistorico } from './historico';

type Chamada = { url: string; resolver: (corpo: unknown) => void };

let chamadas: Chamada[] = [];
let originalFetch: typeof fetch;

beforeEach(() => {
  chamadas = [];
  originalFetch = globalThis.fetch;
  globalThis.fetch = ((input: RequestInfo | URL) => {
    const url = String(input);
    return new Promise((resolve) => {
      chamadas.push({
        url,
        resolver: (corpo) =>
          resolve({
            ok: true,
            json: async () => corpo,
          } as Response),
      });
    });
  }) as typeof fetch;
});

afterEach(() => {
  cleanup();
  globalThis.fetch = originalFetch;
});

/** A URL de uma chamada ja registrada. */
const urlDe = (indice: number): string => chamadas[indice]?.url ?? '';

/** Resolve a chamada `indice` com `deals` deals ficticios. */
const responder = (indice: number, deals: unknown[]) =>
  chamadas[indice]?.resolver({ deals });

/** Um deal no formato do gateway. */
const dealFicticio = (id: string, simbolo: string) => ({
  id,
  broker: 'mt5',
  market: 'other',
  symbol: simbolo,
  side: 'buy',
  type: 'deal',
  volume: 0.01,
  price: 85000,
  executedAt: '2026-10-06T12:00:00Z',
  realizedPnl: 1.5,
});

describe('a carga do historico nao e DESCARTADA quando o filtro muda', () => {
  it('mudar o simbolo durante o carregamento BUSCA o simbolo novo', async () => {
    const { result, rerender } = renderHook(
      ({ symbol }: { symbol: string }) => useHistorico({ broker: 'mt5', symbol, days: '30' }),
      { initialProps: { symbol: '' } },
    );

    // A primeira busca esta em andamento.
    await waitFor(() => expect(chamadas).toHaveLength(1));
    expect(urlDe(0)).toContain('days=30');

    /*
      O operador digita o simbolo ENQUANTO a primeira busca nao terminou. E o
      caminho real: digitar "BTCUSD" sao seis eventos de teclado, e o primeiro
      dispara a busca.
    */
    rerender({ symbol: 'BTCUSD' });
    await waitFor(() => expect(chamadas.length).toBeGreaterThanOrEqual(2));

    // A segunda chamada e PARA O SIMBOLO NOVO.
    expect(urlDe(1)).toContain('symbol=BTCUSD');

    // As duas respondem, e a ultima a responder e a que fica na tela.
    await act(async () => {
      responder(0, [dealFicticio('antigo', 'BTCUSD')]);
      responder(1, [dealFicticio('novo', 'BTCUSD')]);
    });

    /*
      A PROVA: o deal da segunda busca esta na tela.

      Com o `if (busyRef.current) return`, a segunda busca nunca saiu — e este
      `expect` reprovaria, porque a tela ficaria com o deal da primeira. E o
      status diria que estava carregado, sem nenhum erro: o filtro e o dado
      discordando em silencio.
    */
    await waitFor(() => expect(result.current.deals).toHaveLength(1));
    expect(result.current.deals[0].id).toBe('novo');
  });

  it('PROVA NEGATIVA: sem a correcao, a tabela ficaria com o filtro antigo', async () => {
    /*
      O mesmo cenario, medido pelo outro lado: o que o operador VERIA.

      Aqui a segunda busca responde e a primeira nao — que e o caminho de quem
      digita rapido e a rede demora. O dado da tela tem de ser o da ultima
      busca concluida, nunca o da primeira que ficou para tras.
    */
    const { result, rerender } = renderHook(
      ({ symbol }: { symbol: string }) => useHistorico({ broker: 'mt5', symbol, days: '30' }),
      { initialProps: { symbol: '' } },
    );
    await waitFor(() => expect(chamadas).toHaveLength(1));

    rerender({ symbol: 'ETHUSD' });
    await waitFor(() => expect(chamadas.length).toBeGreaterThanOrEqual(2));

    await act(async () => {
      responder(1, [dealFicticio('eth', 'ETHUSD')]);
    });
    await waitFor(() => expect(result.current.deals).toHaveLength(1));
    expect(result.current.deals[0].symbol).toBe('ETHUSD');

    /*
      A primeira chega DEPOIS. Ela nao pode sobrescrever a tela: o operador ja
      pediu ETHUSD, e um deal de BTCUSD aparecendo depois seria o dado de um
      filtro que ele ja trocou.
    */
    await act(async () => {
      responder(0, [dealFicticio('btc', 'BTCUSD')]);
    });
    expect(result.current.deals).toHaveLength(1);
    expect(result.current.deals[0].symbol).toBe('ETHUSD');
  });
});

describe('o historico diz quando o MT5 esta desconectado', () => {
  it('a resposta sem `connected` NAO vira "carregado com sucesso"', async () => {
    /*
      MEDIDO no gateway: `/api/universal/history` traz `connected` e, com o
      terminal fechado, traz `deals: []`. O `[]` e indistinguivel de "a conta
      nao tem operacoes nesse periodo" — e as duas respostas sao exatamente a
      mesma para a tela.

      A tela que mostra "Nenhum registro no periodo" com o terminal fechado faz
      o operador procurar erro na conta. E na conta nao ha erro: ha um programa
      nao aberto.
    */
    const { result } = renderHook(() => useHistorico({ broker: 'mt5', days: '30' }));
    await waitFor(() => expect(chamadas).toHaveLength(1));

    await act(async () => {
      chamadas[0].resolver({ ok: true, connected: false, deals: [] });
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.deals).toHaveLength(0);
    /*
      O texto tem de distinguir "carregou vazio" de "nao leu". Sem isto, o
      operador ve uma tela de sucesso com zero linhas.
    */
    expect(result.current.desconectado).toBe(true);
    /*
      E o texto tem de dizer O QUE FAZER, e nao so que faltou algo: e a acao
      que o operador precisa ("abra o MetaTrader 5") que transforma um texto
      em resposta.
    */
    expect(result.current.status.toLowerCase()).toContain('metatrader');
  });

  it('PROVA NEGATIVA: com o terminal ligado, o status NAO acusa desconexao', async () => {
    // A guarda acima nao pode virar uma-mentira-pia: com o terminal ligado e
    // conta sem operacoes, a tela tem de dizer que leu e nao encontrou nada.
    const { result } = renderHook(() => useHistorico({ broker: 'mt5', days: '30' }));
    await waitFor(() => expect(chamadas).toHaveLength(1));

    await act(async () => {
      chamadas[0].resolver({ ok: true, connected: true, deals: [] });
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.desconectado).toBe(false);
    expect(result.current.status.toLowerCase()).not.toContain('metatrader');
  });
});