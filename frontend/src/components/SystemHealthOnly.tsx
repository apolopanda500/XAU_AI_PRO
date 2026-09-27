// Sistema: o que a MAQUINA do usuario esta usando, e o desempenho do app.
//
// POR QUE SO ISSO
// ===============
// A aba tinha "Watchdog do EA", "Diagnostico do boot", "Telemetria" e
// "Fila de comandos" — quatro blocos sobre a SAUDE DO APP, duplicados em
// Log, na tela de boot e no painel da fila. Nenhum deles diz algo sobre a
// maquina, que e o que a aba promete.
//
// A leitura vem do comando `hardware_telemetry` do Tauri, que consulta o
// SO real (WMI no Windows, `/proc` e sensores no Linux, campos nativos no
// Android). Se a maquina nao expoe um campo, a celula fica "--" e nao zero:
// ausencia de dado nao e medida zero.
//
// Nada aqui executa ordem, alteracao no MT5 ou escrita em disco.
import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { apiBase } from '../lib/api';
import '../theme/system-machine.css';

type Hardware = {
  os: string;
  architecture: string;
  cpu_name: string | null;
  cpu_cores: number;
  cpu_usage_percent: number | null;
  memory_total_gb: number | null;
  memory_available_gb: number | null;
  disk_total_gb: number | null;
  disk_free_gb: number | null;
  cpu_temperature_c: number | null;
  gpu_name: string | null;
  gpu_available: boolean;
  source: string;
};

const REFRESH_MS = 2_000;

const gb = (v: number | null | undefined) =>
  v === null || v === undefined || !Number.isFinite(v) ? '--' : `${v.toFixed(1)} GB`;
const pct = (v: number | null | undefined) =>
  v === null || v === undefined || !Number.isFinite(v) ? '--' : `${v.toFixed(0)}%`;
const val = (v: string | null | undefined) => (v && String(v).trim() ? String(v).trim() : '--');

/** Barra de ocupacao. `None` = a maquina nao expoe o dado. */
function Barra({ usado, total }: { usado: number | null; total: number | null }) {
  if (usado === null || total === null || total <= 0) return <span className="muted">--</span>;
  const p = Math.min(100, Math.max(0, (usado / total) * 100));
  const nivel = p >= 90 ? 'danger' : p >= 75 ? 'warn' : 'ok';
  return (
    <span className="sys-bar-cell">
      <span className="sys-bar"><span className={`sys-bar-fill ${nivel}`} style={{ width: `${p}%` }} /></span>
      <span className="sys-bar-num">{p.toFixed(0)}%</span>
    </span>
  );
}

export default function SystemHealthOnly() {
  const [hw, setHw] = useState<Hardware | null>(null);
  const [erro, setErro] = useState('');
  const [lidoEm, setLidoEm] = useState<string>('');
  // Desempenho do app medido de verdade: quanto tempo o gateway leva para
  // responder a cada leitura. Nao ha como o JavaScript ler a memoria do
  // proprio processo, entao o que e medido aqui e a latencia real, que e o
  // sintoma que o usuario sente quando o app trava.
  const [latencia, setLatencia] = useState<number | null>(null);
  const [gatewayOk, setGatewayOk] = useState<boolean | null>(null);

  useEffect(() => {
    let vivo = true;
    const ler = async () => {
      const t0 = performance.now();
      try {
        const dados = await invoke<Hardware>('hardware_telemetry');
        if (!vivo) return;
        setHw(dados);
        setErro('');
        setLidoEm(new Date().toLocaleTimeString('pt-BR'));
        const r = await fetch(`${apiBase()}/api/health`, { signal: AbortSignal.timeout(4000) });
        if (vivo) {
          setGatewayOk(r.ok);
          setLatencia(performance.now() - t0);
        }
      } catch (e) {
        if (!vivo) return;
        setErro(e instanceof Error ? e.message : 'Falha ao ler a maquina');
        setLatencia(performance.now() - t0);
      }
    };
    void ler();
    const t = window.setInterval(ler, REFRESH_MS);
    return () => { vivo = false; window.clearInterval(t); };
  }, []);

  const ramUsada = hw?.memory_total_gb != null && hw.memory_available_gb != null
    ? Math.max(0, hw.memory_total_gb - hw.memory_available_gb)
    : null;
  const discoUsado = hw?.disk_total_gb != null && hw.disk_free_gb != null
    ? Math.max(0, hw.disk_total_gb - hw.disk_free_gb)
    : null;

  return (
    <main className="system-page">
      <div className="page-head">
        <div>
          <span className="eyebrow">MAQUINA</span>
          <h1>Sistema</h1>
          <span className="muted">Leitura real do aparelho e desempenho do app</span>
        </div>
        <div className="btn-row">
          <span className={`chip ${erro ? 'warn' : 'ok'}`}>{erro ? 'Falha na leitura' : 'Ao vivo'}</span>
          {lidoEm && <span className="muted">{lidoEm}</span>}
        </div>
      </div>

      {erro && <div className="card compact-card sys-erro" role="status">{erro}</div>}

      <section className="card compact-card" aria-labelledby="sys-maquina">
        <div className="section-head">
          <h2 id="sys-maquina">Maquina</h2>
          {hw?.source && <span className="chip">{hw.source}</span>}
        </div>
        <div className="table-scroll">
          <table className="tbl compact-table sys-grid">
            <caption className="sr-only">Especificacoes e uso atual da maquina</caption>
            <thead>
              <tr>
                <th>Item</th><th>Modelo</th>
                <th className="num">Total</th><th className="num">Livre</th>
                <th className="sys-th-bar">Uso</th><th className="num">Extra</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Sistema</td>
                <td>{val(hw?.os)}</td>
                <td className="num muted">{val(hw?.architecture)}</td>
                <td className="num muted">--</td>
                <td className="muted">--</td>
                <td className="num muted">--</td>
              </tr>
              <tr>
                <td>Processador</td>
                <td>{val(hw?.cpu_name)}</td>
                <td className="num">{hw?.cpu_cores ? `${hw.cpu_cores} nucleos` : '--'}</td>
                <td className="num muted">--</td>
                <td className="muted">--</td>
                <td className="num">{hw?.cpu_temperature_c != null ? `${hw.cpu_temperature_c.toFixed(0)} °C` : '--'}</td>
              </tr>
              <tr>
                <td>CPU em uso</td>
                <td className="muted">carga</td>
                <td className="num muted">--</td>
                <td className="num muted">--</td>
                <td><Barra usado={hw?.cpu_usage_percent ?? null} total={100} /></td>
                <td className="num">{pct(hw?.cpu_usage_percent)}</td>
              </tr>
              <tr>
                <td>Video</td>
                <td>{hw?.gpu_available ? val(hw?.gpu_name) : <span className="muted">nao exposto pelo sistema</span>}</td>
                <td className="num muted">--</td>
                <td className="num muted">--</td>
                <td className="muted">--</td>
                <td className="num muted">--</td>
              </tr>
              <tr>
                <td>Memoria</td>
                <td>RAM</td>
                <td className="num">{gb(hw?.memory_total_gb)}</td>
                <td className="num">{gb(hw?.memory_available_gb)}</td>
                <td><Barra usado={ramUsada} total={hw?.memory_total_gb ?? null} /></td>
                <td className="num muted">--</td>
              </tr>
              <tr>
                <td>Disco</td>
                <td>Sistema (C:)</td>
                <td className="num">{gb(hw?.disk_total_gb)}</td>
                <td className="num">{gb(hw?.disk_free_gb)}</td>
                <td><Barra usado={discoUsado} total={hw?.disk_total_gb ?? null} /></td>
                <td className="num muted">--</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="sys-note">
          Celula "--" significa que o sistema nao expoe a informacao, nao que o valor e zero.
        </p>
      </section>

      <section className="card compact-card" aria-labelledby="sys-app">
        <div className="section-head">
          <h2 id="sys-app">Desempenho do app</h2>
          <span className={`chip ${gatewayOk === null ? 'warn' : gatewayOk ? 'ok' : 'danger'}`}>
            {gatewayOk === null ? 'sem leitura' : gatewayOk ? 'gateway ok' : 'gateway sem resposta'}
          </span>
        </div>
        <div className="table-scroll">
          <table className="tbl compact-table sys-grid">
            <caption className="sr-only">Desempenho medido do aplicativo</caption>
            <thead>
              <tr><th>Medida</th><th className="num">Valor</th><th>Referencia</th></tr>
            </thead>
            <tbody>
              <tr>
                <td>Latencia de leitura</td>
                <td className="num">{latencia != null ? `${latencia.toFixed(0)} ms` : '--'}</td>
                <td className="muted">tempo de hardware + gateway, medido a cada {REFRESH_MS / 1000}s</td>
              </tr>
              <tr>
                <td>Intervalo de atualizacao</td>
                <td className="num">{(REFRESH_MS / 1000).toFixed(0)} s</td>
                <td className="muted">esta aba</td>
              </tr>
              <tr>
                <td>Origem da leitura</td>
                <td className="num">{val(hw?.source)}</td>
                <td className="muted">WMI no Windows, /proc no Linux, campos nativos no Android</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
