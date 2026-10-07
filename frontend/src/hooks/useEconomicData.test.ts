import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useEconomicData } from './useEconomicData';

/*
  O CAMINHO INTEIRO DO CALENDARIO (05/10/2026)
  =============================================
  Este arquivo existia sem nenhum teste: `processarEventosApi`, que produz
  `estimado` e `divulgado`, nunca foi exercitada. Os testes da tela injetavam
  `EconomicEvent` ja pronto â€” ou seja, passavam por cima da traducao e da
  normalizacao, que e justamente onde o dado real diverge do sintatico.

  O que a medicao do produtor encontrou (05/10/2026, 111 eventos em 14 dias):

      reais:     82  (feed publico, semana corrente)
      estimados: 29  (padrao de calendario, semana seguinte)

  e os estimados tem formatos DIFERENTES de `when_utc`:

      "2026-10-06T10:00:00+00:00"   feed publico, COM deslocamento
      "2026-10-13T12:00"             agenda local, SEM deslocamento

  Sao dois formatos no mesmo payload. Os dois precisam cair no dia certo.
*/

/* O hook exige o filtro: `filtro.paises` e lido na linha 294. Sem argumento ele
   quebrava com "Cannot read properties of undefined (reading 'paises')". */
const FILTRO = { paises: [], impactos: [], dataInicio: null, dataFim: null };

const COM_FUSO = '2026-10-06T10:00:00+00:00';
const SEM_FUSO = '2026-10-13T12:00';

function eventoApi(extra: Record<string, unknown>) {
  return {
    id: 'ev-1',
    currency: 'EUR',
    title: 'CPI y/y',
    impact: 'high',
    previous: '2,1',
    forecast: '2,0',
    actual: '2,2',
    ...extra,
  };
}

describe('useEconomicData â€” o caminho inteiro do payload a tela', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    localStorage.clear();
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  function responderPayload(resposta: unknown) {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => resposta,
    });
  }

  it('pede o limite que cabe na janela â€” e o que mantinha a semana seguinte fora', async () => {
    /*
      PROVA NEGATIVA: com `limit=50` este teste reprova. A rota devolve
      `[:limit]` e os 29 estimados ficam no fim da lista combinada, entao o
      CORTE acontecia antes deles chegarem a tela. O sintoma era "as semanas
      seguintes estao vazias", e a causa estava no cliente, nao na agenda.
    */
    responderPayload({ events: [eventoApi({ when_utc: COM_FUSO })], fontes: {} });

    const { result } = renderHook(() => useEconomicData(FILTRO));

    await waitFor(() => expect(result.current.carregando).toBe(false));

    const pedido = String(fetchMock.mock.calls[0][0]);
    const limite = Number(new URL(pedido, 'http://x').searchParams.get('limit'));
    // MEDIDO: 111 eventos em 14 dias. 50 cortava a semana seguinte inteira.
    expect(limite).toBeGreaterThanOrEqual(111);
  });

  it('parseia `when_utc` COM deslocamento e SEM deslocamento no mesmo payload', async () => {
    /*
      Duas ABIERTAS no mesmo array. A versao anterior acrescentava "Z" de forma
      cega, o que quebrava a que ja trazia "+00:00" e jogava o evento em
      `new Date()` â€” e o evento aparecia na HORA QUE A TELA ABRIU, em vez do
      dia. Com 33 eventos assim, "Hoje" contava 50 e o resto das semanas
      aparecia vazio.
    */
    responderPayload({
      events: [
        eventoApi({ id: 'com-fuso', when_utc: COM_FUSO }),
        eventoApi({ id: 'sem-fuso', when_utc: SEM_FUSO }),
      ],
      fontes: { reais: 1, estimados: 1 },
    });

    const { result } = renderHook(() => useEconomicData(FILTRO));
    await waitFor(() => expect(result.current.eventos).toHaveLength(2));

    const [comFuso, semFuso] = result.current.eventos;
    expect(Number.isNaN(comFuso.horario.getTime())).toBe(false);
    expect(Number.isNaN(semFuso.horario.getTime())).toBe(false);
    // as duas abrem em dias DIFERENTES: 06/10 e 13/10
    expect(chave(comFuso.horario)).not.toBe(chave(semFuso.horario));
    expect(chave(comFuso.horario)).toBe('2026-10-06');
  });

  it('`estimado` sobrevive a normalizacao â€” o rotulo de procedencia', async () => {
    responderPayload({
      events: [
        eventoApi({ id: 'real', when_utc: COM_FUSO, estimado: false }),
        eventoApi({ id: 'est', when_utc: SEM_FUSO, estimado: true }),
      ],
      fontes: { reais: 1, estimados: 1 },
    });

    const { result } = renderHook(() => useEconomicData(FILTRO));
    await waitFor(() => expect(result.current.eventos).toHaveLength(2));

    // O `id` e montado pelo hook (`${when_utc}-${indice}`), nao vem do payload.
    // A distincao real/estimado e o campo `estimado`.
    const estimados = result.current.eventos.filter((e) => e.estimado);
    expect(estimados).toHaveLength(1);
    expect(estimados[0].horario.toISOString().slice(0, 10)).toBe('2026-10-13');
    expect(result.current.eventos.filter((e) => !e.estimado)).toHaveLength(1);
  });

  it('PROVA NEGATIVA: sem `estimado` no payload, nada e marcado como estimado', async () => {
    /*
      O campo ausente e `false`, nunca `true`. Marcar tudo como estimado
      destruiria a distincao entre o feed publico e a agenda local â€” que e a
      diferenca entre "numero publicado" e "horario previsto".
    */
    responderPayload({ events: [eventoApi({ when_utc: COM_FUSO })], fontes: {} });

    const { result } = renderHook(() => useEconomicData(FILTRO));
    await waitFor(() => expect(result.current.eventos).toHaveLength(1));
    expect(result.current.eventos[0].estimado).toBe(false);
  });

  it('`divulgado` vem do horario, e um evento futuro nao aparece ja divulgado', async () => {
    responderPayload({
      events: [
        eventoApi({ id: 'passado', when_utc: '2026-10-01T10:00:00+00:00' }),
        eventoApi({ id: 'futuro', when_utc: SEM_FUSO }),
      ],
      fontes: {},
    });

    const { result } = renderHook(() => useEconomicData(FILTRO));
    await waitFor(() => expect(result.current.eventos).toHaveLength(2));

    // Ordenado por horario: o de 01/10 ja passou, o de 13/10 nao.
    const ordenados = [...result.current.eventos].sort(
      (a, b) => a.horario.getTime() - b.horario.getTime(),
    );
    expect(ordenados[0].divulgado).toBe(true);
    expect(ordenados[1].divulgado).toBe(false);
  });

  it('traduz o titulo e guarda o original em ingles', async () => {
    responderPayload({
      events: [eventoApi({ when_utc: COM_FUSO, title: 'CPI y/y', previous: null, forecast: null, actual: null })],
      fontes: {},
    });

    const { result } = renderHook(() => useEconomicData(FILTRO));
    await waitFor(() => expect(result.current.eventos).toHaveLength(1));

    const ev = result.current.eventos[0];
    expect(ev.traduzido).toBe(true);
    expect(ev.titulo).not.toBe(ev.tituloOriginal);
    expect(ev.tituloOriginal).toBe('CPI y/y');
  });

  it('PROVA NEGATIVA: valor ausente do payload vira `null`, e nao texto vazio', async () => {
    /*
      `''` e `null` sao estados diferentes. Texto vazio renderizado vira celula
      com conteudo: era o que produzia a coluna Real cheia de `--` onde o
      produtor nao mandou nada.
    */
    responderPayload({
      events: [eventoApi({ when_utc: COM_FUSO, previous: null, forecast: null, actual: null })],
      fontes: {},
    });

    const { result } = renderHook(() => useEconomicData(FILTRO));
    await waitFor(() => expect(result.current.eventos).toHaveLength(1));

    const ev = result.current.eventos[0];
    expect(ev.anterior).toBeNull();
    expect(ev.consenso).toBeNull();
    expect(ev.real).toBeNull();
  });
});

function chave(d: Date): string {
  return d.toISOString().slice(0, 10);
}