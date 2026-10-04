export interface BrokerOption {
  id: string;
  label: string;
  /** Corretoraswhose public catalog the gateway really answers today. */
  readOnly: boolean;
}

export const BROKERS: BrokerOption[] = [
  { id: 'mt5', label: 'MT5', readOnly: false },
  { id: 'binance', label: 'Binance', readOnly: false },
  { id: 'mexc', label: 'MEXC', readOnly: false },
  { id: 'bybit', label: 'Bybit', readOnly: false },
  { id: 'okx', label: 'OKX', readOnly: false },
];

export const MARKETS_BY_BROKER: Record<string, string[]> = {
  mt5: [
    'forex',
    'metals',
    'indices',
    'stocks',
    'commodities',
    'bonds',
    'crypto-spot',
    'crypto-futures',
    'other',
  ],
  binance: ['crypto-spot', 'crypto-futures'],
  mexc: ['crypto-spot', 'crypto-futures'],
  bybit: ['crypto-spot', 'crypto-futures'],
  okx: ['crypto-spot', 'crypto-futures'],
};

export const MARKET_LABELS: Record<string, string> = {
  'crypto-spot': 'Spot',
  'crypto-futures': 'Futuros',
  forex: 'Forex',
  metals: 'Metais',
  indices: 'Índices',
  stocks: 'Ações',
  commodities: 'Commodities',
  bonds: 'Bônus',
  other: 'Outros',
};

export function brokerLabel(broker: string): string {
  return BROKERS.find((item) => item.id === broker)?.label ?? broker.toUpperCase();
}

export function compatibleMarket(broker: string, current: string): string {
  const markets = MARKETS_BY_BROKER[broker] ?? [];
  return markets.includes(current) ? current : (markets[0] ?? '');
}

/**
 * Canonicaliza o símbolo no padrão do app (BTCUSDT).
 *
 * A OKX nomeia o par com hífen (BTC-USDT) e, em futuros, com o sufixo -SWAP.
 * Sem esta normalização o mesmo ativo apareceria como dois instrumentos e a
 * cotação não casaria com a linha da tabela.
 */
export function normalizeSymbol(symbol: string): string {
  return (
    String(symbol || '')
      .trim()
      .toUpperCase()
      // O sufixo precisa sair antes de apagar os separadores, senao "BTC-USDT-SWAP"
      // vira "BTCUSDTSWAP" e nao casa com o par canonico.
      .replace(/[-_]SWAP$/, '')
      .replace(/\.(P|PERP|S)$/, '')
      .replace(/[-/_]/g, '')
  );
}

export interface AssetRow {
  symbol: string;
  displayName: string | null;
  availability: string;
  restrictions: string[];
  digits: number | null;
  point: number | null;
  volumeStep: number | null;
  volumeMin: number | null;
  volumeMax: number | null;
  tradeMode: number | null;
}

/** Extrai o catálogo real devolvido por /api/universal/assets. */
export function parseAssetCatalog(payload: unknown): AssetRow[] {
  const body = (payload ?? {}) as { assets?: unknown };
  const raw = Array.isArray(body.assets) ? body.assets : [];
  const rows: AssetRow[] = [];
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue;
    const row = item as Record<string, unknown>;
    const symbol = normalizeSymbol(String(row.symbol ?? ''));
    if (!symbol) continue;
    rows.push({
      symbol,
      displayName: row.display_name ? String(row.display_name) : null,
      availability: String(row.availability ?? 'unverified'),
      restrictions: Array.isArray(row.restrictions) ? row.restrictions.map(String) : [],
      digits: typeof row.digits === 'number' ? row.digits : null,
      point: typeof row.point === 'number' ? row.point : null,
      volumeStep: typeof row.volume_step === 'number' ? row.volume_step : null,
      volumeMin: typeof row.volume_min === 'number' ? row.volume_min : null,
      volumeMax: typeof row.volume_max === 'number' ? row.volume_max : null,
      tradeMode: typeof row.trade_mode === 'number' ? row.trade_mode : null,
    });
  }
  return rows;
}

/** Ativo que a corretora lista mas não permite operar. */
export function isTradable(row: AssetRow): boolean {
  return row.availability !== 'unavailable' && !row.restrictions.includes('symbol_disabled');
}

export function restrictionLabel(restriction: string): string {
  const labels: Record<string, string> = {
    symbol_disabled: 'desativado na corretora',
    trading_disabled: 'negociação desativada',
    long_only: 'somente compra',
    short_only: 'somente venda',
    close_only: 'somente fechamento',
  };
  return labels[restriction] ?? restriction;
}
