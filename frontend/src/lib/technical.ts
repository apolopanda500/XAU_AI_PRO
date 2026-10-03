/**
 * Indicadores tecnicos calculados a partir de candles REAIS.
 *
 * Este modulo existia tambem como dependencia do gerador de sinal da IA, que
 * aplicava regras fixas sobre RSI/MACD e fabricava valores quando o calculo
 * falhava. Esse uso foi removido: o sinal agora vem da inferencia do modelo
 * treinado (backend/ai_inference.py).
 *
 * O que sobra e o calculo honesto dos indicadores, usado na aba Mercado para
 * exibir RSI/MACD/ATR ao lado dos candles que o MT5 devolveu. Aqui nao ha
 * fallback: se nao ha candles suficientes, o indicador nao e calculado e a
 * interface mostra "indisponivel" em vez de um numero inventado.
 */

export interface Candle {
  time: number | string;
  open: number;
  high: number;
  low: number;
  close: number;
  tick_volume?: number;
  volume?: number;
  real_volume?: number;
}

function closes(candles: readonly Candle[]): number[] {
  return candles.map((c) => Number(c.close)).filter((v) => Number.isFinite(v));
}

/** RSI de Wilder. Exige pelo menos `periodo + 1` candles. */
export function rsi(candles: readonly Candle[], periodo = 14): number | null {
  const c = closes(candles);
  if (c.length < periodo + 1) return null;
  let ganho = 0;
  let perda = 0;
  for (let i = 1; i <= periodo; i++) {
    const dif = c[i] - c[i - 1];
    if (dif >= 0) ganho += dif;
    else perda -= dif;
  }
  let mediaGanho = ganho / periodo;
  let mediaPerda = perda / periodo;
  for (let i = periodo + 1; i < c.length; i++) {
    const dif = c[i] - c[i - 1];
    mediaGanho = (mediaGanho * (periodo - 1) + Math.max(dif, 0)) / periodo;
    mediaPerda = (mediaPerda * (periodo - 1) + Math.max(-dif, 0)) / periodo;
  }
  if (mediaPerda === 0) return 100;
  const rs = mediaGanho / mediaPerda;
  return 100 - 100 / (1 + rs);
}

/** MACD (12, 26, 9). Exige mais candles que a media lenta. */
export function macd(
  candles: readonly Candle[],
  rapida = 12,
  lenta = 26,
  sinal = 9,
): { macd: number; sinal: number; histograma: number } | null {
  const c = closes(candles);
  if (c.length < lenta + sinal + 1) return null;

  const ema = (periodo: number): number[] => {
    const k = 2 / (periodo + 1);
    const out: number[] = [c[0]];
    for (let i = 1; i < c.length; i++) out.push(c[i] * k + out[i - 1] * (1 - k));
    return out;
  };

  const emaRapida = ema(rapida);
  const emaLenta = ema(lenta);
  const linha = c.map((_, i) => emaRapida[i] - emaLenta[i]);
  const linhaSinal = ema(sinal);
  const macdValor = linha[linha.length - 1];
  const sinalValor = linhaSinal[linhaSinal.length - 1];
  return {
    macd: macdValor,
    sinal: sinalValor,
    histograma: macdValor - sinalValor,
  };
}

/** ATR de Wilder. */
export function atr(candles: readonly Candle[], periodo = 14): number | null {
  if (candles.length < periodo + 1) return null;
  const verdadeiros: number[] = [];
  for (let i = 1; i < candles.length; i++) {
    const a = candles[i];
    const b = candles[i - 1];
    const faixa = a.high - a.low;
    const alta = Math.abs(a.high - b.close);
    const baixa = Math.abs(a.low - b.close);
    verdadeiros.push(Math.max(faixa, alta, baixa));
  }
  if (verdadeiros.length < periodo) return null;
  let media = verdadeiros.slice(0, periodo).reduce((s, v) => s + v, 0) / periodo;
  for (let i = periodo; i < verdadeiros.length; i++) {
    media = (media * (periodo - 1) + verdadeiros[i]) / periodo;
  }
  return media;
}
