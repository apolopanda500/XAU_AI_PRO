import { useCallback, useEffect, useRef, useState } from 'react';
import { apiBase } from '../../lib/api';
import { useAppStore } from '../../hooks/useAppStore';

const API = `${apiBase()}`;

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
  const selectedSymbol = useAppStore((s) => s.selectedSymbol);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [gatewayLatencyMs, setGatewayLatencyMs] = useState<number | null>(null);
  const [latencySamples, setLatencySamples] = useState<number[]>([]);
  const requestInFlight = useRef(false);

  const fmt = (v: number | undefined | null, decimals = settings.precision) =>
    v == null ? '--' : v.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

  const quote = quotes.find((item) => item.symbol === selectedSymbol) ?? quotes[0];
  const quoteAgeSec = quote ? Math.max(0, Math.floor((Date.now() - new Date(quote.timestamp).getTime()) / 1000)) : null;
  const exposure = positions.reduce((sum, item) => sum + (Number(item.profit) || 0), 0);

  const refreshRealData = useCallback(async () => {
    if (requestInFlight.current) return;
    requestInFlight.current = true;
    setRefreshing(true);
    setError('');
    const startedAt = performance.now();
    try {
      const [statusResponse, quoteResponse] = await Promise.all([
        fetch(`${API}/api/status`, { signal: AbortSignal.timeout(5000) }),
        fetch(`${API}/api/mt5/quotes?symbols=${encodeURIComponent(selectedSymbol || 'BTCUSDT')}`, { signal: AbortSignal.timeout(5000) }),
      ]);
      const latency = Math.round(performance.now() - startedAt);
      setGatewayLatencyMs(latency);
      setLatencySamples((previous) => [...previous, latency].slice(-20));
      if (!statusResponse.ok) throw new Error(`MT5 HTTP ${statusResponse.status}`);
      const data = await statusResponse.json() as { terminal_connected?: boolean; history_count?: number; account?: Record<string, unknown>; positions?: Array<Record<string, unknown>> };
      setSystemState({ status: data.terminal_connected ? 'operacional' : 'offline', uptime_sec: 0, ws_clients: 0, mt5_connected: Boolean(data.terminal_connected), ai_enabled: false, ai_age_sec: 0, recent_events: Number(data.history_count ?? 0) });
      if (data.account) {
        const a = data.account;
        setAccount({
          login: String(a.login ?? ''), balance: Number(a.balance ?? 0), equity: Number(a.equity ?? 0),
          margin: Number(a.margin ?? 0), free_margin: Number(a.free_margin ?? a.margin_free ?? 0),
          leverage: String(a.leverage ?? 0), server: String(a.server ?? ''), currency: String(a.currency ?? ''),
          profit: Number(a.profit ?? 0), trade_allowed: Boolean(a.trade_allowed),
        });
      }
      if (Array.isArray(data.positions)) {
        setPositions(data.positions.map((p) => ({
          ticket: Number(p.ticket ?? 0), symbol: String(p.symbol ?? ''), side: String(p.side ?? p.type ?? ''), volume: Number(p.volume ?? 0),
          open_price: Number(p.open_price ?? p.price_open ?? 0), current_price: Number(p.current_price ?? p.price_current ?? 0),
          sl: Number(p.sl ?? p.sl_price ?? 0), tp: Number(p.tp ?? p.tp_price ?? 0), profit: Number(p.profit ?? 0), swap: Number(p.swap ?? 0), commission: Number(p.commission ?? 0),
          open_time: String(p.open_time ?? ''), magic: Number(p.magic ?? 0), comment: String(p.comment ?? ''),
        })));
      }
      const quotePayload = await quoteResponse.json() as { quotes?: Array<{ symbol: string; bid: number; ask: number; last: number; volume: number; high: number; low: number; change_pct: number; timestamp: string; source: string }>; errors?: Array<{ symbol: string; error: string }> };
      const rawQuote = quotePayload.quotes?.[0];
      if (rawQuote) addQuote({ ...rawQuote, price: rawQuote.last || (rawQuote.bid + rawQuote.ask) / 2, change: rawQuote.change_pct, spread: rawQuote.ask - rawQuote.bid, digits: 2, point: 0.01 });
      if (quotePayload.errors?.length) setError(`Cotação indisponível: ${quotePayload.errors[0].error}`);
      setLastRefresh(new Date().toLocaleTimeString('pt-BR'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'MT5 indisponível');
    } finally {
      setRefreshing(false);
      requestInFlight.current = false;
    }
  }, [addQuote, selectedSymbol, setAccount, setPositions, setSystemState]);

  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    const cycle = async () => {
      if (!active) return;
      if (document.visibilityState === 'visible') await refreshRealData();
      if (active && settings.dashboardAutoRefresh) timer = window.setTimeout(cycle, Math.max(5000, settings.dashboardRefreshMs));
    };
    void cycle();
    return () => { active = false; if (timer) window.clearTimeout(timer); };
  }, [refreshRealData, settings.dashboardAutoRefresh, settings.dashboardRefreshMs]);

  const statusText = systemState?.mt5_connected && wsConnected ? 'Operacional' : 'Atenção necessária';
  const averageLatency = latencySamples.length ? Math.round(latencySamples.reduce((sum, value) => sum + value, 0) / latencySamples.length) : null;

  return (
    <div className="dashboard-tab">
      <div className="page-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
        <div>
          <h1>Painel</h1>
          <span className="muted">Visão operacional com dados reais do Core e MT5</span>
        </div>
        <div className="btn-row">
        </div>
      </div>

      {error && <div className="placeholder" role="status"><strong>Uma fonte está indisponível</strong><span className="muted">{error}. As demais fontes continuam disponíveis; nenhum dado simulado é exibido.</span></div>}

      <div className="grid cols-4">
        <div className="card"><div className="kpi-label">Saldo real</div><div className="kpi-value">{fmt(account?.balance)}</div><div className="kpi-sub">{account?.currency ?? 'Sem conta'}</div></div>
        <div className="card"><div className="kpi-label">Equidade real</div><div className="kpi-value">{fmt(account?.equity)}</div><div className="kpi-sub">Flutuante: <span className={(account?.profit ?? 0) >= 0 ? 'pos' : 'neg'}>{fmt(account?.profit)}</span></div></div>
        <div className="card"><div className="kpi-label">Posições abertas</div><div className="kpi-value">{positions.length}</div><div className="kpi-sub">Resultado: <span className={exposure >= 0 ? 'pos' : 'neg'}>{fmt(exposure)}</span></div></div>
        <div className="card"><div className="kpi-label">Estado operacional</div><div className="kpi-value"><span className={`chip ${statusText === 'Operacional' ? 'ok' : 'warn'}`}>{statusText}</span></div><div className="kpi-sub">WS {wsConnected ? 'online' : 'offline'} · Core {systemState?.status ?? 'sem telemetria'}</div></div>
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
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><h2>Inventário operacional</h2><span className="muted">somente dados reais</span></div>
        {positions.length ? <div className="tbl-wrap"><table className="tbl"><thead><tr><th>Ticket</th><th>Ativo</th><th>Lado</th><th>Volume</th><th>Entrada</th><th>Atual</th><th>SL / TP</th><th>Resultado</th></tr></thead><tbody>{positions.map((p) => <tr key={p.ticket}><td className="mono">{p.ticket}</td><td><strong>{p.symbol}</strong></td><td><span className={`chip ${p.side.toUpperCase().includes('BUY') ? 'ok' : 'danger'}`}>{p.side}</span></td><td className="mono">{p.volume}</td><td className="mono">{fmt(p.open_price)}</td><td className="mono">{fmt(p.current_price)}</td><td className="mono">{fmt(p.sl)} / {fmt(p.tp)}</td><td className={p.profit >= 0 ? 'pos' : 'neg'}>{fmt(p.profit)}</td></tr>)}</tbody></table></div> : <div className="placeholder"><span>Nenhuma posição aberta informada pelo MT5.</span><span className="muted">O inventário permanece vazio quando não há conexão ou posições reais.</span></div>}
        <div className="grid cols-4" style={{ marginTop: 12 }}><div><span className="kpi-label">Exposição flutuante</span><div className={exposure >= 0 ? 'pos' : 'neg'}>{fmt(exposure)}</div></div><div><span className="kpi-label">Margem usada</span><div>{fmt(account?.margin)}</div></div><div><span className="kpi-label">Margem livre</span><div>{fmt(account?.free_margin)}</div></div><div><span className="kpi-label">Ação recomendada</span><div className="muted">{!account ? 'Conectar MT5' : !systemState?.mt5_connected ? 'Verificar terminal' : positions.some((p) => !p.sl || !p.tp) ? 'Revisar proteção SL/TP' : 'Monitorar'}</div></div></div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><h2>Diagnóstico da conexão</h2><span className="muted">{lastRefresh ? `Atualizado às ${lastRefresh}` : 'Ainda não atualizado manualmente'}</span></div>
        <div className="grid cols-4">
          <div><span className="kpi-label">Bridge MT5</span><div><span className={`chip ${systemState?.mt5_connected ? 'ok' : 'warn'}`}>{systemState?.mt5_connected ? 'Conectado' : 'Sem resposta'}</span></div></div>
          <div><span className="kpi-label">WebSocket Core</span><div><span className={`chip ${wsConnected ? 'ok' : 'danger'}`}>{wsConnected ? 'Online' : 'Offline'}</span></div></div>
          <div><span className="kpi-label">Latência gateway</span><div><span className={`chip ${gatewayLatencyMs != null && gatewayLatencyMs < 1000 ? 'ok' : 'warn'}`}>{gatewayLatencyMs == null ? 'Sem leitura' : `${gatewayLatencyMs} ms`}</span></div></div>
          <div><span className="kpi-label">Média últimos ciclos</span><div className="mono">{averageLatency == null ? '--' : `${averageLatency} ms`}</div></div>
          <div><span className="kpi-label">Idade da cotação</span><div><span className={`chip ${quoteAgeSec != null && quoteAgeSec <= 10 ? 'ok' : 'warn'}`}>{quoteAgeSec == null ? 'Sem dado' : `${quoteAgeSec}s`}</span></div></div>
          <div><span className="kpi-label">Uptime Core</span><div className="mono">{systemState ? `${Math.floor(systemState.uptime_sec / 60)}m ${systemState.uptime_sec % 60}s` : '--'}</div></div>
        </div>
      </div>
    </div>
  );
}
