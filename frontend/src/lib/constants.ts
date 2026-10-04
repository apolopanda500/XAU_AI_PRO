/**
 * Constantes canonicas do XAU AI PRO.
 *
 * Produto universal: nenhum ativo ou simbolo e fixo neste arquivo.
 * Ativos vem do catalogo da corretora (MT5, Binance, MEXC, Bybit, OKX).
 */

/** Limite de simbolos assinados no Core por cliente. */
export const MAX_SUBSCRIBE_SYMBOLS = 24;

/**
 * Normaliza uma lista de simbolos: maiusculas, sem vazio, sem duplicata e
 * dentro do limite do protocolo.
 */
export function normalizeSymbols(symbols: readonly unknown[]): string[] {
  const seen = new Set<string>();
  for (const value of symbols) {
    const symbol = String(value ?? '')
      .trim()
      .toUpperCase();
    if (!symbol || symbol.length > 40 || /\s/.test(symbol)) continue;
    seen.add(symbol);
    if (seen.size >= MAX_SUBSCRIBE_SYMBOLS) break;
  }
  return [...seen];
}
