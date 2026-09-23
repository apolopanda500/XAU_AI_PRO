// Cálculos de risco para XAU AI PRO
// Risk calculations library

export interface RiskMetrics {
  // Risco atual
  dailyDrawdown: number;        // Drawdown diário %
  totalDrawdown: number;        // Drawdown total %
  openRisk: number;            // Risco em posições abertas %
  marginUsed: number;          // Margem utilizada %
  
  // Limites configurados
  maxDailyDrawdown: number;    // Limite drawdown diário %
  maxTotalDrawdown: number;    // Limite drawdown total %
  maxRiskPerTrade: number;     // Risco máximo por trade %
  marginAlertLevel: number;    // Nível de alerta de margem %
  
  // Posições
  openPositions: number;       // Quantidade de posições abertas
  totalVolume: number;         // Volume total em posições
  
  // PnL
  dailyPnl: number;            // PnL do dia
  totalPnl: number;            // PnL total
}

export interface RiskConfig {
  maxDailyDrawdown: number;     // % máximo por dia
  maxTotalDrawdown: number;     // % máximo total
  maxRiskPerTrade: number;      // % risco por trade
  marginAlertLevel: number;     // % alerta de margem
  autoStopOnDrawdown: boolean;  // Parar automaticamente no drawdown
}

export const DEFAULT_RISK_CONFIG: RiskConfig = {
  maxDailyDrawdown: 2,          // 2% — igual ao risk_gate backend
  maxTotalDrawdown: 5,          // 5% — igual à exposição máxima backend
  maxRiskPerTrade: 1,           // 1% risco por trade
  marginAlertLevel: 80,         // Alertar quando margem > 80%
  autoStopOnDrawdown: false,    // Não parar automaticamente
};

export function calculateDailyDrawdown(dailyPnl: number, balance: number): number {
  if (!balance || balance <= 0) return 0;
  return Math.abs(dailyPnl / balance) * 100;
}

export function calculatePositionSize(
  accountBalance: number,
  riskPercent: number,
  entryPrice: number,
  stopLossPrice: number
): number {
  const riskAmount = accountBalance * (riskPercent / 100);
  const riskPerUnit = Math.abs(entryPrice - stopLossPrice);
  if (riskPerUnit <= 0) return 0;
  return riskAmount / riskPerUnit;
}

export function calculateRiskRewardRatio(
  entryPrice: number,
  stopLossPrice: number,
  takeProfitPrice: number
): number {
  const risk = Math.abs(entryPrice - stopLossPrice);
  const reward = Math.abs(takeProfitPrice - entryPrice);
  if (risk <= 0) return 0;
  return reward / risk;
}

export function shouldStopTrading(
  metrics: RiskMetrics,
  config: RiskConfig
): { shouldStop: boolean; reason: string | null } {
  // Verificar drawdown diário
  if (metrics.dailyDrawdown >= config.maxDailyDrawdown) {
    return {
      shouldStop: true,
      reason: `Drawdown diário (${metrics.dailyDrawdown.toFixed(2)}%) atingiu o limite (${config.maxDailyDrawdown}%)`
    };
  }
  
  // Verificar drawdown total
  if (metrics.totalDrawdown >= config.maxTotalDrawdown) {
    return {
      shouldStop: true,
      reason: `Drawdown total (${metrics.totalDrawdown.toFixed(2)}%) atingiu o limite (${config.maxTotalDrawdown}%)`
    };
  }
  
  // Verificar margem
  if (metrics.marginUsed >= config.marginAlertLevel) {
    return {
      shouldStop: true,
      reason: `Margem utilizada (${metrics.marginUsed.toFixed(2)}%) acima do nível de alerta (${config.marginAlertLevel}%)`
    };
  }
  
  return { shouldStop: false, reason: null };
}

export function getRiskLevel(value: number, thresholds: [number, string][]): string {
  for (const [threshold, label] of thresholds) {
    if (value >= threshold) return label;
  }
  return thresholds[thresholds.length - 1]?.[1] ?? 'Baixo';
}

// Thresholds comuns para indicadores de risco
export const DRAWDOWN_THRESHOLDS: [number, string][] = [
  [1, 'Baixo'],
  [3, 'Moderado'],
  [5, 'Alto'],
  [10, 'Crítico'],
];

export const MARGIN_THRESHOLDS: [number, string][] = [
  [30, 'Baixo'],
  [50, 'Moderado'],
  [70, 'Alto'],
  [80, 'Crítico'],
];
