import { useState } from 'react';
import { useAppStore } from '../../hooks/useAppStore';

interface OrdemHistorico {
  ticket: number;
  simbolo: string;
  tipo: string;
  lote: number;
  precoAbertura: number;
  precoFechamento: number;
  sl?: number;
  tp?: number;
  lucro: number;
  comissao: number;
  swap: number;
  dataAbertura: string;
  dataFechamento: string;
}

const HISTORICO_MOCK: OrdemHistorico[] = [
  { ticket: 9001, simbolo: 'XAUUSD', tipo: 'compra', lote: 1.0, precoAbertura: 2330.00, precoFechamento: 2345.00, sl: 2320, tp: 2350, lucro: 150.00, comissao: -3.50, swap: -1.20, dataAbertura: '2026-01-14 09:00', dataFechamento: '2026-01-14 15:30' },
  { ticket: 9002, simbolo: 'EURUSD', tipo: 'venda', lote: 0.5, precoAbertura: 1.0900, precoFechamento: 1.0850, sl: 1.0950, tp: 1.0800, lucro: 250.00, comissao: -2.00, swap: 0, dataAbertura: '2026-01-14 10:00', dataFechamento: '2026-01-14 14:00' },
  { ticket: 9003, simbolo: 'GBPUSD', tipo: 'compra', lote: 0.3, precoAbertura: 1.2600, precoFechamento: 1.2550, sl: 1.2550, tp: 1.2700, lucro: -150.00, comissao: -1.50, swap: -0.80, dataAbertura: '2026-01-13 11:00', dataFechamento: '2026-01-13 16:00' },
  { ticket: 9004, simbolo: 'BTCUSD', tipo: 'venda', lote: 0.02, precoAbertura: 44000.00, precoFechamento: 43500.00, sl: 45000, tp: 43000, lucro: 100.00, comissao: -5.00, swap: 0, dataAbertura: '2026-01-13 14:00', dataFechamento: '2026-01-13 20:00' },
  { ticket: 9005, simbolo: 'USDJPY', tipo: 'compra', lote: 0.5, precoAbertura: 148.00, precoFechamento: 148.50, sl: 147.50, tp: 149.00, lucro: 250.00, comissao: -2.50, swap: -1.00, dataAbertura: '2026-01-12 08:00', dataFechamento: '2026-01-12 17:00' },
  { ticket: 9006, simbolo: 'XAUUSD', tipo: 'venda', lote: 0.5, precoAbertura: 2350.00, precoFechamento: 2340.00, sl: 2360, tp: 2335, lucro: 50.00, comissao: -2.00, swap: -0.50, dataAbertura: '2026-01-12 12:00', dataFechamento: '2026-01-12 18:00' },
];

export default function HistoryTab() {
  const settings = useAppStore((s) => s.settings);
  const [filtroSimbolo, setFiltroSimbolo] = useState<string>('');
  const [filtroTipo, setFiltroTipo] = useState<string>('');
  const [filtroDataInicio, setFiltroDataInicio] = useState<string>('');
  const [filtroDataFim, setFiltroDataFim] = useState<string>('');

  const fmt = (v: number, d = settings.precision) =>
    v.toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d });

  const filtradas = HISTORICO_MOCK.filter((o) => {
    const matchSimbolo = !filtroSimbolo || o.simbolo.toLowerCase().includes(filtroSimbolo.toLowerCase());
    const matchTipo = !filtroTipo || o.tipo === filtroTipo;
    const matchDataInicio = !filtroDataInicio || o.dataAbertura >= filtroDataInicio;
    const matchDataFim = !filtroDataFim || o.dataFechamento <= filtroDataFim + ' 23:59';
    return matchSimbolo && matchTipo && matchDataInicio && matchDataFim;
  });

  const totalLucro = filtradas.reduce((acc, o) => acc + o.lucro, 0);
  const totalTrades = filtradas.length;
  const wins = filtradas.filter((o) => o.lucro > 0).length;
  const winRate = totalTrades > 0 ? (wins / totalTrades) * 100 : 0;
  const totalComissao = filtradas.reduce((acc, o) => acc + Math.abs(o.comissao), 0);
  const totalSwap = filtradas.reduce((acc, o) => acc + Math.abs(o.swap), 0);

  const exportCSV = () => {
    const cabecalho = 'Ticket;Simbolo;Tipo;Lote;Preco Abertura;Preco Fechamento;SL;TP;Lucro;Comissao;Swap;Abertura;Fechamento\n';
    const linhas = filtradas.map((o) =>
      `${o.ticket};${o.simbolo};${o.tipo};${o.lote};${o.precoAbertura};${o.precoFechamento};${o.sl ?? ''};${o.tp ?? ''};${o.lucro};${o.comissao};${o.swap};${o.dataAbertura};${o.dataFechamento}`
    ).join('\n');
    const conteudo = cabecalho + linhas;
    const blob = new Blob([conteudo], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `historico_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="page-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Histórico</h1>
          <span className="muted">Todas as ordens executadas e finalizadas</span>
        </div>
        <div className="btn-row">
          <button className="btn sm primary" onClick={exportCSV}>⬇ Exportar CSV</button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 14, padding: 12 }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <label className="muted" style={{ fontSize: 12 }}>Símbolo</label>
            <input type="text" placeholder="Ex: XAUUSD" value={filtroSimbolo} onChange={(e) => setFiltroSimbolo(e.target.value)}
              style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--panel2)', color: 'var(--text)', fontSize: 13 }} />
          </div>
          <div>
            <label className="muted" style={{ fontSize: 12 }}>Tipo</label>
            <select value={filtroTipo} onChange={(e) => setFiltroTipo(e.target.value)}
              style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--panel2)', color: 'var(--text)', fontSize: 13 }}>
              <option value="">Todos</option>
              <option value="compra">Compra</option>
              <option value="venda">Venda</option>
            </select>
          </div>
          <div>
            <label className="muted" style={{ fontSize: 12 }}>De</label>
            <input type="date" value={filtroDataInicio} onChange={(e) => setFiltroDataInicio(e.target.value)}
              style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--panel2)', color: 'var(--text)', fontSize: 13 }} />
          </div>
          <div>
            <label className="muted" style={{ fontSize: 12 }}>Até</label>
            <input type="date" value={filtroDataFim} onChange={(e) => setFiltroDataFim(e.target.value)}
              style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--panel2)', color: 'var(--text)', fontSize: 13 }} />
          </div>
          <div style={{ marginLeft: 'auto' }}>
            <button className="btn sm ghost" onClick={() => { setFiltroSimbolo(''); setFiltroTipo(''); setFiltroDataInicio(''); setFiltroDataFim(''); }}>Limpar</button>
          </div>
        </div>
      </div>

      <div className="grid cols-4" style={{ marginBottom: 14 }}>
        <div className="card"><div className="kpi-label">Trades</div><div className="kpi-value">{totalTrades}</div></div>
        <div className="card"><div className="kpi-label">Resultado</div><div className={totalLucro >= 0 ? 'kpi-value pos' : 'kpi-value neg'}>{fmt(totalLucro)}</div></div>
        <div className="card"><div className="kpi-label">Win Rate</div><div className="kpi-value">{winRate.toFixed(1)}%</div><div className="kpi-sub">{wins}W / {totalTrades - wins}L</div></div>
        <div className="card"><div className="kpi-label">Custos</div><div className="kpi-value">{fmt(totalComissao + totalSwap)}</div><div className="kpi-sub">comissão + swap</div></div>
      </div>

      {filtradas.length === 0 ? (
        <div className="placeholder">
          <div className="ph-icon">📜</div>
          <span>Nenhuma operação no período.</span>
          <span className="muted">Ajuste os filtros de data ou símbolo.</span>
        </div>
      ) : (
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>Ticket</th><th>Símbolo</th><th>Tipo</th><th>Lote</th><th>Abertura</th><th>Fechamento</th><th>SL</th><th>TP</th><th>Lucro</th><th>Custos</th><th>Período</th></tr></thead>
            <tbody>
              {filtradas.map((o) => (
                <tr key={o.ticket}>
                  <td className="mono">{o.ticket}</td>
                  <td><strong>{o.simbolo}</strong></td>
                  <td><span className={o.tipo === 'compra' ? 'chip ok' : 'chip danger'}>{o.tipo === 'compra' ? '▲ Compra' : '▼ Venda'}</span></td>
                  <td className="mono">{o.lote}</td>
                  <td className="mono">{fmt(o.precoAbertura)}</td>
                  <td className="mono">{fmt(o.precoFechamento)}</td>
                  <td className="mono">{o.sl ? fmt(o.sl) : '--'}</td>
                  <td className="mono">{o.tp ? fmt(o.tp) : '--'}</td>
                  <td className={o.lucro >= 0 ? 'pos' : 'neg'}>{fmt(o.lucro)}</td>
                  <td className="mono muted">{fmt(Math.abs(o.comissao) + Math.abs(o.swap))}</td>
                  <td className="mono muted" style={{ fontSize: 11 }}>{o.dataAbertura.slice(5, 16)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}