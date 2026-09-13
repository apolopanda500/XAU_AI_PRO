import { useAppStore } from '../../hooks/useAppStore';

export default function PositionsTab() {
  const positions = useAppStore((s) => s.positions);
  const settings = useAppStore((s) => s.settings);

  const fmt = (v: number, d = settings.precision) =>
    v.toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d });

  const totalProfit = positions.reduce((acc, p) => acc + (p.profit ?? 0), 0);

  return (
    <div>
      <div className="page-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Carteira</h1>
          <span className="muted">Posicoes abertas na conta MT5</span>
        </div>
        <div className="btn-row">
          <span className="chip">{positions.length} posicoes</span>
          <span className={`chip ${totalProfit >= 0 ? 'ok' : 'danger'}`}>
            Resultado: {fmt(totalProfit)}
          </span>
        </div>
      </div>

      {positions.length === 0 ? (
        <div className="placeholder">
          <div className="ph-icon">💼</div>
          <span>Nenhuma posicao aberta.</span>
          <span className="muted">As posicoes aparecem aqui assim que o EA reporta via Core.</span>
        </div>
      ) : (
        <div className="tbl-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Símbolo</th>
                <th>Lado</th>
                <th>Volume</th>
                <th>Abertura</th>
                <th>Atual</th>
                <th>SL / TP</th>
                <th>Lucro</th>
                <th>Magic</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => (
                <tr key={p.ticket}>
                  <td className="mono">{p.ticket}</td>
                  <td><strong>{p.symbol}</strong></td>
                  <td>
                    <span className={`chip ${p.side === 'buy' ? 'ok' : 'danger'}`}>
                      {p.side === 'buy' ? '▲ Compra' : '▼ Venda'}
                    </span>
                  </td>
                  <td className="mono">{p.volume}</td>
                  <td className="mono">{fmt(p.open_price)}</td>
                  <td className="mono">{fmt(p.current_price)}</td>
                  <td className="mono">
                    {p.sl ? fmt(p.sl) : '--'} / {p.tp ? fmt(p.tp) : '--'}
                  </td>
                  <td className={`mono ${p.profit >= 0 ? 'pos' : 'neg'}`}>{fmt(p.profit)}</td>
                  <td className="mono muted">{p.magic}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
