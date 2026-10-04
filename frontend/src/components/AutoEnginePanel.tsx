// Operacao automatica.
//
// O QUE ESTE PAINEL FAZ
// =====================
// Liga o motor que avalia o modelo treinado e envia ordens sozinho, com os
// limites que o operador declara. Nao ha numero de fallback aqui: cada campo
// vai para `/api/auto/config` e o proprio gateway valida e recusa.
//
// O QUE NAO ESTA NESTE PAINEL
// ===========================
// Aprovacao de ordem. O motor nao abre posicao sem que os limites passem, e
// o `/api/auto/start` so liga com limites validos. O Copiloto ao lado explica
// o que o motor fez, mas nao aperta botao por ele.
//
// O PAR (ATIVO + PERIODO) TAMBEM E ESCOLHA
// ========================================
// O motor ja aceitava `simbolo` e `timeframe` em `/api/auto/config`
// (auto_engine.MotorAuto.configurar), mas o painel nunca mandava: ele ficava
// preso em XAUUSD H1 sem nenhuma opcao na tela. Agora os dois selects vao da
// mesma lista que o painel de sinal usa — so aparece par que TEM modelo no
// disco, porque `_trava_instrumento()` recusa ciclo sem modelo e o operador
// ficaria com o motor "ligado" que nunca opera.
import { useEffect, useMemo, useRef, useState } from 'react';
import { apiBase } from '../lib/api';
import { notify } from '../lib/notify';
import { useAutoState } from '../hooks/queries';
import { BROKERS, MARKETS_BY_BROKER, MARKET_LABELS, compatibleMarket } from '../lib/brokerCatalog';
import '../theme/auto-engine.css';

const API = `${apiBase()}`;

// Os CAMPOS QUE O BACKEND EXIGE (2026-10-04).
//
// O painel mostrava so `lote`, `sl_preco` e `tp_preco`, mas o `LimitesAuto`
// tem TREZE campos e `valido()` exige os dez primeiros. Consequencia medida:
// `confianca_minima` nao tinha campo, entao o valor que o gate usava era o do
// ultimo "Aplicar" gravado no servidor. O operador digitava 36, apertava
// Aplicar, e o motor recusava com "confianca 38.0% abaixo do minimo 55.0%" —
// o numero que ele nunca digitou.
//
// Nenhum valor tem padrao: todos nascem em 0, e 0 significa "nao declarado".
// O backend recusa com o nome do que falta, e a tela mostra esse motivo.
type Limites = {
  lote: number;
  sl_preco: number;
  tp_preco: number;
  banca: number;
  risco_por_trade_pct: number;
  confianca_minima: number;
  edge_minimo: number;
  max_posicoes: number;
  max_operacoes_dia: number;
  perda_diaria_max_pct: number;
  sl_atr: number;
  tp_atr: number;
  intervalo_minutos: number;
};

// Ordem de leitura: o que o operador escolhe primeiro vem primeiro.
// `lote` e os precos sao o modo simples; o bloco de risco e o que o motor
// exige para ligar. A confianca fica no topo do bloco porque e o gate que
// decide se a ordem sai — e era justamente o que nao tinha campo.
const CAMPOS_SIMPLES: Array<{ chave: keyof Limites; rotulo: string; dica: string; passo: number }> = [
  { chave: 'lote', rotulo: 'Quantidade (lote)', dica: 'A partir de 0.01 — sem minimo de banca', passo: 0.01 },
  { chave: 'sl_preco', rotulo: 'Stop Loss', dica: 'Preco cheio (4130) ou distancia (10)', passo: 0.1 },
  { chave: 'tp_preco', rotulo: 'Take Profit', dica: 'Preco cheio (4150) ou distancia (20)', passo: 0.1 },
];

const CAMPOS_RISCO: Array<{ chave: keyof Limites; rotulo: string; dica: string; passo: number }> = [
  { chave: 'confianca_minima', rotulo: 'Confianca minima (%)', dica: 'Probabilidade real do modelo, 0-100. Abaixo disso o motor nao opera', passo: 1 },
  { chave: 'edge_minimo', rotulo: 'Edge minimo', dica: 'Vantagem minima esperada do modelo (0-1)', passo: 0.01 },
  { chave: 'banca', rotulo: 'Banca', dica: 'Capital declarado. Base das demais porcentagens', passo: 100 },
  { chave: 'risco_por_trade_pct', rotulo: 'Risco por operacao (%)', dica: '0 a 10. Quanto da banca cada ordem arrisca', passo: 0.1 },
  { chave: 'perda_diaria_max_pct', rotulo: 'Perda diaria maxima (%)', dica: 'Ao atingir, o motor para o dia', passo: 0.5 },
  { chave: 'max_posicoes', rotulo: 'Maximo de posicoes', dica: 'Posicoes simultaneas', passo: 1 },
  { chave: 'max_operacoes_dia', rotulo: 'Operacoes por dia', dica: 'Teto de ordens em 24 h', passo: 1 },
  { chave: 'sl_atr', rotulo: 'Stop Loss (x ATR)', dica: 'Multiplicador de ATR', passo: 0.1 },
  { chave: 'tp_atr', rotulo: 'Take Profit (x ATR)', dica: 'Multiplicador de ATR', passo: 0.1 },
  { chave: 'intervalo_minutos', rotulo: 'Intervalo entre avaliacoes (min)', dica: 'Cada ciclo avalia uma vez neste intervalo', passo: 1 },
];

const CAMPOS = [...CAMPOS_SIMPLES, ...CAMPOS_RISCO];

type Estado = {
  ativo: boolean;
  ciclo: number;
  simbolo: string;
  timeframe: string;
  // Corretora e mercado que o motor VAI usar. Vem do proprio motor, nao de
  // um default da tela: sem estes dois o backend recusa o "ligar" porque
  // nenhuma corretora e caminho padrao.
  broker?: string;
  market?: string;
  threads: number;
  limites: Partial<Limites>;
  // `modelo` e o nome do artefato que rodou, lido do `.meta.json` pelo
  // backend. O terminal ao vivo mostra este campo em vez de montar um nome.
  decisoes: Array<{
    ts?: string;
    simbolo?: string;
    side?: string;
    acao?: string;
    motivo?: string;
    confianca?: number;
    modelo?: string;
  }>;
  updated_at?: string;
};

type Modelo = { id: string; symbol: string; timeframe: string; pkl_present: boolean };

function num(v: string): number {
  return Number(String(v).replace(',', '.'));
}

export default function AutoEnginePanel() {
  // PAINEL SIMPLES: LOTE + SL + TP + AUTO. Sem banca, risco, confianca,
  // perda ou ATR — o operador decide o tamanho e as protecoes, e o
  // risk_gate do gateway limita a exposicao real. Tudo nasce zerado.
// TODOS os limites nascem em ZERO, e zero significa "nao declarado". Nenhum
// valor entra por padrao: o backend recusa o "ligar" com o nome do que falta,
// e essa recusa e o comportamento correto — um risco que o codigo inventou
// seria pior do que nenhum.
const ZERO: Limites = {
  lote: 0,
  sl_preco: 0,
  tp_preco: 0,
  banca: 0,
  risco_por_trade_pct: 0,
  confianca_minima: 0,
  edge_minimo: 0,
  max_posicoes: 0,
  max_operacoes_dia: 0,
  perda_diaria_max_pct: 0,
  sl_atr: 0,
  tp_atr: 0,
  intervalo_minutos: 0,
};
const [limites, setLimites] = useState<Limites>({ ...ZERO });
  const [status, setStatus] = useState('');
  const [ocupado, setOcupado] = useState(false);
  // 'auto' = o motor decide; 'manual' = o operador decide. Uma mao por vez.
  // O modo nasce do motor ligado: se ele ja estava operando, o operador esta
  // vendo o automatico, e trocar para manual tem de desligar o motor — nunca
  // deixar os dois decidindo a mesma conta.

  // Mesma queryKey do Mini Terminal: um polling so para /api/auto/state,
  // compartilhado entre a sub-aba e a faixa de conferencia.
  const autoQ = useAutoState();
  const estado = (autoQ.data as Estado | undefined) ?? null;

  // Pares que TEM modelo carregavel. Sem isto o operador escolheria um ativo
  // sem modelo e o motor ligaria para depois recusar todo ciclo.
  const [modelos, setModelos] = useState<Modelo[]>([]);
  const [simbolo, setSimbolo] = useState('');
  const [timeframe, setTimeframe] = useState('');

  // CORRETORA E MERCADO DO MOTOR (2026-09-30)
  //
  // O painel aceitava ativo e periodo, mas NAO tinha onde escolher a
  // corretora. O backend exige a escolha (nenhuma corretora e caminho padrao)
  // e recusava o "Aplicar e ligar" com a mensagem
  // "escolha a corretora antes de ligar". O operador nao conseguia cumplir
  // uma exigencia que a tela nao oferecia: nao era erro dele, era falta de
  // campo. O motor ficou ligavel apenas por API.
  const [broker, setBroker] = useState('');
  const [market, setMarket] = useState('');

  const mercados = useMemo(() => MARKETS_BY_BROKER[broker] ?? [], [broker]);

  // Trocar de corretora pode tornar o mercado atual impossivel (Binance nao
  // faz forex). Sem isto o motor aceitaria "binance + metals" e so recusaria
  // no envio, depois de um ciclo inteiro de inferencia.
  useEffect(() => {
    if (!broker) return;
    setMarket((atual) => compatibleMarket(broker, atual));
  }, [broker]);

  useEffect(() => {
    const controller = new AbortController();
    void fetch(`${API}/api/ai/trained`, { signal: controller.signal })
      .then((r) => r.json())
      .then((d: { models?: Modelo[] }) => {
        if (controller.signal.aborted) return;
        setModelos((d.models ?? []).filter((m) => m.pkl_present));
      })
      .catch(() => {
        /* sem lista, os selects ficam com o padrao */
      });
    return () => controller.abort();
  }, []);

  const pares = useMemo(
    () =>
      modelos.map((m) => ({
        simbolo: String(m.symbol).toUpperCase(),
        timeframe: String(m.timeframe).toUpperCase(),
      })),
    [modelos],
  );

  const simbolos = useMemo(() => {
    const unicos = [...new Set(pares.map((p) => p.simbolo))];
    unicos.sort((a, b) => a.localeCompare(b));
    return unicos;
  }, [pares]);

  const periodos = useMemo(
    () => [...new Set(pares.filter((p) => p.simbolo === simbolo).map((p) => p.timeframe))],
    [pares, simbolo],
  );

  // OS CAMPOS DO OPERADOR NAO VOLTAM DO POLLING (2026-09-29).
  //
  // `useAutoState` refetcha a cada 5 s. Antes, os dois efeitos abaixo
  // reescreviam `simbolo`, `timeframe` e os dez limites a cada resposta: o
  // operador digitava 60, o polling chegava e devolvia 55. Na pratica os campos
  // ficavam presos e as ordens saiam com um limite que ninguem tinha escolhido.
  // O sintoma era "os comandos nao funcionam" e "a confianca fica em 55".
  //
  // Regra agora: o servidor preenche os campos UMA vez, no primeiro snapshot.
  // Depois disso quem manda e o operador — ate ele apertar "Aplicar".
  // DOIS ESTADOS VIRARAM UM (2026-10-04)
  // -------------------------------
  // Antes existia `sujo` e um `hidratouRef` que era LIDO e NUNCA ESCRITO —
  // o codigo pretendia travar a rehidratacao no primeiro "Aplicar", e nunca
  // fez. E `setSujo(false)` nao existia: depois da primeira edicao, `sujo`
  // ficava `true` para sempre.
  //
  // A trava funcionava por acidente, via `sujo`. E isso escondia um bug de
  // verdade: como `sujo` nunca voltava a `false`, uma mudanca de configuracao
  // vinda da API (ou de outra tela) NUNCA aparecia no painel — a tela
  // continuava mostrando o valor antigo enquanto o motor usava o novo.
  // A tela afirmando uma coisa e o motor operando outra.
  //
  // Agora o estado e unico e nomeado: `pendente` = o operador digitou algo que
  // o servidor ainda nao gravou. Apos o POST bem-sucedido, `false` de novo, e
  // o proximo snapshot reidrata normalmente.
  const [pendente, setPendente] = useState(false);
  const hidratouRef = useRef(false);

  useEffect(() => {
    if (!estado || pendente) return;
    // Rehidratar so enquanto o operador nao editou nada: depois disso o valor
    // da tela e mais novo que o do servidor.
    if (hidratouRef.current) return;
    hidratouRef.current = true;
    if (estado.simbolo) setSimbolo(String(estado.simbolo).toUpperCase());
    if (estado.timeframe) setTimeframe(String(estado.timeframe).toUpperCase());
    if (estado.broker) setBroker(String(estado.broker).toLowerCase());
    if (estado.market) setMarket(String(estado.market).toLowerCase());
    const l = estado.limites;
    if (l) {
      setLimites((atual) => {
        const seguinte = { ...atual };
        for (const campo of CAMPOS) {
          const v = l[campo.chave];
          if (typeof v === 'number' && !Number.isNaN(v)) seguinte[campo.chave] = v;
        }
        return seguinte;
      });
    }
  }, [estado?.updated_at, estado, pendente]);

  // O par so pode vir da lista de modelos COM modelo carregavel. Se o motor
  // esta em um par reprovado (XAUUSD M15 tem edge 0.0498 contra minimo 0.0500),
  // o select cai no primeiro valido em vez de deixar o operador escolher algo
  // que o motor vai recusar com "modelo ausente".
  useEffect(() => {
    if (!simbolos.length) return;
    setSimbolo((atual) => (simbolos.includes(atual) ? atual : simbolos[0]));
  }, [simbolos]);

  useEffect(() => {
    if (!periodos.length) return;
    setTimeframe((atual) => (periodos.includes(atual) ? atual : periodos[0]));
  }, [periodos]);

  // Marcar "o operador mexeu" e o que tira o painel da sombra do servidor.
  const marcar = <T extends keyof Limites>(campo: T, valor: Limites[T]) => {
    setPendente(true);
    setLimites((l) => ({ ...l, [campo]: valor }));
  };

  // Sem poll proprio: `useAutoState` ja refetcha a cada 5s, junto com o Mini
  // Terminal. Aqui so traduzimos a falha em texto para o operador.
  useEffect(() => {
    if (autoQ.isError && !estado) setStatus('Gateway indisponivel');
  }, [autoQ.isError, estado]);

  const enviar = async (caminho: string, corpo?: Record<string, unknown>) => {
    if (ocupado) return;
    setOcupado(true);
    setStatus('Enviando…');
    try {
      const r = await fetch(`${API}${caminho}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo ?? {}),
        signal: AbortSignal.timeout(10_000),
      });
      const d = (await r.json().catch(() => ({}))) as {
        ok?: boolean;
        error?: string;
        motivo?: string;
      };
      if (r.ok && d.ok !== false) {
        // Três rotinas, três frases: aplicar config nao liga o motor, ligar
        // nao configura, desligar nao mexe nos limites.
        if (caminho === '/api/auto/config') {
          setStatus('Limites e par do motor aplicados.');
          void notify('Motor configurado', `Proximo ciclo avalia ${simbolo} ${timeframe}.`);
        } else if (caminho.includes('start')) {
          setStatus('Motor ligado.');
          void notify('Operacao automatica ligada', `Motor operando ${simbolo} ${timeframe}.`);
        } else {
          setStatus('Motor parou.');
          void notify('Operacao automatica desligada', 'O motor parou de evaluar.');
        }
      } else {
        const motivo = d.error || d.motivo || `HTTP ${r.status}`;
        setStatus(motivo);
        void notify('Recusado', motivo);
      }
      await autoQ.refetch();
      return true;
    } catch (e) {
      setStatus(`Gateway indisponivel: ${e instanceof Error ? e.message : 'erro'}`);
      return false;
    } finally {
      setOcupado(false);
    }
  };

  // Aplica e liga em um clique, sem mentir sobre o caminho feliz.
  //
  // Por que dois `fetch` e nao um: `/api/auto/config` e `/api/auto/start` sao
  // rotas distintas, e o gateway recusa `start` com limites invalidos. Se a
  // configuracao for recusada, o motor NAO pode ligar — senao o operador ve
  // "Operando" com os limites antigos em vigor.
  const aplicarELigar = async () => {
    if (ocupado || ativo) return;
    setOcupado(true);
    try {
      const cfg = await fetch(`${API}/api/auto/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...limites, simbolo, timeframe, broker, market }),
        signal: AbortSignal.timeout(10_000),
      });
      const dCfg = (await cfg.json().catch(() => ({}))) as {
        ok?: boolean;
        error?: string;
        motivo?: string;
      };
      if (!cfg.ok || dCfg.ok === false) {
        const motivo = dCfg.error || dCfg.motivo || `HTTP ${cfg.status}`;
        setStatus(motivo);
        void notify('Configuracao recusada', `${motivo} — o motor nao foi ligado.`);
        return;
      }
      // O servidor JA gravou o que o operador digitou. A partir daqui a tela e
      // o servidor dizem a mesma coisa, entao o proximo snapshot pode reidratar
      // sem sobrescrever a mao do operador.
      //
      // Sem esta linha, `pendente` ficava `true` para sempre e nenhuma mudanca
      // vinda da API aparecia na tela — o painel continuaria mostrando o valor
      // antigo enquanto o motor usava o novo.
      setPendente(false);
      hidratouRef.current = true;
      const ini = await fetch(`${API}/api/auto/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
        signal: AbortSignal.timeout(10_000),
      });
      const dIni = (await ini.json().catch(() => ({}))) as {
        ok?: boolean;
        error?: string;
        motivo?: string;
      };
      if (ini.ok && dIni.ok !== false) {
        setStatus('Motor ligado.');
        void notify('Operacao automatica ligada', `Motor operando ${simbolo} ${timeframe}.`);
      } else {
        const motivo = dIni.error || dIni.motivo || `HTTP ${ini.status}`;
        setStatus(`Configurado, mas nao ligou: ${motivo}`);
        void notify('Nao ligou', motivo);
      }
      await autoQ.refetch();
    } catch (e) {
      setStatus(`Gateway indisponivel: ${e instanceof Error ? e.message : 'erro'}`);
    } finally {
      setOcupado(false);
    }
  };

  const ativo = estado?.ativo ?? false;
  // Sem corretora o backend recusa o "ligar". A tela diz isso ANTES do
  // clique: um botao que so falha depois obriga o operador a descobrir a
  // regra no texto de erro.
  const faltaCorretora = !broker || !market;

  // Par escolhido na tela ainda nao aplicado ao motor.
  const parDiferente =
    Boolean(estado && String(estado.simbolo ?? '').toUpperCase() !== simbolo) ||
    Boolean(estado && String(estado.timeframe ?? '').toUpperCase() !== timeframe) ||
    Boolean(estado && String(estado.broker ?? '').toLowerCase() !== broker) ||
    Boolean(estado && String(estado.market ?? '').toLowerCase() !== market);

  return (
    <section className="card compact-card auto-engine" aria-labelledby="auto-engine-title">
      <div className="section-head">
        <div>
          <h2 id="auto-engine-title">Operacao automatica</h2>
          <span className="muted">
            O motor avalia o modelo treinado do par escolhido e envia ordens sozinho, dentro dos
            limites abaixo
          </span>
        </div>
        <div className="btn-row">
          <span className={`chip ${ativo ? 'ok' : 'warn'}`}>
            {ativo ? 'Automatico operando' : 'Automatico parado'}
          </span>
          <span className="chip">
            {estado?.simbolo ?? '--'} {estado?.timeframe ?? ''}
          </span>
          <span className="chip">ciclo {estado?.ciclo ?? 0}</span>
        </div>
      </div>

      {/* DUAS MAIOS NA MESMA MESA (2026-09-29).

          Antes o operador tinha duas telas: o painel do motor automatico e, duas
          sub-abas abaixo, o `OrderPanel` da ordem manual. Para mandar uma ordem
          na mao ele trocava de contexto; para ligar o motor, voltava. As duas
          coisas usam o MESMO par de ativo — e nada na tela dizia isso.

          Aqui o manual vem logo abaixo dos controles, com o par que ja esta
          selecionado acima. Quem aperta "Operar manualmente" desliga o motor
          primeiro: os dois nao devem decidir a mesma conta ao mesmo tempo. */}

      {/* O MOTOR OPERA UM PAR POR VEZ: escolher ativo + periodo e escolher
          qual modelo roda. So aparecem pares com `.pkl` no disco. */}
      <div className="auto-engine-grid auto-engine-par">
        {/* CORRETORA E MERCADO DO MOTOR (2026-09-30)
            Sem estes dois campos o "Aplicar e ligar" era recusado com
            "escolha a corretora antes de ligar": o backend exige a escolha e a
            tela nao offers. Fica na MESMA grade do par, para nao virar uma
            linha extra de UI. */}
        <label
          className="field"
          title="Corretora que vai executar a ordem. Nenhuma corretora e o padrao: o operador escolhe."
        >
          <span>Corretora</span>
          <select
            aria-label="Corretora do motor automatico"
            value={broker}
            disabled={!BROKERS.length}
            onChange={(e) => {
              setPendente(true);
              setBroker(e.target.value);
            }}
          >
            <option value="">Escolha a corretora</option>
            {BROKERS.map((b) => (
              <option key={b.id} value={b.id}>
                {b.label}
              </option>
            ))}
          </select>
        </label>
        <label
          className="field"
          title="Classe de ativo. A lista segue a corretora escolhida: Binance nao opera forex."
        >
          <span>Mercado</span>
          <select
            aria-label="Mercado do motor automatico"
            value={market}
            disabled={!broker || !mercados.length}
            onChange={(e) => {
              setPendente(true);
              setMarket(e.target.value);
            }}
          >
            {!broker && <option value="">Escolha a corretora antes</option>}
            {mercados.map((m) => (
              <option key={m} value={m}>
                {MARKET_LABELS[m] ?? m}
              </option>
            ))}
          </select>
        </label>
        <label className="field" title="Ativo que o motor vai avaliar a cada ciclo">
          <span>Ativo do motor</span>
          <select
            aria-label="Ativo do motor automatico"
            value={simbolo}
            disabled={!simbolos.length}
            onChange={(e) => {
              setPendente(true);
              setSimbolo(e.target.value.toUpperCase());
            }}
          >
            {!simbolos.length && <option value={simbolo}>{simbolo}</option>}
            {simbolos.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="field" title="Período do modelo treinado deste ativo">
          <span>Período</span>
          <select
            aria-label="Periodo do motor automatico"
            value={timeframe}
            disabled={!periodos.length}
            onChange={(e) => {
              setPendente(true);
              setTimeframe(e.target.value.toUpperCase());
            }}
          >
            {!periodos.length && <option value={timeframe}>{timeframe}</option>}
            {periodos.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <div className="auto-engine-par-chips">
          <span className="chip">
            modelo {simbolo}_{timeframe}
          </span>
          {!modelos.length && <span className="chip warn">lista de modelos indisponível</span>}
        </div>
      </div>

      {/* DOIS BLOCOS, NAO UM (2026-10-04)
          Sao treze campos. Numa grade unica de treze caixas o operador nao
          sabia quais importavam: o `lote` que ele escolhe e o
          `confianca_minima`, que decide se a ordem sai, tinham o mesmo peso
          visual. O titulo de cada bloco diz o que e aquela escolha. */}
      <fieldset className="auto-engine-bloco">
        <legend>Ordem</legend>
        <div className="auto-engine-grid">
          {CAMPOS_SIMPLES.map((campo) => (
            <label key={campo.chave} className="field" title={campo.dica}>
              <span>{campo.rotulo}</span>
              <input
                type="number"
                step={campo.passo}
                value={String(limites[campo.chave])}
                onChange={(e) => marcar(campo.chave, num(e.target.value))}
              />
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="auto-engine-bloco">
        <legend>
          Risco e confiança
          <span className="auto-engine-legenda-nota">
            o motor só liga com todos preenchidos
          </span>
        </legend>
        <div className="auto-engine-grid">
          {CAMPOS_RISCO.map((campo) => (
            <label key={campo.chave} className="field" title={campo.dica}>
              <span>{campo.rotulo}</span>
              <input
                type="number"
                step={campo.passo}
                value={String(limites[campo.chave])}
                onChange={(e) => marcar(campo.chave, num(e.target.value))}
              />
            </label>
          ))}
        </div>
      </fieldset>

      {/* COMO ESTES BOTOES FORAM REESCRITOS (2026-09-30)
          ====================================================
          O dono pediu "botoes melhorados". O problema nao era o visual: era
          que os tres botoes eram indistinguiveis no momento da acao.

          "Aplicar" e "Ligar" pareciam equivalentes — os dois habilitados,
          os dois com a mesma aparencia, e so um deles tinha efeito imediato.
          Um operador que clicava "Ligar" sem "Aplicar" achava que o motor
          estava operando com o par novo, e ele seguia no par antigo.

          Agora:
            - cada botao diz o que FAZ, nao o que e: "Aplicar e ligar" e uma
              acao so, e o caminho feliz em um clique;
            - "Aplicar" separado continua existindo para quem so quer gravar
              sem ligar;
            - "Par pendente" some: o motor so opera o par ja aplicado, e o
              aviso fica visivel em vez de escondido num chip pequeno.
          */}
      <div className="btn-row auto-engine-acoes" role="group" aria-label="Comandos do motor">
        <button
          className="btn primary"
          type="button"
          onClick={() => void aplicarELigar()}
          disabled={ocupado || ativo || parDiferente || faltaCorretora}
        >
          {ativo
            ? 'Operando'
            : faltaCorretora
              ? 'Escolha a corretora'
              : parDiferente
                ? 'Aplique antes de ligar'
                : 'Aplicar e ligar'}
        </button>
        <button
          className="btn"
          type="button"
          onClick={() =>
            void enviar('/api/auto/config', { ...limites, simbolo, timeframe, broker, market })
          }
          disabled={ocupado}
          title="Grava os limites e o par sem ligar o motor"
        >
          Aplicar so
        </button>
        <button
          className="btn danger"
          type="button"
          onClick={() => void enviar('/api/auto/stop')}
          disabled={ocupado || !ativo}
        >
          Parar motor
        </button>
      </div>

      <div className="hint" role="status" aria-live="polite" style={{ marginTop: 6 }}>
        {status || `Threads: ${estado?.threads ?? '--'}`}
      </div>

      {(estado?.decisoes?.length ?? 0) > 0 && (
        <div className="table-scroll auto-engine-decisoes">
          <table className="tbl compact-table dense-grid">
            <thead>
              <tr>
                <th>Quando</th>
                <th>Ativo</th>
                <th>Decisao</th>
                <th className="num">Confianca</th>
                <th>Motivo</th>
              </tr>
            </thead>
            <tbody>
              {(estado?.decisoes ?? []).slice(0, 8).map((d, i) => (
                <tr key={`${d.ts ?? i}`}>
                  <td className="mono">
                    {d.ts ? new Date(d.ts).toLocaleTimeString('pt-BR') : '--'}
                  </td>
                  <td>
                    <strong>{d.simbolo ?? '--'}</strong>
                  </td>
                  <td>
                    <span
                      className={`chip ${/buy|compra/i.test(String(d.side)) ? 'ok' : /sell|venda/i.test(String(d.side)) ? 'warn' : ''}`}
                    >
                      {d.side ?? d.acao ?? '--'}
                    </span>
                  </td>
                  <td className="num">{d.confianca ?? '--'}</td>
                  <td>{d.motivo ?? '--'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

