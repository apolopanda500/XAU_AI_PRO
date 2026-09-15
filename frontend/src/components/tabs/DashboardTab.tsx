import { useCallback, useEffect, useState } from 'react';
import { useAppStore } from '../../hooks/useAppStore';

const MT5 = 'http://127.0.0.1:9001';

export default function DashboardTab() {
  const account = useAppStore((s) => s.account);
  const systemState = useAppStore((s) => s.systemState);
  const wsConnected = useAppStore((s) => s.wsConnected);
  const positions = useAppStore((s) => s.positions);
  const quotes = useAppStore((s) => s.quotes);
  const settings = useAppStore((s) => s.settings);
  const setAccount = useAppStore((s) => s.setAccount);
  const setPositions = useAppStore((s) => s.setPositions);
  const setSystemState = useAppStore((s) => s.setSystemState);
  const addQuote = useAppStore((s) => s.addQuote);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);
  const [error, setError] = useState('');

  const fmt = (v: number | undefined | null, decimals = settings.precision) =>
    v == null ? '--' : v.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

  const quote = quotes.find((item) => item.symbol === 'XAUUSD');
  const exposure = positions.reduce((sum, item) => sum + (Number(item.profit) || 0), 0);

  const refreshRealData = useCallback(async () => {
    setRefreshing(true);
    setError('');
    try {
      const [statusResponse, quoteResponse] = await Promise.all([
        fetch(`${MT5}/api/status`, { signal: AbortSignal.timeout(5000) }),
        fetch(`${MT5}/api/mt5/quote?symbol=XAUUSD`, { signal: AbortSignal.timeout(5000) }),
      ]);
      if (!statusResponse.ok || !quoteResponse.ok) throw new Error(`MT5 HTTP ${statusResponse.status}/${quoteResponse.status}`);
      const data = await statusResponse.json() as { terminal_connected?: boolean; history_count?: number; account?: Record<string, unknown>; positions?: Array<Record<string, unknown>> };
      if (data.account) {
        const a = data.account;
        setAccount({
          login: String(a.login ?? ''), balance: Number(a.balance ?? 0), equity: Number(a.equity ?? 0),
          margin: Number(a.margin ?? 0), free_margin: Number(a.free_margin ?? a.margin_free ?? 0),
          leverage: String(a.leverage ?? 0), server: String(a.server ?? ''), currency: String(a.currency ?? ''),
          profit: Number(a.profit ?? 0), trade_allowed: Boolean(a.trade_allowed),
        });
        setSystemState({ status: data.terminal_connected ? 'operacional' : 'offline', uptime_sec: 0, ws_clients: 0, mt5_connected: Boolean(data.terminal_connected), ai_enabled: false, ai_age_sec: 0, recent_events: Number(data.history_count ?? 0) });
      }
      if (Array.isArray(data.positions)) {
        setPositions(data.positions.map((p) => ({
          ticket: Number(p.ticket ?? 0), symbol: String(p.symbol ?? ''), side: String(p.side ?? p.type ?? ''), volume: Number(p.volume ?? 0),
          open_price: Number(p.open_price ?? p.price_open ?? 0), current_price: Number(p.current_price ?? p.price_current ?? 0),
          sl: Number(p.sl ?? p.sl_price ?? 0), tp: Number(p.tp ?? p.tp_price ?? 0), profit: Number(p.profit ?? 0), swap: Number(p.swap ?? 0), commission: Number(p.commission ?? 0),
          open_time: String(p.open_time ?? ''), magic: Number(p.magic ?? 0), comment: String(p.comment ?? ''),
        })));
      }
      const rawQuote = await quoteResponse.json() as { symbol: string; bid: number; ask: number; last: number; volume: number; high: number; low: number; change_pct: number; timestamp: string; source: string };
      addQuote({ ...rawQuote, price: rawQuote.last || (rawQuote.bid + rawQuote.ask) / 2, change: rawQuote.change_pct, spread: rawQuote.ask - rawQuote.bid, digits: 2, point: 0.01 });
      setLastRefresh(new Date().toLocaleTimeString('pt-BR'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'MT5 indisponível');
    } finally {
      setRefreshing(false);
    }
  }, [addQuote, setAccount, setPositions, setSystemState]);

  useEffect(() => {
    void refreshRealData();
    const timer = window.setInterval(() => void refreshRealData(), 2000);
    return () => window.clearInterval(timer);
  }, [refreshRealData]);

  const statusText = systemState?.mt5_connected && wsConnected ? 'Operacional' : 'Atenção necessária';

  return (
    <div className="dashboard-tab">
      <div className="page-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
        <div>
          <h1>Painel</h1>
          <span className="muted">Visão operacional com dados reais do Core e MT5</span>
        </div>
        <div className="btn-row">
          <button className="btn ghost" type="button" onClick={() => setActiveTab('market')}>Ver mercado</button>
          <button className="btn primary" type="button" onClick={refreshRealData} disabled={refreshing}>
            {refreshing ? 'Atualizando...' : 'Atualizar dados reais'}
          </button>
        </div>
      </div>

      {error && <div className="placeholder" role="alert"><strong>Fonte MT5 indisponível</strong><span className="muted">{error}. Nenhum dado simulado é exibido.</span></div>}

      <div className="grid cols-4">
        <div className="card"><div className="kpi-label">Saldo real</div><div className="kpi-value">{fmt(account?.balance)}</div><div className="kpi-sub">{account?.currency ?? 'Sem conta'}</div></div>
        <div className="card"><div className="kpi-label">Equidade real</div><div className="kpi-value">{fmt(account?.equity)}</div><div className="kpi-sub">Flutuante: <span className={(account?.profit ?? 0) >= 0 ? 'pos' : 'neg'}>{fmt(account?.profit)}</span></div></div>
        <div className="card"><div className="kpi-label">Posições abertas</div><div className="kpi-value">{positions.length}</div><div className="kpi-sub">Resultado: <span className={exposure >= 0 ? 'pos' : 'neg'}>{fmt(exposure)}</span></div></div>
        <div className="card"><div className="kpi-label">Estado operacional</div><div className="kpi-value"><span className={`chip ${statusText === 'Operacional' ? 'ok' : 'warn'}`}>{statusText}</span></div><div className="kpi-sub">WS {wsConnected ? 'online' : 'offline'} · Core {systemState?.status ?? 'aguardando'}</div></div>
      </div>

      <div className="grid cols-2" style={{ marginTop: 14 }}>
        <div className="card">
          <h2>Mercado em tempo real</h2>
          {quote ? <div className="tbl-wrap"><table className="tbl"><tbody>
            <tr><td>Ativo</td><td className="mono">{quote.symbol}</td></tr>
            <tr><td>Bid / Ask</td><td className="mono">{fmt(quote.bid, quote.digits)} / {fmt(quote.ask, quote.digits)}</td></tr>
            <tr><td>Spread</td><td className="mono">{fmt(quote.spread, quote.digits)}</td></tr>
            <tr><td>Fonte</td><td><span className="chip ok">{quote.source}</span></td></tr>
            <tr><td>Última atualização</td><td className="mono">{new Date(quote.timestamp).toLocaleTimeString('pt-BR')}</td></tr>
          </tbody></table></div> : <div className="placeholder"><span>Aguardando cotação real do MT5/Core.</span><span className="muted">Dados simulados bloqueados.</span></div>}
        </div>

        <div className="card">
          <h2>Conta e proteção</h2>
          {account ? <div className="tbl-wrap"><table className="tbl"><tbody>
            <tr><td>Login / servidor</td><td className="mono">{account.login} · {account.server}</td></tr>
            <tr><td>Margem livre</td><td className="mono">{fmt(account.free_margin)}</td></tr>
            <tr><td>Alavancagem</td><td className="mono">1:{account.leverage}</td></tr>
            <tr><td>Negociação</td><td><span className={`chip ${account.trade_allowed ? 'ok' : 'warn'}`}>{account.trade_allowed ? 'Permitida' : 'Bloqueada'}</span></td></tr>
          </tbody></table></div> : <div className="placeholder"><span>Conta MT5 não disponível.</span><span className="muted">Conecte o terminal e atualize os dados.</span></div>}
          <div className="btn-row" style={{ marginTop: 14 }}><button className="btn ghost" type="button" onClick={() => setActiveTab('robot')}>Configurar MT5</button><button className="btn ghost" type="button" onClick={() => setActiveTab('system')}>Ver monitor</button></div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><h2>Diagnóstico da conexão</h2><span className="muted">{lastRefresh ? `Atualizado às ${lastRefresh}` : 'Ainda não atualizado manualmente'}</span></div>
        <div className="grid cols-4">
          <div><span className="kpi-label">Bridge MT5</span><div><span className={`chip ${systemState?.mt5_connected ? 'ok' : 'warn'}`}>{systemState?.mt5_connected ? 'Conectado' : 'Aguardando'}</span></div></div>
          <div><span className="kpi-label">WebSocket Core</span><div><span className={`chip ${wsConnected ? 'ok' : 'danger'}`}>{wsConnected ? 'Online' : 'Offline'}</span></div></div>
          <div><span className="kpi-label">IA</span><div><span className="chip">{systemState?.ai_enabled ? 'Ativa' : 'Desligada'}</span></div></div>
          <div><span className="kpi-label">Uptime Core</span><div className="mono">{systemState ? `${Math.floor(systemState.uptime_sec / 60)}m ${systemState.uptime_sec % 60}s` : '--'}</div></div>
        </div>
      </div>
    </div>
  );
}
