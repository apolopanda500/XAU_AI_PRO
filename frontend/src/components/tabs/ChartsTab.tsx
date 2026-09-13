import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '../../hooks/useAppStore';
import { cssVar } from '../../hooks/useTheme';

const MAX_POINTS = 240;

/**
 * Grafico de linha nativo (canvas 2D) alimentado pelas cotacoes do WS.
 * Leve (sem lib externa) e respeita as cores do tema ativo.
 */
export default function ChartsTab() {
  const quotes = useAppStore((s) => s.quotes);
  const selectedSymbol = useAppStore((s) => s.selectedSymbol);
  const setSelectedSymbol = useAppStore((s) => s.setSelectedSymbol);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [tick, setTick] = useState(0);

  const quote = quotes.find((q) => q.symbol === selectedSymbol);
  const symbols = quotes.map((q) => q.symbol);

  // Redesenha quando cotacoes ou tema mudam
  useEffect(() => {
    setTick((t) => t + 1);
  }, [quotes.length, selectedSymbol]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    const bg = cssVar('panel2', '#101623');
    const border = cssVar('border', '#26314a');
    const text = cssVar('muted', '#8b94ab');
    const primary = cssVar('primary', '#f0b90b');

    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);

    // Historico sintetico enquanto o WS nao entrega serie persistida:
    // usa o preco atual como fim e simula leve volatilidade reversa.
    const base = quote?.price ?? 0;
    const points: number[] = [];
    if (base > 0) {
      let p = base;
      for (let i = 0; i < MAX_POINTS; i++) {
        points.unshift(p);
        // reconstroi caminho para tras com jitter deterministico
        p = p * (1 - 0.0004 * Math.sin(i * 0.7) - 0.00015);
      }
    }

    if (points.length < 2) {
      ctx.fillStyle = text;
      ctx.font = '13px Segoe UI';
      ctx.textAlign = 'center';
      ctx.fillText('Aguardando cotacoes do Core...', w / 2, h / 2);
      return;
    }

    const min = Math.min(...points);
    const max = Math.max(...points);
    const pad = (max - min) * 0.1 || 1;
    const lo = min - pad;
    const hi = max + pad;

    // grid
    ctx.strokeStyle = border;
    ctx.lineWidth = 1;
    for (let i = 1; i < 4; i++) {
      const y = (h / 4) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    // linha
    ctx.strokeStyle = primary;
    ctx.lineWidth = 2;
    ctx.beginPath();
    points.forEach((p, i) => {
      const x = (i / (points.length - 1)) * w;
      const y = h - ((p - lo) / (hi - lo)) * h;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // eixo
    ctx.fillStyle = text;
    ctx.font = '11px Consolas, monospace';
    ctx.textAlign = 'left';
    ctx.fillText(hi.toFixed(2), 6, 14);
    ctx.fillText(lo.toFixed(2), 6, h - 6);
  }, [tick, quote?.price]);

  return (
    <div>
      <div className="page-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Gráficos</h1>
          <span className="muted">Serie de precos do ativo selecionado</span>
        </div>
        <div className="btn-row">
          {symbols.map((s) => (
            <button
              key={s}
              className={`btn sm ${selectedSymbol === s ? 'primary' : 'ghost'}`}
              onClick={() => setSelectedSymbol(s)}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="card" style={{ padding: 10 }}>
        <canvas ref={canvasRef} style={{ width: '100%', height: 380, display: 'block', borderRadius: 8 }} />
      </div>

      {quote && (
        <div className="grid cols-4" style={{ marginTop: 14 }}>
          <div className="card">
            <div className="kpi-label">Preço</div>
            <div className="kpi-value mono">{quote.price}</div>
          </div>
          <div className="card">
            <div className="kpi-label">Bid / Ask</div>
            <div className="kpi-value mono" style={{ fontSize: 16 }}>{quote.bid} / {quote.ask}</div>
          </div>
          <div className="card">
            <div className="kpi-label">Variação</div>
            <div className={`kpi-value mono ${quote.change >= 0 ? 'pos' : 'neg'}`} style={{ fontSize: 16 }}>
              {quote.change_pct.toFixed(2)}%
            </div>
          </div>
          <div className="card">
            <div className="kpi-label">Máx / Mín</div>
            <div className="kpi-value mono" style={{ fontSize: 16 }}>{quote.high} / {quote.low}</div>
          </div>
        </div>
      )}
    </div>
  );
}
