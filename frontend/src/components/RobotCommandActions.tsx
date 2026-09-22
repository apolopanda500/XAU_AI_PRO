import { useRef, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';
import { compatibleMarket } from '../lib/robotAssets';
import { requestId } from '../lib/format';
import { notify } from '../lib/notify';
const API = `${apiBase()}`;

export default function RobotCommandActions() {
  const symbol = useAppStore((s) => s.selectedSymbol);
  const [status, setStatus] = useState('Selecione um ativo.');
  const busy = useRef(false);
  const send = async (action: string, side?: string) => {
    if (busy.current) return;
    const state = useAppStore.getState();
    const activeSymbol = state.selectedSymbol || symbol;
    if (!activeSymbol) { setStatus('Selecione um ativo.'); return; }
    // Usa a corretora/mercado ativos da sessao quando disponiveis; sem dado simulado.
    const stored = (() => { try { return localStorage.getItem('xau-active-account') || ''; } catch { return ''; } })();
    const [storedBroker, storedMarket] = stored.split(':');
    const broker = storedBroker || 'mt5';
    const market = compatibleMarket(broker, storedMarket || 'forex') || 'forex';
    if (!window.confirm(`Confirmar ${action} para ${activeSymbol} em ${broker}/${market}?`)) return;
    busy.current = true; setStatus('Enviando...');
    try {
      const isEaClose = broker === 'mt5' && action === 'close';
      const endpoint = isEaClose ? `${API}/api/ea/close` : `${API}/api/universal/${action}`;
      const r = await fetch(endpoint, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ broker, market, symbol: activeSymbol, side: side || 'buy', order_type: 'market', quantity: 0.01, request_id: requestId(), confirm: true, confirm_live: isEaClose, authorize_execution: isEaClose, execute: false, action }),
        signal: AbortSignal.timeout(8000),
      });
      const d = await r.json() as { error?: string; stage?: string; status?: string };
      if (r.ok) {
        setStatus(`${action} recebido · ${d.stage || d.status || 'registrado'}`);
        void notify('Comando enviado', `${action} ${side ?? ''} ${activeSymbol} registrado no gateway.`);
      } else {
        setStatus(`${action} rejeitado · ${d.error || `HTTP ${r.status}`}`);
        void notify('Comando rejeitado', d.error || `HTTP ${r.status}`);
      }
    } catch { setStatus('Gateway indisponível.'); } finally { busy.current = false; }
  };
  return <div className="card compact-card robot-command-actions"><div className="section-head"><h2>Comandos</h2><span className="chip warn">Confirmação</span></div><div className="btn-row"><button className="btn sm primary" onClick={() => void send('order', 'buy')}>Comprar</button><button className="btn sm danger" onClick={() => void send('order', 'sell')}>Vender</button><button className="btn sm ghost" onClick={() => void send('close')}>Fechar</button><button className="btn sm ghost" onClick={() => void send('modify')}>Modificar</button><button className="btn sm ghost" onClick={() => void send('cancel')}>Cancelar</button></div><div className="hint" role="status" aria-live="polite">{status}</div></div>;
}
