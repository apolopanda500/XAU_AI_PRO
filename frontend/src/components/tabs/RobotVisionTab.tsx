import { useMemo } from 'react';
import { useAppStore, type Quote } from '../../hooks/useAppStore';

interface Prediction {
  symbol: string;
  direction: 'LONG' | 'SHORT';
  confidence: number;
  timeframe: string;
  target: number;
  stop: number;
  price: number;
}

// Simulacao deterministica por simbolo: substituida quando o Core passar a
// publicar predicoes reais via WebSocket (topico ai.prediction).
function derivePrediction(q: Quote, precision: number): Prediction {
  const seed = q.symbol.length * 7 + Math.floor(q.last);
  const bullish = seed % 2 === 0;
  const confidence = 70 + (seed % 26); // 70..95
  const range = Math.max(q.high - q.low, 10 ** -precision);
  return {
    symbol: q.symbol,
    direction: bullish ? 'LONG' : 'SHORT',
    confidence,
    timeframe: 'M15',
    price: q.last,
    target: bullish ? q.last + range * 0.6 : q.last - range * 0.4,
    stop: bullish ? q.last - range * 0.4 : q.last + range * 0.6,
  };
}

export default function RobotVisionTab() {
  const quotes = useAppStore((s) => s.quotes);
  const aiStatus = useAppStore((s) => s.aiStatus);
  const selectedSymbol = useAppStore((s) => s.selectedSymbol);
  const setSelectedSymbol = useAppStore((s) => s.setSelectedSymbol);
  const settings = useAppStore((s) => s.settings);

  const fmt = (v: number | undefined | null, decimals = settings.precision) =>
    v == null
      ? '--'
      : v.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

  const predictions = useMemo(
    () => quotes.map((q) => derivePrediction(q, settings.precision)),
    [quotes, settings.precision],
  );

  const selected = predictions.find((p) => p.symbol === selectedSymbol) ?? null;

  return (
    <div>
      <div className="page-head">
        <h1>AI Vision</h1>
        <span className="muted">Previsões de direção geradas pelo motor de IA</span>
        <span className={`chip ${aiStatus === 'Ativo' ? 'ok' : 'warn'}`} style={{ marginLeft: 'auto' }}>
          IA: {aiStatus}
        </span>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h2>Predição selecionada</h2>
          {selected ? (
            <>
              <div className="grid cols-3">
                <div>
                  <div className="kpi-label">Direção</div>
                  <div className="kpi-value">
                    <span className={`chip ${selected.direction === 'LONG' ? 'ok' : 'danger'}`}>
                      {selected.direction}
                    </span>
                  </div>
                </div>
                <div>
                  <div className="kpi-label">Confiança</div>
                  <div className="kpi-value mono">{selected.confidence}%</div>
                </div>
                <div>
                  <div className="kpi-label">Timeframe</div>
                  <div className="kpi-value mono">{selected.timeframe}</div>
                </div>
              </div>
              <div className="tbl-wrap" style={{ marginTop: 12 }}>
                <table className="tbl">
                  <tbody>
                    <tr><td>Preço atual</td><td className="mono">{fmt(selected.price)}</td></tr>
                    <tr><td>Alvo</td><td className="mono pos">{fmt(selected.target)}</td></tr>
                    <tr><td>Stop</td><td className="mono neg">{fmt(selected.stop)}</td></tr>
                  </tbody>
                </table>
              </div>
              <div className="progress" style={{ marginTop: 12 }}>
                <div className="progress-bar" style={{ width: `${selected.confidence}%` }} />
              </div>
            </>
          ) : (
            <div className="placeholder">
              <div className="ph-icon">🤖</div>
              <span>
                {quotes.length === 0
                  ? 'Sem cotações recebidas do Core. Aguardando WebSocket...'
                  : `Nenhuma previsão para ${selectedSymbol}. Selecione um símbolo na lista.`}
              </span>
            </div>
          )}
        </div>

        <div className="card">
          <h2>Sinais por símbolo</h2>
          {predictions.length === 0 ? (
            <div className="placeholder">
              <div className="ph-icon">📡</div>
              <span>Aguardando cotações para gerar sinais.</span>
            </div>
          ) : (
            <div className="tbl-wrap">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Símbolo</th>
                    <th>Direção</th>
                    <th>Confiança</th>
                    <th>Alvo</th>
                  </tr>
                </thead>
                <tbody>
                  {predictions.map((p) => (
                    <tr
                      key={p.symbol}
                      className={p.symbol === selectedSymbol ? 'selected' : ''}
                      onClick={() => setSelectedSymbol(p.symbol)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td className="mono">{p.symbol}</td>
                      <td>
                        <span className={`chip ${p.direction === 'LONG' ? 'ok' : 'danger'}`}>
                          {p.direction}
                        </span>
                      </td>
                      <td className="mono">{p.confidence}%</td>
                      <td className="mono">{fmt(p.target)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <span className="hint" style={{ display: 'block', marginTop: 10 }}>
            Modo demonstração: sinais derivados das cotações. A integração real chega com o tópico
            <span className="mono"> ai.prediction </span>
            do Core.
          </span>
        </div>
      </div>
    </div>
  );
}
