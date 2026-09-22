// Comunicação com IA para XAU AI PRO
// AI Communication

import { useCallback } from 'react';
import { useAppStore } from './useAppStore';
import { AVAILABLE_MODELS, type AIModel } from '../lib/aiModels';

export interface AISignal {
  id: string;
  symbol: string;
  direction: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  model: string;
  modelVersion: string;
  reason: string;
  timestamp: Date;
  indicators: any;
  risk: {
    suggestedSL: number;
    suggestedTP: number;
    suggestedVolume: number;
    riskPercent: number;
  };
}

export interface AIResponse {
  success: boolean;
  signal?: AISignal;
  error?: string;
  latencyMs: number;
  modelsUsed: string[];
}

export function useAICommunication() {
  const settings = useAppStore((s) => s.settings);
  const aiStatus = useAppStore((s) => s.aiStatus);
  const setAiStatus = useAppStore((s) => s.setAiStatus);

  const getModel = (): AIModel | undefined => {
    return AVAILABLE_MODELS.find(m => m.id === settings.aiModel) || 
           AVAILABLE_MODELS.find(m => m.id === 'xau-pro-v2');
  };

  const generateSignal = useCallback(async (
    symbol: string,
    price: number,
    indicators?: any
  ): Promise<AIResponse> => {
    const startTime = Date.now();
    const model = getModel();

    if (!model) {
      return { success: false, error: 'Modelo não encontrado', latencyMs: 0, modelsUsed: [] };
    }

    setAiStatus('Analisando...');

    try {
      const analysis = simulateAIAnalysis(symbol, price, indicators, model);

      const signal: AISignal = {
        id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
        symbol,
        direction: analysis.direction,
        confidence: analysis.confidence,
        model: model.id,
        modelVersion: model.version,
        reason: analysis.reason,
        timestamp: new Date(),
        indicators: { price, change: analysis.priceChange, volume: indicators?.volume, rsi: indicators?.rsi, macd: indicators?.macd },
        risk: { suggestedSL: analysis.suggestedSL, suggestedTP: analysis.suggestedTP, suggestedVolume: analysis.suggestedVolume, riskPercent: model.parameters.riskPercent || 1 },
      };

      setAiStatus(`Sinal: ${signal.direction} (${signal.confidence}%)`);
      
      return { success: true, signal, latencyMs: Date.now() - startTime, modelsUsed: [model.id] };
    } catch (e) {
      setAiStatus('Erro na IA');
      return { success: false, error: e instanceof Error ? e.message : 'Erro', latencyMs: Date.now() - startTime, modelsUsed: [] };
    }
  }, [settings.aiModel, setAiStatus]);

  const getAvailableModels = (): AIModel[] => AVAILABLE_MODELS;
  
  const changeModel = (modelId: string) => {
    const model = AVAILABLE_MODELS.find(m => m.id === modelId);
    if (model) {
      settings.aiModel = modelId;
      setAiStatus(`Modelo: ${model.name}`);
    }
  };

  return { aiStatus, getModel, generateSignal, getAvailableModels, changeModel, isEnabled: settings.aiEnabled, interval: settings.aiInterval };
}

function simulateAIAnalysis(symbol: string, price: number, indicators: any, model: AIModel) {
  const rsi = indicators?.rsi || 50;
  const macd = indicators?.macd || 0;
  const volume = indicators?.volume || 1;
  
  let direction: 'BUY' | 'SELL' | 'HOLD' = 'HOLD';
  let confidence = 50;
  let reason = '';

  switch (model.type) {
    case 'trend':
      if (macd > 0 && rsi < 70) { direction = 'BUY'; confidence = 70 + (macd * 5); reason = `MACD positivo indica compra`; }
      else if (macd < 0 && rsi > 30) { direction = 'SELL'; confidence = 70 + (Math.abs(macd) * 5); reason = `MACD negativo indica venda`; }
      else { direction = 'HOLD'; confidence = 60; reason = 'Sem tendência clara'; }
      break;
    case 'mean_reversion':
      if (rsi < 30) { direction = 'BUY'; confidence = 75; reason = `RSI ${rsi.toFixed(1)} - oversold`; }
      else if (rsi > 70) { direction = 'SELL'; confidence = 75; reason = `RSI ${rsi.toFixed(1)} - overbought`; }
      else { direction = 'HOLD'; confidence = 65; reason = 'RSI neutro'; }
      break;
    case 'breakout':
      if (volume > 1.5 && Math.abs(macd) > 0.5) { direction = macd > 0 ? 'BUY' : 'SELL'; confidence = 80; reason = `Breakout: vol ${volume.toFixed(1)}`; }
      else { direction = 'HOLD'; confidence = 55; reason = 'Sem breakout'; }
      break;
    case 'multi':
      const buys = (macd > 0 ? 1 : 0) + (rsi < 30 ? 1 : 0);
      const sells = (macd < 0 ? 1 : 0) + (rsi > 70 ? 1 : 0);
      if (buys > sells) { direction = 'BUY'; confidence = 60 + buys * 5; reason = `${buys}B vs ${sells}S`; }
      else if (sells > buys) { direction = 'SELL'; confidence = 60 + sells * 5; reason = `${sells}S vs ${buys}B`; }
      else { direction = 'HOLD'; confidence = 60; reason = 'Sinais mistos'; }
      break;
    default:
      direction = 'HOLD'; confidence = 50; reason = 'Sem análise';
  }

  return { direction, confidence: Math.min(confidence, 95), reason, priceChange: (Math.random() - 0.45) * 0.5, suggestedSL: price * 0.99, suggestedTP: price * 1.02, suggestedVolume: 0.1 };
}
