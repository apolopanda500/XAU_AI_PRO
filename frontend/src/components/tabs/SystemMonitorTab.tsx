import { useState, useEffect, useRef } from 'react';
import { useAppStore } from '../../hooks/useAppStore';

interface LogEntry {
  id: number;
  timestamp: string;
  level: 'info' | 'warn' | 'error';
  message: string;
}

const LOGS_INICIAIS: LogEntry[] = [
  { id: 1, timestamp: '10:30:01', level: 'info', message: 'Sistema inicializado com sucesso' },
  { id: 2, timestamp: '10:30:02', level: 'info', message: 'Conexão WebSocket estabelecida' },
  { id: 3, timestamp: '10:30:05', level: 'warn', message: 'Latência acima do esperado (250ms)' },
  { id: 4, timestamp: '10:31:00', level: 'info', message: 'MT5 conectado - servidor OK' },
  { id: 5, timestamp: '10:32:15', level: 'error', message: 'Falha ao enviar ordem #1002: saldo insuficiente' },
];

const MENSAGENS_LOG = [
  'Heartbeat enviado - latência OK',
  'Cotação XAUUSD atualizada: 2345.50',
  'Ordem #1003 executada com sucesso',
  'Margin level: 245% - saudável',
  'IA processando sinal de compra EURUSD',
  'WebSocket reconectado automaticamente',
  'Cache de cotacoes limpo',
  'Robô EA reportou status: ativo',
];

function CircularProgress({ valor, max, tamanho = 90, espessura = 8, cor }: { valor: number; max: number; tamanho?: number; espessura?: number; cor: string }) {
  const raio = (tamanho - espessura) / 2;
  const circunferencia = 2 * Math.PI * raio;
  const progresso = Math.min(valor / max, 1);
  const offset = circunferencia * (1 - progresso);

  return (
    <svg width={tamanho} height={tamanho} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={tamanho/2} cy={tamanho/2} r={raio} fill="none" stroke="var(--border)" strokeWidth={espessura} />
      <circle cx={tamanho/2} cy={tamanho/2} r={raio} fill="none" stroke={cor} strokeWidth={espessura}
        strokeDasharray={circunferencia} strokeDashoffset={offset} strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 0.5s ease' }} />
    </svg>
  );
}

export default function SystemMonitorTab() {
  const systemState = useAppStore((s) => s.systemState);
  const wsConnected = useAppStore((s) => s.wsConnected);
  const [logs] = useState<LogEntry[]>([]);
  const cpuUsage = 0;
  const memUsage = 0;
  const diskUsage = 0;
  const latencia = 0;
  const temperatura = 0;

  // Métricas reais ainda não são fornecidas pelo Core; não gerar números.

  const corCpu = cpuUsage > 80 ? '#ef4444' : cpuUsage > 50 ? '#eab308' : 'var(--ok)';
  const corMem = memUsage > 80 ? '#ef4444' : memUsage > 50 ? '#eab308' : 'var(--primary)';
  const corDisk = diskUsage > 80 ? '#ef4444' : 'var(--muted)';
  const corTemp = temperatura > 75 ? '#ef4444' : temperatura > 60 ? '#eab308' : 'var(--ok)';

  return (
    <div>
      <div className="page-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Monitor do Sistema</h1>
          <span className="muted">CPU, memória, disco, rede e temperatura em tempo real</span>
        </div>
        <span className={wsConnected ? 'chip ok' : 'chip danger'}>{wsConnected ? '● Online' : '○ Offline'}</span>
      </div>

      <div className="grid cols-4" style={{ marginBottom: 14 }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <div className="kpi-label">CPU</div>
          <div style={{ position: 'relative', display: 'inline-block', margin: '8px 0' }}>
            <CircularProgress valor={cpuUsage} max={100} cor={corCpu} />
            <span style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', fontWeight: 700, fontSize: 16 }}>{cpuUsage.toFixed(0)}%</span>
          </div>
          <div className="kpi-sub">8 threads</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div className="kpi-label">Memória RAM</div>
          <div style={{ margin: '16px 0' }}>
            <div style={{ background: 'var(--border)', borderRadius: 6, height: 12, overflow: 'hidden' }}>
              <div style={{ width: `${memUsage}%`, height: '100%', background: corMem, borderRadius: 6, transition: 'width 0.5s ease' }} />
            </div>
            <div className="kpi-value" style={{ fontSize: 16, marginTop: 8 }}>{memUsage.toFixed(0)}%</div>
          </div>
          <div className="kpi-sub">{(memUsage * 0.16).toFixed(1)} GB / 16 GB</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div className="kpi-label">Disco</div>
          <div style={{ margin: '16px 0' }}>
            <div style={{ background: 'var(--border)', borderRadius: 6, height: 12, overflow: 'hidden' }}>
              <div style={{ width: `${diskUsage}%`, height: '100%', background: corDisk, borderRadius: 6, transition: 'width 0.5s ease' }} />
            </div>
            <div className="kpi-value" style={{ fontSize: 16, marginTop: 8 }}>{diskUsage.toFixed(0)}%</div>
          </div>
          <div className="kpi-sub">{(diskUsage * 5.12).toFixed(0)} GB / 512 GB</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div className="kpi-label">Rede (Latência)</div>
          <div className="kpi-value" style={{ fontSize: 28, margin: '12px 0' }}>{latencia.toFixed(0)}</div>
          <div className="kpi-sub">ms</div>
          <div className="kpi-sub">{latencia < 100 ? '▲ Rápida' : latencia < 200 ? '● Normal' : '▼ Lenta'}</div>
        </div>
      </div>

      <div className="grid cols-2" style={{ marginBottom: 14 }}>
        <div className="card">
          <h2>Temperatura</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 12 }}>
            <CircularProgress valor={temperatura} max={100} tamanho={80} espessura={6} cor={corTemp} />
            <div>
              <div className="kpi-value" style={{ fontSize: 24 }}>{temperatura.toFixed(1)}°C</div>
              <div className="kpi-sub">{temperatura > 75 ? '⚠ Superaquecimento' : temperatura > 60 ? '● Aquecido' : '✓ Normal'}</div>
            </div>
          </div>
        </div>
        <div className="card">
          <h2>Estado do Core</h2>
          {systemState ? (
            <div className="tbl-wrap">
              <table className="tbl"><tbody>
                <tr><td>Status</td><td className="mono">{systemState.status}</td></tr>
                <tr><td>Uptime</td><td className="mono">{Math.floor(systemState.uptime_sec / 60)}m {systemState.uptime_sec % 60}s</td></tr>
                <tr><td>Clientes WS</td><td className="mono">{systemState.ws_clients}</td></tr>
                <tr><td>MT5</td><td><span className={systemState.mt5_connected ? 'chip ok' : 'chip warn'}>{systemState.mt5_connected ? 'Conectado' : 'Desconectado'}</span></td></tr>
                <tr><td>IA</td><td><span className={systemState.ai_enabled ? 'chip primary' : ''}>{systemState.ai_enabled ? 'Ativa' : 'Inativa'}</span></td></tr>
              </tbody></table>
            </div>
          ) : (
            <span className="muted">aguardando estado...</span>
          )}
        </div>
      </div>

      <div className="card">
        <h2>Logs do Sistema</h2>
        <div className="log-box" style={{ maxHeight: 220, fontSize: 12 }}>
          {logs.map((log) => (
            <div key={log.id} style={{ color: log.level === 'error' ? 'var(--danger)' : log.level === 'warn' ? 'var(--warn)' : 'var(--text)' }}>
              <span className="muted">[{log.timestamp}]</span> {log.message}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
