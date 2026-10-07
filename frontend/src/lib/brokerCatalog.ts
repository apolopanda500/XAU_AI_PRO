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
  // Ficha de especificacao (pagina de simbolo da XM): contrato, spread em
  // pontos e swaps. Null = nao informado pela corretora, nunca zero.
  // Opcionais para payload antigo sem os campos continuar tipando.
  contractSize?: number | null;
  spreadPoints?: number | null;
  swapLong?: number | null;
  swapShort?: number | null;
  /**
   * Classe do ativo, como a CORRETORA publicou (`asset_class` em
   * `asset_registry.discover_assets`).
   *
   * MEDIDO (05/10/2026): e o campo que decide a UNIDADE do volume. Na XM,
   * Bolivar (forex) escreve "0,01 Lote(s)" e BTCUSD (crypto) escreve
   * "0,01 Token(s)". Sem este campo no catalogo, a tela so pode escrever
   * "Lote" para qualquer ativo - e isso e presumir classe, que a regra proibe.
   *
   * `null` = a corretora nao devolveu. NUNCA vira um valor adivinhado pelo nome.
   */
  assetClass?: string | null;
  /**
   * O NOME COM QUE O MODELO FOI TREINADO, quando existe (07/10/2026).
   *
   * MEDIDO na conta 391773676 (XMGlobal-MT5 14): o catalogo publica `GOLD`,
   * com `path = Derivatives\Spot Metals\GOLD` e `contract_size = 100`.
   * `XAUUSD` NAO EXISTE no terminal XM. E os `.meta.json` do app se chamam
   * `XAUUSD_H1/H4/M15/M5`.
   *
   * Entao `symbol` e `modelSymbol` sao o MESMO metal com nomes diferentes: um
   * e o que a corretora entende, o outro e o que o `.pkl` procura no disco. O
   * campo existe para a tela casar os dois sem duplicar o mapa do operador em
   * dois lugares.
   *
   * `null` = nenhum modelo treinado com este nome. NUNCA o proprio `symbol`:
   * isso seria dizer que todo par tem modelo, e a lista de modelos mentiria.
   */
  modelSymbol?: string | null;
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
      contractSize: typeof row.contract_size === 'number' ? row.contract_size : null,
      spreadPoints: typeof row.spread_points === 'number' ? row.spread_points : null,
      swapLong: typeof row.swap_long === 'number' ? row.swap_long : null,
      swapShort: typeof row.swap_short === 'number' ? row.swap_short : null,
      assetClass: typeof row.asset_class === 'string' && row.asset_class ? row.asset_class : null,
      modelSymbol: typeof row.model_symbol === 'string' && row.model_symbol ? row.model_symbol : null,
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
