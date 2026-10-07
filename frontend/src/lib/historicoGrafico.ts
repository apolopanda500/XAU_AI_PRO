/**
 * O HISTORICO do grafico: o que desfazer e refazer desfazem.
 *
 * POR QUE ISTO EXISTE
 * ===================
 * O dono pediu "desfazer" e "refazer" na barra do grafico, como na XM. Botao de
 * desfazer sem HISTORICO e um botao decorativo: liga, desliga, e nao muda
 * nada — exatamente o defeito do botao EMA, que ele reportou como "travado de
 * cima azul" (06/10/2026).
 *
 * Por isso o historico mora aqui e nao dentro do componente: ele e dado, e o
 * componente decide o que entra nele.
 *
 * O QUE ENTRA E O QUE NAO ENTRA
 * =============================
 * ENTRA: mudanca que o operador fez e que muda o que o grafico DESENHA — tipo
 * de grafico, indicador ligado, timeframe, linhas de preco.
 *
 * NAO ENTRA: valor que muda sozinho (cotacao, volume, indicador calculado de
 * candles novos). Entrar tornaria o desfazer inutil: a proxima cotacao criaria
 * um passo novo, e o operador nunca voltaria a um estado anterior.
 *
 * O LIMITE
 * ========
 * `LIMITE` passos. Um historico ilimitado cresce sem parar numa sessao longa e
 * nao compra nada — o operador desfaz o que fez nos ultimos segundos, nao o que
 * fez a hora passada. E o limite esta escrito aqui, e nao escondido no
 * componente, para que o botao de desfazer possa dizer "ate onde volta".
 */

/** Uma mudanca do operador, com o estado de ANTES e o de DEPOIS. */
export interface Passo<T> {
  /** Rótulo que o botão de desfazer mostra: "desfazer tipo de gráfico". */
  rotulo: string;
  antes: T;
  depois: T;
}

/** Quantos passos o historico guarda. */
export const LIMITE = 50;

export type Historico<T> = {
  /** Passos ainda desfazíveis, do mais antigo ao mais recente. */
  passos: Array<Passo<T>>;
  /** O que REDEFEZ, para refazer. Sai da pilha quando um passo novo entra. */
  refazer: Array<Passo<T>>;
  /** O estado atual. */
  atual: T;
};

export const historicoVazio = <T>(inicial: T): Historico<T> => ({
  passos: [],
  refazer: [],
  atual: inicial,
});

/**
 * O estado e IGUAL ao que ja esta?
 *
 * `Object.is` sozinho NAO serve: o estado do grafico e um OBJETO
 * (`{tipo, rsi, ema}`), e o React recria esse objeto a cada render. Com
 * `Object.is`, clicar duas vezes no mesmo botao criaria dois passos com o
 * mesmo conteudo — e o operador teria de apertar "desfazer" DUAS vezes para o
 * grafico voltar ao estado anterior (MEDIDO: era o que o teste acusava).
 *
 * A comparacao e por CONTEUDO, campo a campo. O estado e pequeno e plano, e
 * esse e o preco de nao ter passo fantasma.
 */
const iguais = <T>(a: T, b: T): boolean => {
  if (Object.is(a, b)) return true;
  if (typeof a !== 'object' || typeof b !== 'object' || a === null || b === null) return false;
  const chaves = new Set([...Object.keys(a as object), ...Object.keys(b as object)]);
  for (const chave of chaves) {
    if (!Object.is((a as Record<string, unknown>)[chave], (b as Record<string, unknown>)[chave])) {
      return false;
    }
  }
  return true;
};

/**
 * Um passo novo LIMPA a pilha de refazer.
 *
 * E o que toda ferramenta faz: mexer em algo depois de desfazer descarta o
 * "refazer", porque o caminho que ele descreveria deixou de existir.
 */
export function registrar<T>(estado: Historico<T>, depois: T, rotulo: string): Historico<T> {
  if (iguais(estado.atual, depois)) return estado;
  const passo: Passo<T> = { rotulo, antes: estado.atual, depois };
  const passos = [...estado.passos, passo];
  return {
    atual: depois,
    passos: passos.length > LIMITE ? passos.slice(passos.length - LIMITE) : passos,
    refazer: [],
  };
}

/**
 * Desfaz UM passo, ou devolve o estado intacto quando nao ha nenhum.
 *
 * Devolver o MESMO objeto quando nao ha o que desfazer e o que permite ao
 * botao desabilitar por `disabled={!podeDesfazer}` sem um estado extra: e a
 * propria estrutura que diz.
 */
export function desfazer<T>(estado: Historico<T>): Historico<T> {
  const ultimo = estado.passos[estado.passos.length - 1];
  if (!ultimo) return estado;
  return {
    atual: ultimo.antes,
    passos: estado.passos.slice(0, -1),
    refazer: [...estado.refazer, ultimo],
  };
}

/** Refaz UM passo, ou devolve o estado intacto quando nao ha nenhum. */
export function refazer<T>(estado: Historico<T>): Historico<T> {
  const proximo = estado.refazer[estado.refazer.length - 1];
  if (!proximo) return estado;
  return {
    atual: proximo.depois,
    passos: [...estado.passos, proximo],
    refazer: estado.refazer.slice(0, -1),
  };
}

export const podeDesfazer = <T>(estado: Historico<T>): boolean => estado.passos.length > 0;
export const podeRefazer = <T>(estado: Historico<T>): boolean => estado.refazer.length > 0;

/** O rótulo do que o botão de desfazer vai desfazer. */
export const rotuloDesfazer = <T>(estado: Historico<T>): string =>
  estado.passos[estado.passos.length - 1]?.rotulo ?? '';

/** O rótulo do que o botão de refazer vai refazer. */
export const rotuloRefazer = <T>(estado: Historico<T>): string =>
  estado.refazer[estado.refazer.length - 1]?.rotulo ?? '';