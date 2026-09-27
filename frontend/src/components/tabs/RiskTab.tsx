// Tab de Gestão de Risco - XAU AI PRO
import { useRiskManager } from '../../hooks/useRiskManager';
import { useRealRisk } from '../../hooks/useRealRisk';
import { useAppStore } from '../../hooks/useAppStore';
import { fmtPct, fmtMoney, clsPnl } from '../../lib/format';
import { DRAWDOWN_THRESHOLDS, getRiskLevel } from '../../lib/riskCalculations';
import { useState } from 'react';

export default function RiskTab() {
  const {
    metrics, config, isAutoStopEnabled, lastUpdate,
    updateConfig, toggleAutoStop, stopCheck, getMarginLevel, refresh,
  } = useRiskManager();
  
  const real = useRealRisk();

  // Metrica vinda do gateway; '—' quando ele nao devolveu. Nunca zero
  // inventado: ausencia de dado nao e zero.
  const pct = (v: number | null | undefined) => (v === null || v === undefined ? '--' : fmtPct(v));

  // Parada de emergencia: controle real. O toggle antigo era useState do React
  // e nao bloqueava ordem alguma no gateway.
  const killAtivo = real.kill.status === 'ativo';
  const executar = (acao: 'stop' | 'resume') => {
    const pergunta = acao === 'stop'
      ? 'Parar a execucao agora?\n\nO gateway recusara novas ordens ate a retomada.'
      : 'Retomar a execucao?\n\nO gateway exige XAU_ENABLE_EMERGENCY_RESUME=1.';
    if (window.confirm(pergunta)) void (acao === 'stop' ? real.parar() : real.retomar());
  };

  const positions = useAppStore((s) => s.positions);
  const [showConfig, setShowConfig] = useState(false);
  
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
          {killAtivo
            ? <button className="btn danger" onClick={() => executar('resume')} disabled={real.kill.busy}>Retomar execucao</button>
            : <button className="btn warning" onClick={() => executar('stop')} disabled={real.kill.busy}>Parar execucao (emergencia)</button>}
        </div>
      </div>
      
      {shouldStop && (
        <div className="card alert-banner danger">
          <div className="alert-content"><strong>🚨 PARAR TRADING</strong><p>{reason}</p></div>
          <button className="btn warning" onClick={() => executar('resume')}>Retomar execucao</button>
        </div>
      )}
      
      {/* A sessao "Risco real do gateway" abaixo e a fonte autoritativa: vem
          do risk_gate com os limites efetivos (2%/5%/15%, 5 pos, 20 operacoes).
          O bloco de resumo do portfolio abaixo e apenas complementar
          (margem e PnL da conta). Drawdown aparecia nas duas secoes com nomes
          diferentes, dando a impressao de dois medidores de risco distintos. */}

      <div className="section-title">Risco real do gateway (mesma fonte do risk_gate)</div>
      {real.erro ? (
        <div className="card alert-banner warning">
          <div className="alert-content"><strong>Gateway nao devolveu o estado de risco</strong><p>{real.erro}</p></div>
          <button className="btn ghost" onClick={() => void real.refresh()}>Tentar de novo</button>
        </div>
      ) : (
        <div className="metrics-grid">
          {riskCard('Perda diaria', pct(real.estado?.daily_loss_pct), 'limite 2%', (real.estado?.daily_loss_pct ?? 0) >= 2 ? 'Critico' : 'Baixo', clsPnl(real.estado?.daily_loss_pct ?? 0))}
          {riskCard('Exposicao', pct(real.estado?.exposure_pct), 'limite 5%', (real.estado?.exposure_pct ?? 0) >= 5 ? 'Critico' : 'Baixo', clsPnl(real.estado?.exposure_pct ?? 0))}
          {riskCard('Drawdown', pct(real.estado?.drawdown_pct), 'limite 15%', (real.estado?.drawdown_pct ?? 0) >= 15 ? 'Critico' : (real.estado?.drawdown_pct ?? 0) >= 8 ? 'Alto' : 'Baixo', clsPnl(real.estado?.drawdown_pct ?? 0))}
          {riskCard('Posicoes / operacoes', `${real.estado?.open_positions ?? '--'} / ${real.estado?.daily_trades ?? '--'}`, 'limites 5 / 20', ((real.estado?.open_positions ?? 0) >= 5 || (real.estado?.daily_trades ?? 0) >= 20) ? 'Critico' : 'Baixo', '')}
        </div>
      )}
      {real.kill.erro && <p className="auth-erro">{real.kill.erro}</p>}

      <div className="section-title">Resumo da conta</div>
      <div className="metrics-grid">
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
        <label><input type="checkbox" checked={isAutoStopEnabled} onChange={toggleAutoStop} /><span>Somente aviso nesta tela (nao bloqueia o gateway; use "Parar execucao")</span></label>
        </div>
      </div>
    </div>
  );
}
