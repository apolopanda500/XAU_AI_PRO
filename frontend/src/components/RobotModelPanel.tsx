// Modelo e previsao, dentro da aba Robo.
//
// POR QUE A PREVISAO FICA AO LADO DO COMANDO
// ==========================================
// A inferencia so tem utilidade quando o operador pode agir em seguida. Com a
// IA em outra aba, ver o sinal exigia trocar de tela e o comando ficava longe.
// Aqui o sinal, o modelo que o produziu e o botao de ordem estao na mesma pilha.
//
// NADA E INVENTADO NESTA TELA
// ===========================
// A confianca vem de `predict_proba` do modelo publicado. O edge e a accuracy
// vem do .meta.json do treino. Se o .pkl nao existe, o modelo nao entra na
// lista — um modelo "publicavel" sem artefato falharia ao carregar.
import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';
import { SIMBOLO_PRINCIPAL } from '../lib/constants';
import { notify } from '../lib/notify';
import '../theme/robot-model.css';

const API = `${apiBase()}`;

type Modelo = { id: string; symbol: string; timeframe: string; accuracy: number | null; edge: number | null; pkl_present: boolean; publicable: boolean };

type Previsao = {
  signal?: string; confidence?: number; prob_buy?: number; prob_sell?: number; prob_neutral?: number;
  price?: number; edge?: number | null; inference_ms?: number; reason?: string; disponivel?: boolean; available?: boolean;
};

function pct(v: number | null | undefined, casas = 1): string {
  return v === null || v === undefined || !Number.isFinite(v) ? '--' : `${(v * 100).toFixed(casas)}%`;
}

export default function RobotModelPanel() {
  const selectedSymbol = useAppStore((s) => s.selectedSymbol);
  const setSelectedSymbol = useAppStore((s) => s.setSelectedSymbol);
  const [modelos, setModelos] = useState<Modelo[]>([]);
  const [modeloId, setModeloId] = useState('');
  const [threads, setThreads] = useState(0);
  const [previsao, setPrevisao] = useState<Previsao | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [erroLista, setErroLista] = useState('');

  // POR QUE TEM SELETOR DE ATIVO
  // ============================
  // `/api/ai/predict` le APENAS `symbol` + `timeframe` e IGNORA `model_id`
  // (fastapi_gateway.py). Com o botao antigo mandando
  // `symbol = selectedSymbol || 'XAUUSD'`, escolher BTCUSD_H4 ainda enviava
  // XAUUSD: a previsao saia do modelo errado ou falhava, e o painel so
  // parecia funcionar em XAUUSD. Agora o ativo vem da lista que TEM modelo
  // no disco (os 9 simbolos treinados), e o modelo e filtrado por ele.
  const simbolos = useMemo(() => {
    const unicos = [...new Set(modelos.map((m) => m.symbol))];
    unicos.sort((a, b) => {
      if (a === SIMBOLO_PRINCIPAL) return -1;
      if (b === SIMBOLO_PRINCIPAL) return 1;
      return a.localeCompare(b);
    });
    return unicos;
  }, [modelos]);

  const simbolo = useMemo(() => {
    const atual = (selectedSymbol || '').toUpperCase();
    if (atual && (simbolos.length === 0 || simbolos.includes(atual))) return atual;
    return simbolos[0] ?? 'XAUUSD';
  }, [selectedSymbol, simbolos]);

  const visiveis = useMemo(
    () => modelos.filter((m) => m.symbol === simbolo),
    [modelos, simbolo],
  );

  useEffect(() => {
    const controller = new AbortController();
    void fetch(`${API}/api/ai/trained`, { signal: controller.signal })
      .then((r) => r.json())
      .then((d: { models?: Modelo[]; cpu_threads?: number }) => {
        if (controller.signal.aborted) return;
        const lista = (d.models ?? []).filter((m) => m.pkl_present);
        setModelos(lista);
        setThreads(d.cpu_threads ?? 0);
        setErroLista('');
        if (lista.length && !lista.some((m) => m.id === modeloId)) setModeloId(lista[0].id);
      })
      .catch(() => { if (!controller.signal.aborted) setErroLista('Nao foi possivel ler os modelos.'); });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Trocar de ativo muda a lista de modelos; o modelo escolhido nao pode
  // sobreviver de um ativo para o outro, senao o `timeframe` calculado
  // continuaria vindo de um modelo que nao e mais o exibido.
  useEffect(() => {
    if (!visiveis.length) return;
    if (!visiveis.some((m) => m.id === modeloId)) {
      setModeloId(visiveis[0].id);
      setPrevisao(null);
    }
  }, [visiveis, modeloId]);

  const escolhido = useMemo(
    () => modelos.find((m) => m.id === modeloId) ?? null,
    [modelos, modeloId],
  );

  const prever = useCallback(async () => {
    if (!modeloId || ocupado) return;
    setOcupado(true);
    try {
      // O backend resolve o modelo por (symbol, timeframe), nao pelo id.
      const tf = escolhido?.timeframe ?? modeloId.split('_')[1] ?? 'H1';
      const r = await fetch(`${API}/api/ai/predict?symbol=${encodeURIComponent(simbolo)}&timeframe=${encodeURIComponent(tf)}`);
      const d = (await r.json()) as Previsao;
      setPrevisao(d);
      const ok = d.disponivel ?? d.available;
      void notify(ok ? `Sinal ${d.signal}` : 'Previsao indisponivel', ok ? `Confianca ${pct(d.confidence)}` : (d.reason ?? 'sem motivo informado'));
    } catch (e) {
      setPrevisao({ reason: `Gateway indisponivel: ${e instanceof Error ? e.message : 'erro'}` });
    } finally {
      setOcupado(false);
    }
  }, [modeloId, escolhido, simbolo, ocupado]);
  const sinal = previsao?.signal ?? '—';
  const classe = sinal === 'BUY' ? 'pos' : sinal === 'SELL' ? 'neg' : '';
  const disponivel = previsao ? (previsao.disponivel ?? previsao.available) : false;

  return (
    <section className="card compact-card robot-model" aria-labelledby="robot-model-title">
      <div className="section-head">
        <div>
          <h2 id="robot-model-title">Modelo e sinal</h2>
          <span className="muted">Inferencia real do modelo publicado</span>
        </div>
        <span className="chip">{threads ? `${threads} threads` : 'cpu'}</span>
      </div>

      <div className="rm-row">
        <label className="field rm-symbol">
          <span>Ativo</span>
          <select
            aria-label="Ativo do robo"
            value={simbolo}
            disabled={!simbolos.length}
            onChange={(e) => { setSelectedSymbol(e.target.value.toUpperCase()); setPrevisao(null); }}
          >
            {!simbolos.length && <option value={simbolo}>{simbolo}</option>}
            {simbolos.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label className="field">
          <span>Modelo</span>
          <select aria-label="Modelo do robo" value={modeloId} onChange={(e) => { setModeloId(e.target.value); setPrevisao(null); }} disabled={!visiveis.length}>
            {!visiveis.length && <option value="">Nenhum modelo carregavel para {simbolo}</option>}
            {visiveis.map((m) => <option key={m.id} value={m.id}>{m.timeframe} · acc {pct(m.accuracy)} · edge {pct(m.edge)}</option>)}
          </select>
        </label>
        <button className="btn sm primary" type="button" onClick={() => void prever()} disabled={!modeloId || ocupado}>
            {ocupado ? 'Calculando…' : `Prever ${simbolo}`}
        </button>
      </div>

      {erroLista && <p className="hint" role="status">{erroLista}</p>}

      {previsao && (
        <div className="rm-signal">
          <div className={`rm-sinal ${classe}`}>
            <strong>{sinal}</strong>
            <span className="rm-conf">{pct(previsao.confidence)}</span>
          </div>
          <div className="rm-probs">
            <span>Compra <b className="pos">{pct(previsao.prob_buy)}</b></span>
            <span>Venda <b className="neg">{pct(previsao.prob_sell)}</b></span>
            <span>Neutro <b>{pct(previsao.prob_neutral)}</b></span>
          </div>
          <div className="rm-meta">
            <span>Preco <b className="num">{previsao.price ?? '--'}</b></span>
            {escolhido && <span>Edge treino <b className="num">{pct(escolhido.edge)}</b></span>}
            {previsao.inference_ms ? <span>Latencia <b className="num">{Math.round(previsao.inference_ms)} ms</b></span> : null}
          </div>
        </div>
      )}

      {previsao && !disponivel && (
        <p className="hint" role="status">Previsao indisponivel: {previsao.reason ?? 'sem motivo informado'}</p>
      )}
    </section>
  );
}
