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
import { SIMBOLO_PRINCIPAL } from '../lib/constants';
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

  // Mesma queryKey do Mini Terminal: um polling so para /api/auto/state,
  // compartilhado entre a sub-aba e a faixa de conferencia.
  const autoQ = useAutoState();
  const estado = (autoQ.data as Estado | undefined) ?? null;

  // Pares que TEM modelo carregavel. Sem isto o operador escolheria BTCUSD H4
  // e o motor ligaria para depois recusar todo ciclo em `_trava_instrumento`.
  const [modelos, setModelos] = useState<Modelo[]>([]);
  const [simbolo, setSimbolo] = useState(SIMBOLO_PRINCIPAL);
  const [timeframe, setTimeframe] = useState('H1');
  const iniciadoRef = useRef(false);

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
    unicos.sort((a, b) => {
      if (a === SIMBOLO_PRINCIPAL) return -1;
      if (b === SIMBOLO_PRINCIPAL) return 1;
      return a.localeCompare(b);
    });
    return unicos;
  }, [pares]);

  const periodos = useMemo(
    () => [...new Set(pares.filter((p) => p.simbolo === simbolo).map((p) => p.timeframe))],
    [pares, simbolo],
  );

  // O par escolhido nasce do que o motor ja esta operando. Depois disso quem
  // manda e o operador: o polling nao pode voltar o select para o valor antigo
  // enquanto ele esta escolhendo outro ativo.
  useEffect(() => {
    if (iniciadoRef.current || !estado) return;
    if (estado.simbolo) setSimbolo(String(estado.simbolo).toUpperCase());
    if (estado.timeframe) setTimeframe(String(estado.timeframe).toUpperCase());
    iniciadoRef.current = true;
  }, [estado]);

  // A lista de modelos chega depois do estado. Se o par do motor nao existir
  // mais no disco, cai no primeiro disponivel em vez de deixar select invalido.
  useEffect(() => {
    if (!simbolos.length) return;
    setSimbolo((atual) => (simbolos.includes(atual) ? atual : simbolos[0]));
  }, [simbolos]);

  useEffect(() => {
    if (!periodos.length) return;
    setTimeframe((atual) => (periodos.includes(atual) ? atual : periodos[0]));
  }, [periodos]);

  // Sem poll proprio: `useAutoState` ja refetcha a cada 5s, junto com o Mini
  // Terminal. Aqui so traduzimos a falha em texto para o operador.
  useEffect(() => {
    if (autoQ.isError && !estado) setStatus('Gateway indisponivel');
  }, [autoQ.isError, estado]);

  // Os limites mudam no painel; o estado so e sobrescrito enquanto o operador
  // nao digitou nada, para o polling nao apagar o que esta sendo editado.
  useEffect(() => {
    const l = estado?.limites;
    if (!l) return;
    setLimites((atual) => {
      const seguinte = { ...atual };
      for (const campo of CAMPOS) {
        const v = l[campo.chave];
        if (typeof v === 'number' && !Number.isNaN(v)) seguinte[campo.chave] = v;
      }
      return seguinte;
    });
  }, [estado?.updated_at]);

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
          <h2 id="auto-engine-title">Operacao automatica</h2>
          <span className="muted">O motor avalia o modelo e envia ordens sozinho, dentro dos limites abaixo</span>
        </div>
        <div className="btn-row">
          <span className={`chip ${ativo ? 'ok' : 'warn'}`}>{ativo ? 'Operando' : 'Parado'}</span>
          <span className="chip">{estado?.simbolo ?? '--'} {estado?.timeframe ?? ''}</span>
          <span className="chip">ciclo {estado?.ciclo ?? 0}</span>
        </div>
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
            onChange={(e) => setSimbolo(e.target.value.toUpperCase())}
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
            onChange={(e) => setTimeframe(e.target.value.toUpperCase())}
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
              onChange={(e) => setLimites((l) => ({ ...l, [campo.chave]: num(e.target.value) }))}
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
