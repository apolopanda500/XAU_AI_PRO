import { apiBase } from './api';

export const MARKET_ENDPOINTS = {
  overview: '/api/universal/overview',
  assets: '/api/universal/assets',
  quotes: '/api/universal/quotes',
  stats24h: '/api/universal/stats24h',
  candles: '/api/universal/candles',
  depth: '/api/universal/depth',
  trades: '/api/universal/trades',
  status: '/api/status',
  capabilities: '/api/capabilities',
} as const;

export type MarketBroker = 'mt5' | 'binance' | 'mexc' | 'bybit' | 'okx';
export type MarketKind = 'forex' | 'metals' | 'indices' | 'stocks' | 'commodities' | 'bonds' | 'other' | 'crypto-spot' | 'crypto-futures';

export interface MarketSource {
  broker: MarketBroker;
  market: MarketKind;
}

export interface MarketIdentity extends MarketSource {
  symbol: string;
}

export interface Provenance {
  source: string;
  received_at: string;
  provider_timestamp: string | null;
}

export interface MarketAsset extends Provenance {
  broker: MarketBroker;
  market: MarketKind;
  symbol: string;
  display_name: string | null;
  asset_type: string | null;
  base_asset: string | null;
  quote_asset: string | null;
  enabled: boolean | null;
  status: string | null;
  volume_min: number | null;
  volume_max: number | null;
  volume_step: number | null;
  point: number | null;
  digits: number | null;
  trade_mode: number | null;
  availability: 'available' | 'restricted' | 'unavailable' | 'unverified';
  restrictions: string[];
  capabilities: string[];
  capability_matrix: Array<{
    capability: string;
    status: 'available' | 'unsupported' | 'unverified';
    restrictions: string[];
  }>;
}

export interface MarketQuote extends Provenance {
  broker: MarketBroker;
  market: MarketKind;
  symbol: string;
  last: number | null;
  price: number | null;
  bid: number | null;
  ask: number | null;
  spread: number | null;
  high: number | null;
  low: number | null;
  change: number | null;
  change_pct: number | null;
  volume: number | null;
  digits: number | null;
  point: number | null;
  timestamp: string | null;
}

export interface MarketStats24h extends Provenance {
  broker: MarketBroker;
  market: MarketKind;
  symbol: string;
  last: number | null;
  bid: number | null;
  ask: number | null;
  high: number | null;
  low: number | null;
  change: number | null;
  change_pct: number | null;
  volume: number | null;
  quote_volume: number | null;
  trades_count: number | null;
  spread: number | null;
}

export interface MarketCandle extends Provenance {
  broker: MarketBroker;
  market: MarketKind;
  symbol: string;
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
}

export interface DepthLevel {
  price: number | null;
  quantity: number | null;
}

export interface MarketDepth extends Provenance {
  broker: MarketBroker;
  market: MarketKind;
  symbol: string;
  bids: DepthLevel[];
  asks: DepthLevel[];
}

export interface PublicTrade extends Provenance {
  broker: MarketBroker;
  market: MarketKind;
  symbol: string;
  id: string | null;
  price: number | null;
  quantity: number | null;
  quote_quantity: number | null;
  side: 'BUY' | 'SELL' | null;
  provider_timestamp: string | null;
  timestamp: string | null;
}

export interface MarketAccountSnapshot {
  login: string | null;
  server: string | null;
  currency: string | null;
  balance: number | null;
  equity: number | null;
  available: number | null;
  margin: number | null;
  mode: string | null;
  trade_allowed: boolean | null;
  raw: Record<string, unknown> | null;
}

export interface MarketPositionSnapshot {
  ticket: string | null;
  symbol: string | null;
  side: string | null;
  quantity: number | null;
  entry_price: number | null;
  mark_price: number | null;
  unrealized_pnl: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  raw: Record<string, unknown> | null;
}

export interface MarketConnection {
  id: string | null;
  broker: MarketBroker | string;
  market: string;
  active: boolean | null;
  status: string | null;
  account: MarketAccountSnapshot | null;
  positions: MarketPositionSnapshot[];
  pnl: number | null;
  pnl_available: boolean | null;
  error: string | null;
  source: string;
}

export interface MarketOverview extends Provenance {
  mt5_required: boolean | null;
  connected: number | null;
  connections: MarketConnection[];
}

export interface Mt5Heartbeat {
  live: boolean | null;
  age_sec: number | null;
  symbol: string | null;
  autotrading: boolean | null;
  source: string | null;
}

export interface Mt5Status extends Provenance {
  gateway: string | null;
  mt5_connected: boolean | null;
  account: MarketAccountSnapshot | null;
  positions: MarketPositionSnapshot[];
  ea_heartbeat: Mt5Heartbeat | null;
}

export interface MarketItemError {
  symbol: string | null;
  error: string;
}

export interface MarketAssetResponse extends Provenance {
  broker: MarketBroker;
  market: MarketKind;
  assets: MarketAsset[];
  errors: MarketItemError[];
}

export interface MarketQuoteResponse extends Provenance {
  broker: MarketBroker;
  market: MarketKind;
  quotes: MarketQuote[];
  errors: MarketItemError[];
}

export interface MarketStatsResponse extends Provenance {
  broker: MarketBroker;
  market: MarketKind;
  symbol: string;
  stats: MarketStats24h | null;
}

export interface MarketCandleResponse extends Provenance {
  broker: MarketBroker;
  market: MarketKind;
  symbol: string;
  timeframe: string;
  candles: MarketCandle[];
}

export interface MarketDepthResponse extends Provenance {
  broker: MarketBroker;
  market: MarketKind;
  symbol: string;
  bids: DepthLevel[];
  asks: DepthLevel[];
}

export interface MarketTradesResponse extends Provenance {
  broker: MarketBroker;
  market: MarketKind;
  symbol: string;
  trades: PublicTrade[];
}

export interface MarketRequestOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
  fetcher?: typeof fetch;
}

export type MarketApiErrorCode = 'aborted' | 'http' | 'invalid' | 'network' | 'simulated_source' | 'identity';

export class MarketApiError extends Error {
  readonly code: MarketApiErrorCode;
  readonly endpoint: string | null;
  readonly status: number | null;

  constructor(message: string, code: MarketApiErrorCode, endpoint: string | null = null, status: number | null = null) {
    super(message);
    this.name = 'MarketApiError';
    this.code = code;
    this.endpoint = endpoint;
    this.status = status;
  }
}

export interface MarketSourceOption {
  broker: MarketBroker;
  label: string;
  markets: MarketKind[];
  enabled: boolean;
}

export interface MarketCapabilityRow {
  broker: MarketBroker;
  market: MarketKind;
  status: 'active' | 'code_only' | 'planned' | string;
  read_only: boolean;
  capabilities: string[];
  execution: string[];
  withdrawals: boolean;
  transfers: boolean;
}

export interface MarketCapabilities {
  source: string;
  received_at: string;
  provider_timestamp: string | null;
  matrix: MarketCapabilityRow[];
}

export const MARKET_SOURCES: readonly MarketSourceOption[] = [
  { broker: 'mt5', label: 'MetaTrader 5', markets: ['forex', 'metals', 'indices', 'stocks', 'commodities', 'bonds', 'crypto-spot', 'crypto-futures', 'other'], enabled: true },
  { broker: 'binance', label: 'Binance', markets: ['crypto-spot', 'crypto-futures'], enabled: true },
  { broker: 'mexc', label: 'MEXC', markets: ['crypto-spot', 'crypto-futures'], enabled: true },
  { broker: 'bybit', label: 'Bybit', markets: ['crypto-spot', 'crypto-futures'], enabled: false },
  { broker: 'okx', label: 'OKX', markets: ['crypto-spot', 'crypto-futures'], enabled: false },
];

const SOURCE_REJECTION = /simulated|simulation|mock|mocked|fake|dummy|synthetic|placeholder/i;
const PROVIDER_KEYS = new Set(['source', 'provider', 'data_source', 'origin', 'feed']);
const DEFAULT_TIMEOUT_MS = 8_000;
const DEFAULT_RECEIVED_AT = () => new Date().toISOString();

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function firstDefined(...values: unknown[]): unknown {
  return values.find((value) => value !== undefined && value !== null);
}

function readString(value: unknown): string | null {
  if (typeof value === 'string') {
    const text = value.trim();
    return text || null;
  }
  if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  return null;
}

function readBoolean(value: unknown): boolean | null {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase();
    if (normalized === 'true') return true;
    if (normalized === 'false') return false;
  }
  return null;
}

function readNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function readTimestamp(value: unknown): string | null {
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value.toISOString();
  if (typeof value === 'number' && Number.isFinite(value)) {
    const milliseconds = Math.abs(value) > 100_000_000_000 ? value : value * 1000;
    const date = new Date(milliseconds);
    return Number.isNaN(date.getTime()) ? null : date.toISOString();
  }
  if (typeof value === 'string' && value.trim()) {
    const text = value.trim();
    if (/^-?\d+(?:\.\d+)?$/.test(text)) return readTimestamp(Number(text));
    const parsed = Date.parse(text);
    return Number.isNaN(parsed) ? null : new Date(parsed).toISOString();
  }
  return null;
}

function sourceValue(value: unknown): string | null {
  const direct = readString(value);
  if (direct) return direct;
  if (isRecord(value)) {
    for (const key of ['id', 'name', 'provider', 'kind', 'type']) {
      const nested = readString(value[key]);
      if (nested) return nested;
    }
  }
  return null;
}

function assertRealSource(value: unknown, endpoint: string | null = null): void {
  if (typeof value === 'string') {
    if (SOURCE_REJECTION.test(value)) throw new MarketApiError('Fonte simulada ou mock rejeitada.', 'simulated_source', endpoint);
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item) => assertRealSource(item, endpoint));
    return;
  }
  if (!isRecord(value)) return;
  Object.entries(value).forEach(([key, nested]) => {
    if (PROVIDER_KEYS.has(key) || key.toLowerCase().includes('source') || key.toLowerCase().includes('provider')) {
      const candidate = sourceValue(nested);
      if (candidate && SOURCE_REJECTION.test(candidate)) throw new MarketApiError('Fonte simulada ou mock rejeitada.', 'simulated_source', endpoint);
    }
    if (isRecord(nested) || Array.isArray(nested)) assertRealSource(nested, endpoint);
  });
}

function sourceFor(raw: Record<string, unknown>, fallback: string, receivedAt: string): Provenance {
  const candidate = sourceValue(firstDefined(raw.source, raw.provider, raw.data_source, raw.origin, raw.feed));
  const source = candidate ?? fallback;
  assertRealSource(source);
  const providerTimestamp = readTimestamp(firstDefined(raw.provider_timestamp, raw.providerTimestamp, raw.exchange_timestamp, raw.timestamp, raw.time, raw.ts));
  const receivedTimestamp = readTimestamp(firstDefined(raw.received_at, raw.receivedAt, raw.received)) ?? receivedAt;
  return { source, received_at: receivedTimestamp, provider_timestamp: providerTimestamp };
}

function responseSource(payload: Record<string, unknown>, fallback: string, receivedAt: string): Provenance {
  assertRealSource(payload);
  const source = sourceValue(firstDefined(payload.source, payload.provider, payload.data_source, payload.origin, payload.feed));
  if (!source) throw new MarketApiError(`A resposta de ${fallback} não informa a fonte real.`, 'invalid', fallback);
  return sourceFor(payload, source, receivedAt);
}

function marketMatches(actual: string, expected: MarketKind): boolean {
  const value = actual.trim().toLowerCase();
  if (value === expected.toLowerCase()) return true;
  if (expected === 'crypto-spot') return value === 'spot' || value === 'crypto';
  if (expected === 'crypto-futures') return value === 'futures' || value === 'futuro' || value === 'futuros';
  return false;
}

function assertPayloadIdentity(payload: Record<string, unknown>, expected: MarketSource & { symbol?: string }): void {
  const broker = readString(payload.broker);
  const market = readString(payload.market);
  const symbol = readString(payload.symbol);
  if (!broker || !market) throw new MarketApiError('A resposta não informa corretora e mercado.', 'identity');
  if (broker.toLowerCase() !== expected.broker.toLowerCase()) {
    throw new MarketApiError('A resposta veio de outra corretora.', 'identity');
  }
  if (!marketMatches(market, expected.market as MarketKind)) {
    throw new MarketApiError('A resposta veio de outro mercado.', 'identity');
  }
  if (expected.symbol && (!symbol || symbol.toUpperCase() !== expected.symbol.toUpperCase())) {
    throw new MarketApiError('A resposta veio de outro ativo.', 'identity');
  }
}

function assertRowIdentity(row: Record<string, unknown>, expected: MarketSource & { symbol?: string }): void {
  const broker = readString(row.broker);
  const market = readString(row.market);
  const symbol = readString(row.symbol);
  if (broker && broker.toLowerCase() !== expected.broker.toLowerCase()) throw new MarketApiError('A linha veio de outra corretora.', 'identity');
  if (market && !marketMatches(market, expected.market as MarketKind)) throw new MarketApiError('A linha veio de outro mercado.', 'identity');
  if (expected.symbol && symbol && symbol.toUpperCase() !== expected.symbol.toUpperCase()) throw new MarketApiError('A linha veio de outro ativo.', 'identity');
}

function rowsFrom(payload: unknown, keys: string[]): unknown[] | null {
  if (Array.isArray(payload)) return payload;
  if (!isRecord(payload)) return null;
  for (const key of keys) {
    const value = payload[key];
    if (Array.isArray(value)) return value;
    if (isRecord(value)) {
      for (const nestedKey of keys) {
        if (Array.isArray(value[nestedKey])) return value[nestedKey] as unknown[];
      }
    }
  }
  if (isRecord(payload.data)) {
    for (const key of keys) {
      if (Array.isArray(payload.data[key])) return payload.data[key] as unknown[];
    }
  }
  return null;
}

function errorMessage(value: unknown, fallback: string): string {
  if (typeof value === 'string' && value.trim()) return value.trim();
  if (isRecord(value)) {
    const nested = readString(firstDefined(value.message, value.error, value.detail));
    if (nested) return nested;
  }
  return fallback;
}

function itemErrors(payload: Record<string, unknown>): MarketItemError[] {
  const values = Array.isArray(payload.errors) ? payload.errors : Array.isArray(payload.failures) ? payload.failures : [];
  return values.map((value) => {
    if (typeof value === 'string') return { symbol: null, error: value };
    if (isRecord(value)) return { symbol: readString(value.symbol), error: errorMessage(value, 'Falha da fonte.') };
    return { symbol: null, error: 'Falha da fonte.' };
  });
}

function accountSnapshot(value: unknown): MarketAccountSnapshot | null {
  if (!isRecord(value)) return null;
  return {
    login: readString(value.login ?? value.account ?? value.account_id ?? value.id),
    server: readString(value.server ?? value.server_name),
    currency: readString(value.currency ?? value.asset),
    balance: readNumber(value.balance ?? value.totalWalletBalance ?? value.walletBalance),
    equity: readNumber(value.equity ?? value.marginBalance ?? value.totalMarginBalance),
    available: readNumber(value.available ?? value.availableBalance ?? value.free_margin ?? value.margin_free),
    margin: readNumber(value.margin ?? value.marginUsed),
    mode: readString(value.mode),
    trade_allowed: readBoolean(value.trade_allowed ?? value.tradeAllowed),
    raw: value,
  };
}

function positionSnapshot(value: unknown): MarketPositionSnapshot | null {
  if (!isRecord(value)) return null;
  return {
    ticket: readString(value.ticket ?? value.id),
    symbol: readString(value.symbol),
    side: readString(value.side ?? value.type),
    quantity: readNumber(value.quantity ?? value.volume ?? value.amount),
    entry_price: readNumber(value.entry_price ?? value.open_price ?? value.entryPrice),
    mark_price: readNumber(value.mark_price ?? value.current_price ?? value.price_current ?? value.markPrice),
    unrealized_pnl: readNumber(value.unrealized_pnl ?? value.profit ?? value.unRealizedProfit),
    stop_loss: readNumber(value.stop_loss ?? value.sl),
    take_profit: readNumber(value.take_profit ?? value.tp),
    raw: value,
  };
}

function responseRows(payload: Record<string, unknown>, keys: string[], endpoint: string): unknown[] {
  const rows = rowsFrom(payload, keys);
  if (!rows) throw new MarketApiError(`Resposta inválida de ${endpoint}.`, 'invalid', endpoint);
  return rows;
}

function normalizeSymbol(value: unknown): string | null {
  return readString(value)?.toUpperCase() ?? null;
}

function normalizeSource(raw: Record<string, unknown>, fallback: string, receivedAt: string): Provenance {
  return sourceFor(raw, fallback, receivedAt);
}

function normalizeAsset(rawValue: unknown, expected: MarketSource, fallback: string, receivedAt: string): MarketAsset | null {
  const raw = isRecord(rawValue) ? rawValue : { symbol: rawValue };
  const symbol = normalizeSymbol(firstDefined(raw.symbol, raw.ticker, raw.code, raw.name));
  if (!symbol) return null;
  try {
    assertRowIdentity(raw, expected);
  } catch {
    return null;
  }
  const provenance = normalizeSource(raw, fallback, receivedAt);
  const capabilities = Array.isArray(raw.capabilities) ? raw.capabilities.map((item) => readString(item)).filter((item): item is string => item !== null) : [];
  const restrictions = Array.isArray(raw.restrictions) ? raw.restrictions.map((item) => readString(item)).filter((item): item is string => item !== null) : [];
  const availabilityValue = readString(raw.availability);
  const availability = availabilityValue === 'available' || availabilityValue === 'restricted' || availabilityValue === 'unavailable' || availabilityValue === 'unverified' ? availabilityValue : 'unverified';
  const capabilityMatrix = Array.isArray(raw.capability_matrix) ? raw.capability_matrix.flatMap((item) => {
    if (!isRecord(item)) return [];
    const capability = readString(item.capability);
    const status = readString(item.status);
    if (!capability) return [];
    return [{
      capability,
      status: status === 'available' || status === 'unsupported' || status === 'unverified' ? status as 'available' | 'unsupported' | 'unverified' : 'unverified' as const,
      restrictions: Array.isArray(item.restrictions) ? item.restrictions.map((entry) => readString(entry)).filter((entry): entry is string => entry !== null) : [],
    }];
  }) : [];
  return {
    ...provenance,
    broker: expected.broker,
    market: expected.market,
    symbol,
    display_name: readString(firstDefined(raw.display_name, raw.displayName, raw.name, raw.label)),
    asset_type: readString(firstDefined(raw.asset_type, raw.type, raw.category, raw.market_type)),
    base_asset: readString(firstDefined(raw.base_asset, raw.baseAsset, raw.base)),
    quote_asset: readString(firstDefined(raw.quote_asset, raw.quoteAsset, raw.quote)),
    enabled: readBoolean(firstDefined(raw.enabled, raw.active, raw.visible)),
    status: readString(firstDefined(raw.status, raw.state, raw.contractStatus)),
    volume_min: readNumber(firstDefined(raw.volume_min, raw.minVolume, raw.minVol)),
    volume_max: readNumber(firstDefined(raw.volume_max, raw.maxVolume, raw.maxVol)),
    volume_step: readNumber(firstDefined(raw.volume_step, raw.stepSize, raw.lotSize)),
    point: readNumber(firstDefined(raw.point, raw.tickSize, raw.priceTick)),
    digits: readNumber(firstDefined(raw.digits, raw.pricePrecision)),
    trade_mode: readNumber(firstDefined(raw.trade_mode, raw.tradeMode)),
    availability,
    restrictions,
    capabilities,
    capability_matrix: capabilityMatrix,
  };
}

function normalizeQuote(rawValue: unknown, expected: MarketIdentity, fallback: string, receivedAt: string): MarketQuote | null {
  if (!isRecord(rawValue)) return null;
  const symbol = normalizeSymbol(firstDefined(rawValue.symbol, rawValue.ticker));
  if (!symbol || symbol !== expected.symbol.toUpperCase()) return null;
  assertRowIdentity(rawValue, expected);
  const provenance = normalizeSource(rawValue, fallback, receivedAt);
  const bid = readNumber(firstDefined(rawValue.bid, rawValue.bidPrice, rawValue.bidPx, rawValue.bid1));
  const ask = readNumber(firstDefined(rawValue.ask, rawValue.askPrice, rawValue.askPx, rawValue.ask1));
  const last = readNumber(firstDefined(rawValue.last, rawValue.price, rawValue.lastPrice, rawValue.lastTradedPrice));
  const spread = readNumber(firstDefined(rawValue.spread, rawValue.spread_abs)) ?? (bid !== null && ask !== null ? ask - bid : null);
  return {
    ...provenance,
    broker: expected.broker,
    market: expected.market,
    symbol,
    last,
    price: last,
    bid,
    ask,
    spread,
    high: readNumber(firstDefined(rawValue.high, rawValue.highPrice, rawValue.dayHigh, rawValue.high24h)),
    low: readNumber(firstDefined(rawValue.low, rawValue.lowPrice, rawValue.dayLow, rawValue.low24h)),
    change: readNumber(firstDefined(rawValue.change, rawValue.priceChange, rawValue.change_abs)),
    change_pct: readNumber(firstDefined(rawValue.change_pct, rawValue.changePct, rawValue.priceChangePercent, rawValue.changePercent)),
    volume: readNumber(firstDefined(rawValue.volume, rawValue.baseVolume, rawValue.base_volume, rawValue.v, rawValue.qty)),
    digits: readNumber(firstDefined(rawValue.digits, rawValue.precision)),
    point: readNumber(firstDefined(rawValue.point, rawValue.tickSize)),
    timestamp: readTimestamp(firstDefined(rawValue.provider_timestamp, rawValue.providerTimestamp, rawValue.timestamp, rawValue.time)),
  };
}

function normalizeStats(payload: Record<string, unknown>, expected: MarketIdentity, fallback: string, receivedAt: string): MarketStats24h | null {
  const raw = isRecord(payload.stats) ? { ...payload, ...payload.stats } : payload;
  assertPayloadIdentity(raw, expected);
  const provenance = normalizeSource(raw, fallback, receivedAt);
  const bid = readNumber(firstDefined(raw.bid, raw.bidPrice));
  const ask = readNumber(firstDefined(raw.ask, raw.askPrice));
  const last = readNumber(firstDefined(raw.last, raw.price, raw.lastPrice));
  return {
    ...provenance,
    broker: expected.broker,
    market: expected.market,
    symbol: expected.symbol.toUpperCase(),
    last,
    bid,
    ask,
    high: readNumber(firstDefined(raw.high, raw.highPrice, raw.high24h)),
    low: readNumber(firstDefined(raw.low, raw.lowPrice, raw.low24h)),
    change: readNumber(firstDefined(raw.change, raw.priceChange)),
    change_pct: readNumber(firstDefined(raw.change_pct, raw.changePct, raw.priceChangePercent)),
    volume: readNumber(firstDefined(raw.volume, raw.baseVolume, raw.base_volume)),
    quote_volume: readNumber(firstDefined(raw.quote_volume, raw.quoteVolume, raw.volumeQuote, raw.turnover)),
    trades_count: readNumber(firstDefined(raw.trades_count, raw.tradeCount, raw.count)),
    spread: readNumber(raw.spread) ?? (bid !== null && ask !== null ? ask - bid : null),
  };
}

function candleValues(rawValue: unknown): { time: unknown; open: unknown; high: unknown; low: unknown; close: unknown; volume: unknown } | null {
  if (Array.isArray(rawValue)) {
    return { time: rawValue[0], open: rawValue[1], high: rawValue[2], low: rawValue[3], close: rawValue[4], volume: rawValue[5] };
  }
  if (!isRecord(rawValue)) return null;
  return {
    time: firstDefined(rawValue.time, rawValue.timestamp, rawValue.openTime, rawValue.open_time, rawValue.t),
    open: firstDefined(rawValue.open, rawValue.o),
    high: firstDefined(rawValue.high, rawValue.h),
    low: firstDefined(rawValue.low, rawValue.l),
    close: firstDefined(rawValue.close, rawValue.c),
    volume: firstDefined(rawValue.volume, rawValue.v, rawValue.vol, rawValue.tick_volume),
  };
}

function normalizeCandle(rawValue: unknown, expected: MarketIdentity, fallback: string, receivedAt: string): MarketCandle | null {
  const values = candleValues(rawValue);
  if (!values) return null;
  const timestamp = readTimestamp(values.time);
  const time = timestamp ? Math.floor(new Date(timestamp).getTime() / 1000) : null;
  const open = readNumber(values.open);
  const high = readNumber(values.high);
  const low = readNumber(values.low);
  const close = readNumber(values.close);
  if (time === null || open === null || high === null || low === null || close === null) return null;
  const raw = isRecord(rawValue) ? rawValue : {};
  try {
    assertRowIdentity(raw, expected);
  } catch {
    return null;
  }
  return {
    ...normalizeSource(raw, fallback, receivedAt),
    broker: expected.broker,
    market: expected.market,
    symbol: expected.symbol.toUpperCase(),
    time,
    open,
    high,
    low,
    close,
    volume: readNumber(values.volume),
  };
}

function depthLevel(rawValue: unknown): DepthLevel | null {
  if (Array.isArray(rawValue)) return { price: readNumber(rawValue[0]), quantity: readNumber(rawValue[1] ?? rawValue[2]) };
  if (!isRecord(rawValue)) return null;
  return {
    price: readNumber(firstDefined(rawValue.price, rawValue.p, rawValue.level, rawValue[0])),
    quantity: readNumber(firstDefined(rawValue.quantity, rawValue.qty, rawValue.size, rawValue.amount, rawValue.volume)),
  };
}

function normalizeDepth(payload: Record<string, unknown>, expected: MarketIdentity, fallback: string, receivedAt: string): MarketDepthResponse {
  assertPayloadIdentity(payload, expected);
  const provenance = normalizeSource(payload, fallback, receivedAt);
  const asksRaw = Array.isArray(payload.asks) ? payload.asks : rowsFrom(payload.asks, ['asks']) ?? [];
  const bidsRaw = Array.isArray(payload.bids) ? payload.bids : rowsFrom(payload.bids, ['bids']) ?? [];
  return {
    ...provenance,
    broker: expected.broker,
    market: expected.market,
    symbol: expected.symbol.toUpperCase(),
    asks: asksRaw.map(depthLevel).filter((row): row is DepthLevel => row !== null),
    bids: bidsRaw.map(depthLevel).filter((row): row is DepthLevel => row !== null),
  };
}

function tradeSide(raw: Record<string, unknown>): 'BUY' | 'SELL' | null {
  const side = readString(firstDefined(raw.side, raw.takerSide, raw.direction));
  if (side) return side.toUpperCase() === 'SELL' || side.toUpperCase() === 'S' ? 'SELL' : side.toUpperCase() === 'BUY' || side.toUpperCase() === 'B' ? 'BUY' : null;
  const buyerMaker = readBoolean(firstDefined(raw.isBuyerMaker, raw.is_buyer_maker));
  return buyerMaker === null ? null : buyerMaker ? 'SELL' : 'BUY';
}

function tradeValues(rawValue: unknown): { raw: Record<string, unknown>; id: unknown; price: unknown; quantity: unknown; quoteQuantity: unknown; time: unknown } | null {
  if (Array.isArray(rawValue)) {
    return { raw: {}, id: rawValue[0], price: rawValue[1], quantity: rawValue[2], time: rawValue[3] ?? rawValue[5], quoteQuantity: rawValue[4] };
  }
  if (!isRecord(rawValue)) return null;
  return {
    raw: rawValue,
    id: firstDefined(rawValue.id, rawValue.trade_id, rawValue.tradeId),
    price: firstDefined(rawValue.price, rawValue.p),
    quantity: firstDefined(rawValue.quantity, rawValue.qty, rawValue.size, rawValue.amount, rawValue.q),
    quoteQuantity: firstDefined(rawValue.quoteQty, rawValue.quote_qty, rawValue.quoteQuantity, rawValue.quote_quantity),
    time: firstDefined(rawValue.timestamp, rawValue.time, rawValue.T, rawValue.ts),
  };
}

function normalizeTrade(rawValue: unknown, expected: MarketIdentity, fallback: string, receivedAt: string): PublicTrade | null {
  const values = tradeValues(rawValue);
  if (!values) return null;
  const timestamp = readTimestamp(values.time);
  const symbol = normalizeSymbol(firstDefined(values.raw.symbol, values.raw.symbolName)) ?? expected.symbol.toUpperCase();
  if (symbol !== expected.symbol.toUpperCase()) return null;
  try {
    assertRowIdentity(values.raw, expected);
  } catch {
    return null;
  }
  const provenance = normalizeSource(values.raw, fallback, receivedAt);
  return {
    ...provenance,
    broker: expected.broker,
    market: expected.market,
    symbol: expected.symbol.toUpperCase(),
    id: readString(values.id),
    price: readNumber(values.price),
    quantity: readNumber(values.quantity),
    quote_quantity: readNumber(values.quoteQuantity),
    side: tradeSide(values.raw),
    provider_timestamp: timestamp,
    timestamp,
  };
}

function buildUrl(path: string, params: Record<string, string | number | undefined>): string {
  const base = apiBase().replace(/\/+$/, '');
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).length > 0) query.set(key, String(value));
  });
  const suffix = query.toString();
  return `${base}${path}${suffix ? `?${suffix}` : ''}`;
}

async function requestJson(endpoint: string, params: Record<string, string | number | undefined>, options: MarketRequestOptions = {}): Promise<{ payload: Record<string, unknown>; receivedAt: string }> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const onAbort = () => controller.abort();
  if (options.signal) {
    if (options.signal.aborted) controller.abort();
    else options.signal.addEventListener('abort', onAbort, { once: true });
  }
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const fetcher = options.fetcher ?? (typeof fetch === 'function' ? fetch : null);
  if (!fetcher) throw new MarketApiError('Fetch indisponível neste ambiente.', 'network', endpoint);
  try {
    const response = await fetcher(buildUrl(endpoint, params), { method: 'GET', signal: controller.signal, headers: { Accept: 'application/json' } });
    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      throw new MarketApiError(`Resposta JSON inválida de ${endpoint}.`, 'invalid', endpoint, response.status);
    }
    if (!response.ok || (isRecord(payload) && payload.ok === false)) {
      const message = isRecord(payload) ? errorMessage(payload.error ?? payload.message, `Gateway HTTP ${response.status}.`) : `Gateway HTTP ${response.status}.`;
      throw new MarketApiError(message, 'http', endpoint, response.status);
    }
    if (!isRecord(payload)) throw new MarketApiError(`Resposta inválida de ${endpoint}.`, 'invalid', endpoint, response.status);
    return { payload, receivedAt: DEFAULT_RECEIVED_AT() };
  } catch (error) {
    if (error instanceof MarketApiError) throw error;
    if (controller.signal.aborted || (options.signal?.aborted)) throw new MarketApiError('Requisição cancelada.', 'aborted', endpoint);
    throw new MarketApiError(error instanceof Error ? error.message : 'Falha de rede.', 'network', endpoint);
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener('abort', onAbort);
  }
}

function normalizeOverview(payload: Record<string, unknown>, receivedAt: string): MarketOverview {
  const provenance = responseSource(payload, 'universal_gateway', receivedAt);
  const connectionsRaw = Array.isArray(payload.connections) ? payload.connections : [];
  const connections = connectionsRaw.map((value): MarketConnection => {
    const row = isRecord(value) ? value : {};
    const account = accountSnapshot(row.account);
    const positions = Array.isArray(row.positions) ? row.positions.map(positionSnapshot).filter((item): item is MarketPositionSnapshot => item !== null) : [];
    const pnlRecord = isRecord(row.pnl) ? row.pnl : {};
    return {
      id: readString(row.id),
      broker: readString(row.broker) ?? 'unknown',
      market: readString(row.market) ?? '',
      active: readBoolean(row.active),
      status: readString(row.status),
      account,
      positions,
      pnl: readNumber(firstDefined(pnlRecord.value, row.pnl)),
      pnl_available: readBoolean(firstDefined(pnlRecord.available, row.pnl_available)),
      error: readString(row.error),
      source: sourceFor(row, 'universal_gateway', receivedAt).source,
    };
  });
  return {
    ...provenance,
    mt5_required: readBoolean(payload.mt5_required),
    connected: readNumber(payload.connected),
    connections,
  };
}

function fallbackSource(source: MarketSource): string {
  return `${source.broker}_gateway`;
}

function sourceParams(source: MarketSource): Record<string, string> {
  return { broker: source.broker, market: source.market };
}

export function marketsForBroker(broker: MarketBroker): MarketKind[] {
  return MARKET_SOURCES.find((item) => item.broker === broker && item.enabled)?.markets.slice() ?? [];
}

export function normalizeMarketSource(broker: string, market: string): MarketSource | null {
  const normalizedBroker = broker.trim().toLowerCase() as MarketBroker;
  const option = MARKET_SOURCES.find((item) => item.broker === normalizedBroker);
  if (!option || !option.enabled) return null;
  const rawMarket = market.trim().toLowerCase();
  const normalizedMarket = (rawMarket === 'spot' || rawMarket === 'crypto' ? 'crypto-spot' : rawMarket === 'futures' || rawMarket === 'futuros' ? 'crypto-futures' : rawMarket) as MarketKind;
  return option.markets.includes(normalizedMarket) ? { broker: option.broker, market: normalizedMarket } : null;
}

export async function getCapabilities(options: MarketRequestOptions = {}): Promise<MarketCapabilities> {
  const result = await requestJson(MARKET_ENDPOINTS.capabilities, {}, options);
  const provenance = responseSource(result.payload, 'fastapi_gateway', result.receivedAt);
  const matrix = Array.isArray(result.payload.matrix) ? result.payload.matrix.flatMap((value): MarketCapabilityRow[] => {
    if (!isRecord(value)) return [];
    const broker = readString(value.broker);
    const market = readString(value.market);
    if (!broker || !market) return [];
    return [{
      broker: broker as MarketBroker,
      market: market as MarketKind,
      status: readString(value.status) ?? 'unverified',
      read_only: readBoolean(value.read_only) ?? false,
      capabilities: Array.isArray(value.capabilities) ? value.capabilities.map((item) => readString(item)).filter((item): item is string => item !== null) : [],
      execution: Array.isArray(value.execution) ? value.execution.map((item) => readString(item)).filter((item): item is string => item !== null) : [],
      withdrawals: readBoolean(value.withdrawals) ?? true,
      transfers: readBoolean(value.transfers) ?? true,
    }];
  }) : [];
  return { ...provenance, matrix };
}

export async function getOverview(options: MarketRequestOptions = {}): Promise<MarketOverview> {
  const result = await requestJson(MARKET_ENDPOINTS.overview, {}, options);
  return normalizeOverview(result.payload, result.receivedAt);
}

export async function getAssets(source: MarketSource, options: MarketRequestOptions = {}): Promise<MarketAssetResponse> {
  const expected = normalizeMarketSource(source.broker, source.market);
  if (!expected) throw new MarketApiError('Fonte não habilitada.', 'identity', MARKET_ENDPOINTS.assets);
  const result = await requestJson(MARKET_ENDPOINTS.assets, sourceParams(expected), options);
  assertPayloadIdentity(result.payload, expected);
  const provenance = responseSource(result.payload, fallbackSource(expected), result.receivedAt);
  const assets = responseRows(result.payload, ['assets', 'symbols', 'data'], MARKET_ENDPOINTS.assets)
    .map((row) => normalizeAsset(row, expected, provenance.source, result.receivedAt))
    .filter((row): row is MarketAsset => row !== null);
  return { ...provenance, ...expected, assets, errors: itemErrors(result.payload) };
}

export async function getQuotes(source: MarketSource, symbols: string[], options: MarketRequestOptions = {}): Promise<MarketQuoteResponse> {
  const expected = normalizeMarketSource(source.broker, source.market);
  if (!expected) throw new MarketApiError('Fonte não habilitada.', 'identity', MARKET_ENDPOINTS.quotes);
  const normalized = [...new Set(symbols.map((symbol) => symbol.trim().toUpperCase()).filter(Boolean))].slice(0, 24);
  if (!normalized.length) throw new MarketApiError('Informe ao menos um símbolo.', 'invalid', MARKET_ENDPOINTS.quotes);
  const result = await requestJson(MARKET_ENDPOINTS.quotes, { ...sourceParams(expected), symbols: normalized.join(',') }, options);
  assertPayloadIdentity(result.payload, expected);
  const provenance = responseSource(result.payload, fallbackSource(expected), result.receivedAt);
  const requested = new Set(normalized);
  const quotes = responseRows(result.payload, ['quotes', 'data', 'items'], MARKET_ENDPOINTS.quotes)
    .map((row) => normalizeQuote(row, { ...expected, symbol: rowSymbol(row) ?? '' }, provenance.source, result.receivedAt))
    .filter((row): row is MarketQuote => row !== null && requested.has(row.symbol));
  return { ...provenance, ...expected, quotes, errors: itemErrors(result.payload) };
}

function rowSymbol(row: unknown): string | null {
  if (!isRecord(row)) return null;
  return normalizeSymbol(firstDefined(row.symbol, row.ticker));
}

export async function getStats24h(identity: MarketIdentity, options: MarketRequestOptions = {}): Promise<MarketStatsResponse> {
  const expected = normalizeIdentity(identity, MARKET_ENDPOINTS.stats24h);
  const result = await requestJson(MARKET_ENDPOINTS.stats24h, { ...sourceParams(expected), symbol: expected.symbol }, options);
  assertPayloadIdentity(result.payload, expected);
  const provenance = responseSource(result.payload, fallbackSource(expected), result.receivedAt);
  return { ...provenance, ...expected, stats: normalizeStats(result.payload, expected, provenance.source, result.receivedAt) };
}

export async function getCandles(identity: MarketIdentity, timeframe = 'M5', limit = 300, options: MarketRequestOptions = {}): Promise<MarketCandleResponse> {
  const expected = normalizeIdentity(identity, MARKET_ENDPOINTS.candles);
  const safeTimeframe = timeframe.trim().toUpperCase() || 'M5';
  const safeLimit = Math.max(10, Math.min(2000, Math.floor(Number(limit) || 300)));
  const result = await requestJson(MARKET_ENDPOINTS.candles, { ...sourceParams(expected), symbol: expected.symbol, timeframe: safeTimeframe, limit: safeLimit }, options);
  assertPayloadIdentity(result.payload, expected);
  const provenance = responseSource(result.payload, fallbackSource(expected), result.receivedAt);
  const candles = responseRows(result.payload, ['candles', 'data', 'result', 'items'], MARKET_ENDPOINTS.candles)
    .map((row) => normalizeCandle(row, expected, provenance.source, result.receivedAt))
    .filter((row): row is MarketCandle => row !== null)
    .sort((a, b) => a.time - b.time)
    .filter((row, index, rows) => index === 0 || row.time !== rows[index - 1].time);
  return { ...provenance, ...expected, timeframe: safeTimeframe, candles };
}

export async function getDepth(identity: MarketIdentity, limit = 20, options: MarketRequestOptions = {}): Promise<MarketDepthResponse> {
  const expected = normalizeIdentity(identity, MARKET_ENDPOINTS.depth);
  const safeLimit = Math.max(1, Math.min(100, Math.floor(Number(limit) || 20)));
  const result = await requestJson(MARKET_ENDPOINTS.depth, { ...sourceParams(expected), symbol: expected.symbol, limit: safeLimit }, options);
  return normalizeDepth(result.payload, expected, fallbackSource(expected), result.receivedAt);
}

export async function getTrades(identity: MarketIdentity, limit = 20, options: MarketRequestOptions = {}): Promise<MarketTradesResponse> {
  const expected = normalizeIdentity(identity, MARKET_ENDPOINTS.trades);
  const safeLimit = Math.max(1, Math.min(100, Math.floor(Number(limit) || 20)));
  const result = await requestJson(MARKET_ENDPOINTS.trades, { ...sourceParams(expected), symbol: expected.symbol, limit: safeLimit }, options);
  assertPayloadIdentity(result.payload, expected);
  const provenance = responseSource(result.payload, fallbackSource(expected), result.receivedAt);
  const trades = responseRows(result.payload, ['trades', 'data', 'result', 'items'], MARKET_ENDPOINTS.trades)
    .map((row) => normalizeTrade(row, expected, provenance.source, result.receivedAt))
    .filter((row): row is PublicTrade => row !== null);
  return { ...provenance, ...expected, trades };
}

export async function getMt5Status(options: MarketRequestOptions = {}): Promise<Mt5Status> {
  const result = await requestJson(MARKET_ENDPOINTS.status, {}, options);
  const payload = result.payload;
  const provenance = responseSource(payload, 'mt5_gateway', result.receivedAt);
  const heartbeatRaw = isRecord(payload.ea_heartbeat) ? payload.ea_heartbeat : null;
  const heartbeat = heartbeatRaw ? {
    live: readBoolean(heartbeatRaw.live),
    age_sec: readNumber(heartbeatRaw.age_sec ?? heartbeatRaw.ageSec),
    symbol: readString(heartbeatRaw.symbol),
    autotrading: readBoolean(firstDefined(heartbeatRaw.autotrading, heartbeatRaw.autoTrading)),
    source: readString(heartbeatRaw.source),
  } : null;
  return {
    ...provenance,
    gateway: readString(payload.gateway),
    mt5_connected: readBoolean(firstDefined(payload.mt5_connected, payload.terminal_connected)),
    account: accountSnapshot(payload.account),
    positions: Array.isArray(payload.positions) ? payload.positions.map(positionSnapshot).filter((item): item is MarketPositionSnapshot => item !== null) : [],
    ea_heartbeat: heartbeat,
  };
}

function normalizeIdentity(identity: MarketIdentity, endpoint: string): MarketIdentity {
  const source = normalizeMarketSource(identity.broker, identity.market);
  const symbol = normalizeSymbol(identity.symbol);
  if (!source || !symbol) throw new MarketApiError('Identidade de mercado inválida.', 'identity', endpoint);
  return { ...source, symbol };
}

export const fetchUniversalOverview = getOverview;
export const fetchUniversalAssets = getAssets;
export const fetchUniversalQuotes = getQuotes;
export const fetchUniversalStats24h = getStats24h;
export const fetchUniversalCandles = getCandles;
export const fetchUniversalDepth = getDepth;
export const fetchUniversalTrades = getTrades;
export const fetchMt5Status = getMt5Status;

export const marketApi = {
  capabilities: getCapabilities,
  overview: getOverview,
  assets: getAssets,
  quotes: getQuotes,
  stats24h: getStats24h,
  candles: getCandles,
  depth: getDepth,
  trades: getTrades,
  status: getMt5Status,
};

export { buildUrl as buildMarketUrl, sourceFor as marketProvenance, normalizeCandle, normalizeDepth, normalizeQuote, normalizeTrade };
