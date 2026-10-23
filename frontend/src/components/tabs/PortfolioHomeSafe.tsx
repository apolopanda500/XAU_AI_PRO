import { useQuery } from '@tanstack/react-query';
import { apiBase } from '../../lib/api';
import { brokerLabel, MARKET_LABELS } from '../../lib/brokerCatalog';
import { clsPnl, fmtSigned } from '../../lib/format';

// Base resolvida por chamada (13/10/2026), nunca congelada no topo do modulo.

/**
 * Fontes do patrimonio.
 *
 * Os ROTULOS vem do catalogo (`brokerCatalog`), para que o nome da corretora
 * seja o mesmo em todas as telas. A lista de corretoras/missoes continua
 * explicita porque `market` NAO e decorativo na chamada: no MT5 a conta e
 * agregada e o mercado correto e `other` (pedir `forex` filtraria as posicoes
 * so para forex, escondendo metais e cripto); nas exchanges a leitura de conta
 * exige `crypto-spot`. Derivar o mercado do primeiro item do catalogo trocaria
 * o silencio de uma linha por uma posicao FALTANDO na soma — e aqui a regra do
 * projeto vale: dois lados do mesmo dado nao podem discordar do nome.
 */
const SOURCES: ReadonlyArray<{ broker: string; market: string }> = [
  { broker: 'mt5', market: 'other' },
  { broker: 'mexc', market: 'crypto-spot' },
  { broker: 'binance', market: 'crypto-spot' },
  { broker: 'bybit', market: 'crypto-spot' },
  { broker: 'okx', market: 'crypto-spot' },
];
const sources = SOURCES.map(
  (s) => [brokerLabel(s.broker), MARKET_LABELS[s.market] ?? s.market, s.market, s.broker] as const,
);

type Row = {
  name: string;
  market: string;
  status: string;
  balance: string;
  available: string;
  currency: string;
  positions: string;
  pnl: number | null;
};
const empty = (name: string, market: string, broker: string): Row => ({
  name,
  market,
  status: 'Aguardando',
  balance: '--',
  available: '--',
  currency: broker === 'mt5' ? 'USD' : 'USDT',
  positions: '--',
  pnl: null,
});
/*
  SALDO PODE SER NEGATIVO, E O `--` ESCONDIA ISSO (23/10/2026)

  A versao anterior exigia `n >= 0` para formatar. Conta em margem pode ficar
  negativa, e o operador lia `--` - que significa "o gateway nao mandou" em
  toda esta app. O mesmo `--` aparecia no resultado aberto, entao uma posicao
  perdedora era indistinguivel de uma conta sem dados. Aqui o numero sempre
  aparece quando o gateway o entregou; quem decide o sinal e o valor.
*/
const money = (v: unknown) => {
  const n = Number(v);
  return Number.isFinite(n) && Math.abs(n) < 1e15
    ? n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : '--';
};

// Lê conta + posições de todas as fontes em paralelo (mesma lógica validada no ciclo v1.2.3).
async function loadPortfolio(): Promise<Row[]> {
  return Promise.all(
    sources.map(async ([name, market, qm, broker]) => {
      try {
        const [a, p] = await Promise.all([
          fetch(`${apiBase()}/api/universal/account?broker=${broker}&market=${qm}`, {
            signal: AbortSignal.timeout(8000),
          }),
          fetch(`${apiBase()}/api/universal/positions?broker=${broker}&market=${qm}`, {
            signal: AbortSignal.timeout(8000),
          }),
        ]);
        const ad = (await a.json()) as { ok?: boolean; account?: Record<string, unknown> };
        const pd = (await p.json().catch(() => ({}))) as { positions?: unknown[] };
        if (!a.ok || !ad.ok) throw new Error();
        const ac = ad.account ?? {};
        return {
          name,
          market,
          status: 'Conectada',
          balance: money(ac.balance ?? ac.totalWalletBalance ?? ac.equity),
          available: money(ac.available ?? ac.availableBalance ?? ac.free_margin),
          currency: String(ac.currency ?? (broker === 'mt5' ? 'USD' : 'USDT')),
          positions: p.ok && Array.isArray(pd.positions) ? String(pd.positions.length) : '--',
          pnl:
            p.ok && Array.isArray(pd.positions)
              ? (pd.positions as Array<Record<string, unknown>>).reduce(
                  (sum, position) => sum + (Number(position.profit) || 0),
                  0,
                )
              : null,
        };
      } catch {
        return { ...empty(name, market, broker), status: 'Indisponível' };
      }
    }),
  );
}

export default function PortfolioHomeSafe() {
  const q = useQuery({
    queryKey: ['portfolio'],
    queryFn: loadPortfolio,
    refetchInterval: 10000,
    staleTime: 8000,
    retry: 1,
  });
  const rows = q.data ?? sources.map(([n, m, , b]) => empty(n, m, b));
  const updated = q.dataUpdatedAt
    ? new Date(q.dataUpdatedAt).toLocaleTimeString('pt-BR')
    : '--:--:--';
  const busy = q.isFetching;
  const connected = rows.filter((r) => r.status === 'Conectada').length;
  return (
    <div className="portfolio-page">
      <div className="page-head">
        <div>
          <h1>Carteira</h1>
          <span className="muted">
            Contas, saldos e carteiras de todas as corretoras em uma única leitura
          </span>
        </div>
        <div className="btn-row">
          <span className="chip ok">Ao vivo · {updated}</span>
          <button
            className="btn primary"
            type="button"
            onClick={() => void q.refetch()}
            disabled={busy}
          >
            {busy ? 'Atualizando…' : 'Atualizar saldos'}
          </button>
        </div>
      </div>
      <div className="metrics-grid">
        <div className="card metric-card">
          <span className="muted">Contas conectadas</span>
          <strong>
            {connected}/{rows.length}
          </strong>
          <small>fontes disponíveis</small>
        </div>
        <div className="card metric-card">
          <span className="muted">Saldo consolidado</span>
          <strong>--</strong>
          <small>moedas não convertidas</small>
        </div>
        <div className="card metric-card">
          <span className="muted">PNL realizado</span>
          <strong>--</strong>
          <small>histórico por conexão</small>
        </div>
        <div className="card metric-card">
          <span className="muted">Saques</span>
          <strong className="warn-text">Bloqueados</strong>
          <small>proteção da aplicação</small>
        </div>
      </div>
      <div className="card compact-card">
        <h2>Contas e carteiras</h2>
        <div className="table-scroll">
          <table className="tbl compact-table">
            <thead>
              <tr>
                <th>Conta</th>
                <th>Mercado</th>
                <th>Estado</th>
                <th className="num">Saldo total</th>
                <th className="num">Disponível</th>
                <th>Moeda</th>
                <th className="num">Posições</th>
                <th className="num">Resultado aberto</th>
                <th>Saques</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.name}>
                  <td>
                    <strong>{r.name}</strong>
                  </td>
                  <td>{r.market}</td>
                  <td>
                    <span className={`chip ${r.status === 'Conectada' ? 'ok' : 'warn'}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="num">{r.balance}</td>
                  <td className="num">{r.available}</td>
                  <td>{r.currency}</td>
                  <td className="num">{r.positions}</td>
                  <td className={`num ${r.pnl === null ? '' : clsPnl(r.pnl)}`.trim()}>
                    {r.pnl === null ? '--' : fmtSigned(r.pnl, 2)}
                  </td>
                  <td>
                    <span className="chip warn">Bloqueados</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="hint">
        Atualização automática a cada 10 segundos com cache compartilhado entre abas. Nenhuma moeda
        é convertida.
      </div>
    </div>
  );
}
