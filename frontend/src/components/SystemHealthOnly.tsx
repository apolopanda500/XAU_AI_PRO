import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useCoreHealth, useWatchdog, useTelemetry, useTelemetryHistory, useQueue, useBoot } from '../hooks/queries';
import { notify } from '../lib/notify';

type H = { os?: string; architecture?: string; cpu_name?: string; gpu_name?: string; cpu_usage_percent?: number; cpu_cores?: number; memory_total_gb?: number; memory_available_gb?: number };

const EA_LABEL: Record<string, string> = {
  alive: 'Vivo', frozen: 'Travado (arquivo fresh, timestamp parado)',
  stale: 'Offline (heartbeat antigo)', missing: 'Sem heartbeat (EA n�o iniciou)',
  unknown: 'Indeterminado',
};

export default function SystemHealthOnly() {
  // Telemetria local (Tauri) e sa�de do core via react-query: cache, retry e refetch autom�tico.
  const hwQ = useQuery<H>({ queryKey: ['hardware'], queryFn: () => invoke<H>('hardware_telemetry'), refetchInterval: 30000, staleTime: 25000, retry: 1 });
  const coreQ = useCoreHealth();
  const wdQ = useWatchdog();
  const telQ = useTelemetry(50);
  const histQ = useTelemetryHistory(120);
  const qQ = useQueue();
  const bootQ = useBoot();
  const boot = bootQ.data;
  const bootSnap = boot?.snapshot ?? null;
  const coreDown = coreQ.data === false;
  const ea = wdQ.data;
  const eaState = ea?.state ?? 'unknown';
  useEffect(() => {
    if (coreDown) notify('Core XAU AI PRO', 'Gateway local indispon�vel (127.0.0.1:9001). Verifique se o core est� em execu��o.');
  }, [coreDown]);
  const h = hwQ.data ?? null;
  const mem = h?.memory_total_gb && h.memory_available_gb != null ? ((h.memory_total_gb - h.memory_available_gb) / h.memory_total_gb) * 100 : null;
  const at = hwQ.dataUpdatedAt ? new Date(hwQ.dataUpdatedAt).toLocaleTimeString('pt-BR') : '--';
  const core = coreQ.data === true ? 'Online' : coreDown ? 'Indispon�vel' : 'Verificando';
  const busy = hwQ.isFetching || coreQ.isFetching;
  const eaChip = eaState === 'alive' ? 'ok' : eaState === 'frozen' || eaState === 'stale' ? 'warn' : 'danger';
  const hbAge = ea?.heartbeat_age_sec != null ? `${Math.round(ea.heartbeat_age_sec)}s` : '--';
  return <div className="system-page">
    {coreDown && <div className="core-down" role="alert"><span className="core-dot" /> Core local fora do ar � posi��es e cota��es podem estar desatualizadas.</div>}
    <div className="page-head"><div><h1>Sistema</h1><span className="muted">Sa�de do aplicativo e desempenho do computador</span></div><div className="btn-row"><span className={`chip ${core === 'Online' ? 'ok' : 'warn'}`}>Core {core}</span><span className={`chip ${eaChip}`}>EA {EA_LABEL[eaState] ?? eaState}</span><span className={`chip ${(qQ.data?.pending ?? 0) > 0 ? 'warn' : 'ok'}`}>Fila {qQ.data?.pending ?? 0} pendente(s)</span><button type="button" className="btn primary" onClick={() => { void hwQ.refetch(); void coreQ.refetch(); void wdQ.refetch(); void telQ.refetch(); void qQ.refetch(); }} disabled={busy}>{busy ? 'Atualizando�' : 'Atualizar'}</button></div></div>
    <div className="metrics-grid">
      <div className="card metric-card"><span className="muted">Core</span><strong>{core}</strong><small>Gateway local 9001</small></div>
      <div className="card metric-card"><span className="muted">CPU</span><strong>{h?.cpu_usage_percent == null ? '--' : `${h.cpu_usage_percent.toFixed(0)}%`}</strong><small>{h?.cpu_cores ?? '--'} núcleos</small></div>
      <div className="card metric-card"><span className="muted">Memória</span><strong>{mem == null ? '--' : `${mem.toFixed(0)}%`}</strong><small>{h?.memory_total_gb?.toFixed(1) ?? '--'} GB total</small></div>
      <div className="card metric-card"><span className="muted">Snapshots</span><strong>{histQ.data?.count ?? 0}</strong><small>registros do coletor</small></div>
      <div className="card metric-card"><span className="muted">Ultima leitura</span><strong>{at}</strong><small>Telemetria local</small></div>
    </div>
    <div className="card compact-card"><h2>Watchdog do EA</h2>
      <table className="tbl compact-table"><thead><tr><th>Item</th><th>Valor</th></tr></thead>
        <tbody>
          <tr><td>Estado</td><td>{EA_LABEL[eaState] ?? eaState}</td></tr>
          <tr><td>Idade do heartbeat</td><td>{hbAge} (TTL {ea?.ttl_sec ?? 120}s)</td></tr>
          <tr><td>Idade do arquivo</td><td>{ea?.file_age_sec != null ? `${Math.round(ea.file_age_sec)}s` : '--'}</td></tr>
        </tbody></table>
      <div className="hint">Classificacao: vivo (&lt; TTL) - travado (arquivo novo, timestamp parado) - offline (arquivo velho). Somente leitura, nunca envia comandos ao MT5.</div>
    </div>
    <div className="card compact-card"><h2>Diagnostico do boot</h2>
      {boot == null ? <div className="hint">Carregando relatorio do boot...</div> :
        <table className="tbl compact-table"><thead><tr><th>Item</th><th>Valor</th></tr></thead>
          <tbody>
            <tr><td>MT5 pronto</td><td>{boot.mt5_ready ? 'Sim' : 'Nao'}</td></tr>
            <tr><td>Posicoes no boot</td><td>{bootSnap?.positions ?? '--'}</td></tr>
            <tr><td>EA no boot</td><td>{EA_LABEL[bootSnap?.ea_state ?? 'unknown'] ?? bootSnap?.ea_state ?? '--'}</td></tr>
          </tbody></table>}
      <div className="hint">Reconciliacao de intents + primeiro snapshot de telemetria, sem reexecutar loops.</div>
    </div>
    <div className="card compact-card"><h2>Telemetria (�ltimos eventos)</h2>
      {(telQ.data?.events?.length ?? 0) === 0 ? <div className="hint">Sem eventos registrados ainda. A��es do Guardian e reconcilia��es aparecem aqui.</div> :
        <table className="tbl compact-table"><thead><tr><th>Quando</th><th>Evento</th><th>Severidade</th><th>Detalhe</th></tr></thead>
          <tbody>{telQ.data?.events?.map((ev, i) => <tr key={i}><td>{ev.ts_iso ? new Date(ev.ts_iso).toLocaleTimeString('pt-BR') : '--'}</td><td>{ev.kind}</td><td>{ev.severity}</td><td className="muted">{JSON.stringify(ev.data ?? {}).slice(0, 80)}</td></tr>)}</tbody>
        </table>}
    </div>
    <div className="card compact-card"><h2>Fila de comandos (offline)</h2>
      {(qQ.data?.recent?.length ?? 0) === 0 ? <div className="hint">Fila vazia. Comandos DEMO emitidos com o terminal MT5 offline ficam aqui e s�o reexecutados automaticamente quando ele volta (ordens novas ficam "skipped" para revis�o manual).</div> :
        <table className="tbl compact-table"><thead><tr><th>ID</th><th>Comando</th><th>Status</th><th>Tentativas</th><th>Erro</th></tr></thead>
          <tbody>{qQ.data?.recent?.map((it) => <tr key={it.queue_id}><td className="muted">{it.queue_id}</td><td>{it.kind}</td><td><span className={`chip ${it.status === 'sent' ? 'ok' : it.status === 'pending' ? 'warn' : 'danger'}`}>{it.status}</span></td><td>{it.attempts}</td><td className="muted">{it.last_error ? String(it.last_error).slice(0, 60) : '--'}</td></tr>)}</tbody>
        </table>}
      <div className="hint">Pendentes: {qQ.data?.pending ?? 0} � Enviados: {qQ.data?.sent ?? 0} � Falhados: {qQ.data?.failed ?? 0} � Skipped: {qQ.data?.skipped ?? 0}</div>
    </div>
    <div className="card compact-card"><h2>Ambiente</h2>
      <table className="tbl compact-table"><thead><tr><th>Item</th><th>Valor</th></tr></thead>
        <tbody>
          <tr><td>Sistema operacional</td><td>{h?.os ?? '--'}</td></tr>
          <tr><td>Arquitetura</td><td>{h?.architecture ?? '--'}</td></tr>
          <tr><td>Processador</td><td>{h?.cpu_name ?? '--'}</td></tr>
          <tr><td>Placa de v�deo</td><td>{h?.gpu_name ?? '--'}</td></tr>
        </tbody></table>
    </div>
    <div className="hint">Leitura autom�tica a cada 30 segundos com cache local. O alerta do sistema operacional avisa quando o core sai do ar.</div>
  </div>;
}
