// Sistema: o que a MAQUINA do usuario esta usando, e o desempenho do app.
//
// POR QUE SO ISSO
// ===============
// A aba tinha "Watchdog do EA", "Diagnostico do boot", "Telemetria" e
// "Fila de comandos" - quatro blocos sobre a SAUDE DO APP, duplicados em
// Log, na tela de boot e no painel da fila. Nenhum deles diz algo sobre a
// maquina, que e o que a aba promete.
//
// No desktop a leitura vem do comando `hardware_telemetry` do Tauri, que
// consulta o SO real (WMI no Windows, `/proc` e sensores no Linux). Se a
// maquina nao expoe um campo, a celula fica "--" e nao zero: ausencia de
// dado nao e medida zero.
//
// No Android (APK cliente leve) a telemetria local de hardware do PC nao
// existe e tentar WMI/powershell produz erro enganoso. Nesse caso a tela
// mostra estado limpo de cliente movel e mede apenas a latencia do gateway.
//
// Nada aqui executa ordem, alteracao no MT5 ou escrita em disco.
import { useCallback, useEffect, useRef, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { apiBase, isMobileRuntime } from '../lib/api';
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
// O intervalo e folgado: uso de CPU e temperatura nao mudam em 2s. O gateway
// e medido separadamente, que e barato e e o que o usuario precisa ver mexer.
const REFRESH_MS = 10_000;
// Vida da ultima leitura entre montagens da aba.
const CACHE_MS = 10_000;

type Leitura = {
  hw: Hardware | null;
  erro: string;
  lidoEm: string;
  latencia: number | null;
  gatewayOk: boolean | null;
  mobile: boolean;
};

// Fora do componente de proposito: sobrevive a montagem/desmontagem da aba.
let ultimaLeitura: Leitura = {
  hw: null,
  erro: '',
  lidoEm: '',
  latencia: null,
  gatewayOk: null,
  mobile: false,
};
let ultimaLeituraEm = 0;

/** Somente para teste: limpa o cache de modulo entre casos. */
export function limparCacheSistema() {
  ultimaLeitura = { hw: null, erro: '', lidoEm: '', latencia: null, gatewayOk: null, mobile: false };
  ultimaLeituraEm = 0;
}

const cacheFresco = () => Date.now() - ultimaLeituraEm < CACHE_MS;

/*
  OS FORMATADORES DEVOLVEM `null`, NAO "--"
  =========================================
  Ausencia agora e OMITIR: uma linha a menos, nao uma celula com trace.
*/
const gb = (v: number | null | undefined) =>
  v === null || v === undefined || !Number.isFinite(v) ? null : `${v.toFixed(1)} GB`;
const pct = (v: number | null | undefined) =>
  v === null || v === undefined || !Number.isFinite(v) ? null : `${v.toFixed(0)}%`;
const val = (v: string | null | undefined) =>
  v && String(v).trim() ? String(v).trim() : null;

function Medida({ rotulo, valor }: { rotulo: string; valor: string | null }) {
  if (valor === null) return null;
  return (
    <div className="sys-medida">
      <span className="sys-medida-rotulo">{rotulo}</span>
      <span className="sys-medida-valor">{valor}</span>
    </div>
  );
}

function Barra({ usado, total }: { usado: number | null; total: number | null }) {
  if (usado === null || total === null || total <= 0) return null;
  const p = Math.min(100, Math.max(0, (usado / total) * 100));
  const nivel = p >= 90 ? 'danger' : p >= 75 ? 'warn' : 'ok';
  return (
    <span className="sys-bar">
      <span className={`sys-bar-fill ${nivel}`} style={{ width: `${p}%` }} />
    </span>
  );
}

/** Junta as partes que existem, sem deixar buraco duplo no meio. */
function juntar(...partes: Array<string | null>): string | null {
  const cheio = partes.filter((p): p is string => p !== null && p.length > 0);
  return cheio.length ? cheio.join(' · ') : null;
}

export default function SystemHealthOnly() {
  // Estado inicial vindo do cache: abrir a aba ja mostra o ultimo valor.
  const [hw, setHw] = useState<Hardware | null>(ultimaLeitura.hw);
  const [erro, setErro] = useState(ultimaLeitura.erro);
  const [lidoEm, setLidoEm] = useState(ultimaLeitura.lidoEm);
  // Desempenho do app medido de verdade: quanto tempo o gateway leva para
  // responder a cada leitura.
  const [latencia, setLatencia] = useState<number | null>(ultimaLeitura.latencia);
  const [gatewayOk, setGatewayOk] = useState<boolean | null>(ultimaLeitura.gatewayOk);
  const [mobile, setMobile] = useState<boolean>(ultimaLeitura.mobile || isMobileRuntime());
  // Diz quando ainda nao ha nada para mostrar.
  const [carregando, setCarregando] = useState(ultimaLeitura.hw === null && !ultimaLeitura.mobile);
  const emVoo = useRef(false);
  const lerRef = useRef<(forcado?: boolean) => void>(() => {});

  const aplicar = useCallback((nova: Leitura) => {
    ultimaLeitura = nova;
    ultimaLeituraEm = Date.now();
    setErro(nova.erro);
    setLidoEm(nova.lidoEm);
    setLatencia(nova.latencia);
    setGatewayOk(nova.gatewayOk);
    setMobile(nova.mobile);
    // So re-renderiza a tabela se os numeros mudaram de verdade.
    setHw((atual) =>
      atual && nova.hw && JSON.stringify(atual) === JSON.stringify(nova.hw) ? atual : nova.hw,
    );
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
      const mobileRuntime = isMobileRuntime();
      setMobile(mobileRuntime);
      setCarregando(ultimaLeitura.hw === null && !ultimaLeitura.mobile && !mobileRuntime);
      const t0 = performance.now();
      try {
        if (mobileRuntime) {
          // No Android o APK e cliente leve: a telemetria de hardware do PC
          // (WMI/powershell) nao existe aqui. Medimos apenas o gateway e
          // exibimos estado limpo, sem erro contraditorio.
          let ok: boolean | null = null;
          try {
            const r = await fetch(`${apiBase()}/api/health`, { signal: AbortSignal.timeout(4000) });
            ok = r.ok || r.status === 401;
          } catch {
            ok = false;
          }
          if (!vivo) return;
          aplicar({
            hw: null,
            erro: '',
            lidoEm: new Date().toLocaleTimeString('pt-BR'),
            latencia: performance.now() - t0,
            gatewayOk: ok,
            mobile: true,
          });
          return;
        }

        const dados = await invoke<Hardware>('hardware_telemetry');
        let ok: boolean | null = null;
        try {
          const r = await fetch(`${apiBase()}/api/health`, { signal: AbortSignal.timeout(4000) });
          ok = r.ok || r.status === 401;
        } catch {
          ok = false;
        }
        if (!vivo) return;
        aplicar({
          hw: dados,
          erro: '',
          lidoEm: new Date().toLocaleTimeString('pt-BR'),
          latencia: performance.now() - t0,
          gatewayOk: ok,
          mobile: false,
        });
      } catch (e) {
        if (!vivo) return;
        aplicar({
          hw: ultimaLeitura.hw,
          erro: mobileRuntime ? '' : e instanceof Error ? e.message : 'Falha ao ler a maquina',
          lidoEm: new Date().toLocaleTimeString('pt-BR'),
          latencia: performance.now() - t0,
          gatewayOk: null,
          mobile: mobileRuntime,
        });
      } finally {
        emVoo.current = false;
      }
    };
    lerRef.current = ler;
    void ler();
    const t = window.setInterval(() => {
      if (document.hidden) return;
      void ler(true);
    }, REFRESH_MS);
    const aoVoltar = () => {
      if (!document.hidden) void ler();
    };
    document.addEventListener('visibilitychange', aoVoltar);
    return () => {
      vivo = false;
      window.clearInterval(t);
      document.removeEventListener('visibilitychange', aoVoltar);
    };
  }, [aplicar]);

  const ramUsada =
    hw?.memory_total_gb != null && hw.memory_available_gb != null
      ? Math.max(0, hw.memory_total_gb - hw.memory_available_gb)
      : null;
  const discoUsado =
    hw?.disk_total_gb != null && hw.disk_free_gb != null
      ? Math.max(0, hw.disk_total_gb - hw.disk_free_gb)
      : null;

  return (
    <main className="system-page">
      <div className="page-head">
        <div>
          <span className="eyebrow">MAQUINA</span>
          <h1>Sistema</h1>
          <span className="muted">
            {mobile
              ? 'Telemetria limpa do cliente móvel e desempenho do gateway'
              : 'Leitura real do aparelho e desempenho do app'}
          </span>
        </div>
        <div className="btn-row">
          {mobile ? (
            <span className={`chip ${gatewayOk === false ? 'warn' : 'ok'}`}>
              Modo Mobile Ativo · Latência Gateway {latencia != null ? `${latencia.toFixed(0)} ms` : '—'}
            </span>
          ) : (
            <span className={`chip ${erro || carregando ? 'warn' : 'ok'}`}>
              {carregando ? 'Lendo…' : erro ? 'Falha na leitura' : 'Ao vivo'}
            </span>
          )}
          {lidoEm && <span className="muted">{lidoEm}</span>}
          <button
            type="button"
            className="btn xs ghost"
            onClick={() => lerRef.current(true)}
            disabled={carregando && !mobile}
            aria-label="Atualizar leitura da maquina"
          >
            {carregando && !mobile ? 'Atualizando…' : 'Atualizar'}
          </button>
        </div>
      </div>

      {carregando && !hw && !mobile && (
        <p className="sys-esperando" role="status">
          Lendo a máquina.
        </p>
      )}

      {erro && !mobile && (
        <div className="card compact-card sys-erro" role="status">
          {erro}
        </div>
      )}

      {mobile ? (
        <>
          <section className="sys-core" aria-labelledby="sys-core-mobile">
            <h2 id="sys-core-mobile">
              <span className="sys-core-num">Core 1</span>
              <span className="sys-core-nome">Cliente móvel</span>
              <span className="chip ok">Android</span>
            </h2>
            <div className="sys-lista">
              <Medida rotulo="Modo" valor="Mobile ativo (cliente leve)" />
              <Medida rotulo="Telemetria local do PC" valor="não aplicável neste aparelho" />
              <Medida
                rotulo="Gateway"
                valor={gatewayOk === null ? 'sem leitura' : gatewayOk ? 'respondendo' : 'sem resposta'}
              />
              <Medida rotulo="Latência do gateway" valor={latencia != null ? `${latencia.toFixed(0)} ms` : null} />
              <Medida rotulo="Atualização" valor={`${(REFRESH_MS / 1000).toFixed(0)} s`} />
              <Medida rotulo="Lida em" valor={lidoEm || null} />
            </div>
          </section>
          <p className="sys-note">
            No Android, a inferência e a telemetria pesada rodam no gateway/servidor. A leitura local de CPU, WMI e
            PowerShell do Windows não é executada neste cliente.
          </p>
        </>
      ) : (
        <>
          {/* ============== CORE 1 - MÁQUINA ============== */}
          <section className="sys-core" aria-labelledby="sys-core-1">
            <h2 id="sys-core-1">
              <span className="sys-core-num">Core 1</span>
              <span className="sys-core-nome">Máquina</span>
              {hw?.source && <span className="chip">{hw.source}</span>}
            </h2>
            <div className="sys-lista">
              <Medida rotulo="Sistema" valor={juntar(val(hw?.os), val(hw?.architecture))} />
              <Medida
                rotulo="Processador"
                valor={juntar(val(hw?.cpu_name), hw?.cpu_cores ? `${hw.cpu_cores} núcleos` : null)}
              />
              <Medida
                rotulo="Temperatura"
                valor={hw?.cpu_temperature_c != null ? `${hw.cpu_temperature_c.toFixed(0)} °C` : null}
              />
              <Medida
                rotulo="Vídeo"
                valor={hw?.gpu_available ? val(hw?.gpu_name) : 'não exposto pelo sistema'}
              />
            </div>
          </section>

          {/* ============== CORE 2 - RECURSOS ============== */}
          <section className="sys-core" aria-labelledby="sys-core-2">
            <h2 id="sys-core-2">
              <span className="sys-core-num">Core 2</span>
              <span className="sys-core-nome">Recursos</span>
            </h2>
            <div className="sys-lista">
              {pct(hw?.cpu_usage_percent) !== null && (
                <Recurso
                  nome="CPU"
                  barra={<Barra usado={hw?.cpu_usage_percent ?? null} total={100} />}
                  uso={pct(hw?.cpu_usage_percent)}
                  detalhe={hw?.cpu_cores ? `${hw.cpu_cores} núcleos` : null}
                />
              )}
              {ramUsada !== null && (
                <Recurso
                  nome="Memória"
                  barra={<Barra usado={ramUsada} total={hw?.memory_total_gb ?? null} />}
                  uso={
                    hw?.memory_total_gb && ramUsada !== null
                      ? pct((ramUsada / hw.memory_total_gb) * 100)
                      : null
                  }
                  detalhe={juntar(gb(hw?.memory_total_gb), `${gb(hw?.memory_available_gb)} livres`)}
                />
              )}
              {discoUsado !== null && (
                <Recurso
                  nome="Disco C:"
                  barra={<Barra usado={discoUsado} total={hw?.disk_total_gb ?? null} />}
                  uso={
                    hw?.disk_total_gb && discoUsado !== null
                      ? pct((discoUsado / hw.disk_total_gb) * 100)
                      : null
                  }
                  detalhe={juntar(gb(hw?.disk_total_gb), `${gb(hw?.disk_free_gb)} livres`)}
                />
              )}
              {pct(hw?.cpu_usage_percent) === null && ramUsada === null && discoUsado === null && (
                <p className="sys-sem-dado">O sistema não expõe medição de uso.</p>
              )}
            </div>
          </section>

          {/* ============== CORE 3 - APP ============== */}
          <section className="sys-core" aria-labelledby="sys-core-3">
            <h2 id="sys-core-3">
              <span className="sys-core-num">Core 3</span>
              <span className="sys-core-nome">Aplicativo</span>
              <span className={`chip ${gatewayOk === null ? 'warn' : gatewayOk ? 'ok' : 'danger'}`}>
                {gatewayOk === null ? 'Sem leitura' : gatewayOk ? 'Gateway ok' : 'Gateway sem resposta'}
              </span>
            </h2>
            <div className="sys-lista">
              <Medida rotulo="Latência da leitura" valor={latencia != null ? `${latencia.toFixed(0)} ms` : null} />
              <Medida rotulo="Intervalo de atualização" valor={`${(REFRESH_MS / 1000).toFixed(0)} s`} />
              <Medida rotulo="Origem da leitura" valor={val(hw?.source)} />
            </div>
          </section>

          {/* ============== CORE 4 - LEITURA ============== */}
          <section className="sys-core" aria-labelledby="sys-core-4">
            <h2 id="sys-core-4">
              <span className="sys-core-num">Core 4</span>
              <span className="sys-core-nome">Leitura</span>
            </h2>
            <div className="sys-lista">
              <Medida rotulo="Lida em" valor={lidoEm || null} />
              <Medida
                rotulo="Coleta"
                valor={hw?.source === 'WMI' ? 'WMI no Windows' : hw?.source ? String(hw.source) : null}
              />
              <Medida rotulo="Estado" valor={erro ? 'falha na leitura' : carregando ? 'lendo…' : 'ao vivo'} />
            </div>
          </section>
        </>
      )}
    </main>
  );
}

/** Uma linha de recurso: nome, barra, porcentagem e detalhe. */
function Recurso({
  nome,
  barra,
  uso,
  detalhe,
}: {
  nome: string;
  barra: React.ReactNode;
  uso: string | null;
  detalhe: string | null;
}) {
  return (
    <div className="sys-recurso">
      <span className="sys-recurso-nome">{nome}</span>
      {barra}
      {uso && <span className="sys-recurso-uso">{uso}</span>}
      {detalhe && <span className="sys-recurso-detalhe">{detalhe}</span>}
    </div>
  );
}
