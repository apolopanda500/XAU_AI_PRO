// Tab de Gestão de Risco - XAU AI PRO
import { useRiskManager } from '../../hooks/useRiskManager';
import { useAppStore } from '../../hooks/useAppStore';
import { fmtPct, fmtMoney, clsPnl } from '../../lib/format';
import { DRAWDOWN_THRESHOLDS, getRiskLevel } from '../../lib/riskCalculations';
import { useState } from 'react';

export default function RiskTab() {
  const {
    metrics, config, isAutoStopEnabled, lastUpdate,
    updateConfig, toggleAutoStop, stopCheck, getDrawdownLevel, getMarginLevel, refresh,
  } = useRiskManager();
  
  const positions = useAppStore((s) => s.positions);
  const [showConfig, setShowConfig] = useState(false);
  
  const drawdownLevel = getDrawdownLevel();
  const marginLevel = getMarginLevel();
  const { shouldStop, reason } = stopCheck();
  
  const riskCard = (label: string, value: string, sub: string, level: string, color: string) => (
    <div className="card risk-card">
      <div className="risk-label">{label}</div>
      <div className={`risk-value ${color}`}>{value}</div>
      <div className="risk-sub">{sub}</div>
      <div className={`risk-level chip ${level === 'Crítico' ? 'danger' : level === 'Alto' ? 'warn' : 'ok'}`}>{level}</div>
    </div>
  );
  
  if (!metrics) {
    return (
      <div className="risk-page">
        <div className="page-head">
          <div><h1>🛡️ Gestão de Risco</h1><span className="muted">Monitore e controle seu risco</span></div>
          <button className="btn primary" onClick={refresh}>Atualizar</button>
        </div>
        <div className="placeholder">Carregando métricas...</div>
      </div>
    );
  }
  
  return (
    <div className="risk-page">
      <div className="page-head">
        <div><h1>🛡️ Gestão de Risco</h1><span className="muted">{lastUpdate ? `Atualizado ${lastUpdate.toLocaleTimeString('pt-BR')}` : 'Aguardando...'}</span></div>
        <div className="btn-row">
          <button className={`btn ${showConfig ? 'primary' : 'ghost'}`} onClick={() => setShowConfig(!showConfig)}>{showConfig ? 'Ocultar' : 'Configurar'}</button>
          <button className="btn ghost" onClick={toggleAutoStop}>{isAutoStopEnabled ? '⏹️ Auto-Parar: ATIVO' : '▶️ Auto-Parar: DESATIVO'}</button>
        </div>
      </div>
      
      {shouldStop && (
        <div className="card alert-banner danger">
          <div className="alert-content"><strong>🚨 PARAR TRADING</strong><p>{reason}</p></div>
          <button className="btn warning" onClick={toggleAutoStop}>Desativar Auto-Parar</button>
        </div>
      )}
      
      <div className="section-title">📊 Risco Atual</div>
      <div className="metrics-grid">
        {riskCard('Drawdown Diário', fmtPct(metrics.dailyDrawdown), `PnL: ${fmtMoney(metrics.dailyPnl, 'USD')}`, drawdownLevel, clsPnl(-metrics.dailyDrawdown))}
        {riskCard('Drawdown Total', fmtPct(metrics.totalDrawdown), 'Do pico', getRiskLevel(metrics.totalDrawdown, DRAWDOWN_THRESHOLDS), clsPnl(-metrics.totalDrawdown))}
        {riskCard('Risco em Aberto', fmtPct(metrics.openRisk), `${metrics.openPositions} pos · Vol: ${metrics.totalVolume.toFixed(2)}`, getRiskLevel(metrics.openRisk, DRAWDOWN_THRESHOLDS), '')}
        {riskCard('Margem Usada', fmtPct(metrics.marginUsed), 'Limite broker', marginLevel, metrics.marginUsed > 80 ? 'danger' : 'ok')}
      </div>
      
      <div className="section-title">💰 Performance</div>
      <div className="metrics-grid">
        <div className="card metric-card"><span className="muted">PnL Diário</span><strong className={clsPnl(metrics.dailyPnl)}>{fmtMoney(metrics.dailyPnl, 'USD')}</strong><small>{fmtPct(metrics.dailyPnl / 10000)} do saldo</small></div>
        <div className="card metric-card"><span className="muted">PnL Total</span><strong className={clsPnl(metrics.totalPnl)}>{fmtMoney(metrics.totalPnl, 'USD')}</strong><small>Acumulado</small></div>
      </div>
      
      {showConfig && (
        <div className="section-title">⚙️ Configurações</div>
      )}
      <div className={`card config-card ${showConfig ? 'visible' : ''}`}>
        <h3>Limites de Risco</h3>
        <div className="config-grid">
          <div className="config-item"><label>Drawdown Diário Máximo</label><div className="config-row"><input type="number" value={config.maxDailyDrawdown} onChange={(e) => updateConfig({ maxDailyDrawdown: Number(e.target.value) })} min="0.1" max="50" step="0.5" /><span>%</span></div></div>
          <div className="config-item"><label>Drawdown Total Máximo</label><div className="config-row"><input type="number" value={config.maxTotalDrawdown} onChange={(e) => updateConfig({ maxTotalDrawdown: Number(e.target.value) })} min="1" max="100" step="1" /><span>%</span></div></div>
          <div className="config-item"><label>Risco por Trade</label><div className="config-row"><input type="number" value={config.maxRiskPerTrade} onChange={(e) => updateConfig({ maxRiskPerTrade: Number(e.target.value) })} min="0.1" max="10" step="0.1" /><span>%</span></div></div>
          <div className="config-item"><label>Alerta de Margem</label><div className="config-row"><input type="number" value={config.marginAlertLevel} onChange={(e) => updateConfig({ marginAlertLevel: Number(e.target.value) })} min="50" max="99" step="5" /><span>%</span></div></div>
        </div>
        <div className="config-actions">
          <label><input type="checkbox" checked={isAutoStopEnabled} onChange={toggleAutoStop} /><span>Parar automaticamente ao atingir limites</span></label>
        </div>
      </div>
    </div>
  );
}
