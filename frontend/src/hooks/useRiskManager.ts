// Hook de gerenciamento de risco para XAU AI PRO.
// Fonte de verdade: posições + conta reais do store (vindas do gateway MT5).
// Sem simulação: métricas derivadas de balance/equity/margin do MT5 e
// limites sincronizados com backend/risk_gate.py (0.10 / 2% / 5% / 5).

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
  
  // Métricas derivadas de dados REAIS do gateway (sem valores simulados).
  // balance/equity/margin vêm de /api/status; positions de /api/positions.
  const calculateMetrics = useCallback((): RiskMetrics => {
    const totalVolume = positions.reduce((sum, p) => sum + (p.volume || 0), 0);
    const floating = positions.reduce((sum, p) => sum + (p.profit || 0), 0);
    const balance = account?.balance || 0;
    const equity = account?.equity ?? balance;
    const margin = account?.margin || 0;
    // Drawdown diário real: distância do equity ao balance (sem pico intradiário
    // no store, usa o pior caso observável agora).
    const dailyDrawdown = balance > 0 ? Math.max(0, (balance - equity) / balance) * 100 : 0;
    const marginUsed = equity > 0 ? (margin / equity) * 100 : 0;
    // Exposição real: volume aberto vs teto do risk_gate (5 posições de 0.10).
    const openRisk = Math.min(100, (totalVolume / 0.5) * 100);
    return {
      dailyDrawdown,
      totalDrawdown: dailyDrawdown,
      openRisk,
      marginUsed: Math.min(100, marginUsed),
      maxDailyDrawdown: state.config.maxDailyDrawdown,
      maxTotalDrawdown: state.config.maxTotalDrawdown,
      maxRiskPerTrade: state.config.maxRiskPerTrade,
      marginAlertLevel: state.config.marginAlertLevel,
      openPositions: positions.length,
      totalVolume,
      dailyPnl: floating,
      totalPnl: floating,
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
