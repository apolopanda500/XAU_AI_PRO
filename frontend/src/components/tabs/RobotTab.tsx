import { useCallback, useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { useAppStore } from '../../hooks/useAppStore';

const MT5 = 'http://127.0.0.1:9001';

export default function RobotTab() {
  const [connecting, setConnecting] = useState(false);
  const [connectionMessage, setConnectionMessage] = useState('');
  const [lastCheck, setLastCheck] = useState('nunca');
  const [error, setError] = useState('');
  const [cpuCores, setCpuCores] = useState<number | null>(null);
  const [memoryMb, setMemoryMb] = useState<number | null>(null);
  const [cpuTemperature, setCpuTemperature] = useState<number | null>(null);
  const [gpuName, setGpuName] = useState<string | null>(null);
  const [gpuMonitoring, setGpuMonitoring] = useState(false);
  const robotStatus = useAppStore((s) => s.robotStatus);
  const setRobotStatus = useAppStore((s) => s.setRobotStatus);
  const magicNumber = useAppStore((s) => s.magicNumber);
  const setMagicNumber = useAppStore((s) => s.setMagicNumber);
  const account = useAppStore((s) => s.account);
  const systemState = useAppStore((s) => s.systemState);
  const settings = useAppStore((s) => s.settings);
  const setSettings = useAppStore((s) => s.setSettings);
  const setAccount = useAppStore((s) => s.setAccount);

  const checkConnection = useCallback(async () => {
    setConnecting(true);
    try {
      const response = await fetch(`${MT5}/api/status`, { signal: AbortSignal.timeout(5000) });
      if (!response.ok) throw new Error(`MT5 HTTP ${response.status}`);
      const data = await response.json() as { account?: Record<string, unknown> };
      if (data.account) {
        const a = data.account;
        setAccount({ login: String(a.login ?? ''), balance: Number(a.balance ?? 0), equity: Number(a.equity ?? 0), margin: Number(a.margin ?? 0), free_margin: Number(a.free_margin ?? a.margin_free ?? 0), leverage: String(a.leverage ?? 0), server: String(a.server ?? ''), currency: String(a.currency ?? ''), profit: Number(a.profit ?? 0), trade_allowed: Boolean(a.trade_allowed) });
      }
      setRobotStatus('Conectado'); setError(''); setConnectionMessage('MT5 conectado com dados reais.');
    } catch (err) {
      setRobotStatus('Desconectado'); setAccount(null); setError(err instanceof Error ? err.message : 'MT5 indisponível'); setConnectionMessage('MT5 não respondeu. Verifique o terminal e o bridge.');
    } finally { setLastCheck(new Date().toLocaleTimeString('pt-BR')); setConnecting(false); }
  }, [setAccount, setRobotStatus]);

  useEffect(() => {
    setCpuCores(navigator.hardwareConcurrency || null);
    const memory = (performance as Performance & { memory?: { usedJSHeapSize: number } }).memory;
    if (memory) setMemoryMb(Math.round(memory.usedJSHeapSize / 1024 / 1024));
    const readHardware = async () => {
      try {
        const telemetry = await invoke<{ cpu_temperature_c?: number; gpu_name?: string; gpu_available: boolean }>('hardware_telemetry');
        setCpuTemperature(telemetry.cpu_temperature_c ?? null);
        setGpuName(telemetry.gpu_available ? telemetry.gpu_name ?? null : null);
      } catch {
        setCpuTemperature(null);
        setGpuName(null);
      }
    };
    void readHardware();
    const hardwareTimer = window.setInterval(() => void readHardware(), 15000);
    let timer: number | undefined;
    if (settings.mt5AutoConnect) {
      void checkConnection();
      timer = window.setInterval(() => void checkConnection(), 5000);
    }
    return () => { if (timer) window.clearInterval(timer); window.clearInterval(hardwareTimer); };
  }, [checkConnection, settings.mt5AutoConnect]);

  const disconnectRobot = () => { setRobotStatus('Desconectado'); setAccount(null); setConnectionMessage('Conexão visual encerrada. O EA não foi desligado nem alterado.'); };

  return <div className="robot-tab">
    <div className="page-head"><h1>Robô MT5</h1><span className="muted">Conexão real, execução manual e estado do Expert Advisor</span></div>
    <div className="grid cols-2">
      <div className="card"><h2>Controle seguro</h2><div className="switch-row"><div><div className="switch-label">Estado da conexão</div><div className="switch-desc">Somente leitura e sincronização com o terminal</div></div><span className={`chip ${robotStatus === 'Conectado' ? 'ok' : 'warn'}`}>{robotStatus}</span></div>
        <div className="field"><label htmlFor="magic">Magic Number</label><input id="magic" type="number" value={magicNumber} onChange={(e) => setMagicNumber(Number(e.target.value) || 0)} /><span className="hint">Identificação das operações do XAU AI PRO.</span></div>
        <div className="field"><label htmlFor="mt5path">Caminho do terminal MT5</label><input id="mt5path" type="text" placeholder="C:\Program Files\MetaTrader 5\terminal64.exe" value={settings.mt5Path} onChange={(e) => setSettings({ mt5Path: e.target.value })} /></div>
        <div className="check-row"><input id="mt5auto" type="checkbox" checked={settings.mt5AutoConnect} onChange={(e) => setSettings({ mt5AutoConnect: e.target.checked })} /><label htmlFor="mt5auto">Sincronizar automaticamente ao iniciar</label></div>
        <div className="btn-row" style={{ marginTop: 16 }}><button className="btn primary" type="button" onClick={checkConnection} disabled={connecting}>{connecting ? 'Verificando...' : 'Conectar e atualizar'}</button><button className="btn danger" type="button" onClick={disconnectRobot} disabled={connecting}>Desconectar app</button></div>
        <div className="hint" style={{ marginTop: 10 }}>Última verificação real: {lastCheck}</div>{connectionMessage && <div className="hint" role="status" style={{ marginTop: 8 }}>{connectionMessage}</div>}{error && <div className="hint neg" role="alert" style={{ marginTop: 8 }}>Erro: {error}</div>}
      </div>
      <div className="card"><h2>Terminal MT5</h2>{account ? <div className="tbl-wrap"><table className="tbl"><tbody><tr><td>Login</td><td className="mono">{account.login}</td></tr><tr><td>Servidor</td><td>{account.server}</td></tr><tr><td>Saldo / equidade</td><td className="mono">{account.balance} / {account.equity} {account.currency}</td></tr><tr><td>Margem livre</td><td className="mono">{account.free_margin}</td></tr><tr><td>Negociação</td><td><span className={`chip ${account.trade_allowed ? 'ok' : 'warn'}`}>{account.trade_allowed ? 'Permitida' : 'Bloqueada'}</span></td></tr></tbody></table></div> : <div className="placeholder"><span>Terminal MT5 aguardando conexão real.</span><span className="muted">Nenhum dado simulado é exibido.</span></div>}<div style={{ marginTop: 12 }}><span className="chip">Core: {systemState?.status ?? 'aguardando'}</span> <span className="chip">EA: {robotStatus}</span></div><div className="hint" style={{ marginTop: 12 }}>Desconectar o app não desliga nem altera o EA. Ordens dependem da configuração manual do usuário.</div></div>
    </div>
    <div className="card" style={{ marginTop: 14 }}><h2>Recursos e segurança</h2><div className="grid cols-4"><div><span className="kpi-label">CPU disponível</span><div className="kpi-value">{cpuCores ?? '--'}<span className="kpi-sub"> núcleos</span></div></div><div><span className="kpi-label">Temperatura CPU</span><div className="kpi-value">{cpuTemperature != null ? `${cpuTemperature.toFixed(1)} °C` : '--'}</div><div className="kpi-sub">Leitura nativa; indisponível sem sensor</div></div><div><span className="kpi-label">GPU opcional</span><div className="check-row" style={{ margin: '6px 0' }}><input id="gpu-monitoring" type="checkbox" checked={gpuMonitoring} onChange={(e) => setGpuMonitoring(e.target.checked)} /><label htmlFor="gpu-monitoring">Monitorar</label></div><div className="kpi-sub">{gpuMonitoring ? (gpuName ?? 'GPU não exposta pelo driver') : 'Desativado pelo usuário'}</div></div><div><span className="kpi-label">Operação</span><div><span className="chip warn">Manual</span></div><div className="kpi-sub">Sem saque e sem ordem automática</div></div></div><div className="hint" style={{ marginTop: 12 }}>A GPU é apenas monitorada quando habilitada; o app não envia ordens nem movimenta ativos.</div></div>
  </div>;
}
