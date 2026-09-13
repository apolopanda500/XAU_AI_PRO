import { useAppStore } from '../../hooks/useAppStore';

export default function DashboardTab() {
  const account = useAppStore((s) => s.account);
  const systemState = useAppStore((s) => s.systemState);
  const wsConnected = useAppStore((s) => s.wsConnected);
  const positions = useAppStore((s) => s.positions);
  const settings = useAppStore((s) => s.settings);

  const fmt = (v: number | undefined | null, decimals = settings.precision) =>
    v == null ? '--' : v.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

  const equity = account?.equity ?? null;
  const balance = account?.balance ?? null;
  const floating = account?.profit ?? null;

  return (
    <div>
      <div className="page-head">
        <h1>Painel</h1>
        <span className="muted">Visao geral do sistema e da conta MT5</span>
      </div>

      <div className="grid cols-4">
        <div className="card">
          <div className="kpi-label">Saldo</div>
          <div className="kpi-value">{fmt(balance)}</div>
          <div className="kpi-sub">{account?.currency ?? 'USD'}</div>
        </div>
        <div className="card">
          <div className="kpi-label">Equidade</div>
          <div className="kpi-value">{fmt(equity)}</div>
          <div className="kpi-sub">
            Flutuante:{' '}
            {floating != null ? (
              <span className={floating >= 0 ? 'pos' : 'neg'}>
                {fmt(floating)}
              </span>
            ) : (
              '--'
            )}
          </div>
        </div>
        <div className="card">
          <div className="kpi-label">Posições Abertas</div>
          <div className="kpi-value">{positions.length}</div>
          <div className="kpi-sub">Magic #{settings.mt5AutoConnect ? 'auto' : 'manual'}</div>
        </div>
        <div className="card">
          <div className="kpi-label">Conexão WS</div>
          <div className="kpi-value">
            <span className={`chip ${wsConnected ? 'ok' : 'danger'}`}>{wsConnected ? 'Online' : 'Offline'}</span>
          </div>
          <div className="kpi-sub">Core: {systemState?.status ?? 'aguardando'}</div>
        </div>
      </div>

      <div className="grid cols-2" style={{ marginTop: 14 }}>
        <div className="card">
          <h2>Estado do Sistema</h2>
          {systemState ? (
            <div className="tbl-wrap">
              <table className="tbl">
                <tbody>
                  <tr><td>Status</td><td className="mono">{systemState.status}</td></tr>
                  <tr><td>Uptime</td><td className="mono">{Math.floor(systemState.uptime_sec / 60)}m {systemState.uptime_sec % 60}s</td></tr>
                  <tr><td>Clientes WS</td><td className="mono">{systemState.ws_clients}</td></tr>
                  <tr><td>MT5</td><td><span className={`chip ${systemState.mt5_connected ? 'ok' : 'warn'}`}>{systemState.mt5_connected ? 'Conectado' : 'Desconectado'}</span></td></tr>
                  <tr><td>IA</td><td><span className={`chip ${systemState.ai_enabled ? 'primary' : ''}`}>{systemState.ai_enabled ? 'Ativa' : 'Inativa'}</span></td></tr>
                  <tr><td>Eventos recentes</td><td className="mono">{systemState.recent_events}</td></tr>
                </tbody>
              </table>
            </div>
          ) : (
            <div className="placeholder">
              <div className="ph-icon">⏳</div>
              <span>Aguardando primeiro SystemState do Core...</span>
            </div>
          )}
        </div>

        <div className="card">
          <h2>Conta MT5</h2>
          {account ? (
            <div className="tbl-wrap">
              <table className="tbl">
                <tbody>
                  <tr><td>Login</td><td className="mono">{account.login}</td></tr>
                  <tr><td>Servidor</td><td>{account.server}</td></tr>
                  <tr><td>Moeda</td><td>{account.currency}</td></tr>
                  <tr><td>Alavancagem</td><td className="mono">1:{account.leverage}</td></tr>
                  <tr><td>Margem</td><td className="mono">{fmt(account.margin)}</td></tr>
                  <tr><td>Margem livre</td><td className="mono">{fmt(account.free_margin)}</td></tr>
                  <tr><td>Negociação</td><td><span className={`chip ${account.trade_allowed ? 'ok' : 'warn'}`}>{account.trade_allowed ? 'Permitida' : 'Bloqueada'}</span></td></tr>
                </tbody>
              </table>
            </div>
          ) : (
            <div className="placeholder">
              <div className="ph-icon">🔌</div>
              <span>Sem conta conectada. Configure o MT5 na aba Robô.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
