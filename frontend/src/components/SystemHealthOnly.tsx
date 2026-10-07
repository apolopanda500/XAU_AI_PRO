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

/*
  OS FORMATADORES DEVOLVEM `null`, NAO "--"
  =========================================
  Isto mudou em 05/10/2026. Antes `gb`, `pct` e `val` devolviam a string "--"
  quando o dado nao existia, e a tabela de Maquina tinha SEIS colunas — quatro
  delas quase sempre "--".

  A tela ficava coberta de trace, e o operador lia aquilo como "o sistema esta
  com defeito" quando a verdade era outra: o Windows simplesmente nao expoe
  temperatura de CPU para aquele modelo, e nao ha coluna "Livre" para "Sistema".

  Um trace e a forma ERRADA de dizer "isto nao se aplica aqui": ele ocupa uma
  celula, compete com numeros reais e parece valor. Ausencia agora e OMITIR.
*/

const gb = (v: number | null | undefined) =>
  v === null || v === undefined || !Number.isFinite(v) ? null : `${v.toFixed(1)} GB`;
const pct = (v: number | null | undefined) =>
  v === null || v === undefined || !Number.isFinite(v) ? null : `${v.toFixed(0)}%`;
const val = (v: string | null | undefined) =>
  v && String(v).trim() ? String(v).trim() : null;

/**
 * Uma medida da secao: rotulo + valor.
 *
 * Não renderiza NADA quando não há valor. É a diferença entre uma linha a menos
 * e uma linha com trace — e uma linha a menos é o que o dono pediu.
 */
function Medida({ rotulo, valor }: { rotulo: string; valor: string | null }) {
  if (valor === null) return null;
  return (
    <div className="sys-medida">
      <span className="sys-medida-rotulo">{rotulo}</span>
      <span className="sys-medida-valor">{valor}</span>
    </div>
  );
}

/**
 * Barra de ocupacao.
 *
 * Sem barra E sem trace quando o par não existe: a seção de recursos mostra
 * só CPU, memória e disco que o sistema de fato expõe.
 */
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

      {/*
        ENQUANTO CARREGA, A ABA MOSTRA UMA LINHA SÓ.

        Este é o defeito que o dono chamou de "travando ao abrir a primeira vez",
        e ele não era lentidão de leitura — era o que a tela mostrava durante a
        leitura.

        MEDIDO: `hardware_telemetry` no Windows abre `powershell.exe` e roda
        cinco consultas CIM. Leva segundos na primeira vez de cada sessão. A
        tabela antiga era renderizada durante ESSE TEMPO TODO, e ela não tem
        dado nenhum até o fim: saíam quatro colunas de "--" em seis. O operador
        via uma parede de traceados e lia como travamento.

        Agora as quatro seções aparecem na hora com os nomes, e o corpo fica
        aguardando uma linha só. A tela pinta imediatamente e diz o que está
        acontecendo — que é o que um indicador honesto faz.
      */}
      {carregando && !hw && (
        <p className="sys-esperando" role="status">
          Lendo a máquina…
        </p>
      )}

      {erro && (
        <div className="card compact-card sys-erro" role="status">
          {erro}
        </div>
      )}

      {/* ============== CORE 1 — MÁQUINA ==============
          O que este aparelho É. Uma medida por linha, e só as que existem:
          nada de "Livre" para "Sistema", nada de "Total" para "Vídeo". */}
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
          <Medida rotulo="Temperatura" valor={hw?.cpu_temperature_c != null ? `${hw.cpu_temperature_c.toFixed(0)} °C` : null} />
          {/* GPU ausente é RESPOSTA, não ausência: o sistema_ACTIVE_
              consultou e não achou. Por isso o texto é um dado e não um buraco. */}
          <Medida
            rotulo="Vídeo"
            valor={hw?.gpu_available ? val(hw?.gpu_name) : 'não exposto pelo sistema'}
          />
        </div>
      </section>

      {/* ============== CORE 2 — RECURSOS ==============
          Onde o operador olha quando o app engasga. Uma linha por recurso, com
          a barra, a porcentagem, o total e o livre — cada parte aparecendo só se
          o sistema a forneceu. */}
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
          {/* Nenhum dos três: a seção inteira some. Uma seção vazia com três
              linhas de trace é pior que seção nenhuma. */}
          {pct(hw?.cpu_usage_percent) === null && ramUsada === null && discoUsado === null && (
            <p className="sys-sem-dado">O sistema não expõe medição de uso.</p>
          )}
        </div>
      </section>

      {/* ============== CORE 3 — APP ==============
          O sintoma que o operador sente: quanto tempo leva e se o gateway
          responde. */}
      <section className="sys-core" aria-labelledby="sys-core-3">
        <h2 id="sys-core-3">
          <span className="sys-core-num">Core 3</span>
          <span className="sys-core-nome">Aplicativo</span>
          <span className={`chip ${gatewayOk === null ? 'warn' : gatewayOk ? 'ok' : 'danger'}`}>
            {gatewayOk === null ? 'Sem leitura' : gatewayOk ? 'Gateway ok' : 'Gateway sem resposta'}
          </span>
        </h2>
        <div className="sys-lista">
          <Medida
            rotulo="Latência da leitura"
            valor={latencia != null ? `${latencia.toFixed(0)} ms` : null}
          />
          <Medida rotulo="Intervalo de atualização" valor={`${(REFRESH_MS / 1000).toFixed(0)} s`} />
          <Medida rotulo="Origem da leitura" valor={val(hw?.source)} />
        </div>
      </section>

      {/* ============== CORE 4 — LEITURA ==============
          Procedência: quando este dado foi lido e de onde veio. É a seção que
          responde "de onde saiu esse número?", e por isso ela existe separada
          do dado. */}
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
