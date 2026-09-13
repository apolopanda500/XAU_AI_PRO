import { useAppStore } from '../../hooks/useAppStore';

export default function MarketTab() {
  const quotes = useAppStore((s) => s.quotes);
  const selectedSymbol = useAppStore((s) => s.selectedSymbol);
  const setSelectedSymbol = useAppStore((s) => s.setSelectedSymbol);
  const wsConnected = useAppStore((s) => s.wsConnected);

  const fmt = (v: number, d = 2) =>
    v.toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d });

  return (
    <div>
      <div className="page-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Mercado</h1>
          <span className="muted">Cotacoes em tempo real via WS do Core</span>
        </div>
        <span className={`chip ${wsConnected ? 'ok' : 'danger'}`}>{wsConnected ? 'WS Online' : 'WS Offline'}</span>
      </div>

      {quotes.length === 0 ? (
        <div className="placeholder">
          <div className="ph-icon">📈</div>
          <span>Nenhuma cotacao recebida ainda.</span>
          <span className="muted">Verifique se o Core esta rodando e conectado ao MT5.</span>
        </div>
      ) : (
        <div className="tbl-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>Símbolo</th>
                <th>Preço</th>
                <th>Bid</th>
                <th>Ask</th>
                <th>Spread</th>
                <th>Var %</th>
                <th>Máx / Mín</th>
                <th>Vol</th>
                <th>Fonte</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {quotes.map((q) => (
                <tr key={q.symbol} className={selectedSymbol === q.symbol ? 'selected' : ''}>
                  <td>
                    <strong>{q.symbol}</strong>
                  </td>
                  <td className="mono">{fmt(q.price, q.digits)}</td>
                  <td className="mono">{fmt(q.bid, q.digits)}</td>
                  <td className="mono">{fmt(q.ask, q.digits)}</td>
                  <td className="mono">{q.spread}</td>
                  <td className={`mono ${q.change >= 0 ? 'pos' : 'neg'}`}>
                    {q.change >= 0 ? '▲' : '▼'} {fmt(q.change_pct, 2)}%
                  </td>
                  <td className="mono">{fmt(q.high, q.digits)} / {fmt(q.low, q.digits)}</td>
                  <td className="mono">{q.volume}</td>
                  <td>
                    <span className="chip">{q.source}</span>
                  </td>
                  <td>
                    <button
                      className={`btn xs ${selectedSymbol === q.symbol ? 'primary' : 'ghost'}`}
                      onClick={() => setSelectedSymbol(q.symbol)}
                    >
                      {selectedSymbol === q.symbol ? 'Selecionado' : 'Selecionar'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
