// Histórico de operações, uma tabela só.
//
// O QUE FOI REMOVIDO E POR QUÊ
// ==============================
// A aba tinha DUAS tabelas e um bloco "PnL da seleção": a tabela de
// operações e, acima, um cumulativo por período; mais chips por ativo que
// marcavam linhas para somar um subconjunto. Três Ways de ler a mesma
// coisa, com o PnL repetido em cada uma. A seleção tambémembaçava a leitura:
// clicar numa linha mudava três números no topo sem indicar qual conta
// estava selecionada.
//
// Agora é uma tabela. O cumulativo por período continua, porque compara
// janelas e não é repetição.
//
// COMPATIBILIDADE COM OUTRAS CORRETORAS
// =====================================
// `all` faz o hook consultar MT5 e as exchanges em paralelo e juntar o que
// respondeu. Bybit e OKX entraram na lista: o backend já tem cliente para
// os dois (ver capabilities). Para exchange, o símbolo é obrigatório —
// não há como listar histórico sem saber o par.
import { useMemo, useState } from 'react';
import { fmtNum, fmtSigned, clsPnl } from '../../lib/format';
import { useHistorico, resumir, toNumber, dealDate, type Deal } from '../../lib/historico';
import '../../theme/history.css';
// Carregado por último: sobrescreve as celulas de 40px do history.css.
import '../../theme/history-grid.css';

const BROKERS: Array<{ value: string; label: string }> = [
  { value: 'all', label: 'Todas' },
  { value: 'mt5', label: 'MT5' },
  { value: 'binance', label: 'Binance' },
  { value: 'mexc', label: 'MEXC' },
  { value: 'bybit', label: 'Bybit' },
  { value: 'okx', label: 'OKX' },
];

const limits: Record<string, number> = { '1': 100, '7': 200, '15': 300, '30': 500, '90': 500, '365': 500, '0': 500 };
const periods: Record<string, string> = { '1': 'Hoje', '7': '7 dias', '15': '15 dias', '30': '30 dias', '90': '90 dias', '365': '1 ano', '0': 'Tudo' };

const num = fmtNum;
const money = (v: unknown) => fmtSigned(v, 2);
const cls = (v: number) => (v > 0 ? 'acum-pos' : v < 0 ? 'acum-neg' : '');
const date = (v?: string) => { if (!v) return '--'; const d = new Date(v); return Number.isNaN(d.getTime()) ? v : d.toLocaleString('pt-BR'); };
const brokerTone = (broker?: string) => (broker === 'mt5' ? 'mt5' : broker === 'binance' ? 'warn' : broker === 'mexc' ? 'ok' : 'neutral');

export default function HistoryTab() {
  const [broker, setBroker] = useState('all');
  const [symbol, setSymbol] = useState('');
  const [days, setDays] = useState('1');
  // Fonte única de deals: o Analytics montado abaixo usa o mesmo hook, então
  // as duas seções não podem divergir em número.
  const { deals, erro: error, status, updatedAt, recarregar: load, loading } = useHistorico({ broker, symbol, days });

  const rows = useMemo(() => deals.slice(0, limits[days] ?? 500), [deals, days]);
  const acc = resumir;
  const tot = acc(rows);

  const perPeriod = Object.keys(periods)
    .filter((k) => k !== days && k !== '0')
    .map((k) => {
      const ini = new Date(Date.now() - Number(k) * 86400000).toISOString();
      const pool = rows.filter((d) => {
        const when = dealDate(d);
        if (!when) return false;
        const t = new Date(when);
        return !Number.isNaN(t.getTime()) && t >= new Date(ini);
      });
      return { key: k, label: periods[k], ...acc(pool) };
    });

  const exportCsv = () => {
    const cols = ['ID/Ticket', 'Corretora', 'Ativo', 'Lado', 'Quantidade', 'Preco', 'PNL', 'Data'];
    const linhas = rows.map((r) => [r.id, r.broker, r.symbol, r.side, r.quantity ?? r.volume, r.price, r.realizedPnl, r.executedAt ?? r.close_time]);
    const csv = [cols, ...linhas].map((linha) => linha.join(';')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'historico-universal.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main className="history-page quantum-history">
      <div className="page-head">
        <div>
          <span className="eyebrow">REGISTRO UNIVERSAL</span>
          <h1>Histórico</h1>
          <span className="muted">Execuções reais de todas as corretoras</span>
        </div>
        <div className="btn-row">
          <button className="btn ghost" onClick={exportCsv} disabled={!rows.length}>Exportar CSV</button>
          <button className="btn primary" type="button" onClick={() => void load()} disabled={loading}>
            {loading ? 'Lendo…' : 'Atualizar'}
          </button>
        </div>
      </div>

      <div className="card compact-card history-filter-card">
        <div className="history-filters">
          <label className="field">
            Corretora
            <select value={broker} onChange={(e) => setBroker(e.target.value)}>
              {BROKERS.map((b) => <option key={b.value} value={b.value}>{b.label}</option>)}
            </select>
          </label>
          <label className="field">
            Ativo
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder={broker === 'mt5' ? 'Opcional (ex.: XAUUSD)' : 'Obrigatório (ex.: BTCUSDT)'}
            />
          </label>
          <label className="field">
            Período
            <select value={days} onChange={(e) => setDays(e.target.value)}>
              <option value="1">Hoje</option>
              <option value="7">7 dias</option>
              <option value="15">15 dias</option>
              <option value="30">30 dias</option>
              <option value="90">90 dias</option>
              <option value="365">1 ano</option>
              <option value="0">Tudo</option>
            </select>
          </label>
          <div className="history-count">
            <span className="muted">Exibindo</span>
            <strong>{rows.length}</strong>
            {updatedAt !== '--:--:--' && <span className="muted">· {updatedAt}</span>}
          </div>
        </div>
        {error && <div className="placeholder" role="status">{error}</div>}
        <div className="history-status-row"><span className="muted">Fontes: {status}</span></div>
      </div>

      <div className="metrics-grid">
        <div className="card metric-card">
          <span className="muted">PnL do período</span>
          <strong className={cls(tot.total)}>{money(tot.total)}</strong>
          <small>{tot.qty} operações</small>
        </div>
        <div className="card metric-card">
          <span className="muted">Ganhos / Perdas</span>
          <strong>{tot.wins} / {tot.losses}</strong>
          <small>Acerto {tot.winRate.toFixed(1)}%</small>
        </div>
        <div className="card metric-card">
          <span className="muted">Bruto</span>
          <strong>{money(tot.grossWin)} / {money(-tot.grossLoss)}</strong>
          <small>{tot.profitFactor === Infinity ? 'Sem perdas' : `Fator ${tot.profitFactor.toFixed(2)}`}</small>
        </div>
      </div>

      <div className="card compact-card acum-table-card">
        <h2>Por período</h2>
        <div className="table-scroll">
          <table className="tbl compact-table history-grid">
            <thead>
              <tr>
                <th>Período</th><th className="num">Operações</th><th className="num">PnL</th>
                <th className="num">Ganhos</th><th className="num">Perdas</th>
                <th className="num">Acerto</th><th className="num">Fator</th>
              </tr>
            </thead>
            <tbody>
              {perPeriod.filter((p) => p.qty > 0).map((p) => (
                <tr key={p.key}>
                  <td>{p.label}</td>
                  <td className="num">{p.qty}</td>
                  <td className={`num ${cls(p.total)}`}>{money(p.total)}</td>
                  <td className="num acum-pos">{p.wins}</td>
                  <td className="num acum-neg">{p.losses}</td>
                  <td className="num">{p.winRate.toFixed(0)}%</td>
                  <td className="num">{p.profitFactor === Infinity ? '∞' : p.profitFactor.toFixed(2)}</td>
                </tr>
              ))}
              {perPeriod.every((p) => p.qty === 0) && <tr><td colSpan={7}>Sem operações nos demais períodos.</td></tr>}
            </tbody>
          </table>
        </div>
        <p className="csv-note">Calculado sobre os registros do filtro atual. Use "Tudo" para o acumulado completo.</p>
      </div>

      <div className="card compact-card table-scroll history-table-card">
        <table className="tbl compact-table history-grid history-deals">
          <caption className="sr-only">Execuções reais por corretora</caption>
          <thead>
            <tr>
              <th>Data</th><th>Ativo</th><th>Lado</th><th>Corretora</th>
              <th className="num">Quantidade</th><th className="num">Preço</th><th className="num">PnL</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r: Deal, i) => {
              const p = toNumber(r.realizedPnl);
              const value = Number.isFinite(p) ? p : 0;
              return (
                <tr key={`${r.id}-${i}`} className={value > 0 ? 'history-row-positive' : value < 0 ? 'history-row-negative' : ''}>
                  <td className="history-when">{date(r.executedAt ?? r.close_time)}</td>
                  <td><strong>{r.symbol ?? '--'}</strong></td>
                  <td><span className={`chip ${/buy/i.test(String(r.side)) ? 'ok' : /sell/i.test(String(r.side)) ? 'warn' : 'neutral'}`}>{r.side ?? '--'}</span></td>
                  <td><span className={`chip ${brokerTone(r.broker)}`}>{(r.broker ?? '--').toUpperCase()}</span></td>
                  <td className="num">{num(r.quantity ?? r.volume, 4)}</td>
                  <td className="num">{num(r.price, 5)}</td>
                  <td className={`num ${value > 0 ? 'pos' : value < 0 ? 'neg' : ''}`}>{num(r.realizedPnl, 2)}</td>
                </tr>
              );
            })}
            {!rows.length && !error && <tr><td colSpan={7}>Nenhum registro no período.</td></tr>}
          </tbody>
        </table>
      </div>
    </main>
  );
}
