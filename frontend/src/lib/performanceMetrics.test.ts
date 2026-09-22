// Testes para performanceMetrics.ts
import { describe, it, expect } from 'vitest';
import { calculateWinRate, calculateProfitFactor, calculatePerformanceBySymbol, type TradeResult } from '../lib/performanceMetrics';

describe('performanceMetrics', () => {
  const mockTrades: TradeResult[] = [
    { id: '1', ticket: 1, symbol: 'XAUUSD', side: 'BUY', volume: 0.1, entryPrice: 100, exitPrice: 105, pnl: 50, pnlPercent: 0.5, commission: 1, swap: 0, holdingTimeMinutes: 60, timestamp: '2026-01-01T00:00:00Z' },
    { id: '2', ticket: 2, symbol: 'XAUUSD', side: 'SELL', volume: 0.1, entryPrice: 105, exitPrice: 100, pnl: 50, pnlPercent: 0.5, commission: 1, swap: 0, holdingTimeMinutes: 60, timestamp: '2026-01-02T00:00:00Z' },
    { id: '3', ticket: 3, symbol: 'BTCUSDT', side: 'BUY', volume: 0.01, entryPrice: 50000, exitPrice: 49000, pnl: -100, pnlPercent: -0.2, commission: 2, swap: 0, holdingTimeMinutes: 120, timestamp: '2026-01-03T00:00:00Z' },
    { id: '4', ticket: 4, symbol: 'BTCUSDT', side: 'BUY', volume: 0.01, entryPrice: 49000, exitPrice: 51000, pnl: 200, pnlPercent: 0.4, commission: 2, swap: 0, holdingTimeMinutes: 60, timestamp: '2026-01-04T00:00:00Z' },
  ];

  describe('calculateWinRate', () => {
    it('should calculate win rate correctly', () => {
      const winRate = calculateWinRate(mockTrades);
      expect(winRate).toBe(75); // 3 wins out of 4 trades
    });

    it('should return 0 for empty array', () => {
      expect(calculateWinRate([])).toBe(0);
    });
  });

  describe('calculateProfitFactor', () => {
    it('should calculate profit factor correctly', () => {
      // Gross profit: 50 + 50 + 200 = 300
      // Gross loss: 100
      // PF = 300 / 100 = 3
      const pf = calculateProfitFactor(mockTrades);
      expect(pf).toBeCloseTo(3, 2);
    });

    it('should return 0 when no losses', () => {
      const winningTrades = mockTrades.filter(t => t.pnl > 0);
      const pf = calculateProfitFactor(winningTrades);
      expect(pf).toBe(Infinity);
    });
  });

  describe('calculatePerformanceBySymbol', () => {
    it('should group performance by symbol', () => {
      const bySymbol = calculatePerformanceBySymbol(mockTrades);
      expect(bySymbol).toHaveProperty('XAUUSD');
      expect(bySymbol).toHaveProperty('BTCUSDT');
      expect(bySymbol.XAUUSD.totalTrades).toBe(2);
      expect(bySymbol.BTCUSDT.totalTrades).toBe(2);
    });
  });
});
