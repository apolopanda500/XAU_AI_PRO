// Painel de IA para XAU AI PRO
// AI Panel - universal: opera em todos os simbolos suportados

import { useState, useCallback, useEffect, useMemo } from 'react';
import { useAICommunication, type AISignal } from '../../hooks/useAICommunication';
import { useAppStore } from '../../hooks/useAppStore';
import { fmtNum, fmtPct } from '../../lib/format';
import { HelpTooltip } from '../../components/HelpTooltip';
import { apiBase } from '../../lib/api';
import { rsi as calcRsi, macd as calcMacd, type Candle } from '../../lib/technical';

const API = `${apiBase()}`;
const TF_BY_MODEL: Record<string, string> = { M1: 'M1', M5: 'M5', M15: 'M15', H1: 'H1', H4: 'H4', D1: 'D1' };

type TrainedArtifact = {
  artifact: string;
  status: string;
  training_verified: boolean;
  training_metadata_status: string;
  trained_symbol: string | null;
  trained_timeframe: string | null;
  train_date: string | null;
  algorithm: string | null;
  model_version: string | null;
  dataset_version: string | null;
  feature_count: number | null;
};

export default function AIPanel() {
  const quotes = useAppStore((s) => s.quotes);
  const selectedSymbol = useAppStore((s) => s.selectedSymbol);
  const setAiStatus = useAppStore((s) => s.setAiStatus);

  const { aiStatus, getModel, generateSignal, getAvailableModels, changeModel, isEnabled, interval } = useAICommunication();

  const [currentSignal, setCurrentSignal] = useState<AISignal | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [recentSignals, setRecentSignals] = useState<AISignal[]>([]);
  const [indicatorStatus, setIndicatorStatus] = useState('Aguardando candles do MT5...');
  const [trainedModels, setTrainedModels] = useState<TrainedArtifact[]>([]);
  const [catalogStatus, setCatalogStatus] = useState('Carregando catálogo local...');

  useEffect(() => {
    const controller = new AbortController();
    const loadCatalog = async () => {
      try {
        const response = await fetch(`${API}/api/ai/models`, { signal: controller.signal });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json() as { models?: TrainedArtifact[] };
        if (!Array.isArray(data.models)) throw new Error('Resposta inválida');
        setTrainedModels(data.models);
        setCatalogStatus(data.models.length ? '' : 'Nenhum artefato de modelo instalado.');
      } catch (error) {
        if (!controller.signal.aborted) setCatalogStatus(`Catálogo indisponível: ${error instanceof Error ? error.message : 'erro desconhecido'}`);
      }
    };
    void loadCatalog();
    return () => controller.abort();
  }, []);

  const currentQuote = useMemo(() => quotes.find(q => q.symbol === selectedSymbol), [quotes, selectedSymbol]);
  const activeModel = getModel();
  const [selectedModel, setSelectedModel] = useState(activeModel?.id || 'xau-pro-v2');

  // Indicadores REAIS: candles do MT5 -> RSI/MACD locais. Sem valores aleatórios.
  const loadIndicators = useCallback(async (symbol: string, timeframe: string) => {
    try {
      const url = `${API}/api/mt5/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&count=200`;
      const r = await fetch(url, { signal: AbortSignal.timeout(8000) });
      const d = (await r.json()) as { candles?: Candle[]; error?: string };
      if (!r.ok || !d.candles?.length) {
        setIndicatorStatus(`Sem candles: ${d.error ?? 'MT5 indisponível'}`);
        return null;
      }
      const rsiValue = calcRsi(d.candles);
      const macdValue = calcMacd(d.candles);
      const lastVolume = 1;
      setIndicatorStatus(`${d.candles.length} candles ${timeframe} · RSI ${rsiValue?.toFixed(1) ?? '--'} · MACD ${macdValue?.macd.toFixed(3) ?? '--'}`);
      return { rsi: rsiValue ?? 50, macd: macdValue?.macd ?? 0, volume: lastVolume };
    } catch (e) {
      setIndicatorStatus(`Gateway indisponível: ${e instanceof Error ? e.message : 'erro'}`);
      return null;
    }
  }, []);

  const handleGenerateSignal = useCallback(async () => {
    if (!currentQuote || !isEnabled || !activeModel) return;
    setIsAnalyzing(true);
    const indicators = await loadIndicators(currentQuote.symbol, TF_BY_MODEL[activeModel.parameters.timeframe ?? 'M15'] ?? 'M15');
    if (!indicators) {
      setIsAnalyzing(false);
      setAiStatus('IA: candles indisponíveis');
      return;
    }
    const response = await generateSignal(currentQuote.symbol, currentQuote.price, indicators);
    setIsAnalyzing(false);
    if (response.success && response.signal) {
      setCurrentSignal(response.signal);
      setRecentSignals(prev => [response.signal!, ...prev.slice(0, 9)]);
      setAiStatus(`Sinal: ${response.signal.direction} (${response.signal.confidence}%)`);
    }
  }, [currentQuote, isEnabled, activeModel, generateSignal, setAiStatus, loadIndicators]);

  useEffect(() => {
    if (!isEnabled || !currentQuote) return;
    const id = window.setInterval(handleGenerateSignal, interval * 1000);
    return () => clearInterval(id);
  }, [isEnabled, currentQuote, interval, handleGenerateSignal]);

  const handleModelChange = (modelId: string) => {
    changeModel(modelId);
    setSelectedModel(modelId);
    handleGenerateSignal();
  };

  const model = activeModel;
  const availableModels = getAvailableModels();
  const signalClass = currentSignal?.direction === 'BUY' ? 'pos' : currentSignal?.direction === 'SELL' ? 'neg' : '';

  const catalog = (
    <section className="ai-info-section" aria-label="Modelos treinados instalados">
      <h4>Artefatos de modelos instalados</h4>
      <p className="muted">Inventário local somente leitura. Metadados declarados não comprovam integridade do arquivo, desempenho nem vínculo com operações.</p>
      {catalogStatus && <p className="muted">{catalogStatus}</p>}
      {trainedModels.map(item => (
        <div className="ai-model-card" key={item.artifact}>
          <div className="ai-model-info">
            <strong>{item.artifact}</strong>
            <span>Treinado para: {item.trained_symbol ?? 'não informado'} · Timeframe: {item.trained_timeframe ?? 'não informado'}</span>
            <span>Treino: {item.train_date ?? 'não informado'} · Algoritmo: {item.algorithm ?? 'não informado'}</span>
            <span>Versão declarada: {item.model_version ?? 'não informada'} · Dataset: {item.dataset_version ?? 'não informado'} · Features: {item.feature_count ?? 'não informado'}</span>
            <span>Estado do arquivo: {item.status} (idade do arquivo; não é validação do treino) · Metadados: {item.training_metadata_status === 'present' ? 'presentes (não verificados)' : item.training_metadata_status === 'mismatch' ? 'divergentes do nome do arquivo' : item.training_metadata_status === 'invalid' ? 'inválidos' : 'ausentes'}</span>
          </div>
        </div>
      ))}
    </section>
  );

  if (!isEnabled) {
    return (
      <div className="ai-panel disabled">
        <div className="ai-header">
          <h3>Inteligencia Artificial</h3>
          <span className="muted">Desativado</span>
        </div>
        <div className="ai-disabled">
          <HelpTooltip text="Ative a IA nas configuracoes">
            <span>IA desativada.</span>
          </HelpTooltip>
        </div>
        {catalog}
      </div>
    );
  }

    return (
    <div className="ai-panel">
      <div className="ai-header">
        <h3>Inteligencia Artificial</h3>
        <span className="muted">{aiStatus}</span>
      </div>
      <p className="muted">Os perfis abaixo analisam indicadores localmente; não são os artefatos treinados listados no catálogo.</p>
      <div className="hint" style={{ marginBottom: 8 }}>{indicatorStatus}</div>
      <div className="ai-model-card">
        <div className="ai-model-info">
          <div className="ai-model-name">
            {model?.name || 'Sem modelo'}
            <span className="ai-model-version">v{model?.version}</span>
          </div>
          <div className="ai-model-type">
            <span className="chip">{model?.type || 'unknown'}</span>
          </div>
        </div>
        <div className="ai-model-selector">
          <label>Perfil de indicadores:</label>
          <select value={selectedModel} onChange={(e) => handleModelChange(e.target.value)}>
            {availableModels.map(m => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.type})
              </option>
            ))}
          </select>
        </div>
      </div>
      {catalog}

      {currentSignal && (
        <div className={`ai-signal-card ${signalClass}`}>
          <div className="ai-signal-header">
            <span className="ai-symbol">{currentSignal.symbol}</span>
            <span className={`ai-direction ${signalClass}`}>
              {currentSignal.direction === 'BUY' ? 'COMPRA' : currentSignal.direction === 'SELL' ? 'VENDA' : 'AGUARDAR'}
            </span>
            <span className={`ai-confidence ${signalClass}`}>{fmtPct(currentSignal.confidence)}</span>
          </div>
          <div className="ai-signal-reason"><strong>Razao:</strong> {currentSignal.reason}</div>
          <div className="ai-signal-details">
            <div className="detail-item"><span className="detail-label">Preco</span><span className="detail-value mono">{fmtNum(currentSignal.indicators.price, 2)}</span></div>
            {currentSignal.indicators.rsi != null && (
              <div className="detail-item"><span className="detail-label">RSI</span><span className="detail-value mono">{fmtNum(currentSignal.indicators.rsi, 1)}</span></div>
            )}
            {currentSignal.indicators.macd != null && (
              <div className="detail-item"><span className="detail-label">MACD</span><span className="detail-value mono">{fmtNum(currentSignal.indicators.macd, 3)}</span></div>
            )}
          </div>
          <div className="ai-risk-section">
            <h4>Sugestencias de Risco</h4>
            <div className="ai-risk-grid">
              <div className="risk-item"><span className="risk-label">Stop Loss</span><span className="risk-value mono">{fmtNum(currentSignal.risk.suggestedSL, 2)}</span></div>
              <div className="risk-item"><span className="risk-label">Take Profit</span><span className="risk-value mono">{fmtNum(currentSignal.risk.suggestedTP, 2)}</span></div>
              <div className="risk-item"><span className="risk-label">Volume</span><span className="risk-value mono">{fmtNum(currentSignal.risk.suggestedVolume, 2)}</span></div>
              <div className="risk-item"><span className="risk-label">Risco</span><span className="risk-value">{currentSignal.risk.riskPercent}%</span></div>
            </div>
          </div>
        </div>
      )}

      <div className="ai-actions">
        <HelpTooltip text="Gerar novo sinal">
          <button className="btn primary" onClick={handleGenerateSignal} disabled={isAnalyzing || !currentQuote}>
            {isAnalyzing ? 'Analisando...' : 'Gerar Sinal'}
          </button>
        </HelpTooltip>
      </div>

      {recentSignals.length > 0 && (
        <div className="ai-recent-signals">
          <h4>Sinais Recentes</h4>
          <div className="ai-signals-list">
            {recentSignals.map((signal) => (
              <div key={signal.id} className={`ai-signal-item ${signal.direction === 'BUY' ? 'pos' : signal.direction === 'SELL' ? 'neg' : ''}`}>
                <span className="signal-time">{signal.timestamp.toLocaleTimeString('pt-BR')}</span>
                <span className="signal-symbol">{signal.symbol}</span>
                <span className="signal-direction">{signal.direction}</span>
                <span className="signal-confidence">{fmtPct(signal.confidence)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {model && (
        <div className="ai-info-section">
          <h4>Sobre o Modelo</h4>
          <div className="ai-model-description">{model.description}</div>
          <div className="ai-parameters">
            <strong>Parametros:</strong>
            <div className="params-grid">
              {Object.entries(model.parameters).map(([key, value]) => (
                <div key={key} className="param-item">
                  <span className="param-key">{key}:</span>
                  <span className="param-value mono">{String(value)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

