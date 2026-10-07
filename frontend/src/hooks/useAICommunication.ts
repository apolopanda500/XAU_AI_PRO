/**
 * Sinal da IA — inferência REAL do modelo treinado.
 *
 * ESTE ARQUIVO SUBSTITUI O GERADOR DE REGRAS FIXAS.
 *
 * O que existia antes (removido de propósito):
 *
 *   const rsi    = ... ? indicators.rsi : 50;   // RSI inventado
 *   const macd   = ... ? indicators.macd : 0;    // MACD inventado
 *   const volume = ... ? indicators.volume : 1;  // SEMPRE 1
 *   confidence = 70 + (macd * 5);               // constante por regra
 *   confidence = 75 / 80 / 60 / 55 / 50;        // mais constantes
 *   suggestedSL: price * 0.99;                  // aritmética fixa
 *   suggestedTP: price * 1.02;                  // aritmética fixa
 *   suggestedVolume: 0.1;                       // constante
 *
 * Dois problemas graves: o perfil "breakout" exigia volume > 1.5 e por isso
 * NUNCA disparava (o volume era hardcoded em 1); e a "confiança" era um número
 * fixo apresentado na tela como se fosse uma estatística do modelo.
 *
 * AGORA: o sinal vem de POST /api/ai/predict, que roda o classificador
 * treinado sobre os candles do MT5 e devolve a probabilidade real. A confiança
 * mostrada É a probabilidade do modelo. Quando não há dado, não há sinal — a
 * resposta traz `available: false` e o motivo, e a UI diz isso.
 */
import { useCallback, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from './useAppStore';

const API = `${apiBase()}`;

export type DirecaoSinal = 'BUY' | 'SELL' | 'NEUTRAL';

export interface SinalIA {
  id: string;
  symbol: string;
  timeframe: string;
  direction: DirecaoSinal;
  /** Probabilidade real do classificador (0-100). Nunca uma constante. */
  confidence: number;
  probBuy: number;
  probSell: number;
  probNeutral: number;
  price: number;
  atr: number;
  edge: number | null;
  accuracy: number | null;
  reason: string;
  model: string;
  inferenceMs: number;
  timestamp: Date;
}

export interface ModeloTreinado {
  id: string;
  symbol: string;
  timeframe: string;
  publicable: boolean;
  reason: string;
  accuracy: number | null;
  f1: number | null;
  baseline: number | null;
  edge: number | null;
  edgeMin: number | null;
  edgeFolds: number[];
  edgeMean: number | null;
  edgeStd: number | null;
  trainSamples: number | null;
  testSamples: number | null;
  purged: number | null;
  trainDate: string | null;
  featureVersion: string | null;
  featureHash: string | null;
  algorithm: string | null;
  pklPresent: boolean;
  cpuThreads: number;
}

/** Resposta crua do backend, já normalizada para camelCase. */
interface RespostaPredict {
  ok?: boolean;
  available?: boolean;
  reason?: string;
  symbol?: string;
  timeframe?: string;
  signal?: string;
  confidence?: number;
  prob_buy?: number;
  prob_sell?: number;
  prob_neutral?: number;
  price?: number;
  atr?: number;
  edge?: number | null;
  accuracy?: number | null;
  inference_ms?: number;
  model?: string;
}

export interface ResultadoInferencia {
  sinal: SinalIA | null;
  /** `true` quando o backend respondeu e a inferência rodou de fato. */
  disponivel: boolean;
  /** Motivo legível para a UI. Vazio quando deu tudo certo. */
  motivo: string;
}

const MOTIVO_TIMEOUT = 'Sem resposta do gateway. O serviço de inferência não respondeu a tempo.';

async function pedirPrevisao(
  symbol: string,
  timeframe: string,
  signal?: AbortSignal,
): Promise<ResultadoInferencia> {
  const url = `${API}/api/ai/predict?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`;
  let r: Response;
  try {
    r = await fetch(url, { signal: signal ?? AbortSignal.timeout(20000) });
  } catch (e) {
    const mensagem =
      e instanceof DOMException && e.name === 'AbortError'
        ? MOTIVO_TIMEOUT
        : `Gateway inacessível: ${e instanceof Error ? e.message : 'erro'}`;
    return { sinal: null, disponivel: false, motivo: mensagem };
  }

  let d: RespostaPredict;
  try {
    d = (await r.json()) as RespostaPredict;
  } catch {
    return {
      sinal: null,
      disponivel: false,
      motivo: `Resposta inválida do gateway (HTTP ${r.status})`,
    };
  }

  if (!r.ok || d.ok === false) {
    return { sinal: null, disponivel: false, motivo: d.reason || `HTTP ${r.status}` };
  }
  if (d.available !== true) {
    return { sinal: null, disponivel: false, motivo: d.reason || 'Inferência indisponível' };
  }
  if (typeof d.confidence !== 'number' || typeof d.signal !== 'string') {
    return { sinal: null, disponivel: false, motivo: 'Resposta sem confiança' };
  }

  return {
    disponivel: true,
    motivo: '',
    sinal: {
      id:
        typeof crypto !== 'undefined' && 'randomUUID' in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.floor(Math.random() * 1e9)}`,
      symbol: d.symbol ?? symbol,
      timeframe: d.timeframe ?? timeframe,
      direction: (d.signal === 'BUY' || d.signal === 'SELL' ? d.signal : 'NEUTRAL') as DirecaoSinal,
      confidence: d.confidence,
      probBuy: d.prob_buy ?? 0,
      probSell: d.prob_sell ?? 0,
      probNeutral: d.prob_neutral ?? 0,
      price: d.price ?? 0,
      atr: d.atr ?? 0,
      edge: d.edge ?? null,
      accuracy: d.accuracy ?? null,
      reason: d.reason ?? '',
      model: d.model ?? '',
      inferenceMs: d.inference_ms ?? 0,
      timestamp: new Date(),
    },
  };
}

/** Inventário dos modelos treinados, com métricas reais. */
export async function buscarModelosTreinados(
  signal?: AbortSignal,
): Promise<{ modelos: ModeloTreinado[]; cpuThreads: number; erro: string }> {
  try {
    const r = await fetch(`${API}/api/ai/trained`, {
      signal: signal ?? AbortSignal.timeout(10000),
    });
    if (!r.ok) return { modelos: [], cpuThreads: 0, erro: `HTTP ${r.status}` };
    const d = (await r.json()) as {
      models?: Array<Record<string, unknown>>;
      cpu_threads?: number;
    };
    const modelos = (d.models ?? []).map((m) => ({
      id: String(m.id ?? ''),
      symbol: String(m.symbol ?? ''),
      timeframe: String(m.timeframe ?? ''),
      publicable: Boolean(m.publicable),
      reason: String(m.reason ?? ''),
      accuracy: (m.accuracy as number | null) ?? null,
      f1: (m.f1 as number | null) ?? null,
      baseline: (m.baseline as number | null) ?? null,
      edge: (m.edge as number | null) ?? null,
      edgeMin: (m.edge_min as number | null) ?? null,
      edgeFolds: Array.isArray(m.edge_folds) ? (m.edge_folds as number[]) : [],
      edgeMean: (m.edge_mean as number | null) ?? null,
      edgeStd: (m.edge_std as number | null) ?? null,
      trainSamples: (m.train_samples as number | null) ?? null,
      testSamples: (m.test_samples as number | null) ?? null,
      purged: (m.purged as number | null) ?? null,
      trainDate: (m.train_date as string | null) ?? null,
      featureVersion: (m.feature_version as string | null) ?? null,
      featureHash: (m.feature_hash as string | null) ?? null,
      algorithm: (m.algorithm as string | null) ?? null,
      pklPresent: Boolean(m.pkl_present),
      cpuThreads: Number(m.cpu_threads ?? 0),
    }));
    return { modelos, cpuThreads: d.cpu_threads ?? 0, erro: '' };
  } catch (e) {
    return {
      modelos: [],
      cpuThreads: 0,
      erro: e instanceof Error ? e.message : 'erro',
    };
  }
}

/**
 * Hook de inferência. Substitui `useAICommunication`.
 *
 * `timeframe` vem do modelo escolhido pelo operador: cada modelo treinado tem
 * o seu timeframe, e usar outro seria alimentar o classificador com dados que
 * ele não viu no treino.
 */
export function useInferenciaIA(timeframe: string, enabled: boolean) {
  const [sinal, setSinal] = useState<SinalIA | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [disponivel, setDisponivel] = useState(false);
  const setAiStatus = useAppStore((s) => s.setAiStatus);

  /*
    O INTERRUPTOR `enabled` NAO ERA USADO (05/10/2026).

    O parâmetro existia na assinatura e não aparecia no corpo: o hook inferia
    sempre e escrevia `aiStatus` sempre. Como nenhum componente o chamava com
    ligado, o cabeçalho ficava em "AI: Inativo" — o valor inicial do store —
    mesmo com a IA inteira implementada no EA (`AIConnector`, `AIEngine`,
    `ModelGovernance`).

    Aqui ele passa a valer, e desligado não escreve NADA: deixar o estado
    intacto é o que permite ao operador ver o último sinal real depois de
    pausar, em vez de ver a tela zerar.
  */
  const ligar = enabled;

  const inferir = useCallback(
    async (symbol: string, signal?: AbortSignal): Promise<ResultadoInferencia> => {
      if (!ligar) {
        const parado = {
          disponivel: false,
          sinal: null,
          motivo: 'IA desligada pelo operador',
        } as unknown as ResultadoInferencia;
        setMotivo(parado.motivo);
        return parado;
      }
      setCarregando(true);
      const r = await pedirPrevisao(symbol, timeframe, signal);
      setCarregando(false);
      setDisponivel(r.disponivel);
      setMotivo(r.motivo);
      if (r.sinal) {
        setSinal(r.sinal);
        setAiStatus(
          `Sinal: ${r.sinal.direction} (${r.sinal.confidence.toFixed(1)}%) · ` +
            `${r.sinal.model} · ${r.sinal.inferenceMs.toFixed(0)}ms`,
        );
      } else {
        // Sem inferência, o último sinal deixa de valer: um preço velho com
        // confiança de minuto atrás é pior do que nenhuma informação.
        setSinal(null);
        setAiStatus(`IA: ${r.motivo}`);
      }
      return r;
    },
    [timeframe, ligar, setAiStatus],
  );

  /*
    O ESTADO DA IA NO CABEÇALHO, com um interruptor que o operador controla.

    Antes o texto vinha do último `inferir()` — e como ninguém chamava, ficava
    em "Inativo" para sempre. Agora o texto segue o interruptor, e o status só
    é escrito quando a IA está ligada.
  */
  const ativar = useCallback(
    (ligado: boolean) => {
      setAiStatus(ligado ? 'Ativa' : 'Inativa');
    },
    [setAiStatus],
  );

  return { sinal, carregando, motivo, disponivel, inferir, ativar };
}
