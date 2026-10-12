// @vitest-environment jsdom
/*
  A MARCA "ESTIMADO" NAO DEPENDE DO DIA DA SEMANA (09/10/2026)
  ===========================================================
  MEDIDO: em 09/10/2026 o teste *"marca evento estimado como estimado"* reprovou
  sem que nada do calendario tivesse sido alterado.

  A CAUSA
  =======
  O calendario mostra SEMPRE os sete dias da semana visivel
  (`diasCompletosDaSemana`). O teste montava o evento em `H.em(3, 10, 0)`, e
  `em(3, ...)` e um OFFSET de dias — nao o dia 3 do mes.

  MEDIDO: a semana visivel de quinta 09/10 e 05/10 a 11/10, e `em(3, ...)` era
  **12/10**, na semana seguinte. Sem aba para o dia, `.cal-row-tag` nao era
  renderizado, e o teste reprovava.

  De quarta a sexta, "hoje + 3 dias" ainda cabia na semana e o teste passava.
  Ele tinha um **prazo de validade que ninguem escolheu** — e o relogio era o
  motor da falha.

  POR QUE UM ARQUIVO SO
  =====================
  A correcao foi `em(0, ...)`: hoje esta sempre na semana visivel. Mas isso e
  uma afirmacao sobre o RELOGIO, e um teste que roda com o relogio real nao
  pode provar uma coisa do relogio. Aqui a data e CONGELADA e o calendario e
  carregado em varios dias da semana.

  Sem isso, o teste passaria hoje e reprovaria amanha sem que ninguem soubesse
  porque — que e exatamente o defeito que este arquivo existe para impedir.
*/
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';

/*
  SETE DIAS, UM DE CADA VEZ
  ==========================
  Cobre a semana inteira, de domingo a sabado, de 2026:

      04/10 domingo   o PIOR caso para `em(0)`: primeiro dia da semana visivel
      05/10 segunda
      06/10 terca
      07/10 quarta    `em(3, ...)` = 10/10 — ainda na semana, o teste antigo
                     passaria
      08/10 quinta    `em(3, ...)` = 11/10 — ainda na semana, idem
      09/10 sexta     o dia em que o defeito foi medido: `em(3, ...)` = 12/10,
                     JA na semana seguinte, e reprovava
      10/10 sabado    `em(3, ...)` = 13/10 — semana seguinte

  O trecho 05/10 a 11/10 e a janela medida na captura de 07/10 00:38.
*/
const DIAS = [
  '2026-10-04T09:00:00',
  '2026-10-05T09:00:00',
  '2026-10-06T09:00:00',
  '2026-10-07T09:00:00',
  '2026-10-08T09:00:00',
  '2026-10-09T09:00:00',
  '2026-10-10T09:00:00',
];

/**
 * O estado que o `useEconomicData` devolve.
 *
 * `vi.resetModules()` reexecuta a fabrica do `vi.mock`, que cria um estado
 * novo. Por isso o estado e lido DEPOIS do reset — e e o mesmo objeto que o
 * componente vai ler, porque os dois imports acontecem depois dele.
 */
const estado = { eventos: [] as unknown[] };

vi.mock('../../hooks/useEconomicData', () => ({
  useEconomicData: () => ({
    eventos: estado.eventos,
    carregando: false,
    erro: null,
    ultimaAtualizacao: new Date(),
    proximoEventoAlto: null,
    refreshManual: () => {},
    totalEventos: estado.eventos.length,
    fontes: { reais: 0, estimados: 0, feedDisponivel: true, erro: '' },
  }),
}));

/** Um evento estimado, no horario `iso`. */
const evento = (iso: string, id = 'est') => ({
  id,
  horario: new Date(iso),
  codigoPais: 'US',
  nomePais: 'Estados Unidos',
  bandeira: 'US',
  impacto: 'alto',
  titulo: 'Um evento estimado',
  tituloOriginal: 'An estimated event',
  anterior: null,
  consenso: '1,1',
  previsao: null,
  real: null,
  estimado: true,
  traduzido: true,
});

/** Carrega o calendario com o relogio parado em `iso`. */
async function montarNoDia(iso: string, eventos: unknown[]) {
  vi.setSystemTime(new Date(iso));
  vi.resetModules();
  estado.eventos = eventos;
  const { default: EconomicCalendarTab } = await import('./EconomicCalendarTab');
  return render(<EconomicCalendarTab />);
}

/** As marcas de texto que a linha carrega. */
const marcas = (): string[] =>
  Array.from(document.querySelectorAll('.cal-row-tag')).map((n) => n.textContent?.trim() ?? '');

describe('a marca de estimado nao depende do dia da semana', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  for (const iso of DIAS) {
    it(`a marca aparece com o dia congelado em ${iso.slice(0, 10)}`, async () => {
      const { unmount } = await montarNoDia(iso, [evento(iso)]);
      expect(document.querySelector('.cal-row'), `sem linha em ${iso}`).toBeTruthy();
      expect(marcas(), `sem a marca em ${iso}`).toContain('estimado');
      unmount();
    });
  }

  it('PROVA NEGATIVA: `hoje + 3 dias` perde a marca no SABADO — e o calendario esta inteiro', async () => {
    /*
      A prova de que este arquivo existe.

      Sabado 10/10: a semana visivel e 04/10 a 10/10. `em(0, ...)` = 10/10, o
      ultimo dia da semana, e a marca aparece. `em(3, ...)` = 13/10, na semana
      seguinte: nao ha aba, nao ha linha, e nao ha marca.

      Nenhum arquivo do calendario foi tocado entre as duas medidas. O que muda
      e o dia. E por isso que o teste antigo passava de quarta a sexta.
    */
    const sabado = '2026-10-10T09:00:00';
    const treze = '2026-10-13T10:00:00';

    const hoje = await montarNoDia(sabado, [evento(sabado)]);
    expect(document.querySelector('.cal-row')).toBeTruthy();
    expect(marcas(), 'hoje tem de mostrar a marca').toContain('estimado');
    hoje.unmount();

    const futuro = await montarNoDia(sabado, [evento(treze, 'futuro')]);
    expect(
      document.querySelector('.cal-row'),
      'o evento de hoje+3 caiu fora da semana visivel — e a semana tem sete dias',
    ).toBeNull();
    expect(
      marcas(),
      'sem linha, e sem marca: e o que o teste antigo media as 00:00 de 09/10',
    ).not.toContain('estimado');
    futuro.unmount();
  });
});