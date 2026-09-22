// Tab de Alertas - XAU AI PRO
import { useAlertManager } from '../../hooks/useAlertManager';
import { useAppStore } from '../../hooks/useAppStore';
import { fmtNum } from '../../lib/format';
import { useState } from 'react';
import type { AlertType } from '../../hooks/useAlertManager';

export default function AlertTab() {
  const { alerts, activeAlerts, recentlyTriggered, createAlert, removeAlert, toggleAlert, getSelectedQuote } = useAlertManager();
  const selectedSymbol = useAppStore((s) => s.selectedSymbol);
  const quotes = useAppStore((s) => s.quotes);
  const [showForm, setShowForm] = useState(false);
  const [newAlert, setNewAlert] = useState({ type: 'price_above' as AlertType, symbol: selectedSymbol || 'XAUUSD', condition: '' });
  
  const quote = getSelectedQuote();
  
  const handleCreate = () => {
    if (!newAlert.symbol || !newAlert.condition) { alert('Preencha symbol e condição'); return; }
    const value = parseFloat(newAlert.condition) || 0;
    createAlert({
      type: newAlert.type,
      symbol: newAlert.symbol,
      condition: newAlert.condition,
      value,
      active: true,
    });
    setNewAlert({ type: 'price_above', symbol: selectedSymbol || 'XAUUSD', condition: '' });
    setShowForm(false);
  };
  
  const getIcon = (type: AlertType) => type === 'price_above' ? '📈' : type === 'price_below' ? '📉' : type === 'spread_above' ? '📊' : '⏰';
  const getColor = (type: AlertType) => type === 'price_above' ? 'pos' : type === 'price_below' ? 'neg' : type === 'spread_above' ? 'warn' : 'ok';
  
  return (
    <div className="alert-page">
      <div className="page-head">
        <div><h1>🔔 Alertas de Mercado</h1><span className="muted">{activeAlerts.length} ativos · {alerts.length} total</span></div>
        <div className="btn-row">
          <button className={`btn ${showForm ? 'primary' : 'ghost'}`} onClick={() => setShowForm(!showForm)}>{showForm ? 'Cancelar' : '+ Novo Alerta'}</button>
          <button className="btn ghost" onClick={() => window.alert('Notificação enviada!')}>🔔 Testar</button>
        </div>
      </div>
      
      {showForm && (
        <div className="card form-card">
          <h3>Criar Alerta</h3>
          <div className="form-grid">
            <div className="form-item">
              <label>Tipo</label>
              <select value={newAlert.type} onChange={(e) => setNewAlert({ ...newAlert, type: e.target.value as AlertType })}>
                <option value="price_above">Preço Sobe (≥)</option>
                <option value="price_below">Preço Cai (≤)</option>
                <option value="spread_above">Spread Aumenta</option>
                <option value="time">Horário</option>
              </select>
            </div>
            <div className="form-item">
              <label>Ativo</label>
              <select value={newAlert.symbol} onChange={(e) => setNewAlert({ ...newAlert, symbol: e.target.value })}>
                {quotes.map(q => <option key={q.symbol} value={q.symbol}>{q.symbol}</option>)}
              </select>
            </div>
            <div className="form-item">
              <label>Valor</label>
              <input type="text" value={newAlert.condition} onChange={(e) => setNewAlert({ ...newAlert, condition: e.target.value })} placeholder="Ex: 95.000 ou 14:30" />
            </div>
          </div>
          <div className="form-actions">
            <button className="btn primary" onClick={handleCreate}>Criar</button>
            <button className="btn ghost" onClick={() => setShowForm(false)}>Cancelar</button>
          </div>
        </div>
      )}
      
      <div className="section-title">📋 Alertas Ativos ({activeAlerts.length})</div>
      {activeAlerts.length > 0 ? (
        <div className="alerts-list">
          {activeAlerts.map(alert => {
            const q = quotes.find(ql => ql.symbol === alert.symbol);
            const isTriggered = alert.triggeredAt && (Date.now() - alert.triggeredAt.getTime()) < 60000;
            return (
              <div key={alert.id} className={`card alert-item ${isTriggered ? 'triggered' : ''}`}>
                <div className="alert-icon">{getIcon(alert.type)}</div>
                <div className="alert-info">
                  <div className="alert-header">
                    <span className={`alert-type chip ${getColor(alert.type)}`}>{alert.type.replace('_', ' ').toUpperCase()}</span>
                    <span className="alert-symbol">{alert.symbol}</span>
                  </div>
                  <div className="alert-condition">
                    {alert.type === 'time' ? `📅 ${alert.condition}hs` : alert.type === 'price_above' ? `📈 ≥ ${fmtNum(alert.value)}` : alert.type === 'price_below' ? `📉 ≤ ${fmtNum(alert.value)}` : `📊 Spread ≥ ${fmtNum(alert.value, 4)}`}
                  </div>
                  {q && alert.type.startsWith('price') && (
                    <div className="alert-current">Preço atual: <strong>{fmtNum(q.price, 2)}</strong> {alert.type === 'price_above' && q.price >= alert.value ? ' ✅' : ''}</div>
                  )}
                  {alert.timesTriggered > 0 && <div className="alert-triggered">Acionado {alert.timesTriggered}x</div>}
                </div>
                <div className="alert-actions">
                  <button className="btn xs ghost" onClick={() => toggleAlert(alert.id)}>{alert.active ? '⏸️' : '▶️'}</button>
                  <button className="btn xs danger" onClick={() => removeAlert(alert.id)}>🗑️</button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="placeholder"><span>Nenhum alerta ativo</span><span className="muted">Crie seu primeiro alerta</span></div>
      )}
      
      {recentlyTriggered.length > 0 && (
        <div className="section-title">⚡ Recentemente Acionados</div>
      )}
    </div>
  );
}
