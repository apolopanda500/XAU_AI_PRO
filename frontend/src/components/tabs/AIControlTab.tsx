// Painel de IA do XAU AI PRO.
//
// O sinal vem da INFERENCIA REAL do modelo treinado
// (POST /api/ai/predict -> backend/ai_inference.py). Não há mais gerador de
// regras no frontend: os valores de RSI/MACD/volume fixos, a confiança
// constante por regra e o SL/TP em preco*0,99 / preco*1,02 foram removidos.
//
// Quando o modelo não está publicado, ou o MT5 não devolve candles, ou o
// timeframe não bate com o treino, a tela mostra o motivo. Não há número
// inventado para preencher espaço.

import { useCallback, useEffect, useMemo, useState } from 'react';
import { HelpTooltip } from '../../components/HelpTooltip';
import CopilotPanel from '../../components/CopilotPanel';
import '../copilot.css';
import { useAppStore } from '../../hooks/useAppStore';
import {
  buscarModelosTreinados,
  useInferenciaIA,
  type ModeloTreinado,
  type SinalIA,
} from '../../hooks/useAICommunication';
import { fmtNum, fmtPct } from '../../lib/format';

const ROTULO_DIR: Record<string, string> = {
  BUY: 'Compra',
  SELL: 'Venda',
  NEUTRAL: 'Aguardar',
};

function pct(n: number | null, casas = 4): string {
  return n === null ? '--' : `${n >= 0 ? '+' : ''}${(n * 100).toFixed(casas * 100 - 1)}%`;
}

function num(n: number | null, casas = 4): string {
  return n === null ? '--' : n.toFixed(casas);
}

export default function AIPanel() {
  const selectedSymbol = useAppStore((s) => s.selectedSymbol) || 'XAUUSD';
  const aiEnabled = useAppStore((s) => s.settings.aiEnabled);
  const aiInterval = useAppStore((s) => s.settings.aiInterval) || 60;
  // Aba interna: 'modelo' e a leitura do operador (probabilidade real do
  // modelo treinado); 'copiloto' e a conversa sobre o codigo do EA. Os dois
  // coexistem em vez de se substituirem — um responde "o que o modelo diz
  // agora", o outro responde "por que o codigo esta assim".
  const [aba, setAba] = useState<'modelo' | 'copiloto'>('modelo');

  const [modelos, setModelos] = useState<ModeloTreinado[]>([]);
  const [cpuThreads, setCpuThreads] = useState(0);
  const [modeloId, setModeloId] = useState<string>('');
  const [erroCatalogo, setErroCatalogo] = useState('');
  const [historico, setHistorico] = useState<SinalIA[]>([]);

  const modelo = modelos.find((m) => m.id === modeloId) ?? null;
  const timeframe = modelo?.timeframe ?? 'H1';

  // Inventario agrupado por simbolo: o treino cobre varios pares, e listar 36
  // artefatos em sequencia nao deixa ver quais simbolos estao cobertos.
  const porSimbolo = useMemo(() => {
    const mapa = new Map<string, ModeloTreinado[]>();
    for (const m of modelos) {
      const chave = (m.symbol || 'SEM_SIMBOLO').toUpperCase();
      const lista = mapa.get(chave);
      if (lista) lista.push(m);
      else mapa.set(chave, [m]);
    }
    for (const lista of mapa.values()) {
      lista.sort((a, b) => a.timeframe.localeCompare(b.timeframe));
    }
    return [...mapa.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [modelos]);

  const totalPublicados = modelos.filter((m) => m.publicable && m.pklPresent).length;

  const { sinal, carregando, motivo, disponivel, inferir } = useInferenciaIA(
    timeframe,
    aiEnabled,
  );

  // Inventário dos modelos treinados.
  useEffect(() => {
    const controller = new AbortController();
    void buscarModelosTreinados(controller.signal).then(({ modelos: lista, cpuThreads: cpus, erro }) => {
      if (controller.signal.aborted) return;
      setModelos(lista);
      setCpuThreads(cpus);
      setErroCatalogo(erro);
      // Preselecciona o primeiro publicavel com artefato carregado.
      const primeiro = lista.find((m) => m.publicable && m.pklPresent) ?? lista[0] ?? null;
      if (primeiro) setModeloId(primeiro.id);
    });
    return () => controller.abort();
  }, []);

  const rodar = useCallback(async () => {
    const r = await inferir(selectedSymbol);
    if (r.sinal) setHistorico((h) => [r.sinal!, ...h].slice(0, 10));
  }, [inferir, selectedSymbol]);

  // Inferência ao vivo, no intervalo configurado pelo operador.
  useEffect(() => {
    if (!aiEnabled || !modelo) return;
    void rodar();
    const id = window.setInterval(() => void rodar(), Math.max(15, aiInterval) * 1000);
    return () => clearInterval(id);
  }, [aiEnabled, modelo, aiInterval, rodar]);

  if (!aiEnabled) {
    return (
      <div className="ai-panel disabled">
        <div className="ai-header">
          <h3>Inteligência Artificial</h3>
          <span className="muted">Desativado</span>
        </div>
        <div className="ai-disabled">
          <HelpTooltip text="Ative a IA nas configurações">
            <span>IA desativada.</span>
          </HelpTooltip>
        </div>
        {/* O copiloto NAO depende do motor de inferencia: ele le o codigo e
            o mapa de achados. Deixa-lo disponivel com a IA desligada e o
            comportamento correto — desligar a inferencia nao deve apagar a
            ferramenta de diagnostico do codigo. */}
        <CopilotPanel />
      </div>
    );
  }

  const classe = sinal?.direction === 'BUY' ? 'pos' : sinal?.direction === 'SELL' ? 'neg' : '';

  return (
    <div className="ai-panel">
      <div className="ai-header">
        <h3>Inteligência Artificial</h3>
        <span className="muted">
          {sinal ? `inferência real · ${sinal.inferenceMs.toFixed(0)}ms` : 'sem inferência'}
          {cpuThreads > 0 ? ` · ${cpuThreads} threads CPU` : ''}
        </span>
      </div>

      <div className="copilot-tabs" role="tablist" style={{ marginBottom: 10 }}>
        <button
          type="button"
          role="tab"
          aria-selected={aba === 'modelo'}
          className={`copilot-tab ${aba === 'modelo' ? 'on' : ''}`}
          onClick={() => setAba('modelo')}
        >
          Modelo
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={aba === 'copiloto'}
          className={`copilot-tab ${aba === 'copiloto' ? 'on' : ''}`}
          onClick={() => setAba('copiloto')}
        >
          Copiloto
        </button>
      </div>

      {aba === 'copiloto' ? (
        <CopilotPanel />
      ) : (
        <>
      {/* Seleção de modelo: o operador escolhe o artefato e vê as métricas reais. */}
      <div className="ai-model-card">
        <div className="ai-model-info">
          <div className="ai-model-name">
            {modelo ? `${modelo.symbol || selectedSymbol} ${modelo.timeframe}` : 'Nenhum modelo'}
          </div>
          <span>
            {modelo?.algorithm ?? '--'} · {modelo?.featureVersion ?? '--'} ·{' '}
            {modelo?.trainSamples ?? '--'} amostras de treino
          </span>
        </div>
        <div className="ai-model-selector">
          <label htmlFor="ai-modelo">Modelo</label>
          <select
            id="ai-modelo"
            value={modeloId}
            onChange={(e) => setModeloId(e.target.value)}
          >
            {modelos.length === 0 && <option value="">—</option>}
            {porSimbolo.map(([simbolo, lista]) => (
              <optgroup key={simbolo} label={simbolo}>
                {lista.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.timeframe} · acc {num(m.accuracy, 3)} · edge {pct(m.edge, 3)}
                    {m.publicable ? '' : ' (reprovado)'}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>
      </div>

      {/* Métricas do modelo escolhido. */}
      {modelo && (
        <section className="ai-info-section" aria-label="Desempenho do modelo">
          <h4>Desempenho medido</h4>
          <div className="metrics-grid">
            <div className="card metric-card">
              <span className="muted">Acurácia</span>
              <strong>{fmtNum(modelo.accuracy, 4)}</strong>
              <small>palpite: {num(modelo.baseline, 3)}</small>
            </div>
            <div className="card metric-card">
              <span className="muted">Edge</span>
              <strong className={modelo.edge != null && modelo.edge > 0 ? 'pos' : ''}>
                {pct(modelo.edge, 2)}
              </strong>
              <small>mínimo exigido: {pct(modelo.edgeMin, 0)}</small>
            </div>
            <div className="card metric-card">
              <span className="muted">Edge médio</span>
              <strong>{pct(modelo.edgeMean, 2)}</strong>
              <small>desvio {num(modelo.edgeStd, 3)}</small>
            </div>
            <div className="card metric-card">
              <span className="muted">Teste</span>
              <strong>{modelo.testSamples ?? '--'}</strong>
              <small>purga: {modelo.purged ?? '--'} candles</small>
            </div>
          </div>
          {modelo.edgeFolds.length > 0 && (
            <p className="muted">
              Edge por fold: {modelo.edgeFolds.map((e) => pct(e, 2)).join('  ')}
            </p>
          )}
          {!modelo.publicable && (
            <p className="auth-erro">
              Modelo reprovado na porta de qualidade — não pode operar. Motivo:{' '}
              {modelo.reason || 'não registrado'}
            </p>
          )}
        </section>
      )}

      {/* Sinal. Só aparece quando a inferência rodou de verdade. */}
      {sinal ? (
        <div className={`ai-signal-card ${classe}`}>
          <div className="ai-signal-header">
            <span className="ai-symbol">
              {sinal.symbol} {sinal.timeframe}
            </span>
            <span className={`ai-direction ${classe}`}>{ROTULO_DIR[sinal.direction]}</span>
            <span className={`ai-confidence ${classe}`}>
              {fmtPct(sinal.confidence)}
            </span>
          </div>
          <div className="ai-signal-details">
            <div className="detail-item">
              <span className="detail-label">Compra</span>
              <span className="detail-value mono">{fmtPct(sinal.probBuy * 100)}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Venda</span>
              <span className="detail-value mono">{fmtPct(sinal.probSell * 100)}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Neutro</span>
              <span className="detail-value mono">{fmtPct(sinal.probNeutral * 100)}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Preço</span>
              <span className="detail-value mono">{fmtNum(sinal.price, 2)}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">ATR</span>
              <span className="detail-value mono">{fmtNum(sinal.atr, 2)}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Modelo</span>
              <span className="detail-value mono">{sinal.model}</span>
            </div>
          </div>
          <p className="muted">
            A confiança é a probabilidade que o modelo atribui à decisão. Stop Loss,
            Take Profit e volume não vêm do modelo: são definidos pelo operador no
            tamanho da posição, porque dependem da banca e do risco por trade.
          </p>
        </div>
      ) : (
        <div className="placeholder" role="status">
          {carregando
            ? 'Inferindo…'
            : disponivel
              ? 'Sem sinal.'
              : motivo || 'Aguardando inferência.'}
        </div>
      )}

      <div className="ai-actions">
        <button className="btn primary" onClick={() => void rodar()} disabled={carregando || !modelo}>
          {carregando ? 'Inferindo...' : 'Inferir agora'}
        </button>
      </div>

      {historico.length > 0 && (
        <div className="ai-recent-signals">
          <h4>Sinais recentes</h4>
          <div className="ai-signals-list">
            {historico.map((s) => (
              <div
                key={s.id}
                className={`ai-signal-item ${s.direction === 'BUY' ? 'pos' : s.direction === 'SELL' ? 'neg' : ''}`}
              >
                <span className="signal-time">{s.timestamp.toLocaleTimeString('pt-BR')}</span>
                <span className="signal-symbol">
                  {s.symbol} {s.timeframe}
                </span>
                <span className="signal-direction">{s.direction}</span>
                <span className="signal-confidence">{fmtPct(s.confidence)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <section className="ai-info-section" aria-label="Inventário de modelos">
        <h4>Inventário de modelos</h4>
        <p className="muted">
          {modelos.length} artefatos em {porSimbolo.length} símbolos ·{' '}
          {totalPublicados} publicados para operar · {cpuThreads} threads de CPU
        </p>
        {erroCatalogo && <p className="auth-erro">Catálogo: {erroCatalogo}</p>}
        {porSimbolo.map(([simbolo, lista]) => {
          const prontos = lista.filter((m) => m.publicable && m.pklPresent).length;
          return (
            <div className="ai-symbol-block" key={simbolo}>
              <div className="ai-symbol-head">
                <span className="ai-symbol-code">{simbolo}</span>
                <span className={`chip ${prontos > 0 ? 'ok' : 'warn'}`}>
                  {prontos}/{lista.length}
                </span>
              </div>
              <div className="ai-symbol-chips">
                {lista.map((m) => {
                  const estado = m.publicable && m.pklPresent
                    ? 'ok'
                    : m.publicable
                      ? 'warn'
                      : 'bad';
                  const rotulo = m.publicable && m.pklPresent
                    ? 'pronto'
                    : m.publicable
                      ? 'sem artefato'
                      : 'reprovado';
                  return (
                    <button
                      type="button"
                      key={m.id}
                      className={`ai-model-chip is-${estado}${m.id === modeloId ? ' is-selected' : ''}`}
                      onClick={() => setModeloId(m.id)}
                      title={`${m.id} · acc ${num(m.accuracy, 4)} · edge ${pct(m.edge, 4)}`}
                    >
                      <span className="chip-tf">{m.timeframe}</span>
                      <span className="chip-state">{rotulo}</span>
                    </button>
                  );
                })}
              </div>
              {lista.some((m) => !m.publicable && m.reason) && (
                <p className="muted">
                  {lista
                    .filter((m) => !m.publicable && m.reason)
                    .map((m) => `${m.timeframe}: ${m.reason}`)
                    .join(' · ')}
                </p>
              )}
            </div>
          );
        })}
        {modelos.length === 0 && !erroCatalogo && (
          <p className="muted">Nenhum metadado de modelo encontrado.</p>
        )}
      </section>
        </>
      )}
    </div>
  );
}
