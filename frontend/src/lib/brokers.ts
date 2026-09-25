/** Contrato comum para contas, ativos, histórico e execução multi-corretora. */

export type BrokerId = 'mt5' | 'mexc' | 'binance' | 'bybit' | 'okx';
export type MarketType = 'forex' | 'crypto-spot' | 'crypto-futures' | 'indices' | 'metals' | 'stocks' | 'commodities' | 'bonds' | 'options' | 'other';
export type AccountMode = 'DEMO' | 'REAL' | 'UNKNOWN';
export type OrderSide = 'BUY' | 'SELL';
export type OrderStatus = 'NEW' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELED' | 'REJECTED' | 'UNKNOWN';

export interface BrokerCapabilities {
  broker: BrokerId;
  label: string;
  markets: MarketType[];
  supportsDemo: boolean;
  supportsReal: boolean;
  supportsPositions: boolean;
  supportsProtection: boolean;
  supportsTrading: boolean;
  supportsWithdraw: false;
}

export interface TradingAccount {
  id: string;
  broker: BrokerId;
  label: string;
  login?: string;
  server?: string;
  currency: string;
  mode: AccountMode;
  connected: boolean;
  tradeAllowed: boolean;
  balance?: number;
  equity?: number;
  freeMargin?: number;
  updatedAt?: string;
}

export interface UniversalDeal {
  id: string;
  broker: BrokerId;
  accountId: string;
  market: MarketType;
  symbol: string;
  side: OrderSide;
  entry: 'IN' | 'OUT' | 'TRADE' | 'FEE' | 'TRANSFER' | 'UNKNOWN';
  status: OrderStatus;
  quantity: number;
  price: number;
  grossPnl: number;
  commission: number;
  swap: number;
  fee: number;
  realizedPnl: number;
  orderId?: string;
  positionId?: string;
  executedAt: string;
  source: string;
}

export const BROKER_CAPABILITIES: readonly BrokerCapabilities[] = [
  { broker: 'mt5', label: 'MetaTrader 5', markets: ['forex', 'metals', 'indices', 'stocks', 'commodities', 'bonds', 'crypto-spot', 'crypto-futures', 'other'], supportsDemo: true, supportsReal: false, supportsPositions: true, supportsProtection: false, supportsTrading: false, supportsWithdraw: false },
  { broker: 'mexc', label: 'MEXC', markets: ['crypto-spot', 'crypto-futures'], supportsDemo: false, supportsReal: false, supportsPositions: false, supportsProtection: false, supportsTrading: false, supportsWithdraw: false },
  { broker: 'binance', label: 'Binance', markets: ['crypto-spot', 'crypto-futures'], supportsDemo: false, supportsReal: false, supportsPositions: true, supportsProtection: false, supportsTrading: false, supportsWithdraw: false },
  { broker: 'bybit', label: 'Bybit', markets: ['crypto-spot', 'crypto-futures'], supportsDemo: false, supportsReal: false, supportsPositions: false, supportsProtection: false, supportsTrading: false, supportsWithdraw: false },
  { broker: 'okx', label: 'OKX', markets: ['crypto-spot', 'crypto-futures'], supportsDemo: false, supportsReal: false, supportsPositions: false, supportsProtection: false, supportsTrading: false, supportsWithdraw: false },
];

export function marketLabel(market: MarketType): string {
  return ({ 'crypto-spot': 'Cripto Spot', 'crypto-futures': 'Cripto Futures', forex: 'Forex', metals: 'Metais', indices: 'Índices', stocks: 'Ações', commodities: 'Commodities', bonds: 'Bonds', options: 'Opções', other: 'Outro' } as Record<MarketType, string>)[market];
}
