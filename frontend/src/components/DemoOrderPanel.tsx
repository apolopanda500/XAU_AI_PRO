// Painel de execução DEMO com confirmação manual em 2 etapas.
// Segurança: somente conta DEMO (trade_mode do MT5); volume máx 0.10;
// SL/TP obrigatórios; order_check antes de order_send no gateway.
import { useEffect, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';

const GATEWAY = `${apiBase()}`;
const MAX_VOLUME = 0.1;
const CONFIRM_WORD = 'CONFIRMO';

type AccountMode = 'DEMO' | 'REAL' | 'UNKNOWN' | 'indisponível';
type OrderResult = {
  ok: boolean; stage?: string; retcode?: number; comment?: string;
  order?: number; deal?: number; demo?: boolean; error?: string;
  order_type?: string; price?: number; sl?: number; tp?: number; side?: string;
};

export default function DemoOrderPanel() {
  const symbol = useAppStore((s) => s.selectedSymbol);
  const [mode, setMode] = useState<AccountMode>('indisponível');
  const [tradeAllowed, setTradeAllowed] = useState(false);
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [volume, setVolume] = useState('0.01');
  const [sl, setSl] = useState('');
  const [tp, setTp] = useState('');
  const [understood, setUnderstood] = useState(false);
  const [confirmWord, setConfirmWord] = useState('');
  const [kind, setKind] = useState<'market' | 'limit' | 'stop'>('market');
  const [price, setPrice] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<OrderResult | null>(null);
  const [statusMsg, setStatusMsg] = useState('Aguardando gateway...');

  // Lê o modo real da conta (trade_mode do MT5) — somente leitura.
  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const r = await fetch(`${GATEWAY}/api/status`, { signal: AbortSignal.timeout(4000) });
        const d = (await r.json()) as {
          account?: { mode?: string; trade_allowed?: boolean };
        };
        if (!active) return;
        const m = (d.account?.mode ?? 'UNKNOWN').toUpperCase();
        setMode(m === 'DEMO' || m === 'REAL' ? m : 'UNKNOWN');
        setTradeAllowed(Boolean(d.account?.trade_allowed));
        setStatusMsg(
          m === 'DEMO'
            ? 'Conta DEMO confirmada pelo MT5.'
            : m === 'REAL'
              ? 'Conta REAL detectada: ordens demo serão recusadas.'
              : 'Modo da conta desconhecido.',
        );
      } catch {
        if (!active) return;
        setMode('indisponível');
        setStatusMsg('Gateway indisponível (porta 9001 offline).');
      }
    };
    void load();
    const t = window.setInterval(load, 15000);
    return () => {
      active = false;
      window.clearInterval(t);
    };
  }, []);

  const num = (v: string) => Number(String(v).replace(',', '.'));
  const vol = num(volume);
  const slNum = num(sl);
  const tpNum = num(tp);
  const priceNum = num(price);
  const fieldsValid =
    Boolean(symbol) && vol > 0 && vol <= MAX_VOLUME && slNum > 0 && tpNum > 0 &&
    (kind === 'market' || priceNum > 0);
  const confirmed = understood && confirmWord.trim().toUpperCase() === CONFIRM_WORD;
  const canSend =
    !busy && fieldsValid && confirmed && mode === 'DEMO' && tradeAllowed;

  // Comandos de gestão de posição: trailing, break-even,
  // parcial e aplicar/remover proteção. Todos exigem a mesma confirmação
  // de 2 etapas e passam pelo gateway DEMO (nunca emite ordem REAL).
  const sendCommand = async (path: string, extra: Record<string, unknown> = {}) => {
    if (!confirmed || mode !== 'DEMO' || busy) return;
    setBusy(true);
    setResult(null);
    try {
      const r = await fetch(`${GATEWAY}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, confirm_demo: true, ...extra }),
      });
      const d = (await r.json()) as OrderResult & { command?: string };
      setResult(d);
    } catch (e) {
      setResult({ ok: false, error: `Gateway indisponível: ${e instanceof Error ? e.message : 'erro'}` });
    } finally {
      setBusy(false);
    }
  };

  const send = async () => {
    if (!canSend) return;
    setBusy(true);
    setResult(null);
    try {
      const path = kind === 'market' ? '/api/demo/order' : '/api/demo/pending';
      const body: Record<string, unknown> = kind === 'market'
        ? { symbol, side, volume: vol, sl: slNum, tp: tpNum, confirm_demo: true }
        : { symbol, side, kind, price: priceNum, volume: vol, sl: slNum, tp: tpNum, confirm_demo: true };
      const r = await fetch(`${GATEWAY}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const d = (await r.json()) as OrderResult & { order_type?: string; price?: number; sl?: number; tp?: number };
      setResult(d);
    } catch (e) {
      setResult({
        ok: false,
        error: `Gateway indisponível: ${e instanceof Error ? e.message : 'erro'}`,
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card demo-order-panel" style={{ marginTop: 14 }}>
      <div className="btn-row" style={{ justifyContent: 'space-between', marginTop: 0 }}>
        <div>
          <h2 style={{ margin: 0 }}>Execução DEMO · {symbol || 'ativo não selecionado'}</h2>
          <span className="muted">order_check → order_send · volume máx 0.10 · SL/TP obrigatórios</span>
        </div>
        <span className={`chip ${mode === 'DEMO' ? 'ok' : mode === 'REAL' ? 'danger' : 'warn'}`}>{mode === 'DEMO' ? 'Conta DEMO' : mode === 'REAL' ? 'Conta REAL' : mode}</span>
      </div>
      <div className="grid cols-4" style={{ marginTop: 12 }}>
        <div className="field"><label htmlFor="demo-side">Lado</label><select id="demo-side" value={side} onChange={(e) => setSide(e.target.value as 'BUY' | 'SELL')}><option>BUY</option><option>SELL</option></select></div>
        <div className="field"><label htmlFor="demo-volume">Volume (máx 0.10)</label><input id="demo-volume" type="number" min="0" max={MAX_VOLUME} step="any" value={volume} onChange={(e) => setVolume(e.target.value)} /></div>
        <div className="field"><label htmlFor="demo-sl">Stop Loss *</label><input id="demo-sl" type="number" step="any" value={sl} onChange={(e) => setSl(e.target.value)} /></div>
        <div className="field"><label htmlFor="demo-tp">Take Profit *</label><input id="demo-tp" type="number" step="any" value={tp} onChange={(e) => setTp(e.target.value)} /></div>
        <div className="field"><label htmlFor="demo-kind">Execução</label>
          <select id="demo-kind" value={kind} onChange={(e) => setKind(e.target.value as 'market' | 'limit' | 'stop')}>
            <option value="market">Mercado (imediata)</option>
            <option value="limit">Limit (pendente, preço alvo)</option>
            <option value="stop">Stop (pendente, rompimento)</option>
          </select>
        </div>
        {kind !== 'market' && (
          <div className="field"><label htmlFor="demo-price">Preço alvo *</label><input id="demo-price" type="number" step="any" value={price} onChange={(e) => setPrice(e.target.value)} /></div>
        )}
      </div>
      <div className="config-actions" style={{ marginTop: 12 }}>
        <label><input type="checkbox" checked={understood} onChange={(e) => setUnderstood(e.target.checked)} /><span>Entendo que esta ordem vai para conta DEMO (dinheiro fictício).</span></label>
        <div className="field" style={{ marginTop: 8 }}><label htmlFor="demo-confirm-word">Digite {CONFIRM_WORD} para liberar</label><input id="demo-confirm-word" type="text" value={confirmWord} onChange={(e) => setConfirmWord(e.target.value)} placeholder={CONFIRM_WORD} autoComplete="off" /></div>
      </div>
      <div className="btn-row" style={{ marginTop: 12 }}>
        <button className="btn primary" type="button" onClick={() => void send()} disabled={!canSend} aria-label={`Enviar ordem demo ${side} ${symbol}`}>{busy ? 'Enviando...' : `Enviar DEMO ${side} (${kind === 'market' ? 'mercado' : kind})`}</button>
      </div>

      <div className="section-title" style={{ marginTop: 14, fontSize: 13 }}>Gestão da posição DEMO</div>
      <div className="btn-row" style={{ marginTop: 0 }}>
        <button className="btn ghost" type="button" disabled={!confirmed || mode !== 'DEMO' || busy} onClick={() => void sendCommand('/api/demo/trailing')} title="Trailing stop ativo na posição">Trailing</button>
        <button className="btn ghost" type="button" disabled={!confirmed || mode !== 'DEMO' || busy} onClick={() => void sendCommand('/api/demo/breakeven')} title="Move o SL para o preço de entrada (break-even)">Break-even</button>
        <button className="btn ghost" type="button" disabled={!confirmed || mode !== 'DEMO' || busy} onClick={() => void sendCommand('/api/demo/partial-close', { volume: Math.min(vol, MAX_VOLUME / 2) })} title="Fecha parcial da posição">Parcial</button>
        <button className="btn ghost" type="button" disabled={!confirmed || mode !== 'DEMO' || busy} onClick={() => void sendCommand('/api/demo/set-protection', { sl: slNum, tp: tpNum })} title="Aplica SL/TP informados na posição">Proteção</button>
        <button className="btn ghost" type="button" disabled={!confirmed || mode !== 'DEMO' || busy} onClick={() => void sendCommand('/api/demo/remove-protection')} title="Remove SL/TP da posição">Remover prot.</button>
      </div>
      <div className="hint" style={{ marginTop: 6 }}>{kind === 'market' ? 'Mercado: solicita execução com SL/TP obrigatórios; confirme o resultado no MT5.' : `Pendente ${kind.toUpperCase()}: solicita entrada no preço alvo com SL/TP. O preenchimento e a proteção dependem da corretora; não há garantia de OCO.`} Mesma confirmação de 2 etapas · sempre via gateway DEMO.</div>

      <div className="hint" style={{ marginTop: 8 }}>{statusMsg} {!tradeAllowed && mode !== 'indisponível' && 'Negociação bloqueada no terminal. '}{mode === 'REAL' && 'Ordens demo recusadas em conta REAL. '}{!fieldsValid && 'Preencha volume ≤ 0.10, SL e TP.'}{kind !== 'market' && !priceNum && ' Preço alvo obrigatório.'}{fieldsValid && !confirmed && ' Confirme as 2 etapas para liberar. '}</div>
      {result && (
        <div className={`hint ${result.ok ? '' : 'neg'}`} role="status" style={{ marginTop: 8 }}>
          {result.ok
            ? <span>Ordem aceita · stage {result.stage} · retcode {result.retcode} · ticket {result.order} · deal {result.deal}{result.order_type ? ` · ${result.order_type}` : ''}{result.price ? ` · @ ${result.price}` : ''}{result.comment ? ` · ${result.comment}` : ''}</span>
            : <span>Recusada{result.stage ? ` · stage ${result.stage}` : ''}{result.retcode !== undefined ? ` · retcode ${result.retcode}` : ''}{result.comment ? ` · ${result.comment}` : ''}{result.error ? ` · ${result.error}` : ''}</span>}
        </div>
      )}
    </div>
  );
}

