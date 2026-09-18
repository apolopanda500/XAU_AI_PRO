import { useCallback, useEffect, useRef, useState } from 'react';
import '../theme/mini-terminal.css';
const API = 'http://127.0.0.1:9001';
type Position = { ticket?: number | string; symbol?: string; type?: number | string; volume?: number; open_price?: number; price_current?: number; sl?: number; tp?: number; profit?: number; swap?: number };
type Account = { login?: number | string; name?: string; server?: string; currency?: string; balance?: number; equity?: number; margin?: number; free_margin?: number; margin_level?: number; profit?: number; leverage?: number | string };
type EventRow = { id: string; source: string; info: string; at: Date; kind?: string };
const num = (v: unknown, d = 2) => { const n = Number(v); return Number.isFinite(n) ? n.toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d }) : '--' };
const clsPnl = (v: number) => (v > 0 ? 'mt-pnl-pos' : v < 0 ? 'mt-pnl-neg' : '');
const sideOf = (p: Position) => { const t = p.type; return (t === 1 || t === 'sell' || t === 'SELL' || t === 0x1000) ? 'SELL' : 'BUY'; };
const eventDate = (data: any, fallback: Date) => { const raw = Array.isArray(data?.lines) ? data.lines.find((x: any) => x?.message)?.time ?? data.lines.find((x: any) => x?.message)?.timestamp : undefined; if (!raw) return fallback; const parsed = new Date(String(raw).replace(/^(\d{4})\.(\d{2})\.(\d{2}) /, '$1-$2-$3T')); return Number.isNaN(parsed.getTime()) ? fallback : parsed; };
export default function UniversalLiveTerminalLatest() {
  const [account, setAccount] = useState<Account | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<EventRow[]>([]);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const poll = useCallback(async () => {
    if (busyRef.current) return;
    busyRef.current = true; setBusy(true);
    const defs: Array<[string, string, (data: any) => string]> = [
      ['MT5', '/api/journal?limit=10', (d) => { const line = Array.isArray(d.lines) ? d.lines.find((x: any) => x?.message)?.message : ''; return line || ''; }],
      ['MEXC', '/api/universal/account?broker=mexc&market=crypto-spot', (d) => d.ok !== false ? `Conta Spot lida · saldo ${d.account?.balance ?? d.available ?? d.balance ?? '--'} ${d.account?.currency ?? ''} · ativos ${d.assets?.length ?? d.balances?.length ?? '--'}` : 'Conta Spot indisponível'],
      ['MEXC', '/api/universal/positions?broker=mexc&market=crypto-futures', (d) => d.ok !== false ? `Futuros lidos · posições ${d.positions?.length ?? 0}` : 'Futuros indisponíveis'],
      ['BINANCE', '/api/universal/account?broker=binance&market=crypto-spot', (d) => d.ok !== false ? `Conta Spot lida · saldo ${d.account?.balance ?? d.available ?? d.balance ?? '--'} ${d.account?.currency ?? ''} · ativos ${d.assets?.length ?? d.balances?.length ?? '--'}` : 'Conta Spot indisponível'],
      ['BINANCE', '/api/universal/positions?broker=binance&market=crypto-futures', (d) => d.ok !== false ? `Futuros lidos · posições ${d.positions?.length ?? 0}` : 'Futuros indisponíveis'],
    ];
    try {
      const [st, ac, ps] = await Promise.all([
        fetch(`${API}/api/status`, { signal: AbortSignal.timeout(5000) }).then((r) => r.json()).catch(() => null),
        fetch(`${API}/api/account`, { signal: AbortSignal.timeout(5000) }).then((r) => r.json()).catch(() => null),
        fetch(`${API}/api/positions`, { signal: AbortSignal.timeout(5000) }).then((r) => r.json()).catch(() => null),
      ]);
      setConnected(Boolean(st?.terminal_connected));
      const acct = (ac && typeof ac === 'object' ? (ac.account ?? ac) : null) as Account | null;
      setAccount(acct && (acct.login !== undefined || acct.balance !== undefined) ? acct : null);
      setPositions(Array.isArray(ps?.positions) ? ps.positions : []);
      const out = (await Promise.all(defs.map(async ([source, path, format]) => {
        try { const response = await fetch(API + path, { signal: AbortSignal.timeout(6000) }); const data = await response.json(); const now = new Date(); return { id: `${source}:${path}`, source, info: format(data), at: path.includes('/journal') ? eventDate(data, now) : now, kind: path.includes('/journal') ? 'TRADES' : response.ok ? 'INFO' : 'WARN' }; }
        catch { return { id: `${source}:${path}`, source, info: 'Fonte indisponível · gateway sem resposta', at: new Date(), kind: 'WARN' }; }
      }))).filter((event) => event !== null && event.info.length > 0) as EventRow[];
      setEvents(out);
    } finally { busyRef.current = false; setBusy(false); }
  }, []);
  useEffect(() => { void poll(); const timer = window.setInterval(() => void poll(), 10000); return () => window.clearInterval(timer); }, [poll]);

  const floating = positions.reduce((s, p) => s + (Number(p.profit) || 0), 0);
  const volume = positions.reduce((s, p) => s + (Number(p.volume) || 0), 0);
  const margin = Number(account?.margin ?? 0);
  const freeMargin = Number(account?.free_margin ?? 0);
  const marginLevel = Number(account?.margin_level ?? 0);
  return <div className="card compact-card robot-live-latest">
    <div className="section-head mini-terminal-head"><div><h2>Mini Terminal</h2><span className="muted">Conta, posições e eventos ao vivo · estilo MetaTrader</span></div>
      <div className="btn-row"><span className={`chip ${connected ? 'ok' : 'warn'}`}>{connected ? 'Terminal conectado' : 'Terminal desconectado'}</span>
        <button type="button" className="btn sm primary" onClick={() => void poll()} disabled={busy}>{busy ? 'Lendo…' : 'Atualizar'}</button></div></div>
    <div className="mt-account-grid">
      <div><span>Conta</span><strong>{account?.login ?? '--'}</strong></div>
      <div><span>Servidor</span><strong>{account?.server || '--'}</strong></div>
      <div><span>Saldo</span><strong>{num(account?.balance)} {account?.currency ?? ''}</strong></div>
      <div><span>Patrimônio</span><strong>{num(account?.equity)} {account?.currency ?? ''}</strong></div>
      <div><span>Flutuante</span><strong className={clsPnl(floating)}>{num(floating)}</strong></div>
      <div><span>Margem</span><strong>{num(margin)}</strong></div>
      <div><span>Margem livre</span><strong>{num(freeMargin)}</strong></div>
      <div><span>Nível</span><strong className={marginLevel > 0 && marginLevel < 200 ? 'neg' : ''}>{marginLevel > 0 ? `${marginLevel.toFixed(1)}%` : '--'}</strong></div>
    </div>
    <div className="mini-terminal-positions">
      <div className="section-head"><div><h3>Posições abertas</h3><span className="muted">{positions.length} posição(ões) · volume {num(volume, 2)}</span></div></div>
      <div className="table-scroll"><table className="tbl compact-table"><thead><tr><th>Ticket</th><th>Ativo</th><th>Tipo</th><th>Volume</th><th>Abertura</th><th>Atual</th><th>SL</th><th>TP</th><th>Swap</th><th>PnL</th></tr></thead>
        <tbody>{positions.map((p) => <tr key={String(p.ticket)}>
          <td className="mono">{p.ticket ?? '--'}</td><td><strong>{p.symbol ?? '--'}</strong></td>
          <td><span className={`chip ${sideOf(p) === 'BUY' ? 'ok' : 'warn'}`}>{sideOf(p)}</span></td>
          <td className="num">{num(p.volume, 2)}</td><td className="num">{num(p.open_price, 2)}</td><td className="num">{num(p.price_current, 2)}</td>
          <td className="num">{p.sl ? num(p.sl, 2) : '--'}</td><td className="num">{p.tp ? num(p.tp, 2) : '--'}</td>
          <td className="num">{num(p.swap ?? 0, 2)}</td>
          <td className={`num ${clsPnl(Number(p.profit ?? 0))}`}>{num(p.profit, 2)}</td></tr>)}
          {!positions.length && <tr><td colSpan={10} className="mt-empty">Nenhuma posição aberta.</td></tr>}</tbody></table></div>
    </div>
    <div className="mini-terminal-universal"><div className="section-head"><div><h3>Eventos universais</h3><span className="muted">Journal MT5 e corretoras de cripto</span></div></div>
      <div className="table-scroll"><table className="tbl compact-table mt-events"><thead><tr><th>Hora</th><th>Fonte</th><th>Tipo</th><th>Informação</th></tr></thead>
        <tbody>{events.map((event) => <tr key={event.id}><td className="mono">{event.at.toLocaleTimeString('pt-BR')}</td><td><strong>{event.source}</strong></td><td><span className={`chip ${event.kind === 'WARN' ? 'warn' : event.kind === 'TRADES' ? 'mt5' : 'ok'}`}>{event.kind ?? 'INFO'}</span></td><td>{event.info}</td></tr>)}
          {!events.length && <tr><td colSpan={4} className="mt-empty">Nenhum evento recebido.</td></tr>}</tbody></table></div>
    </div>
  </div>;
}
