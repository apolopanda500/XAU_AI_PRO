import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useCoreHealth, useWatchdog, useTelemetry, useTelemetryHistory, useQueue } from '../hooks/queries';
import { notify } from '../lib/notify';

type H = { os?: string; architecture?: string; cpu_name?: string; gpu_name?: string; cpu_usage_percent?: number; cpu_cores?: number; memory_total_gb?: number; memory_available_gb?: number };

const EA_LABEL: Record<string, string> = {
  alive: 'Vivo', frozen: 'Travado (arquivo fresh, timestamp parado)',
  stale: 'Offline (heartbeat antigo)', missing: 'Sem heartbeat (EA não iniciou)',
  unknown: 'Indeterminado',
};

// Mini-gráfico SVG da curva de equity a partir do histórico de snapshots.
function EquitySpark({ histQ }: { histQ: ReturnType<typeof useTelemetryHistory> }) {
  const rows = (histQ.data?.snapshots ?? []).filter((s) => typeof s.equity === 'number');
  if (rows.length < 2) {
    return <div className="card compact-card"><h2>Equity (histórico)</h2>
      <div className="hint">Ainda sem pontos suficientes. O coletor registra um snapshot por minuto enquanto o gateway roda.</div></div>;
  }
  const W = 560, H = 96, PAD = 8;
  const vals = rows.map((s) => s.equity as number);
  const min = Math.min(...vals), max = Math.max(...vals);
  const span = max - min || 1;
  const pts = rows.map((s, i) => {
    const x = PAD + (i / (rows.length - 1)) * (W - 2 * PAD);
    const y = H - PAD - ((s.equity as number) - min) / span * (H - 2 * PAD);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const first = rows[0], last = rows[rows.length - 1];
  const delta = (last.equity as number) - (first.equity as number);
  const up = delta >= 0;
  return <div className="card compact-card"><h2>Equity (histórico)</h2>
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label="Curva de equity">
      <polyline points={pts} fill="none" stroke={up ? '#2fbf71' : '#e5484d'} strokeWidth={2} />
    </svg>
    <div className="hint">{rows.length} pontos · {min.toFixed(2)} – {max.toFixed(2)} · variação {up ? '+' : ''}{delta.toFixed(2)}</div>
  </div>;
}

export default function SystemHealthOnly() {
  // Telemetria local (Tauri) e saúde do core via react-query: cache, retry e refetch automático.
  const hwQ = useQuery<H>({ queryKey: ['hardware'], queryFn: () => invoke<H>('hardware_telemetry'), refetchInterval: 30000, staleTime: 25000, retry: 1 });
  const coreQ = useCoreHealth();
  const wdQ = useWatchdog();
  const telQ = useTelemetry(50);
  const histQ = useTelemetryHistory(120);
  const qQ = useQueue();
  const coreDown = coreQ.data === false;
  const ea = wdQ.data;
  const eaState = ea?.state ?? 'unknown';
  useEffect(() => {
    if (coreDown) notify('Core XAU AI PRO', 'Gateway local indisponível (127.0.0.1:9001). Verifique se o core está em execução.');
  }, [coreDown]);
  const h = hwQ.data ?? null;
  const mem = h?.memory_total_gb && h.memory_available_gb != null ? ((h.memory_total_gb - h.memory_available_gb) / h.memory_total_gb) * 100 : null;
  const at = hwQ.dataUpdatedAt ? new Date(hwQ.dataUpdatedAt).toLocaleTimeString('pt-BR') : '--';
  const core = coreQ.data === true ? 'Online' : coreDown ? 'Indisponível' : 'Verificando';
  const busy = hwQ.isFetching || coreQ.isFetching;
  const eaChip = eaState === 'alive' ? 'ok' : eaState === 'frozen' || eaState === 'stale' ? 'warn' : 'danger';
  const hbAge = ea?.heartbeat_age_sec != null ? `${Math.round(ea.heartbeat_age_sec)}s` : '--';
  return <div className="system-page">
    {coreDown && <div className="core-down" role="alert"><span className="core-dot" /> Core local fora do ar — posições e cotações podem estar desatualizadas.</div>}
    <div className="page-head"><div><h1>Sistema</h1><span className="muted">Saúde do aplicativo e desempenho do computador</span></div><div className="btn-row"><span className={`chip ${core === 'Online' ? 'ok' : 'warn'}`}>Core {core}</span><span className={`chip ${eaChip}`}>EA {EA_LABEL[eaState] ?? eaState}</span><span className={`chip ${(qQ.data?.pending ?? 0) > 0 ? 'warn' : 'ok'}`}>Fila {qQ.data?.pending ?? 0} pendente(s)</span><button type="button" className="btn primary" onClick={() => { void hwQ.refetch(); void coreQ.refetch(); void wdQ.refetch(); void telQ.refetch(); void qQ.refetch(); }} disabled={busy}>{busy ? 'Atualizando…' : 'Atualizar'}</button></div></div>
    <EquitySpark histQ={histQ} />
    <div className="metrics-grid">
      <div className="card metric-card"><span className="muted">Equity agora</span><strong>{histQ.data?.last?.equity ?? '--'}</strong><small>Último snapshot</small></div>
      <div className="card metric-card"><span className="muted">Posições</span><strong>{histQ.data?.last?.positions ?? '--'}</strong><small>Snapshots: {histQ.data?.count ?? 0}</small></div>
      <div className="card metric-card"><span className="muted">Core</span><strong>{core}</strong><small>Gateway local 9001</small></div>
      <div className="card metric-card"><span className="muted">CPU</span><strong>{h?.cpu_usage_percent == null ? '--' : `${h.cpu_usage_percent.toFixed(0)}%`}</strong><small>{h?.cpu_cores ?? '--'} núcleos</small></div>
      <div className="card metric-card"><span className="muted">Memória</span><strong>{mem == null ? '--' : `${mem.toFixed(0)}%`}</strong><small>{h?.memory_total_gb?.toFixed(1) ?? '--'} GB total</small></div>
      <div className="card metric-card"><span className="muted">Última leitura</span><strong>{at}</strong><small>Telemetria local</small></div>
    </div>
    <div className="card compact-card"><h2>Watchdog do EA</h2>
      <table className="tbl compact-table"><thead><tr><th>Item</th><th>Valor</th></tr></thead>
        <tbody>
          <tr><td>Estado</td><td>{EA_LABEL[eaState] ?? eaState}</td></tr>
          <tr><td>Idade do heartbeat</td><td>{hbAge} (TTL {ea?.ttl_sec ?? 120}s)</td></tr>
          <tr><td>Idade do arquivo</td><td>{ea?.file_age_sec != null ? `${Math.round(ea.file_age_sec)}s` : '--'}</td></tr>
        </tbody></table>
      <div className="hint">Classificação: vivo (&lt; TTL) · travado (arquivo novo, timestamp parado) · offline (arquivo velho). Somente leitura — nunca envia comandos ao MT5.</div>
    </div>
    <div className="card compact-card"><h2>Telemetria (últimos eventos)</h2>
      {(telQ.data?.events?.length ?? 0) === 0 ? <div className="hint">Sem eventos registrados ainda. Ações do Guardian e reconciliações aparecem aqui.</div> :
        <table className="tbl compact-table"><thead><tr><th>Quando</th><th>Evento</th><th>Severidade</th><th>Detalhe</th></tr></thead>
          <tbody>{telQ.data?.events?.map((ev, i) => <tr key={i}><td>{ev.ts_iso ? new Date(ev.ts_iso).toLocaleTimeString('pt-BR') : '--'}</td><td>{ev.kind}</td><td>{ev.severity}</td><td className="muted">{JSON.stringify(ev.data ?? {}).slice(0, 80)}</td></tr>)}</tbody>
        </table>}
    </div>
    <div className="card compact-card"><h2>Fila de comandos (offline)</h2>
      {(qQ.data?.recent?.length ?? 0) === 0 ? <div className="hint">Fila vazia. Comandos DEMO emitidos com o terminal MT5 offline ficam aqui e são reexecutados automaticamente quando ele volta (ordens novas ficam "skipped" para revisão manual).</div> :
        <table className="tbl compact-table"><thead><tr><th>ID</th><th>Comando</th><th>Status</th><th>Tentativas</th><th>Erro</th></tr></thead>
          <tbody>{qQ.data?.recent?.map((it) => <tr key={it.queue_id}><td className="muted">{it.queue_id}</td><td>{it.kind}</td><td><span className={`chip ${it.status === 'sent' ? 'ok' : it.status === 'pending' ? 'warn' : 'danger'}`}>{it.status}</span></td><td>{it.attempts}</td><td className="muted">{it.last_error ? String(it.last_error).slice(0, 60) : '--'}</td></tr>)}</tbody>
        </table>}
      <div className="hint">Pendentes: {qQ.data?.pending ?? 0} · Enviados: {qQ.data?.sent ?? 0} · Falhados: {qQ.data?.failed ?? 0} · Skipped: {qQ.data?.skipped ?? 0}</div>
    </div>
    <div className="card compact-card"><h2>Ambiente</h2>
      <table className="tbl compact-table"><thead><tr><th>Item</th><th>Valor</th></tr></thead>
        <tbody>
          <tr><td>Sistema operacional</td><td>{h?.os ?? '--'}</td></tr>
          <tr><td>Arquitetura</td><td>{h?.architecture ?? '--'}</td></tr>
          <tr><td>Processador</td><td>{h?.cpu_name ?? '--'}</td></tr>
          <tr><td>Placa de vídeo</td><td>{h?.gpu_name ?? '--'}</td></tr>
        </tbody></table>
    </div>
    <div className="hint">Leitura automática a cada 30 segundos com cache local. O alerta do sistema operacional avisa quando o core sai do ar.</div>
  </div>;
}