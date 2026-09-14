import { useState } from 'react';
import { useAppStore } from '../../hooks/useAppStore';

export default function RobotTab() {
  const [connecting, setConnecting] = useState(false);
  const [connectionMessage, setConnectionMessage] = useState('');
  const robotStatus = useAppStore((s) => s.robotStatus);
  const setRobotStatus = useAppStore((s) => s.setRobotStatus);
  const magicNumber = useAppStore((s) => s.magicNumber);
  const setMagicNumber = useAppStore((s) => s.setMagicNumber);
  const account = useAppStore((s) => s.account);
  const systemState = useAppStore((s) => s.systemState);
  const settings = useAppStore((s) => s.settings);
  const setSettings = useAppStore((s) => s.setSettings);
  const setAccount = useAppStore((s) => s.setAccount);

  const connectRobot = async () => {
    setConnecting(true);
    setConnectionMessage('Verificando MT5 e o EA...');
    try {
      const response = await fetch('http://127.0.0.1:9001/health', { signal: AbortSignal.timeout(5000) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setRobotStatus('Conectado');
      setConnectionMessage('MT5 e EA conectados com dados reais.');
    } catch {
      setRobotStatus('Desconectado');
      setAccount(null);
      setConnectionMessage('MT5/EA não respondeu em 127.0.0.1:9001. Inicie o EA e tente novamente.');
    } finally {
      setConnecting(false);
    }
  };

  const disconnectRobot = () => {
    setRobotStatus('Desconectado');
    setAccount(null);
    setConnectionMessage('Conexão do app encerrada. O EA não foi alterado nem desligado.');
  };

  return (
    <div>
      <div className="page-head">
        <h1>Robô MT5</h1>
        <span className="muted">Controle do Expert Advisor e da ponte com o Core</span>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h2>Estado do Robô</h2>
          <div className="switch-row">
            <div>
              <div className="switch-label">Robô ativo</div>
              <div className="switch-desc">EA envia sinais de execucao ao Core</div>
            </div>
            <span className={`chip ${robotStatus === 'Conectado' ? 'ok' : 'warn'}`}>
              {robotStatus}
            </span>
          </div>
          <div className="field">
            <label htmlFor="magic">Magic Number</label>
            <input
              id="magic"
              type="number"
              value={magicNumber}
              onChange={(e) => setMagicNumber(Number(e.target.value) || 0)}
            />
            <span className="hint">Usado para identificar operacoes abertas pelo XAU AI PRO.</span>
          </div>
          <div className="field">
            <label htmlFor="mt5path">Caminho do terminal MT5</label>
            <input
              id="mt5path"
              type="text"
              placeholder="C:\Program Files\MetaTrader 5\terminal64.exe"
              value={settings.mt5Path}
              onChange={(e) => setSettings({ mt5Path: e.target.value })}
            />
            <span className="hint">Opcional: usado para auto-iniciar o terminal.</span>
          </div>
          <div className="check-row">
            <input
              id="mt5auto"
              type="checkbox"
              checked={settings.mt5AutoConnect}
              onChange={(e) => setSettings({ mt5AutoConnect: e.target.checked })}
            />
            <label htmlFor="mt5auto">Conectar automaticamente ao iniciar</label>
          </div>
          <div className="btn-row" style={{ marginTop: 16 }}>
            <button className="btn primary" type="button" onClick={connectRobot} disabled={connecting}>
              {connecting ? 'Conectando...' : 'Conectar robô'}
            </button>
            <button className="btn danger" type="button" onClick={disconnectRobot} disabled={connecting}>
              Desconectar
            </button>
          </div>
          {connectionMessage && <div className="hint" role="status" style={{ marginTop: 10 }}>{connectionMessage}</div>}
        </div>

        <div className="card">
          <h2>Conexão MT5</h2>
          {account ? (
            <div className="tbl-wrap">
              <table className="tbl">
                <tbody>
                  <tr><td>Login</td><td className="mono">{account.login}</td></tr>
                  <tr><td>Servidor</td><td>{account.server}</td></tr>
                  <tr><td>Equidade</td><td className="mono">{account.equity}</td></tr>
                  <tr><td>Negociação</td><td>
                    <span className={`chip ${account.trade_allowed ? 'ok' : 'warn'}`}>
                      {account.trade_allowed ? 'Permitida' : 'Bloqueada'}
                    </span>
                  </td></tr>
                </tbody>
              </table>
            </div>
          ) : (
            <div className="placeholder">
              <div className="ph-icon">🔌</div>
              <span>MT5 nao conectado.</span>
              <span className="muted">Inicie o terminal com o EA XAU AI PRO ativo.</span>
            </div>
          )}
          <div style={{ marginTop: 12 }}>
            <span className="chip primary">EA: {robotStatus}</span>{' '}
            <span className="chip">Core: {systemState?.status ?? 'aguardando'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
