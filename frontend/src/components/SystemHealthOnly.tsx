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
//
// POR QUE TEM CACHE AQUI TAMBEM
// =============================
// O comando ja guarda 8 s no lado Rust (TELEMETRY_CACHE), mas isso so evita
// coletas DUPLICAS dentro de uma mesma abertura da aba. Trocar de aba e
// voltar desmontava o componente: o estado voltava ao zero, a tabela inteira
// aparecia "--" e uma nova leitura partia do zero — o usuario lia como
// "recarregou sozinho". O cache de modulo abaixo mantem a ultima leitura
// viva entre montagens, e o estado de carregamento diz quando o dado ainda
// nao existe em vez de fingir que tudo esta em "--".
//
// O intervalo tambem nao roda com a janela oculta: sem isso o powershell
// ficava abrindo em segundo plano sem ninguem olhar.
import { useCallback, useEffect, useRef, useState } from 'react';
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

// A leitura no Windows abre um powershell.exe e roda cinco consultas CIM.
// Com 2s eram 30 processos por minuto e o app MORREU (os filhos ficaram
// orfaos e todas as abas passaram a dizer "gateway indisponivel"). Alem do
// cache de 8s no lado Rust, o intervalo aqui tambem e folgado: uso de CPU e
// temperatura nao mudam em 2s. O gateway e medido separadamente, que e
// barato e e o que o usuario precisa ver mexer.
const REFRESH_MS = 10_000;
// Vida da ultima leitura entre montagens da aba. Igual ao intervalo: o
// proximo tick ja busca dados novos, mas voltar para a aba mostra a ultima
// leitura na hora em vez de apagar a tela.
const CACHE_MS = 10_000;

type Leitura = {
  hw: Hardware | null;
  erro: string;
  lidoEm: string;
  latencia: number | null;
  gatewayOk: boolean | null;
};

// Fora do componente de proposito: sobrevive a montagem/desmontagem da aba.
let ultimaLeitura: Leitura = { hw: null, erro: '', lidoEm: '', latencia: null, gatewayOk: null };
let ultimaLeituraEm = 0;

/** Somente para teste: limpa o cache de modulo entre casos. */
export function limparCacheSistema() {
  ultimaLeitura = { hw: null, erro: '', lidoEm: '', latencia: null, gatewayOk: null };
  ultimaLeituraEm = 0;
}

const cacheFresco = () => Date.now() - ultimaLeituraEm < CACHE_MS;

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
  // Estado inicial vindo do cache: abrir a aba ja mostra o ultimo valor.
  const [hw, setHw] = useState<Hardware | null>(ultimaLeitura.hw);
  const [erro, setErro] = useState(ultimaLeitura.erro);
  const [lidoEm, setLidoEm] = useState(ultimaLeitura.lidoEm);
  // Desempenho do app medido de verdade: quanto tempo o gateway leva para
  // responder a cada leitura. Nao ha como o JavaScript ler a memoria do
  // proprio processo, entao o que e medido aqui e a latencia real, que e o
  // sintoma que o usuario sente quando o app trava.
  const [latencia, setLatencia] = useState<number | null>(ultimaLeitura.latencia);
  const [gatewayOk, setGatewayOk] = useState<boolean | null>(ultimaLeitura.gatewayOk);
  // Diz quando ainda nao ha nada para mostrar. Sem isso a cabeca mostrava
  // "Ao vivo" enquanto a tabela dizia "--" em tudo.
  const [carregando, setCarregando] = useState(ultimaLeitura.hw === null);
  const emVoo = useRef(false);
  const lerRef = useRef<(forcado?: boolean) => void>(() => {});

  const aplicar = useCallback((nova: Leitura) => {
    ultimaLeitura = nova;
    ultimaLeituraEm = Date.now();
    setErro(nova.erro);
    setLidoEm(nova.lidoEm);
    setLatencia(nova.latencia);
    setGatewayOk(nova.gatewayOk);
    // So re-renderiza a tabela se os numeros mudaram de verdade: um tick que
    // devolve a mesma leitura nao deve mexer na tela.
    setHw((atual) => (
      atual && nova.hw && JSON.stringify(atual) === JSON.stringify(nova.hw) ? atual : nova.hw
    ));
    setCarregando(false);
  }, []);

  useEffect(() => {
    let vivo = true;
    const ler = async (forcado = false) => {
      if (emVoo.current) return;
      if (!forcado && cacheFresco()) {
        aplicar(ultimaLeitura);
        return;
      }
      emVoo.current = true;
      setCarregando(ultimaLeitura.hw === null);
      const t0 = performance.now();
      try {
        const dados = await invoke<Hardware>('hardware_telemetry');
        const r = await fetch(`${apiBase()}/api/health`, { signal: AbortSignal.timeout(4000) });
        if (!vivo) return;
        aplicar({
          hw: dados,
          erro: '',
          lidoEm: new Date().toLocaleTimeString('pt-BR'),
          latencia: performance.now() - t0,
          gatewayOk: r.ok,
        });
      } catch (e) {
        if (!vivo) return;
        aplicar({
          hw: ultimaLeitura.hw,
          erro: e instanceof Error ? e.message : 'Falha ao ler a maquina',
          lidoEm: new Date().toLocaleTimeString('pt-BR'),
          latencia: performance.now() - t0,
          gatewayOk: null,
        });
      } finally {
        emVoo.current = false;
      }
    };
    lerRef.current = ler;
    void ler();
    const t = window.setInterval(() => {
      // Janela oculta nao gasta powershell: o tick de verdade e quando o
      // usuario volta a olhar (abaixo, visibilitychange).
      if (document.hidden) return;
      void ler(true);
    }, REFRESH_MS);
    const aoVoltar = () => { if (!document.hidden) void ler(); };
    document.addEventListener('visibilitychange', aoVoltar);
    return () => {
      vivo = false;
      window.clearInterval(t);
      document.removeEventListener('visibilitychange', aoVoltar);
    };
  }, [aplicar]);

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
          <span className={`chip ${erro || carregando ? 'warn' : 'ok'}`}>
            {carregando ? 'Lendo…' : erro ? 'Falha na leitura' : 'Ao vivo'}
          </span>
          {lidoEm && <span className="muted">{lidoEm}</span>}
          <button
            type="button"
            className="btn xs ghost"
            onClick={() => lerRef.current(true)}
            disabled={carregando}
            aria-label="Atualizar leitura da maquina"
          >
            {carregando ? 'Atualizando…' : 'Atualizar'}
          </button>
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
      </section>

      <section className="card compact-card" aria-labelledby="sys-app">
        <div className="section-head">
          <h2 id="sys-app">Desempenho do app</h2>
          <span className={`chip ${gatewayOk === null ? 'warn' : gatewayOk ? 'ok' : 'danger'}`}>
            {gatewayOk === null ? 'Sem leitura' : gatewayOk ? 'Gateway ok' : 'Gateway sem resposta'}
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
