import { useAppStore } from '../../hooks/useAppStore';

export default function StrategyTesterTab() {
  const selectedSymbol = useAppStore((s) => s.selectedSymbol);

  return (
    <div>
      <div className="page-head">
        <h1>Teste de Estratégia</h1>
        <span className="muted">Backtest e otimizacao (Fase 5 - motor no Core)</span>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h2>Configuração do Backtest</h2>
          <div className="field">
            <label htmlFor="bt-symbol">Símbolo</label>
            <input id="bt-symbol" type="text" value={selectedSymbol} readOnly />
            <span className="hint">Siga o simbolo selecionado na aba Mercado.</span>
          </div>
          <div className="field">
            <label htmlFor="bt-period">Período</label>
            <select id="bt-period" defaultValue="6m">
              <option value="1m">1 mês</option>
              <option value="3m">3 meses</option>
              <option value="6m">6 meses</option>
              <option value="1y">1 ano</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="bt-model">Modelo</label>
            <select id="bt-model" defaultValue="tick">
              <option value="tick">Cada tick</option>
              <option value="1m">OHLC 1 min</option>
              <option value="open">Somente abertura</option>
            </select>
          </div>
          <button className="btn primary" disabled title="Disponivel na Fase 5">
            Executar Backtest
          </button>
        </div>

        <div className="card">
          <h2>Resultados</h2>
          <div className="placeholder">
            <div className="ph-icon">🧪</div>
            <span>Motor de backtest ainda nao integrado.</span>
            <span className="muted">Previsto no roadmap (Fase 5: estrategia e backtest no Core Rust).</span>
          </div>
        </div>
      </div>
    </div>
  );
}
