import { useQuery } from '@tanstack/react-query';
import { apiBase } from '../../lib/api';

const API = `${apiBase()}`;
const sources = [['MT5', 'Forex/CFD', 'other'], ['MEXC', 'Spot/Futuros', 'crypto-spot'], ['Binance', 'Spot/Futuros', 'crypto-spot']] as const;
type Row = { name: string; market: string; status: string; balance: string; available: string; currency: string; positions: string; pnl: string };
const empty = (name: string, market: string): Row => ({ name, market, status: 'Aguardando', balance: '--', available: '--', currency: name === 'MT5' ? 'USD' : 'USDT', positions: '--', pnl: '--' });
const money = (v: unknown) => { const n = Number(v); return Number.isFinite(n) && n >= 0 && n < 1e15 ? n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '--'; };

// Lê conta + posições de todas as fontes em paralelo (mesma lógica validada no ciclo v1.2.3).
async function loadPortfolio(): Promise<Row[]> {
  return Promise.all(sources.map(async ([name, market, qm]) => {
    const broker = name === 'MT5' ? 'mt5' : name.toLowerCase();
    try {
      const [a, p] = await Promise.all([
        fetch(`${API}/api/universal/account?broker=${broker}&market=${qm}`, { signal: AbortSignal.timeout(8000) }),
        fetch(`${API}/api/universal/positions?broker=${broker}&market=${qm}`, { signal: AbortSignal.timeout(8000) }),
      ]);
      const ad = await a.json() as { ok?: boolean; account?: Record<string, unknown> };
      const pd = await p.json().catch(() => ({})) as { positions?: unknown[] };
      if (!a.ok || !ad.ok) throw new Error();
      const ac = ad.account ?? {};
      return {
        name, market, status: 'Conectada',
        balance: money(ac.balance ?? ac.totalWalletBalance ?? ac.equity),
        available: money(ac.available ?? ac.availableBalance ?? ac.free_margin),
        currency: String(ac.currency ?? (name === 'MT5' ? 'USD' : 'USDT')),
        positions: p.ok && Array.isArray(pd.positions) ? String(pd.positions.length) : '--',
        pnl: p.ok && Array.isArray(pd.positions) ? money((pd.positions as Array<Record<string, unknown>>).reduce((sum, position) => sum + (Number(position.profit) || 0), 0)) : '--',
      };
    } catch { return { ...empty(name, market), status: 'Indisponível' }; }
  }));
}

export default function PortfolioHomeSafe() {
  const q = useQuery({ queryKey: ['portfolio'], queryFn: loadPortfolio, refetchInterval: 10000, staleTime: 8000, retry: 1 });
  const rows = q.data ?? sources.map(([n, m]) => empty(n, m));
  const updated = q.dataUpdatedAt ? new Date(q.dataUpdatedAt).toLocaleTimeString('pt-BR') : '--:--:--';
  const busy = q.isFetching;
  const connected = rows.filter((r) => r.status === 'Conectada').length;
  return <div className="portfolio-page">
    <div className="page-head"><div><h1>Patrimônio</h1><span className="muted">Contas, carteiras e saldos em uma única leitura</span></div><div className="btn-row"><span className="chip ok">Ao vivo · {updated}</span><button className="btn primary" type="button" onClick={() => void q.refetch()} disabled={busy}>{busy ? 'Atualizando…' : 'Atualizar saldos'}</button></div></div>
    <div className="metrics-grid"><div className="card metric-card"><span className="muted">Contas conectadas</span><strong>{connected}/{rows.length}</strong><small>fontes disponíveis</small></div><div className="card metric-card"><span className="muted">Saldo consolidado</span><strong>--</strong><small>moedas não convertidas</small></div><div className="card metric-card"><span className="muted">PNL realizado</span><strong>--</strong><small>histórico por conexão</small></div><div className="card metric-card"><span className="muted">Saques</span><strong className="warn-text">Bloqueados</strong><small>proteção da aplicação</small></div></div>
    <div className="card compact-card"><h2>Contas e carteiras</h2><div className="table-scroll"><table className="tbl compact-table"><thead><tr><th>Conta</th><th>Mercado</th><th>Estado</th><th>Saldo total</th><th>Disponível</th><th>Moeda</th><th>Posições</th><th>Saques</th></tr></thead><tbody>{rows.map((r) => <tr key={r.name}><td><strong>{r.name}</strong></td><td>{r.market}</td><td><span className={`chip ${r.status === 'Conectada' ? 'ok' : 'warn'}`}>{r.status}</span></td><td className="num">{r.balance}</td><td className="num">{r.available}</td><td>{r.currency}</td><td className="num">{r.positions}</td><td><span className="chip warn">Bloqueados</span></td></tr>)}</tbody></table></div></div>
    <div className="hint">Atualização automática a cada 10 segundos com cache compartilhado entre abas. Nenhuma moeda é convertida.</div>
  </div>;
}
