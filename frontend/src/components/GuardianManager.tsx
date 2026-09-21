import { useEffect, useState, type ChangeEvent } from 'react';
import { apiBase } from '../lib/api';
import { requestId } from '../lib/format';
import { notify } from '../lib/notify';
import { useGuardian, useIntents, usePositions, useReconcile, useCommand } from '../hooks/queries';

const API = `${apiBase()}`;
type Rule = {
  breakeven: { trigger: number; offset: number };
  trailing: { mode: 'fixed' | 'step' | 'atr'; distance: number; step: number; atr_period: number; atr_multiplier: number };
  partials: Array<{ trigger: number; volume: number }>;
  profit_lock: { trigger: number; giveback: number };
  time_exit: { max_minutes: number; close_at: string };
};
const EMPTY_RULE: Rule = {
  breakeven: { trigger: 0, offset: 0 },
  trailing: { mode: 'step', distance: 0, step: 0, atr_period: 14, atr_multiplier: 2 },
  partials: [],
  profit_lock: { trigger: 0, giveback: 0 },
  time_exit: { max_minutes: 0, close_at: '' },
};
const num = (v: string) => (Number.isFinite(Number(v)) ? Number(v) : 0);

type PosRow = { ticket?: number; symbol?: string; type?: string; volume?: number; profit?: number; time?: number };
const hhmmss = (s: number) => [Math.floor(s / 3600), Math.floor((s % 3600) / 60), s % 60].map((n) => String(n).padStart(2, '0')).join(':');

// Linha de posição com atualização de P/L a cada poll e timer de tempo real.
function LivePosRow({ p, watched, onPick }: { p: PosRow; watched: boolean; onPick: (t: string) => void }) {
  const open = Number(p.time ?? 0);
  const [elapsed, setElapsed] = useState(open > 0 ? Math.max(0, Math.floor(Date.now() / 1000 - open)) : 0);
  useEffect(() => {
    if (open <= 0) return;
    const id = window.setInterval(() => setElapsed(Math.max(0, Math.floor(Date.now() / 1000 - open))), 1000);
    return () => window.clearInterval(id);
  }, [open]);
  const profit = Number(p.profit ?? 0);
  const tk = String(p.ticket ?? '');
  return (
    <div className="guardian-rule-row">
      <span className="chip">{tk}</span>
      <span>{String(p.symbol ?? '')} · {String(p.type ?? '')} · {Number(p.volume ?? 0)}</span>
      <span className={profit >= 0 ? 'ok' : 'danger'}>{profit >= 0 ? '+' : ''}{profit.toFixed(2)}</span>
      <span className="hint">{open > 0 ? hhmmss(elapsed) : '--:--:--'}</span>
      {watched ? <span className="chip ok">guardian</span> : <button className="btn xs ghost" onClick={() => onPick(tk)}>Preencher</button>}
    </div>
  );
}

export default function GuardianManager() {
  const guardian = useGuardian();
  const intents = useIntents(25);
  const reconcile = useReconcile();
  const tickNow = useCommand('/api/guardian/tick');
  const positions = usePositions();
  const posRows = ((positions.data as { positions?: unknown } | undefined)?.positions ?? []) as unknown as PosRow[];
  const [ticket, setTicket] = useState('');
  const [rule, setRule] = useState<Rule>(EMPTY_RULE);
  const [p1t, setP1t] = useState(''); const [p1v, setP1v] = useState('');
  const [p2t, setP2t] = useState(''); const [p2v, setP2v] = useState('');
  const [p3t, setP3t] = useState(''); const [p3v, setP3v] = useState('');
  const [status, setStatus] = useState('');
  const engine = String(guardian.data?.guardian ?? 'offline');
  const active = engine === 'enabled';
  const chip = active ? 'chip ok' : engine === 'paused_emergency_stop' ? 'chip danger' : 'chip warn';
  const setBusy = useCommand('/api/guardian/set');
  const removeBusy = useCommand('/api/guardian/remove');

  const setPart = (setter: (v: string) => void) => (e: ChangeEvent<HTMLInputElement>) => setter(e.target.value);
  const patch = (path: string, value: number | string) => setRule((prev) => {
    const next = structuredClone(prev);
    const keys = path.split('.');
    let node = next as unknown as Record<string, unknown>;
    for (let i = 0; i < keys.length - 1; i++) node = node[keys[i]] as Record<string, unknown>;
    node[keys[keys.length - 1]] = value;
    return next;
  });

  const activate = async () => {
    const tk = num(ticket);
    if (tk <= 0) { setStatus('Informe o ticket da posição DEMO.'); return; }
    if (!window.confirm(`Ativar guardian DEMO para o ticket ${tk}? O motor passa a gerenciar SL/parciais automaticamente.`)) return;
    const partials = [[p1t, p1v], [p2t, p2v], [p3t, p3v]]
      .map(([t, v]) => ({ trigger: num(t), volume: num(v) }))
      .filter((p) => p.trigger > 0 && p.volume > 0);
    const d = await setBusy.run({
      ticket: tk, request_id: requestId(), confirm: true, confirm_demo: true,
      breakeven: rule.breakeven, trailing: rule.trailing, partials,
      profit_lock: rule.profit_lock, time_exit: rule.time_exit,
    });
    if (d?.ok) {
      setStatus(`Guardian ativo para o ticket ${tk}.`);
      void notify('Guardian ativo', `Ticket ${tk} sob gestão contínua (DEMO).`);
    } else {
      setStatus(`Recusado · ${String(d?.error ?? 'erro desconhecido')}`);
      void notify('Guardian recusado', String(d?.error ?? 'erro desconhecido'));
    }
    void guardian.refetch();
  };

  const removeRule = async (tk: string) => {
    if (!window.confirm(`Remover regra do guardian para ${tk}? A posição continua aberta.`)) return;
    const d = await removeBusy.run({ ticket: num(tk), confirm: true, confirm_demo: true });
    setStatus(d?.ok ? `Regra ${tk} removida.` : `Recusado · ${String(d?.error ?? 'erro desconhecido')}`);
    void guardian.refetch();
  };

  return (
    <div className="card compact-card guardian-manager">
      <div className="section-head">
        <h2>Guardian · Trade Manager (DEMO)</h2>
        <span className={chip}>{engine === 'offline' ? 'gateway offline' : engine}</span>
      </div>
      <div className="btn-row">
        <input className="input sm" type="number" min="1" placeholder="Ticket da posição" value={ticket} onChange={setPart(setTicket)} />
        <button className="btn sm primary" onClick={() => { void activate(); }} disabled={setBusy.busy || !active}>{setBusy.busy ? 'Ativando…' : 'Ativar guardian'}</button>
        <button className="btn sm ghost" onClick={() => { void removeRule(ticket); }} disabled={removeBusy.busy || !active}>Remover</button>
        <button className="btn sm ghost" onClick={() => { void tickNow.run({}).then(() => { void guardian.refetch(); }); }} disabled={tickNow.busy}>{tickNow.busy ? 'Executando…' : 'Tick agora'}</button>
      </div>
      <div className="guardian-grid">
        <label>Breakeven gatilho <input className="input sm" type="number" step="0.1" value={rule.breakeven.trigger} onChange={(e) => patch('breakeven.trigger', num(e.target.value))} /></label>
        <label>Breakeven offset <input className="input sm" type="number" step="0.01" value={rule.breakeven.offset} onChange={(e) => patch('breakeven.offset', num(e.target.value))} /></label>
        <label>Trailing modo
          <select className="input sm" value={rule.trailing.mode} onChange={(e) => patch('trailing.mode', e.target.value)}>
            <option value="fixed">fixed</option><option value="step">step</option><option value="atr">ATR</option>
          </select>
        </label>
        <label>Trailing distância <input className="input sm" type="number" step="0.1" value={rule.trailing.distance} onChange={(e) => patch('trailing.distance', num(e.target.value))} /></label>
        <label>Trailing passo <input className="input sm" type="number" step="0.1" value={rule.trailing.step} onChange={(e) => patch('trailing.step', num(e.target.value))} /></label>
        <label>ATR período <input className="input sm" type="number" min="2" value={rule.trailing.atr_period} onChange={(e) => patch('trailing.atr_period', num(e.target.value))} /></label>
        <label>ATR multiplicador <input className="input sm" type="number" step="0.1" value={rule.trailing.atr_multiplier} onChange={(e) => patch('trailing.atr_multiplier', num(e.target.value))} /></label>
        <label>TP1 gatilho <input className="input sm" type="number" step="0.1" value={p1t} onChange={setPart(setP1t)} /></label>
        <label>TP1 volume <input className="input sm" type="number" step="0.01" value={p1v} onChange={setPart(setP1v)} /></label>
        <label>TP2 gatilho <input className="input sm" type="number" step="0.1" value={p2t} onChange={setPart(setP2t)} /></label>
        <label>TP2 volume <input className="input sm" type="number" step="0.01" value={p2v} onChange={setPart(setP2v)} /></label>
        <label>TP3 gatilho <input className="input sm" type="number" step="0.1" value={p3t} onChange={setPart(setP3t)} /></label>
        <label>TP3 volume <input className="input sm" type="number" step="0.01" value={p3v} onChange={setPart(setP3v)} /></label>
        <label>Profit lock gatilho <input className="input sm" type="number" step="0.1" value={rule.profit_lock.trigger} onChange={(e) => patch('profit_lock.trigger', num(e.target.value))} /></label>
        <label>Profit lock devolução <input className="input sm" type="number" step="0.1" value={rule.profit_lock.giveback} onChange={(e) => patch('profit_lock.giveback', num(e.target.value))} /></label>
        <label>Time exit (min) <input className="input sm" type="number" value={rule.time_exit.max_minutes} onChange={(e) => patch('time_exit.max_minutes', num(e.target.value))} /></label>
        <label>Fechar às (HH:MM) <input className="input sm" type="time" value={rule.time_exit.close_at} onChange={(e) => patch('time_exit.close_at', e.target.value)} /></label>
      </div>
      <div className="hint" role="status" aria-live="polite">{status || 'Configure os módulos desejados e ative para o ticket. Campos zerados ficam desligados.'}</div>
      {guardian.data && guardian.data.count > 0 && (
        <div className="guardian-rules">
          {Object.entries(guardian.data.rules ?? {}).map(([tk, r]) => (
            <div key={tk} className="guardian-rule-row">
              <span className="chip">#{tk}</span>
              <span>{String(r.symbol ?? '')} · {String(r.side ?? '')}</span>
              <button className="btn xs ghost" onClick={() => { void removeRule(tk); }}>Remover</button>
            </div>
          ))}
        </div>
      )}
      {guardian.data?.last_error && <div className="hint danger">Último erro: {String(guardian.data.last_error)}</div>}
      <div className="section-head"><h3>Ciclo imediato</h3>
        <button className="btn xs ghost" onClick={() => { void tickNow.run().then(() => { void guardian.refetch(); }); }} disabled={tickNow.busy || !active}>{tickNow.busy ? 'Executando…' : 'Tick agora'}</button></div>
      {tickNow.data && (
        <div className="hint" role="status" aria-live="polite">
          {tickNow.data.ok
            ? `Tick ok · regras: ${String((tickNow.data as { count?: unknown }).count ?? 0)} · ações: ${String(((tickNow.data as { actions?: unknown[] }).actions ?? []).length)}`
            : `Tick falhou: ${String(tickNow.data.error ?? 'erro desconhecido')}`}
        </div>
      )}
      <div className="guardian-live">
        <div className="section-head"><h3>Posições monitoradas (tempo real)</h3><span className="chip">{posRows.length}</span></div>
        {posRows.map((p) => (
          <LivePosRow key={String(p.ticket ?? '')} p={p}
            watched={Object.keys(guardian.data?.rules ?? {}).includes(String(p.ticket ?? ''))}
            onPick={(t) => { setTicket(t); setStatus(`Ticket ${t} preenchido.`); }} />
        ))}
        {positions.data && posRows.length === 0 && <div className="hint">Nenhuma posição aberta no momento.</div>}
        {!positions.data && <div className="hint">Aguardando posições do gateway…</div>}
      </div>
      <div className="guardian-audit">
        <div className="section-head"><h3>Intents (auditoria)</h3><span className="chip">{intents.data?.count ?? 0}</span>
          <button className="btn xs ghost" onClick={() => { void reconcile.run().then(() => { void intents.refetch(); }); }} disabled={reconcile.busy}>{reconcile.busy ? 'Reconciliando…' : 'Reconciliar agora'}</button></div>
        {reconcile.report && (
          <div className="hint" role="status" aria-live="polite">
            {reconcile.report.ok
              ? `Verificados: ${reconcile.report.checked ?? 0} · reconciliados: ${reconcile.report.reconciled ?? 0} · desconhecidos: ${reconcile.report.unknown ?? 0} · pendentes: ${reconcile.report.still_pending ?? 0}`
              : `Reconciliação falhou: ${reconcile.report.error ?? 'erro desconhecido'}`}
          </div>
        )}
        {(intents.data?.intents ?? []).slice(0, 8).map((it) => (
          <div key={it.intent_id} className="guardian-rule-row">
            <span className={`chip ${it.status === 'sent' || it.status === 'reconciled' ? 'ok' : it.status === 'pending' ? 'warn' : 'danger'}`}>{it.status}</span>
            <span>{String(it.kind ?? '')} · {String(it.ts_iso ?? '')}</span>
          </div>
        ))}
        {!intents.data && <div className="hint">Sem registros de auditoria.</div>}
      </div>
    </div>
  );
}
