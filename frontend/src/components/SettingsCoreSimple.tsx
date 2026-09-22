import { useEffect, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';
import { definirPin, removerPin, validarPin } from '../auth/auth';
import { THEMES } from '../hooks/useTheme';
import '../theme/settings.css';

type Section = 'general' | 'alerts' | 'connections' | 'security';
const tabs: [Section, string][] = [['general', 'Geral / Interface'], ['alerts', '🔔 Notificações & Alertas'], ['connections', '🔑 Conexões & API'], ['security', '🔒 Segurança & Risco']];
const fmt = (v: unknown) => { const n = Number(v); return Number.isFinite(n) ? n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '--'; };
export default function SettingsCoreSimple() {
  const settings = useAppStore((state) => state.settings);
  const setSettings = useAppStore((state) => state.setSettings);
  const [section, setSection] = useState<Section>('general');
  const [status, setStatus] = useState('');
  const [pin1, setPin1] = useState('');
  const [pin2, setPin2] = useState('');
  const [connected, setConnected] = useState(false);
  const [account, setAccount] = useState<Record<string, unknown> | null>(null);
  const [connectivity, setConnectivity] = useState<Record<string, string>>({});
  const refreshAccount = () => {
    fetch(`${apiBase()}/api/status`, { signal: AbortSignal.timeout(5000) }).then((r) => r.json()).then((d: any) => setConnected(Boolean(d?.terminal_connected))).catch(() => setConnected(false));
    fetch(`${apiBase()}/api/account`, { signal: AbortSignal.timeout(5000) }).then((r) => r.json()).then((data: any) => { const a = data && typeof data === 'object' ? (data.account ?? data) : null; setAccount(a && typeof a === 'object' ? a : null); }).catch(() => setAccount(null));
  };
  useEffect(() => { refreshAccount(); const timer = window.setInterval(refreshAccount, 15000); return () => window.clearInterval(timer); }, []);
  useEffect(() => { if (section !== 'connections') return; let active = true; const check = async () => { const items: Record<string, string> = {}; for (const [name, path] of [['Gateway local', '/api/health'], ['MT5', '/api/status'], ['MEXC API', '/api/universal/account?broker=mexc&market=crypto-spot'], ['Binance API', '/api/universal/account?broker=binance&market=crypto-spot']] as const) { const started = performance.now(); try { const response = await fetch(`${apiBase()}${path}`, { signal: AbortSignal.timeout(5000) }); items[name] = response.ok ? `Online · ${Math.round(performance.now() - started)} ms` : 'Indisponível'; } catch { items[name] = 'Indisponível'; } } if (active) setConnectivity(items); }; void check(); const timer = window.setInterval(check, 15000); return () => { active = false; window.clearInterval(timer); }; }, [section]);
  const createPin = async () => {
    if (!pin1 || pin1 !== pin2) { setStatus('Os PINs digitados não conferem.'); return; }
    const error = validarPin(pin1);
    if (error) { setStatus(error); return; }
    await definirPin(pin1).catch(() => undefined);
    setSettings({ pinEnabled: true, pinCode: '' });
    setPin1(''); setPin2('');
    setStatus('PIN ativado e salvo neste dispositivo.');
  };
  const togglePin = async () => {
    if (settings.pinEnabled) {
      const pin = window.prompt('Digite o PIN atual para desativar:') || '';
      const error = validarPin(pin);
      if (error) { setStatus(error); return; }
      await removerPin().catch(() => undefined);
      setSettings({ pinEnabled: false, pinCode: '' });
      setStatus('PIN desativado.');
      return;
    }
    setSection('security');
  };

  return (
    <div className="card settings-card">
      <div className="section-head">
        <div><h2>Configurações</h2><span className="muted">Interface, alertas, conexões e segurança</span></div>
        <span className={`chip ${connected ? 'ok' : 'warn'}`}>{connected ? 'MT5 conectado' : 'MT5 desconectado'}</span>
      </div>
      <div className="settings-layout">
        <nav className="settings-nav" aria-label="Seções de configuração">
          {tabs.map(([id, label]) => (
            <button key={id} type="button" className={`settings-nav-item ${section === id ? 'active' : ''}`} onClick={() => setSection(id)}>{label}</button>
          ))}
        </nav>
        {section === 'general' && (
          <div className="settings-panel">
            <h3>🎨 Tema da interface</h3>
            <div className="theme-grid">
              {THEMES.map((theme) => (
                <button key={theme.id} type="button" className={`theme-swatch theme-swatch-${theme.id} ${settings.theme === theme.id ? 'selected' : ''}`} onClick={() => setSettings({ theme: theme.id })}>
                  <span className="theme-preview" aria-hidden="true"><i /><i /><i /></span>
                  <span className="theme-name">{theme.label}</span>
                  {settings.theme === theme.id && <span className="chip ok">ativo</span>}
                </button>
              ))}
            </div>
            <h3>⚙️ Preferências</h3>
            <div className="settings-rows">
              <label className="switch-row"><span>Animações da interface</span><input type="checkbox" checked={settings.animations} onChange={(e) => setSettings({ animations: e.target.checked })} /></label>
              <label className="switch-row"><span>Sons de alerta</span><input type="checkbox" checked={settings.soundEnabled} onChange={(e) => setSettings({ soundEnabled: e.target.checked })} /></label>
              <label className="switch-row"><span>Notificações do sistema</span><input type="checkbox" checked={settings.notifications} onChange={(e) => setSettings({ notifications: e.target.checked })} /></label>
              <label className="switch-row"><span>Auto-scroll nos terminais</span><input type="checkbox" checked={settings.autoScroll} onChange={(e) => setSettings({ autoScroll: e.target.checked })} /></label>
              <label className="switch-row"><span>Precisão decimal: {settings.precision} casas</span><input type="range" min={0} max={5} value={settings.precision} onChange={(e) => setSettings({ precision: Number(e.target.value) })} /></label>
            </div>
          </div>
        )}
        {section === 'alerts' && (
          <div className="settings-panel">
            <h3>🔔 Canais de notificação</h3>
            <div className="settings-rows">
              <label className="switch-row"><span>Notificações do sistema</span><input type="checkbox" checked={settings.notifications} onChange={(e) => setSettings({ notifications: e.target.checked })} /></label>
              <label className="switch-row"><span>Sons de alerta</span><input type="checkbox" checked={settings.soundEnabled} onChange={(e) => setSettings({ soundEnabled: e.target.checked })} /></label>
            </div>
            <h3>Slack</h3>
            <div className="settings-rows">
              <label className="switch-row"><span>Ativar webhook do Slack</span><input type="checkbox" checked={settings.slackActive} onChange={(e) => setSettings({ slackActive: e.target.checked })} /></label>
              <label className="switch-row"><span>Webhook</span><input className="input" value={settings.slackWebhook} onChange={(e) => setSettings({ slackWebhook: e.target.value })} placeholder="https://hooks.slack.com/..." /></label>
            </div>
            <h3>Telegram</h3>
            <div className="settings-rows">
              <label className="switch-row"><span>Ativar bot do Telegram</span><input type="checkbox" checked={settings.telegramActive} onChange={(e) => setSettings({ telegramActive: e.target.checked })} /></label>
              <label className="switch-row"><span>Token</span><input className="input" value={settings.telegramToken} onChange={(e) => setSettings({ telegramToken: e.target.value })} /></label>
              <label className="switch-row"><span>Chat ID</span><input className="input" value={settings.telegramChatId} onChange={(e) => setSettings({ telegramChatId: e.target.value })} /></label>
            </div>
            <h3>Discord</h3>
            <div className="settings-rows">
              <label className="switch-row"><span>Ativar webhook do Discord</span><input type="checkbox" checked={settings.discordActive} onChange={(e) => setSettings({ discordActive: e.target.checked })} /></label>
              <label className="switch-row"><span>Webhook</span><input className="input" value={settings.discordWebhook} onChange={(e) => setSettings({ discordWebhook: e.target.value })} /></label>
            </div>
          </div>
        )}
        {section === 'connections' && (
          <div className="settings-panel">
            <h3>🖥️ MetaTrader 5</h3>
            <div className="settings-rows">
              <label className="switch-row"><span>Caminho do terminal</span><input className="input" value={settings.mt5Path} onChange={(e) => setSettings({ mt5Path: e.target.value })} placeholder="terminal64.exe" /></label>
              <label className="switch-row"><span>Conectar automaticamente ao abrir</span><input type="checkbox" checked={settings.mt5AutoConnect} disabled /></label>
            </div>
            <p className="hint">Por segurança, o app nunca inicia o MT5 sozinho — a conexão é sempre uma ação sua na aba do Robô.</p>
            <h3>🌐 Saúde das conexões</h3>
            <div className="conn-list">
              {Object.entries(connectivity).length === 0 && <span className="muted">Verificando…</span>}
              {Object.entries(connectivity).map(([name, state]) => (
                <div key={name} className="conn-row"><strong>{name}</strong><span className={`chip ${state.startsWith('Online') ? 'ok' : 'warn'}`}>{state}</span></div>
              ))}
            </div>
            <h3>📡 Conta ativa</h3>
            <div className="conn-list">
              {account ? (
                <>
                  <div className="conn-row"><strong>Login</strong><span className="mono">{String(account.login ?? '--')}</span></div>
                  <div className="conn-row"><strong>Servidor</strong><span>{String(account.server ?? '--')}</span></div>
                  <div className="conn-row"><strong>Moeda</strong><span>{String(account.currency ?? '--')}</span></div>
                  <div className="conn-row"><strong>Saldo</strong><span className="mono">{fmt(account.balance)}</span></div>
                  <div className="conn-row"><strong>Patrimônio</strong><span className="mono">{fmt(account.equity)}</span></div>
                </>
              ) : <span className="muted">Sem conta carregada {connected ? '' : '(MT5 desconectado)'}</span>}
            </div>
          </div>
        )}
        {section === 'security' && (
          <div className="settings-panel">
            <h3>🔒 PIN de acesso</h3>
            <p className="hint">O PIN protege a abertura do app. É validado com PBKDF2-SHA256 (150k iterações) e salvo apenas neste dispositivo.</p>
            <div className="settings-rows">
              <label className="switch-row"><span>Exigir PIN ao abrir o app</span><input type="checkbox" checked={settings.pinEnabled} onChange={() => void togglePin()} /></label>
            </div>
            <div className="pin-form">
              <input className="input" type="password" inputMode="numeric" maxLength={8} placeholder="Novo PIN (4-8 dígitos)" value={pin1} onChange={(e) => setPin1(e.target.value.replace(/\D/g, ''))} />
              <input className="input" type="password" inputMode="numeric" maxLength={8} placeholder="Confirmar PIN" value={pin2} onChange={(e) => setPin2(e.target.value.replace(/\D/g, ''))} />
              <button type="button" className="btn primary sm" onClick={() => void createPin()}>Salvar PIN</button>
            </div>
            <h3>🛡️ Risco & IA</h3>
            <div className="settings-rows">
              <label className="switch-row"><span>Motor de IA habilitado (decisões do robô)</span><input type="checkbox" checked={settings.aiEnabled} onChange={(e) => setSettings({ aiEnabled: e.target.checked })} /></label>
              <label className="switch-row"><span>Modelo</span><input className="input" value={settings.aiModel} onChange={(e) => setSettings({ aiModel: e.target.value })} /></label>
              <label className="switch-row"><span>Intervalo da IA: {settings.aiInterval}s</span><input type="range" min={30} max={300} step={10} value={settings.aiInterval} onChange={(e) => setSettings({ aiInterval: Number(e.target.value) })} /></label>
            </div>
            {status && <div className="hint" role="status">{status}</div>}
          </div>
        )}
      </div>
    </div>
  );}
