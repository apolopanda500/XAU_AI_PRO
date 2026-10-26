/*
  INDICADORES QUE O OPERADOR LIGA NO GRAFICO (23/10/2026)
  ======================================================
  Todos saem dos CANDLES EXIBIDOS, sem fonte externa: se faltar candle, a
  saida e `null` e o ponto nao aparece. `null` e ausencia, nunca zero — um
  `0` desenharia uma linha que o preco nunca tocou.

  MEDIDO: o grafico so oferecia EMA, RSI e MACD. SMA, Bollinger e VWAP sao os
  tres que o MT5 traz de fabrica e que o operador usa para decidir entrada e
  saida; sem eles a barra "Indicadores" era uma lista incompleta.
*/

/** Ponto nulo ate completar a janela; `null` nunca vira `0`. */
function nulos(n: number): Array<number | null> {
  return new Array(Math.max(0, n)).fill(null);
}

/**
 * Media movel SIMPLES. `periodo < 2` devolve tudo nulo: uma "media de 1" e o
 * proprio preco desenhado de novo, e chamar isso de indicador seria rotulo
 * sem funcao.
 */
export function smaValores(
  fechamentos: number[],
  periodo: number,
): Array<number | null> {
  if (periodo < 2 || fechamentos.length < periodo) return nulos(fechamentos.length);
  const saida: Array<number | null> = nulos(fechamentos.length);
  let soma = 0;
  for (let i = 0; i < fechamentos.length; i += 1) {
    soma += fechamentos[i];
    if (i >= periodo) soma -= fechamentos[i - periodo];
    if (i >= periodo - 1) saida[i] = soma / periodo;
  }
  return saida;
}

export type Bollinger = {
  media: Array<number | null>;
  superior: Array<number | null>;
  inferior: Array<number | null>;
};

/**
 * Bandas de Bollinger: media simples de `periodo` e `desvios` desvios-padrao
 * POPULACIONAIS da mesma janela (a definicao que o MT5 usa no `Bands`).
 *
 * `desvios <= 0` devolve media sem banda — e nao uma banda colada na media,
 * que pareceria aperto de volatilidade onde nao ha medicao.
 */
export function bollingerValores(
  fechamentos: number[],
  periodo = 20,
  desvios = 2,
): Bollinger {
  const media = smaValores(fechamentos, periodo);
  if (periodo < 2 || desvios <= 0) {
    return { media, superior: media.map(() => null), inferior: media.map(() => null) };
  }
  const superior: Array<number | null> = [];
  const inferior: Array<number | null> = [];
  for (let i = 0; i < fechamentos.length; i += 1) {
    const m = media[i];
    if (m === null || i < periodo - 1) {
      superior.push(null);
      inferior.push(null);
      continue;
    }
    let variancia = 0;
    for (let j = i - periodo + 1; j <= i; j += 1) {
      const d = fechamentos[j] - m;
      variancia += d * d;
    }
    const sd = Math.sqrt(variancia / periodo);
    superior.push(m + desvios * sd);
    inferior.push(m - desvios * sd);
  }
  return { media, superior, inferior };
}

/**
 * VWAP: preco medio ponderado pelo VOLUME, acumulado desde o primeiro candle
 * exibido. Sem volume (vela sintetica ou fonte que nao manda) devolve tudo
 * nulo — VWAP sem volume e uma media aritmetica disfarcada.
 */
export function vwapValores(
  candles: Array<{ high: number; low: number; close: number; volume: number }>,
): Array<number | null> {
  let somaPv = 0;
  let somaV = 0;
  return candles.map((c) => {
    const volume = Number(c.volume);
    if (!(volume > 0)) return null;
    const tipico = (Number(c.high) + Number(c.low) + Number(c.close)) / 3;
    if (!Number.isFinite(tipico)) return null;
    somaPv += tipico * volume;
    somaV += volume;
    return somaV > 0 ? somaPv / somaV : null;
  });
}
