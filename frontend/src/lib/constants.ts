/**
 * Constantes canonicas do XAU AI PRO.
 *
 * Este arquivo existe para eliminar a triplicacao da lista de simbolos que
 * existia em `lib/protocol.ts` (DEFAULT_SYMBOLS), `hooks/useAppStore.ts`
 * (DEFAULT_MARKET_WATCHLIST) e `components/tabs/MarketTab.tsx`. Tres copias
 * da mesma informacao divergem com o tempo — e ja divergiram: as duas primeiras
 * eram identicas, a terceira nao.
 *
 * ORDEM: XAUUSD primeiro. A lista global e o fallback quando nao ha mercado
 * selecionado, e o produto se chama XAU AI PRO. Uma lista global que comecava
 * em BTCUSDT respondia "Bitcoin" para quem abria o app sem escolher mercado.
 * Listas por mercado continuam existindo em MarketTab, onde BTCUSDT abrir a
 * frente de uma exchange cripto e o comportamento correto.
 */

/** Simbolo principal do produto. */
export const SIMBOLO_PRINCIPAL = 'XAUUSD';

/**
 * Watchlist global padrao. Usada quando nao ha mercado selecionado e como
 * fallback do handshake do Core.
 */
export const DEFAULT_SYMBOLS: readonly string[] = [
  SIMBOLO_PRINCIPAL,
  'EURUSD',
  'GBPUSD',
  'USDJPY',
  'AUDUSD',
  'USDCAD',
  'NZDUSD',
  'BTCUSDT',
  'ETHUSDT',
] as const;

/** Limite de simbolos assinados no Core por cliente. */
export const MAX_SUBSCRIBE_SYMBOLS = 24;

/**
 * Normaliza uma lista de simbolos: maiusculas, sem vazio, sem duplicata e
 * dentro do limite do protocolo. Substitui as quatro copias que existiam em
 * useAppStore, useMarketWebSocket, MarketTab e marketApi.
 */
export function normalizeSymbols(symbols: readonly unknown[]): string[] {
  const seen = new Set<string>();
  for (const value of symbols) {
    const symbol = String(value ?? '').trim().toUpperCase();
    // O Core rejeita simbolo com espaco ou excessivamente longo.
    if (!symbol || symbol.length > 40 || /\s/.test(symbol)) continue;
    seen.add(symbol);
    if (seen.size >= MAX_SUBSCRIBE_SYMBOLS) break;
  }
  return [...seen];
}
