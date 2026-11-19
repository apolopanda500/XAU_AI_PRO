// Filtro unico do feed de eventos do Mini Terminal (UniversalLiveTerminal).
//
// PROBLEMA MEDIDO (18/11/2026, SM-A057M): o feed renderizava linhas de
// `MEXC` e `BINANCE` ("indisponivel") ao lado de linhas de MT5 mesmo com a
// corretora fora de operacao - o operador via restos de contas que a
// carteira nao mostra.
//
// REGRA: corretoras em estado planejado/registry-inativo (MEXC, BINANCE,
// BYBIT, OKX) so aparecem no feed quando a conta REAL do gateway responde
// `ok` - e quem sabe disso e o resultado do proprio `/api/universal/accounts`.
// MT5 e MOTOR sempre aparecem: fazem parte do caminho ativo.
//
// Fonte unica para o consumidor e para o teste. Nenhuma outra tela filtra
// por esta regra.

export type TerminalEventSource = 'MT5' | 'MOTOR' | string;

export type TerminalEventRow = {
  id: string;
  source: string;
  info: string;
  at: Date;
  kind: string;
};

const CORRETORAS_EM_PLANEJAMENTO = new Set(['MEXC', 'BINANCE', 'BYBIT', 'OKX']);

/** Corretoras legitimas no feed hoje: sempre MT5 e MOTOR (ciclo ativo). */
const SOURCES_ATIVAS = new Set(['MT5', 'MOTOR']);

/**
 * Devolve so as linhas cuja fonte e (a) parte do caminho ativo (MT5/MOTOR),
 * ou (b) corretora que respondeu `ok` no gateway - que e o unico sinal de
 * "conectada na carteira" disponivel nesta build.
 */
export function filtrarEventosAtivos<T extends TerminalEventRow>(
  rows: T[],
  brokersOk: ReadonlyArray<string> = [],
): T[] {
  const ativos = new Set(
    brokersOk.map((broker) => String(broker).trim().toUpperCase()).filter(Boolean),
  );
  return rows.filter((row) => {
    const source = String(row.source ?? '')
      .trim()
      .toUpperCase();
    if (SOURCES_ATIVAS.has(source)) return true;
    if (CORRETORAS_EM_PLANEJAMENTO.has(source)) return ativos.has(source);
    // Fonte desconhecida (logcat, sistema, etc.): mantida.
    return true;
  });
}
