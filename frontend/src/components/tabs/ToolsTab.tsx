import { useState } from 'react';
import { useAppStore } from '../../hooks/useAppStore';

export default function ToolsTab() {
  const wsConnected = useAppStore((s) => s.wsConnected);
  const [log, setLog] = useState<string[]>([
    '[xau-ai-pro] Log de eventos (dados do Core aparecem aqui)',
  ]);

  const push = (msg: string) => setLog((l) => [...l.slice(-200), msg]);

  const runCheck = async (name: string) => {
    push(`[${new Date().toLocaleTimeString('pt-BR')}] ${name}: ${wsConnected ? 'Core online, executando...' : 'Core offline - verifique a conexao'}`);
  };

  return (
    <div>
      <div className="page-head">
        <h1>Ferramentas</h1>
        <span className="muted">Utilidades de diagnostico e manutencao</span>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h2>Diagnóstico</h2>
          <div className="btn-row">
            <button className="btn primary" onClick={() => runCheck('Teste de conexao WS')}>Testar Conexão WS</button>
            <button className="btn ghost" onClick={() => runCheck('Snapshot de cotacoes')}>Snapshot Cotações</button>
            <button className="btn ghost" onClick={() => runCheck('Verificacao de estado')}>Verificar Estado</button>
          </div>
        </div>

        <div className="card">
          <h2>Manutenção</h2>
          <div className="btn-row">
            <button className="btn ghost" onClick={() => setLog(['[xau-ai-pro] Log limpo'])}>Limpar Log</button>
            <button className="btn danger" onClick={() => push('[xau-ai-pro] Cache de cotacoes invalidado (sinalizacão)')}>Invalidar Cache</button>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h2>Log de Eventos</h2>
        <div className="log-box" id="tools-log">
          {log.join('\n')}
        </div>
      </div>
    </div>
  );
}
