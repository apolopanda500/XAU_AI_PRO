// Modelos de IA para XAU AI PRO
// AI Models for XAU AI PRO

export interface AIModel {
  id: string;
  name: string;
  version: string;
  type: 'trend' | 'mean_reversion' | 'breakout' | 'multi' | 'scalp';
  description: string;
  confidence: number;        // 0-1
  parameters: ModelParameters;
  supportedSymbols: string[];
}

export interface ModelParameters {
  timeframe?: 'M1' | 'M5' | 'M15' | 'H1' | 'H4' | 'D1';
  riskPercent?: number;
  stopLossPips?: number;
  takeProfitPips?: number;
  maxPositions?: number;
  // Parâmetros específicos do modelo
  emaFast?: number;
  emaSlow?: number;
  rsiPeriod?: number;
  rsiOverbought?: number;
  rsiOversold?: number;
  atrPeriod?: number;
  atrMultiplier?: number;
  bbPeriod?: number;
  bbStdDev?: number;
}

export const AVAILABLE_MODELS: AIModel[] = [
  {
    id: 'xau-pro-v2',
    name: 'XAU Pro V2',
    version: '2.1.0',
    type: 'multi',
    description: 'Modelo completo com múltiplos indicadores',
    confidence: 0.78,
    parameters: {
      timeframe: 'M15',
      riskPercent: 1,
      stopLossPips: 50,
      takeProfitPips: 100,
      maxPositions: 5,
      emaFast: 20,
      emaSlow: 50,
      rsiPeriod: 14,
      atrPeriod: 14,
      atrMultiplier: 2,
    },
    supportedSymbols: ['XAUUSD', 'GBPUSD', 'EURUSD', 'USDJPY', 'BTCUSDT'],
  },
  {
    id: 'trend-follower',
    name: 'Trend Follower',
    version: '1.5.0',
    type: 'trend',
    description: 'Siga tendências com EMA e MACD',
    confidence: 0.72,
    parameters: {
      timeframe: 'H1',
      riskPercent: 1.5,
      stopLossPips: 75,
      takeProfitPips: 150,
      maxPositions: 3,
      emaFast: 20,
      emaSlow: 50,
      rsiPeriod: 14,
    },
    supportedSymbols: ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'BTCUSDT'],
  },
  {
    id: 'mean-reversion',
    name: 'Mean Reversion',
    version: '1.3.0',
    type: 'mean_reversion',
    description: 'Trade reversões à média com RSI e Bandas de Bollinger',
    confidence: 0.68,
    parameters: {
      timeframe: 'M5',
      riskPercent: 0.8,
      stopLossPips: 30,
      takeProfitPips: 45,
      maxPositions: 8,
      rsiPeriod: 14,
      rsiOverbought: 70,
      rsiOversold: 30,
      bbPeriod: 20,
      bbStdDev: 2,
    },
    supportedSymbols: ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD'],
  },
  {
    id: 'breakout',
    name: 'Breakout Trader',
    version: '1.2.0',
    type: 'breakout',
    description: 'Identifica e opera rompimentos com ATR',
    confidence: 0.75,
    parameters: {
      timeframe: 'M15',
      riskPercent: 1.2,
      stopLossPips: 40,
      takeProfitPips: 80,
      maxPositions: 4,
      atrPeriod: 14,
      atrMultiplier: 1.5,
    },
    supportedSymbols: ['XAUUSD', 'GBPUSD', 'EURUSD', 'BTCUSDT', 'ETHUSDT'],
  },
  {
    id: 'scalp',
    name: 'Scalp Pro',
    version: '1.0.0',
    type: 'scalp',
    description: 'Operações rápidas para ganho small e frequente',
    confidence: 0.70,
    parameters: {
      timeframe: 'M1',
      riskPercent: 0.5,
      stopLossPips: 15,
      takeProfitPips: 20,
      maxPositions: 10,
    },
    supportedSymbols: ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD'],
  },
];

export function getModelById(id: string): AIModel | undefined {
  return AVAILABLE_MODELS.find(m => m.id === id);
}

export function getModelsByType(type: AIModel['type']): AIModel[] {
  return AVAILABLE_MODELS.filter(m => m.type === type);
}

export function getRecommendedModel(symbol: string): AIModel | undefined {
  // Retorna o modelo multi como padrão para maior confiabilidade
  return AVAILABLE_MODELS.find(m => m.id === 'xau-pro-v2');
}