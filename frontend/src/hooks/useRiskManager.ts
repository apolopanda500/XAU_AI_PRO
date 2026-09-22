// Hook de gerenciamento de risco para XAU AI PRO
// Risk management hook

import { useState, useCallback, useEffect, useRef } from 'react';
import { useAppStore } from './useAppStore';
import type { RiskMetrics, RiskConfig } from '../lib/riskCalculations';
import {
  calculateDailyDrawdown,
  shouldStopTrading,
  getRiskLevel,
  DRAWDOWN_THRESHOLDS,
  MARGIN_THRESHOLDS,
  DEFAULT_RISK_CONFIG,
} from '../lib/riskCalculations';

type RiskLevel = string;

export interface RiskState {
  metrics: RiskMetrics | null;
  config: RiskConfig;
  isAutoStopEnabled: boolean;
  lastUpdate: Date | null;
}

export function useRiskManager() {
  const [state, setState] = useState<RiskState>({
    metrics: null,
    config: { ...DEFAULT_RISK_CONFIG },
    isAutoStopEnabled: false,
    lastUpdate: null,
  });
  
  const positions = useAppStore((s) => s.positions);
  const account = useAppStore((s) => s.account);
  
  // Simula cálculo de métricas de risco baseado nas posições
  const calculateMetrics = useCallback((): RiskMetrics => {
    const totalVolume = positions.reduce((sum, p) => sum + (p.volume || 0), 0);
    const dailyPnl = positions.reduce((sum, p) => sum + (p.profit || 0), 0);
    const balance = account?.balance || 10000;
    
    return {
      dailyDrawdown: calculateDailyDrawdown(dailyPnl, balance),
      totalDrawdown: Math.min(15, dailyPnl / balance * 100), // Simulado
      openRisk: (totalVolume / 100) * 0.1, // Simulado
      marginUsed: Math.min(95, (totalVolume * 100) / (balance || 1) * 0.5), // Simulado
      maxDailyDrawdown: state.config.maxDailyDrawdown,
      maxTotalDrawdown: state.config.maxTotalDrawdown,
      maxRiskPerTrade: state.config.maxRiskPerTrade,
      marginAlertLevel: state.config.marginAlertLevel,
      openPositions: positions.length,
      totalVolume,
      dailyPnl,
      totalPnl: dailyPnl * 2, // Simulado
    };
  }, [positions, account, state.config]);
  
  // Atualizar métricas periodicamente
  useEffect(() => {
    const metrics = calculateMetrics();
    setState((prev) => ({
      ...prev,
      metrics,
      lastUpdate: new Date(),
    }));
  }, [calculateMetrics]);
  
  // Atualizar configurações
  const updateConfig = useCallback((updates: Partial<RiskConfig>) => {
    setState((prev) => ({
      ...prev,
      config: { ...prev.config, ...updates },
    }));
  }, []);
  
  // Toggle auto-stop
  const toggleAutoStop = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isAutoStopEnabled: !prev.isAutoStopEnabled,
    }));
  }, []);
  
  // Verificar se deve parar trading
  const stopCheck = useCallback((): { shouldStop: boolean; reason: string | null } => {
    if (!state.metrics) return { shouldStop: false, reason: null };
    return shouldStopTrading(state.metrics, state.config);
  }, [state.metrics, state.config]);
  
  // Obter nível de risco
  const getDrawdownLevel = useCallback((): RiskLevel => {
    if (!state.metrics) return 'Baixo';
    return getRiskLevel(state.metrics.dailyDrawdown, DRAWDOWN_THRESHOLDS);
  }, [state.metrics]);
  
  const getMarginLevel = useCallback((): RiskLevel => {
    if (!state.metrics) return 'Baixo';
    return getRiskLevel(state.metrics.marginUsed, MARGIN_THRESHOLDS);
  }, [state.metrics]);
  
  return {
    metrics: state.metrics,
    config: state.config,
    isAutoStopEnabled: state.isAutoStopEnabled,
    lastUpdate: state.lastUpdate,
    updateConfig,
    toggleAutoStop,
    stopCheck,
    getDrawdownLevel,
    getMarginLevel,
    refresh: () => setState((prev) => ({ ...prev, lastUpdate: new Date() })),
  };
}
