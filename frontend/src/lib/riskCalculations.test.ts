// Testes para riskCalculations.ts
import { describe, it, expect } from 'vitest';
import { calculateDailyDrawdown, calculatePositionSize, calculateRiskRewardRatio } from '../lib/riskCalculations';

describe('riskCalculations', () => {
  describe('calculateDailyDrawdown', () => {
    it('should calculate drawdown percentage correctly', () => {
      expect(calculateDailyDrawdown(-100, 10000)).toBeCloseTo(1.0, 2);
      expect(calculateDailyDrawdown(-500, 10000)).toBeCloseTo(5.0, 2);
      expect(calculateDailyDrawdown(100, 10000)).toBeCloseTo(1.0, 2);
    });

    it('should return 0 when balance is 0 or invalid', () => {
      expect(calculateDailyDrawdown(-100, 0)).toBe(0);
      expect(calculateDailyDrawdown(-100, null as any)).toBe(0);
      expect(calculateDailyDrawdown(-100, undefined as any)).toBe(0);
    });
  });

  describe('calculatePositionSize', () => {
    it('should calculate correct position size based on risk', () => {
      // $10,000 account, 1% risk, entry $100, stop $95
      // Risk amount: $100, Risk per unit: $5, Position: 20 units
      const size = calculatePositionSize(10000, 1, 100, 95);
      expect(size).toBeCloseTo(20, 2);
    });

    it('should return 0 when risk per unit is 0', () => {
      expect(calculatePositionSize(10000, 1, 100, 100)).toBe(0);
    });
  });

  describe('calculateRiskRewardRatio', () => {
    it('should calculate R:R correctly', () => {
      // Entry 100, SL 95, TP 110
      // Risk: 5, Reward: 10, R:R = 2
      const rr = calculateRiskRewardRatio(100, 95, 110);
      expect(rr).toBe(2);
    });

    it('should return 0 when risk is 0', () => {
      expect(calculateRiskRewardRatio(100, 100, 110)).toBe(0);
    });
  });
});
