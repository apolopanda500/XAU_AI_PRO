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
import '../theme/auto-engine.css';

const API = `${apiBase()}`;

type Limites = {
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

type Estado = {
  ativo: boolean;
  ciclo: number;
  simbolo: string;
  timeframe: string;
  threads: number;
  limites: Partial<Limites>;
  decisoes: Array<{ ts?: string; simbolo?: string; side?: string; acao?: string; motivo?: string; confianca?: number }>;
  updated_at?: string;
};

type Modelo = { id: string; symbol: string; timeframe: string; pkl_present: boolean };

const CAMPOS: Array<{ chave: keyof Limites; rotulo: string; dica: string; passo: number }> = [
  { chave: 'banca', rotulo: 'Banca', dica: 'Base de calculo, nao o saldo da conta', passo: 10 },
  { chave: 'risco_por_trade_pct', rotulo: 'Risco por trade %', dica: '0 a 10', passo: 0.1 },
  { chave: 'confianca_minima', rotulo: 'Confianca minima %', dica: 'Probabilidade real do modelo', passo: 1 },
  { chave: 'edge_minimo', rotulo: 'Edge minimo', dica: '0.05 = 5%', passo: 0.01 },
  { chave: 'max_posicoes', rotulo: 'Max posicoes', dica: 'Simultaneas', passo: 1 },
  { chave: 'max_operacoes_dia', rotulo: 'Operacoes/dia', dica: 'Teto diario', passo: 1 },
  { chave: 'perda_diaria_max_pct', rotulo: 'Perda diaria %', dica: 'Ao atingir, o motor para', passo: 0.5 },
  { chave: 'sl_atr', rotulo: 'Stop (x ATR)', dica: 'Multiplicador de ATR', passo: 0.1 },
  { chave: 'tp_atr', rotulo: 'Alvo (x ATR)', dica: 'Multiplicador de ATR', passo: 0.1 },
  { chave: 'intervalo_minutos', rotulo: 'Intervalo (min)', dica: 'Entre avaliacoes', passo: 1 },
];

function num(v: string): number {
  return Number(String(v).replace(',', '.'));
}

export default function AutoEnginePanel() {
  const [limites, setLimites] = useState<Limites>({
    banca: 20, risco_por_trade_pct: 1, confianca_minima: 55, edge_minimo: 0.05,
    max_posicoes: 2, max_operacoes_dia: 20, perda_diaria_max_pct: 2,
    sl_atr: 1.5, tp_atr: 3, intervalo_minutos: 15,
  });
  const [status, setStatus] = useState('');
  const [ocupado, setOcupado] = useState(false);
  // 'auto' = o motor decide; 'manual' = o operador decide. Uma mao por vez.
  // O modo nasce do motor ligado: se ele ja estava operando, o operador esta
  // vendo o automatico, e trocar para manual tem de desligar o motor — nunca
  // deixar os dois decidindo a mesma conta.
  const [modo, setModo] = useState<'auto' | 'manual'>('auto');

  // Mesma queryKey do Mini Terminal: um polling so para /api/auto/state,
  // compartilhado entre a sub-aba e a faixa de conferencia.
  const autoQ = useAutoState();
  const estado = (autoQ.data as Estado | undefined) ?? null;

  // Pares que TEM modelo carregavel. Sem isto o operador escolheria um ativo
  // sem modelo e o motor ligaria para depois recusar todo ciclo.
  const [modelos, setModelos] = useState<Modelo[]>([]);
  const [simbolo, setSimbolo] = useState('');
  const [timeframe, setTimeframe] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    void fetch(`${API}/api/ai/trained`, { signal: controller.signal })
      .then((r) => r.json())
      .then((d: { models?: Modelo[] }) => {
        if (controller.signal.aborted) return;
        setModelos((d.models ?? []).filter((m) => m.pkl_present));
      })
      .catch(() => { /* sem lista, os selects ficam com o padrao */ });
    return () => controller.abort();
  }, []);

  const pares = useMemo(
    () => modelos.map((m) => ({ simbolo: String(m.symbol).toUpperCase(), timeframe: String(m.timeframe).toUpperCase() })),
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
  const [sujo, setSujo] = useState(false);
  const aplicadoRef = useRef(false);

  useEffect(() => {
    if (!estado || sujo || aplicadoRef.current) return;
    if (estado.simbolo) setSimbolo(String(estado.simbolo).toUpperCase());
    if (estado.timeframe) setTimeframe(String(estado.timeframe).toUpperCase());
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
  }, [estado?.updated_at, estado, sujo]);

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
    setSujo(true);
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
      const d = (await r.json().catch(() => ({}))) as { ok?: boolean; error?: string; motivo?: string };
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
    } catch (e) {
      setStatus(`Gateway indisponivel: ${e instanceof Error ? e.message : 'erro'}`);
    } finally {
      setOcupado(false);
    }
  };

  const ativo = estado?.ativo ?? false;
  // Par escolhido na tela ainda nao aplicado ao motor.
  const parDiferente = Boolean(
    estado
    && String(estado.simbolo ?? '').toUpperCase() !== simbolo,
  ) || Boolean(
    estado
    && String(estado.timeframe ?? '').toUpperCase() !== timeframe,
  );

  return (
    <section className="card compact-card auto-engine" aria-labelledby="auto-engine-title">
      <div className="section-head">
        <div>
          <h2 id="auto-engine-title">Operacao</h2>
          <span className="muted">Manual a mao ou automatico — os dois no mesmo lugar, com o mesmo par de ativo</span>
        </div>
        <div className="btn-row">
          <span className={`chip ${ativo ? 'ok' : 'warn'}`}>{ativo ? 'Automatico operando' : 'Automatico parado'}</span>
          <span className="chip">{estado?.simbolo ?? '--'} {estado?.timeframe ?? ''}</span>
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

      <div className="auto-engine-modes" role="group" aria-label="Modo de operacao">
        <button
          type="button"
          className={`btn sm ${modo === 'manual' ? 'primary' : ''}`}
          aria-pressed={modo === 'manual'}
          onClick={() => setModo('manual')}
        >
          Operar na mao
        </button>
        <button
          type="button"
          className={`btn sm ${modo === 'auto' ? 'primary' : ''}`}
          aria-pressed={modo === 'auto'}
          onClick={() => setModo('auto')}
        >
          Deixar o motor
        </button>
        <span className="muted">
          {modo === 'manual'
            ? 'Voce envia a ordem. O motor fica parado.'
            : 'O motor avalia a cada intervalo. A ordem manual e bloqueada.'}
        </span>
      </div>

      {/* O MOTOR OPERA UM PAR POR VEZ: escolher ativo + periodo e escolher
          qual modelo roda. So aparecem pares com `.pkl` no disco. */}
      <div className="auto-engine-grid auto-engine-par">
        <label className="field" title="Ativo que o motor vai avaliar a cada ciclo">
          <span>Ativo do motor</span>
          <select
            aria-label="Ativo do motor automatico"
            value={simbolo}
            disabled={!simbolos.length}
            onChange={(e) => { setSujo(true); setSimbolo(e.target.value.toUpperCase()); }}
          >
            {!simbolos.length && <option value={simbolo}>{simbolo}</option>}
            {simbolos.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label className="field" title="Período do modelo treinado deste ativo">
          <span>Período</span>
          <select
            aria-label="Periodo do motor automatico"
            value={timeframe}
            disabled={!periodos.length}
            onChange={(e) => { setSujo(true); setTimeframe(e.target.value.toUpperCase()); }}
          >
            {!periodos.length && <option value={timeframe}>{timeframe}</option>}
            {periodos.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <div className="auto-engine-par-chips">
          <span className="chip">modelo {simbolo}_{timeframe}</span>
          {parDiferente && <span className="chip warn">par novo · aplique para trocar</span>}
          {!modelos.length && <span className="chip warn">lista de modelos indisponível</span>}
        </div>
      </div>

      <div className="auto-engine-grid">
        {CAMPOS.map((campo) => (
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

      {/* Tres comandos: aplicar, ligar, desligar. "Rodar um ciclo" saiu —
          repetia o que o proprio loop faz e ficava ao lado do Ligar. */}
      <div className="btn-row" style={{ marginTop: 8 }}>
        <button className="btn sm primary" type="button" onClick={() => void enviar('/api/auto/config', { ...limites, simbolo, timeframe })} disabled={ocupado}>Aplicar</button>
        <button className="btn sm" type="button" onClick={() => void enviar('/api/auto/start')} disabled={ocupado || ativo}>Ligar</button>
        <button className="btn sm danger" type="button" onClick={() => void enviar('/api/auto/stop')} disabled={ocupado || !ativo}>Desligar</button>
      </div>

      <div className="hint" role="status" aria-live="polite" style={{ marginTop: 6 }}>{status || `Threads: ${estado?.threads ?? '--'}`}</div>

      {(estado?.decisoes?.length ?? 0) > 0 && (
        <div className="table-scroll auto-engine-decisoes">
          <table className="tbl compact-table dense-grid">
            <thead><tr><th>Quando</th><th>Ativo</th><th>Decisao</th><th className="num">Confianca</th><th>Motivo</th></tr></thead>
            <tbody>
              {(estado?.decisoes ?? []).slice(0, 8).map((d, i) => (
                <tr key={`${d.ts ?? i}`}>
                  <td className="mono">{d.ts ? new Date(d.ts).toLocaleTimeString('pt-BR') : '--'}</td>
                  <td><strong>{d.simbolo ?? '--'}</strong></td>
                  <td><span className={`chip ${/buy|compra/i.test(String(d.side)) ? 'ok' : /sell|venda/i.test(String(d.side)) ? 'warn' : ''}`}>{d.side ?? d.acao ?? '--'}</span></td>
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
