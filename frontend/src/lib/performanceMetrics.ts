// Métricas de performance para XAU AI PRO
// Performance metrics library

export interface TradeResult {
  id: string;
  ticket: number;
  symbol: string;
  side: 'BUY' | 'SELL';
  volume: number;
  entryPrice: number;
  exitPrice: number;
  pnl: number;
  pnlPercent: number;
  commission: number;
  swap: number;
  holdingTimeMinutes: number;
  timestamp: string;
  magic?: number;
  comment?: string;
}

export interface SymbolMetrics {
  totalTrades: number;
  winRate: number;
  totalPnl: number;
  averagePnl: number;
  profitFactor: number;
}

export function calculateWinRate(trades: TradeResult[]): number {
  if (trades.length === 0) return 0;
  const wins = trades.filter(t => t.pnl > 0).length;
  return (wins / trades.length) * 100;
}

export function calculateProfitFactor(trades: TradeResult[]): number {
  const grossProfit = trades.filter(t => t.pnl > 0).reduce((sum, t) => sum + t.pnl, 0);
  const grossLoss = Math.abs(trades.filter(t => t.pnl < 0).reduce((sum, t) => sum + t.pnl, 0));
  if (grossLoss === 0) return grossProfit > 0 ? Infinity : 0;
  return grossProfit / grossLoss;
}

export function calculateExpectancy(trades: TradeResult[]): number {
  if (trades.length === 0) return 0;
  const winRate = calculateWinRate(trades) / 100;
  const avgWin = trades.filter(t => t.pnl > 0).reduce((sum, t) => sum + t.pnl, 0) / 
                  Math.max(1, trades.filter(t => t.pnl > 0).length);
  const avgLoss = Math.abs(trades.filter(t => t.pnl < 0).reduce((sum, t) => sum + t.pnl, 0) /
                  Math.max(1, trades.filter(t => t.pnl < 0).length));
  return (winRate * avgWin) - ((1 - winRate) * avgLoss);
}

export function calculatePerformanceBySymbol(trades: TradeResult[]): Record<string, SymbolMetrics> {
  const bySymbol: Record<string, TradeResult[]> = {};
  
  trades.forEach(t => {
    if (!bySymbol[t.symbol]) bySymbol[t.symbol] = [];
    bySymbol[t.symbol].push(t);
  });
  
  const result: Record<string, SymbolMetrics> = {};
  
  Object.entries(bySymbol).forEach(([symbol, symbolTrades]) => {
    result[symbol] = {
      totalTrades: symbolTrades.length,
      winRate: calculateWinRate(symbolTrades),
      totalPnl: symbolTrades.reduce((sum, t) => sum + t.pnl, 0),
      averagePnl: symbolTrades.length > 0 ? symbolTrades.reduce((sum, t) => sum + t.pnl, 0) / symbolTrades.length : 0,
      profitFactor: calculateProfitFactor(symbolTrades),
    };
  });
  
  return result;
}
