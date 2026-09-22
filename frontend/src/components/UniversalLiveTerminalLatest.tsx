import { useMemo } from 'react';
import { apiBase } from '../lib/api';
import { useCoreStatus, useAccount, usePositions, useJournal, useAllCryptoAccounts } from '../hooks/queries';
import { fmtNum, clsPnl, sideOfPosition, extractSymbol, requestId } from '../lib/format';
import { notify } from '../lib/notify';
import '../theme/mini-terminal.css';

const API = `${apiBase()}`;
type Position = { ticket?: number | string; symbol?: string; type?: number | string; volume?: number; open_price?: number; price_current?: number; sl?: number; tp?: number; profit?: number; swap?: number };
type Account = { login?: number | string; name?: string; server?: string; currency?: string; balance?: number; equity?: number; margin?: number; free_margin?: number; margin_level?: number; profit?: number; leverage?: number | string };

// Origem/mercado ativos da sessão (mesma convenção do RobotCommandActions).
const activeAccount = (): { broker: string; market: string } => {
  try {
    const [broker, market] = (localStorage.getItem('xau-active-account') || '').split(':');
    return { broker: broker || 'mt5', market: market || 'forex' };
  } catch { return { broker: 'mt5', market: 'forex' }; }
};

export default function UniversalLiveTerminalLatest() {
  const statusQ = useCoreStatus();
  const accountQ = useAccount();
  const positionsQ = usePositions();
  const journalQ = useJournal(10);          // journal MT5: 10s (baixa latência)
  const cryptoQ = useAllCryptoAccounts();   // cripto: 30s (fundo de Rede)

  const connected = Boolean(statusQ.data?.terminal_connected);
  const eaHeartbeat = (statusQ.data?.ea_heartbeat ?? {}) as { live?: boolean; age_sec?: number; symbol?: string };
  const accountRaw = accountQ.data as Record<string, unknown> | undefined;
  const account = (accountRaw && typeof accountRaw === 'object' ? ((accountRaw.account ?? accountRaw) as Account) : null);
  const positions = useMemo(() => (Array.isArray(positionsQ.data?.positions) ? (positionsQ.data.positions as Position[]) : []), [positionsQ.data]);

  const events = useMemo(() => {
    const now = new Date();
    const rows: Array<{ id: string; source: string; info: string; at: Date; kind: string }> = [];
    // Journal MT5 (grade trader: tipo + símbolo + mensagem)
    for (const line of (journalQ.data?.lines ?? []) as Array<Record<string, unknown>>) {
      const message = String(line?.message ?? '').trim();
      if (!message) continue;
      const kind = /trade|order|execut|buy|sell|close|fill/i.test(message) ? 'TRADES' : /warn|alert/i.test(message) ? 'WARN' : /error|fail/i.test(message) ? 'ERROR' : 'INFO';
      const rawTime = line?.time ?? line?.timestamp;
      const parsed = rawTime ? new Date(String(rawTime).replace(/^(\d{4})\.(\d{2})\.(\d{2}) /, '$1-$2-$3T')) : now;
      rows.push({ id: `mt5-${rows.length}-${message.slice(0, 24)}`, source: 'MT5', info: message, at: Number.isNaN(parsed.getTime()) ? now : parsed, kind });
    }
    // Contas de cripto (Spot/Futuros de MEXC e Binance) — conteúdo de conta real, não "informação básica"
    for (const c of cryptoQ.data ?? []) {
      if (!c.ok) { rows.push({ id: `cry-${c.broker}-${c.market}`, source: c.broker.toUpperCase(), info: `${c.market === 'crypto-spot' ? 'Spot' : 'Futuros'} indisponível`, at: now, kind: 'WARN' }); continue; }
      const bal = fmtNum(c.balance, 2);
      const assets = c.assets.length ? ` · ${c.assets.length} ativos` : '';
      rows.push({ id: `cry-${c.broker}-${c.market}`, source: c.broker.toUpperCase(), info: `${c.market === 'crypto-spot' ? 'Conta Spot' : 'Conta Futuros'} · saldo ${bal} ${c.currency}${assets}`, at: now, kind: 'INFO' });
    }
    return rows.sort((a, b) => b.at.getTime() - a.at.getTime()).slice(0, 14);
  }, [journalQ.data, cryptoQ.data]);

  // Fechamento ao vivo de posição (envia ordem de fechamento pelo gateway)
  const closePosition = async (p: Position) => {
    const { broker, market } = activeAccount();
    if (!window.confirm(`Fechar posição ${p.ticket ?? ''} (${p.symbol ?? '--'}) via ${broker.toUpperCase()}/${market}?`)) return;
    try {
      const isEa = broker === 'mt5';
      const endpoint = isEa ? `${API}/api/ea/close` : `${API}/api/universal/close`;
      const r = await fetch(endpoint, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ broker, market, symbol: p.symbol ?? '', ticket: p.ticket, request_id: requestId(), confirm: true, confirm_live: isEa, authorize_execution: isEa, execute: !isEa, action: 'close' }),
        signal: AbortSignal.timeout(10000),
      });
      const d = await r.json() as { error?: string; stage?: string; status?: string };
      if (r.ok) {
        notify('Fechamento de posição', `Ordem de fechamento enviada para ${p.symbol ?? 'posição'} (ticket ${p.ticket ?? '--'}).`);
        void positionsQ.refetch();
      } else {
        notify('Fechamento rejeitado', d.error || `HTTP ${r.status}`);
      }
    } catch { notify('Gateway indisponível', 'Não foi possível enviar o fechamento agora.'); }
  };
  const closeAllPositions = async () => {
    if (!positions.length || !window.confirm(`Fechar ${positions.length} posição(ões) do EA? Esta ação envia comandos reais.`)) return;
    await Promise.all(positions.map((position) => closePosition(position)));
    void positionsQ.refetch();
  };

  const floating = positions.reduce((s, p) => s + (Number(p.profit) || 0), 0);
  const volume = positions.reduce((s, p) => s + (Number(p.volume) || 0), 0);
  const margin = Number(account?.margin ?? 0);
  const freeMargin = Number(account?.free_margin ?? 0);
  const marginLevel = Number(account?.margin_level ?? 0);
  const busy = statusQ.isFetching || accountQ.isFetching || positionsQ.isFetching;
  const refreshAll = () => { void statusQ.refetch(); void accountQ.refetch(); void positionsQ.refetch(); void cryptoQ.refetch(); };

  return <div className="card compact-card robot-live-latest">
    <div className="section-head mini-terminal-head"><div><h2>Mini Terminal</h2><span className="muted">Conta, posições e eventos ao vivo · estilo MetaTrader</span></div>
      <div className="btn-row"><span className={`chip ${connected ? 'ok' : 'warn'}`}>{connected ? 'Terminal conectado' : 'Terminal desconectado'}</span><span className={`chip ${eaHeartbeat.live ? 'ok' : 'warn'}`}>EA {eaHeartbeat.live ? `vivo · ${eaHeartbeat.age_sec ?? 0}s` : 'sem heartbeat'}</span>
        <button type="button" className="btn sm primary" onClick={refreshAll} disabled={busy}>{busy ? 'Lendo…' : 'Atualizar'}</button></div></div>
    <div className="mt-account-grid">
      <div><span>Conta</span><strong>{account?.login ?? '--'}</strong></div>
      <div><span>Servidor</span><strong>{account?.server || '--'}</strong></div>
      <div><span>Saldo</span><strong>{fmtNum(account?.balance)} {account?.currency ?? ''}</strong></div>
      <div><span>Patrimônio</span><strong>{fmtNum(account?.equity)} {account?.currency ?? ''}</strong></div>
      <div><span>Flutuante</span><strong className={clsPnl(floating)}>{fmtNum(floating)}</strong></div>
      <div><span>Margem</span><strong>{fmtNum(margin)}</strong></div>
      <div><span>Margem livre</span><strong>{fmtNum(freeMargin)}</strong></div>
      <div><span>Nível</span><strong className={marginLevel > 0 && marginLevel < 200 ? 'neg' : ''}>{marginLevel > 0 ? `${marginLevel.toFixed(1)}%` : '--'}</strong></div>
    </div>
    <div className="mini-terminal-positions">
      <div className="section-head"><div><h3>Posições abertas</h3><span className="muted">{positions.length} posição(ões) · volume {fmtNum(volume, 2)} · dados reais sincronizados</span></div><div className="btn-row"><button type="button" className="btn xs danger" onClick={() => void closeAllPositions()} disabled={!positions.length || busy}>Fechar todas</button><button type="button" className="btn xs ghost" onClick={() => void positionsQ.refetch()} disabled={busy}>Sincronizar</button></div></div>
      <div className="table-scroll"><table className="tbl compact-table positions-table"><thead><tr><th>Ticket</th><th>Ativo</th><th>Tipo</th><th>Volume</th><th>Abertura</th><th>Atual</th><th>SL</th><th>TP</th><th>Swap</th><th>PnL</th><th>Ações</th></tr></thead>
        <tbody>{positions.map((p) => <tr key={String(p.ticket)}>
          <td className="mono">{p.ticket ?? '--'}</td><td><strong>{p.symbol ?? '--'}</strong></td>
          <td><span className={`chip ${sideOfPosition(p) === 'BUY' ? 'ok' : 'warn'}`}>{sideOfPosition(p)}</span></td>
          <td className="num">{fmtNum(p.volume, 2)}</td><td className="num">{fmtNum(p.open_price, 2)}</td><td className="num">{fmtNum(p.price_current, 2)}</td>
          <td className="num">{p.sl ? fmtNum(p.sl, 2) : '--'}</td><td className="num">{p.tp ? fmtNum(p.tp, 2) : '--'}</td>
          <td className="num">{fmtNum(p.swap ?? 0, 2)}</td>
          <td className={`num ${clsPnl(Number(p.profit ?? 0))}`}>{fmtNum(p.profit, 2)}</td>
          <td className="mt-actions-cell"><button type="button" className="btn sm danger mt-close-btn" onClick={() => void closePosition(p)}>Fechar</button></td></tr>)}
          {!positions.length && <tr><td colSpan={11} className="mt-empty">{positionsQ.isFetching ? 'Carregando posições…' : 'Nenhuma posição aberta.'}</td></tr>}</tbody></table></div>
    </div>
    <div className="mini-terminal-universal"><div className="section-head"><div><h3>Eventos universais</h3><span className="muted">Journal MT5 em 10s · contas de cripto em 30s (fundo de Rede)</span></div></div>
      <div className="table-scroll"><table className="tbl compact-table mt-events"><thead><tr><th>Hora</th><th>Fonte</th><th>Tipo</th><th>Símbolo</th><th>Informação</th></tr></thead>
        <tbody>{events.map((event) => <tr key={event.id}><td className="mono">{event.at.toLocaleTimeString('pt-BR')}</td><td><span className={`mt-source ${event.source.toLowerCase()}`}>{event.source}</span></td><td><span className={`ev-kind ${event.kind}`}>{event.kind}</span></td><td className="ev-sym">{extractSymbol(event.info)}</td><td>{event.info}</td></tr>)}
          {!events.length && <tr><td colSpan={5} className="mt-empty">{journalQ.isFetching ? 'Lendo journal…' : 'Nenhum evento recebido.'}</td></tr>}</tbody></table></div>
    </div>
  </div>;
}
