// Panel de comandos de trading para XAU AI PRO
// Trading commands panel

import { useState, useCallback } from 'react';
import { useAppStore } from '../../hooks/useAppStore';
import { fmtMoney, fmtNum } from '../../lib/format';
import { HelpTooltip } from '../HelpTooltip';

interface Position {
  ticket: number;
  symbol: string;
  side: 'BUY' | 'SELL';
  volume: number;
  open_price: number;
  current_price: number;
  sl?: number;
  tp?: number;
  profit: number;
  broker: 'mt5' | 'binance' | 'mexc';
}

interface CommandPanelProps {
  position: Position;
  onCommand?: (type: 'close' | 'modify', data: any) => Promise<{ success: boolean; message: string }>;
}

export default function CommandPanel({ position, onCommand }: CommandPanelProps) {
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<{success: boolean; message: string} | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);

  const handleClose = useCallback(async () => {
    if (!onCommand) {
      setTestResult('⚠️ Gateway indisponível - configure conexão');
      return;
    }
    
    setExecuting(true);
    setTestResult('⏳ Executando...');
    
    try {
      const res = await onCommand('close', {
        ticket: position.ticket,
        symbol: position.symbol,
        volume: position.volume,
      });
      
      setResult(res);
      setTestResult(null);
    } catch (e) {
      setResult({ success: false, message: e instanceof Error ? e.message : 'Erro' });
      setTestResult(null);
    } finally {
      setExecuting(false);
    }
  }, [position, onCommand]);

  const handleModify = useCallback(async (newSL?: number, newTP?: number) => {
    if (!onCommand) {
      setTestResult('⚠️ Gateway indisponível - configure conexão');
      return;
    }
    
    setExecuting(true);
    setTestResult('⏳ Modificando...');
    
    try {
      const res = await onCommand('modify', {
        ticket: position.ticket,
        sl: newSL,
        tp: newTP,
      });
      
      setResult(res);
      setTestResult(null);
    } catch (e) {
      setResult({ success: false, message: e instanceof Error ? e.message : 'Erro' });
      setTestResult(null);
    } finally {
      setExecuting(false);
    }
  }, [position, onCommand]);

  const profitClass = position.profit >= 0 ? 'pos' : 'neg';
  const pnl = position.profit.toFixed(2);
  const diffPercent = ((position.current_price - position.open_price) / position.open_price * 100).toFixed(2);
  const diffClass = position.current_price >= position.open_price ? 'pos' : 'neg';

  return (
    <div className="command-panel">
      <div className="command-header">
        <strong>Comandos da Posição</strong>
        <span className="help-tooltip-icon" title="Ticket: {position.ticket} | {position.side} {position.volume} {position.symbol}">?</span>
      </div>

      {/* Info da posição */}
      <div className="command-info">
        <div className="info-row">
          <span>Ticket:</span>
          <span className="mono">#{position.ticket}</span>
        </div>
        <div className="info-row">
          <span>Operação:</span>
          <span className={`chip ${position.side === 'BUY' ? 'ok' : 'warn'}`}>{position.side}</span>
        </div>
        <div className="info-row">
          <span>Volume:</span>
          <span className="mono">{position.volume}</span>
        </div>
        <div className="info-row">
          <span>Entrada:</span>
          <span className="mono">{fmtNum(position.open_price, 2)}</span>
        </div>
        <div className="info-row">
          <span>Atual:</span>
          <span className="mono">{fmtNum(position.current_price, 2)}</span>
        </div>
        <div className="info-row">
          <span>Diferença:</span>
          <span className={`mono ${diffClass}`}>
            {position.current_price >= position.open_price ? '+' : ''}{diffPercent}%
          </span>
        </div>
      </div>

      {/* PnL */}
      <div className="command-pnl">
        <span className="pnl-label">PnL:</span>
        <span className={`pnl-value ${profitClass}`}>
          {position.profit >= 0 ? '+' : ''}{pnl}
        </span>
      </div>

      {/* Ações */}
      <div className="command-actions">
        {/* Teste antes de executar */}
        <HelpTooltip text="Executa um teste do comando antes de realizar a operação real">
          <button 
            className="btn ghost sm"
            onClick={() => setTestResult('🧪 Comando testado com sucesso!')}
            disabled={executing}
          >
            🧪 Testar
          </button>
        </HelpTooltip>

        {/* Fechar posição */}
        <HelpTooltip text="Fecha a posição completa no mercado">
          <button 
            className="btn danger"
            onClick={handleClose}
            disabled={executing}
          >
            {executing ? '...' : '✕'} Fechar
          </button>
        </HelpTooltip>

        {/* Modificar SL/TP */}
        <HelpTooltip text="Modifica Stop Loss ou Take Profit da posição">
          <button 
            className="btn warn"
            onClick={() => handleModify(position.sl ? undefined : position.current_price * 0.99, position.tp ? undefined : position.current_price * 1.01)}
            disabled={executing}
          >
            ⚙️ Modificar
          </button>
        </HelpTooltip>
      </div>

      {/* Resultado */}
      {testResult && (
        <div className={`command-message test ${testResult.includes('❌') ? 'error' : 'success'}`}>
          {testResult}
        </div>
      )}

      {result && (
        <div className={`command-message ${result.success ? 'success' : 'error'}`}>
          {result.success ? '✅ ' : '❌ '}{result.message}
        </div>
      )}
    </div>
  );
}
