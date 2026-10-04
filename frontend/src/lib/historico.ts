/**
 * Fonte unica do historico de deals ( trades ).
 *
 * ANTES: HistoryTab e AnalyticsTab carregavam /api/universal/history cada um
 * com seu proprio fetch, seu proprio parser de numero pt-BR/en, sua propria
 * conta de win-rate e profit factor, e sua propria lista de corretoras. As
 * duas abas mostravam a mesma informacao com numeros que podiam divergir —
 * a mesma conta aparecia com numeros diferentes em abas diferentes, sem que
 * nenhum dos dois estivesse errado.
 *
 * AGORA: um unico modulo busca, normaliza e resume. As duas abas consomem a
 * mesma fonte, entao os numeros concordam por construcao.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiBase } from './api';

export interface Deal {
  id?: string | number;
  broker?: string;
  market?: string;
  symbol?: string;
  side?: string;
  quantity?: number | string;
  volume?: number;
  price?: number | string;
  realizedPnl?: number | string;
  profit?: number;
  executedAt?: string;
  close_time?: string;
  comment?: string;
  position_id?: number | string;
}

/** Resumo de uma pool de deals. Base de win-rate, PF e PnL. */
export interface Resumo {
  total: number;
  wins: number;
  losses: number;
  closed: number;
  qty: number;
  winRate: number;
  profitFactor: number;
  grossWin: number;
  grossLoss: number;
}

/** Parser numerico tolerante a pt-BR e en. Substitui 3 copias locais. */
export function toNumber(value: unknown): number {
  if (typeof value === 'number') return value;
  if (typeof value !== 'string' || !value.trim()) return Number.NaN;
  const cleaned = value.replace(/\s/g, '');
  const normalized = cleaned.includes(',') ? cleaned.replace(/\./g, '').replace(',', '.') : cleaned;
  return Number(normalized);
}

/** PnL realizado de um deal, tolerante a campo ausente. */
export function dealPnl(deal: Deal): number {
  const explicit = toNumber(deal.realizedPnl);
  if (Number.isFinite(explicit)) return explicit;
  return Number.isFinite(deal.profit) ? (deal.profit as number) : 0;
}

/** Data do deal, seja `executedAt` ou `close_time`. */
export function dealDate(deal: Deal): string {
  return deal.executedAt ?? deal.close_time ?? '';
}

/** Resume uma pool de deals. Substitui as copias em History e Analytics. */
export function resumir(deals: readonly Deal[]): Resumo {
  const pnls = deals.map(dealPnl);
  const wins = pnls.filter((p) => p > 0).length;
  const losses = pnls.filter((p) => p < 0).length;
  const grossWin = pnls.filter((p) => p > 0).reduce((s, p) => s + p, 0);
  const grossLoss = Math.abs(pnls.filter((p) => p < 0).reduce((s, p) => s + p, 0));
  const closed = wins + losses;
  return {
    total: pnls.reduce((s, p) => s + p, 0),
    wins,
    losses,
    closed,
    qty: deals.length,
    // performanceMetrics.ts trabalha com TradeResult[]; aqui calculamos direto
    // sobre os PnLs ja extraidos para nao inventar um objeto de trade falso.
    winRate: closed > 0 ? (wins / closed) * 100 : 0,
    profitFactor: grossLoss > 0 ? grossWin / grossLoss : grossWin > 0 ? Infinity : 0,
    grossWin,
    grossLoss,
  };
}

const API = `${apiBase()}`;

/** Corretoras consultadas. MT5 e as cripto; o resto e derivado. */
const BROKERS = ['mt5', 'mexc', 'binance'] as const;

export interface HistoricoState {
  deals: Deal[];
  loading: boolean;
  erro: string;
  status: string;
  updatedAt: string;
  recarregar: () => void;
}

export interface HistoricoOptions {
  broker?: string;
  symbol?: string;
  days?: string;
}

/**
 * Chave estavel de um deal, para deduplicar.
 *
 * POR QUE NAO E SO O `id`
 * ==========================
 * O `id` do gateway e o ticket do MT5, que e um contador POR CONTA. A tela
 * consulta varias corretoras ao mesmo tempo e junta tudo numa lista, entao o
 * mesmo ticket aparece em duas contas — e o React ainda avisaria, porque o
 * `id` repetido vira `key` repetida.
 *
 * A chave precisa do que torna o deal unico no conjunto: corretora, conta,
 * ticket, horario e lado. Sem o horario, um deal de abertura e o de fechamento
 * da mesma posicao (mesmo ticket, mesmo conta) continuariam colidindo.
 */
export function dealChave(deal: Deal, indice = 0): string {
  const partes = [
    deal.broker ?? '',
    String(deal.id ?? ''),
    deal.symbol ?? '',
    deal.executedAt ?? deal.close_time ?? '',
    String(deal.side ?? ''),
  ];
  const chave = partes.join('|');
  // O indice so entra quando o resto e vazio: sem ticket, horario e lado, dois
  // deals seriam indistinguiveis e um deles sumiria da tela. Quando existe
  // qualquer um desses campos, dois deals de verdade NUNCA tem a mesma chave.
  return chave === '||||' ? `sem-campos|${indice}` : chave;
}

/** Remove deals repetidos, preservando a ordem de chegada. */
export function deduplicar(deals: Deal[]): Deal[] {
  const vistas = new Set<string>();
  const saida: Deal[] = [];
  deals.forEach((deal, indice) => {
    const chave = dealChave(deal, indice);
    if (vistas.has(chave)) return;
    vistas.add(chave);
    saida.push(deal);
  });
  return saida;
}

/**
 * Hook de historico. Compartilhado por HistoryTab e AnalyticsTab para que as
 * duas abas leiam exatamente os mesmos deals.
 */
export function useHistorico(options: HistoricoOptions = {}): HistoricoState {
  const { broker = 'all', symbol = '', days = '90' } = options;
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState('');
  const [status, setStatus] = useState('Carregando historico real...');
  const [updatedAt, setUpdatedAt] = useState('--:--:--');
  const [tick, setTick] = useState(0);
  const busyRef = useRef(false);

  useEffect(() => {
    let active = true;

    const carregar = async () => {
      if (busyRef.current) return;
      busyRef.current = true;
      setErro('');
      const lista = broker === 'all' ? [...BROKERS] : [broker];

      const settled = await Promise.allSettled(
        lista.map(async (b) => {
          if (b !== 'mt5' && !symbol.trim()) {
            return { broker: b, deals: [] as Deal[], skipped: true };
          }
          const params = new URLSearchParams({
            broker: b,
            market: b === 'mt5' ? 'other' : 'crypto-spot',
            days,
          });
          if (symbol.trim()) params.set('symbol', symbol.trim());
          const resposta = await fetch(`${API}/api/universal/history?${params}`, {
            signal: AbortSignal.timeout(15000),
          });
          const corpo = (await resposta.json()) as { deals?: Deal[]; error?: string };
          if (!resposta.ok) throw new Error(corpo.error || `${b} indisponivel`);
          return { broker: b, deals: corpo.deals ?? [] };
        }),
      );

      if (!active) return;

      const coletados: Array<{ broker: string; deals: Deal[] }> = [];
      const falhas: string[] = [];
      settled.forEach((resultado, indice) => {
        if (resultado.status === 'fulfilled') {
          if (!resultado.value.skipped) {
            coletados.push({ broker: resultado.value.broker, deals: resultado.value.deals });
          }
        } else {
          const motivo = resultado.reason;
          falhas.push(
            `${lista[indice]}: ${motivo instanceof Error ? motivo.message : 'indisponivel'}`,
          );
        }
      });

      const plano = coletados.flatMap(({ broker: b, deals: lista }) =>
        lista.map((deal) => ({ ...deal, broker: deal.broker ?? b })),
      );
      plano.sort((a, b) => dealDate(b).localeCompare(dealDate(a)));
      // Deduplica DEPOIS do sort: a ordem vem de varias corretoras, e o mesmo
      // ticket pode aparecer em contas diferentes. Sem esta linha o operador
      // via a mesma operacao duas vezes na tabela.
      setDeals(deduplicar(plano));

      const contagem = coletados.map((c) => `${c.broker}: ${c.deals.length}`).join('  |  ');
      setStatus(
        falhas.length
          ? `${contagem || 'sem fontes'}  |  falhas parciais: ${falhas.join(' | ')}`
          : contagem || 'Sem fontes para o filtro atual',
      );
      setErro(coletados.length ? '' : falhas.join(' | '));
      setUpdatedAt(new Date().toLocaleTimeString('pt-BR'));
      setLoading(false);
      busyRef.current = false;
    };

    void carregar();
    return () => {
      active = false;
    };
  }, [broker, symbol, days, tick]);

  const recarregar = useCallback(() => {
    busyRef.current = false;
    setLoading(true);
    setTick((n) => n + 1);
  }, []);

  return useMemo(
    () => ({ deals, loading, erro, status, updatedAt, recarregar }),
    [deals, loading, erro, status, updatedAt, recarregar],
  );
}
