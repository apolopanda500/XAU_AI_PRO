import { QueryClient } from '@tanstack/react-query';
import { useCallback, useState } from 'react';
import { apiBase } from '../lib/api';
import { useQuery } from '@tanstack/react-query';

// Um cliente compartilhado para consultas futuras do gateway. O cache fica
// isolado do estado operacional do robô e não executa comandos de trading.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5_000,
    },
  },
});

export function useCoreHealth() {
  return useQuery({
    queryKey: ['core-health'],
    queryFn: async () => {
      const response = await fetch(`${apiBase()}/api/health`);
      if (!response.ok) throw new Error(`Gateway HTTP ${response.status}`);
      const payload = (await response.json()) as { ok?: boolean };
      return payload.ok === true;
    },
    refetchInterval: 30_000,
    staleTime: 25_000,
    retry: 1,
  });
}

type Json = Record<string, unknown>;
const API = `${apiBase()}`;
const get = async <T>(path: string, timeoutMs = 8000): Promise<T> => {
  const r = await fetch(`${API}${path}`, { signal: AbortSignal.timeout(timeoutMs) });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json() as Promise<T>;
};

// Consultas de leitura do gateway (cache compartilhado entre abas; sem comandos).
export function useCoreStatus() {
  return useQuery({
    queryKey: ['core-status'],
    queryFn: () => get<Json>('/api/status'),
    refetchInterval: 10_000,
    staleTime: 9_000,
  });
}
export function useAccount() {
  return useQuery({
    queryKey: ['mt5-account'],
    queryFn: () => get<Json>('/api/account'),
    refetchInterval: 10_000,
    staleTime: 9_000,
  });
}
export function usePositions() {
  return useQuery({
    queryKey: ['mt5-positions'],
    queryFn: () => get<Json>('/api/positions'),
    refetchInterval: 10_000,
    staleTime: 9_000,
  });
}
export type JournalLine = { message?: string; time?: string; timestamp?: string };
export type JournalResponse = { lines?: JournalLine[]; count?: number };
export function useJournal(limit = 10) {
  return useQuery<JournalResponse>({
    queryKey: ['mt5-journal', limit],
    queryFn: () => get<JournalResponse>(`/api/journal?limit=${limit}`),
    refetchInterval: 10_000,
    staleTime: 9_000,
  });
}
// Guardian Engine (gestão contínua de posições DEMO) — status em 5s.
export type GuardianStatus = {
  ok?: boolean;
  guardian?: string;
  trade_only?: boolean;
  interval_sec?: number;
  count?: number;
  last_tick?: string | null;
  last_error?: string | null;
  emergency_stop?: boolean;
  rules?: Record<string, Record<string, unknown>>;
  state?: Record<string, Record<string, unknown>>;
  last_actions?: Array<Record<string, unknown>>;
};
export function useGuardian() {
  return useQuery<GuardianStatus>({
    queryKey: ['guardian-status'],
    queryFn: () => get<GuardianStatus>('/api/guardian/status'),
    refetchInterval: 5_000,
    staleTime: 4_000,
    retry: 1,
  });
}

// Motor de operação automática (/api/auto/state) — 5s.
//
// O painel de Automação e o Mini Terminal leem ESTA query: uma chamada só
// para as duas telas. O painel abandonou o fetch proprio em favor dela, que
// e a razão de o motor aparecer rodando na conferência sem duplicar polling.
export type AutoState = {
  ok?: boolean;
  ativo?: boolean;
  simbolo?: string;
  timeframe?: string;
  broker?: string;
  market?: string;
  ciclo?: number;
  threads?: number;
  updated_at?: string;
  limites?: Json;
  // Campos que o backend ja devolve em cada decisao (`auto_engine.Decisao`)
  // e que o Mini Terminal le para mostrar o que o motor esta fazendo agora.
  // Estavam de fora do tipo, entao a tela so conseguia mostrar `motivo`.
  decisoes?: Array<{
    ts?: string;
    simbolo?: string;
    timeframe?: string;
    side?: string;
    acao?: string;
    motivo?: string;
    confianca?: number | null;
    edge?: number | null;
    volume?: number | null;
    sl?: number | null;
    tp?: number | null;
    risco?: number | null;
    /** Nome do artefato que produziu a inferencia do ciclo, lido do
     *  `.meta.json` pelo backend. O Mini Terminal mostra este valor em vez
     *  de fabricar `random_forest_<simbolo>_<tf>` no proprio JSX. */
    modelo?: string;
  }>;
};
export function useAutoState() {
  return useQuery<AutoState>({
    queryKey: ['auto-state'],
    queryFn: () => get<AutoState>('/api/auto/state'),
    refetchInterval: 5_000,
    staleTime: 4_000,
    retry: 1,
  });
}

// Watchdog do EA + telemetria (Fase 3) — estado do EA em 15s.
export type WatchdogStatus = {
  ok?: boolean;
  state?: 'alive' | 'frozen' | 'stale' | 'missing' | 'unknown';
  heartbeat_age_sec?: number | null;
  file_age_sec?: number | null;
  ttl_sec?: number;
  file?: string;
  payload?: Json;
  source?: string;
};
export type TelemetryEvent = { ts_iso?: string; kind?: string; severity?: string; data?: Json };
export type TelemetryStatus = {
  ok?: boolean;
  events?: TelemetryEvent[];
  count?: number;
  total?: number;
  by_kind?: Json;
  by_severity?: Json;
  ea?: WatchdogStatus;
  source?: string;
};
export function useWatchdog() {
  return useQuery<WatchdogStatus>({
    queryKey: ['watchdog-status'],
    queryFn: () => get<WatchdogStatus>('/api/watchdog'),
    refetchInterval: 15_000,
    staleTime: 14_000,
    retry: 1,
  });
}
export function useTelemetry(limit = 100) {
  return useQuery<TelemetryStatus>({
    queryKey: ['telemetry', limit],
    queryFn: () => get<TelemetryStatus>(`/api/telemetry?limit=${limit}`),
    refetchInterval: 15_000,
    staleTime: 14_000,
    retry: 1,
  });
}

// Histórico de snapshots de saúde (equity/posições/EA ao longo do tempo).
export type TelemetrySnapshot = {
  ts?: number;
  ts_iso?: string;
  source?: string;
  terminal_connected?: boolean;
  equity?: number | null;
  balance?: number | null;
  margin_free?: number | null;
  positions?: number;
  floating_profit?: number | null;
  ea_state?: string;
};
export type TelemetryHistory = {
  ok?: boolean;
  snapshots?: TelemetrySnapshot[];
  count?: number;
  last?: TelemetrySnapshot | null;
};
export function useTelemetryHistory(limit = 120) {
  return useQuery<TelemetryHistory>({
    queryKey: ['telemetry-history', limit],
    queryFn: () => get<TelemetryHistory>(`/api/telemetry/history?limit=${limit}`),
    refetchInterval: 60_000,
    staleTime: 55_000,
    retry: 1,
  });
}

// Fila persistente de comandos (Fase 4) — comandos DEMO offline reexecutados sozinhos.
export type QueueItem = {
  queue_id?: string;
  kind?: string;
  status?: string;
  attempts?: number;
  last_error?: string | null;
  created_at?: string;
  updated_at?: string;
};
export type QueueStatus = {
  ok?: boolean;
  count?: number;
  pending?: number;
  sent?: number;
  failed?: number;
  skipped?: number;
  recent?: QueueItem[];
  last_run?: Json;
  file?: string;
  source?: string;
};
export function useQueue() {
  return useQuery<QueueStatus>({
    queryKey: ['queue-status'],
    queryFn: () => get<QueueStatus>('/api/queue/status'),
    refetchInterval: 10_000,
    staleTime: 9_000,
    retry: 1,
  });
}

// Intent log (auditoria de operações) — últimos intents consolidados em 8s.
export type IntentRow = {
  intent_id: string;
  kind?: string;
  ts_iso?: string;
  status?: string;
  data?: Json;
  events?: Array<Json>;
};
export type IntentsSnapshot = {
  ok?: boolean;
  intents?: IntentRow[];
  count?: number;
  file?: string;
};
export function useIntents(limit = 25) {
  return useQuery<IntentsSnapshot>({
    queryKey: ['intents-snapshot', limit],
    queryFn: () => get<IntentsSnapshot>(`/api/intents?limit=${limit}`),
    refetchInterval: 8_000,
    staleTime: 7_000,
    retry: 1,
  });
}

// POST genérico de comando DEMO (guardian/tick, guardian/set, guardian/remove).
// Retorna { data, busy, run } como o useReconcile: erro vira objeto, nunca throw.
export type CommandResult = { ok?: boolean; error?: string } & Record<string, unknown>;
export function useCommand(route: string, timeoutMs = 15000) {
  const [data, setData] = useState<CommandResult | null>(null);
  const [busy, setBusy] = useState(false);
  const run = useCallback(
    async (payload: Record<string, unknown> = {}) => {
      if (busy) return null;
      setBusy(true);
      try {
        const r = await fetch(`${API}${route}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          signal: AbortSignal.timeout(timeoutMs),
        });
        const d = (await r.json()) as CommandResult;
        setData(d);
        return d;
      } catch (e) {
        const d: CommandResult = {
          ok: false,
          error: e instanceof Error ? e.message : 'Gateway indisponível.',
        };
        setData(d);
        return d;
      } finally {
        setBusy(false);
      }
    },
    [busy, route, timeoutMs],
  );
  return { data, busy, run };
}

// Reconciliação manual de intents contra a conta (POST; relatório exibido no painel).
export type ReconcileReport = {
  ok?: boolean;
  checked?: number;
  reconciled?: number;
  unknown?: number;
  still_pending?: number;
  error?: string;
};
export function useReconcile() {
  const [report, setReport] = useState<ReconcileReport | null>(null);
  const [busy, setBusy] = useState(false);
  const run = useCallback(async () => {
    if (busy) return;
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/intents/reconcile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
        signal: AbortSignal.timeout(15000),
      });
      const d = (await r.json()) as ReconcileReport;
      setReport(d);
      return d;
    } catch (e) {
      const d: ReconcileReport = {
        ok: false,
        error: e instanceof Error ? e.message : 'Gateway indisponível.',
      };
      setReport(d);
      return d;
    } finally {
      setBusy(false);
    }
  }, [busy]);
  return { report, busy, run };
}

// Diagnóstico do boot (reconciliação + snapshot inicial) — leitura única, sem polling.
export type BootSnapshot = {
  ts_iso?: string;
  equity?: number | null;
  balance?: number | null;
  positions?: number;
  floating_profit?: number | null;
  ea_state?: string;
  terminal_connected?: boolean;
};
export type BootReport = {
  ok?: boolean;
  mt5_ready?: boolean;
  error?: string;
  snapshot?: BootSnapshot | null;
  snapshot_error?: string;
  source?: string;
};
export function useBoot() {
  return useQuery<BootReport>({
    queryKey: ['boot-report'],
    queryFn: () => get<BootReport>('/api/boot'),
    staleTime: 60_000,
    retry: 1,
  });
}

// Expert Advisors instalados no terminal (/api/eas) — inventario de disco.
export type EaInventoryItem = {
  nome?: string;
  arquivo?: string;
  extensao?: string;
  executavel?: boolean;
  tem_codigo_fonte?: boolean;
  bytes?: number;
  modificado_em?: string;
  hash_sha256_16?: string;
};
export type EaInventory = {
  ok?: boolean;
  status?: string;
  error?: string;
  experts_dir?: string | null;
  experts?: EaInventoryItem[];
  count?: number;
  executaveis?: number;
  apenas_fonte?: number;
  commands_enabled?: boolean;
  control_supported?: boolean;
  observed_at?: string;
};
export function useEaInventory() {
  return useQuery<EaInventory>({
    queryKey: ['ea-inventory'],
    queryFn: () => get<EaInventory>('/api/eas'),
    refetchInterval: 60_000,
    staleTime: 30_000,
    retry: 1,
  });
}

// Estado por EA (/api/eas/status): instalado + visto no journal + heartbeat.
export type EaDetailed = EaInventoryItem & {
  estado?: string;
  no_journal?: boolean;
  ocorrencias_journal?: number;
  ultima_linha_journal?: string | null;
};
export type EaStatusDetail = EaInventory & {
  detalhado?: EaDetailed[];
  heartbeat?: WatchdogStatus & Record<string, unknown>;
  heartbeat_estado?: string;
  nota?: string;
};
export function useEaStatusDetail() {
  return useQuery<EaStatusDetail>({
    queryKey: ['ea-status-detail'],
    queryFn: () => get<EaStatusDetail>('/api/eas/status', 30000),
    refetchInterval: 30_000,
    staleTime: 25_000,
    retry: 1,
  });
}

// Runtime do EA (/api/ea/status): heartbeat vivo, autotrading, terminal.
//
// Este e o sinal que destrava os comandos: o gateway recusa qualquer comando
// de EA sem heartbeat vivo, entao a interface mostra o motivo em vez de um
// botao morto sem explicacao.
export type EaRuntime = {
  ok?: boolean;
  live?: boolean;
  terminal_connected?: boolean;
  autotrading?: boolean;
  ea_heartbeat?: {
    live?: boolean;
    reason?: string;
    state?: string;
    age_sec?: number;
    file_age_sec?: number;
    symbol?: string;
    timeframe?: string;
    source?: string;
  };
  source?: string;
};
export function useEaRuntime() {
  return useQuery<EaRuntime>({
    queryKey: ['ea-runtime'],
    queryFn: () => get<EaRuntime>('/api/ea/status'),
    refetchInterval: 10_000,
    staleTime: 9_000,
    retry: 1,
  });
}

// Contas universal (MEXC/Binance · Spot/Futuros) em paralelo — alimenta eventos e patrimônio.
export type CryptoAccount = {
  broker: string;
  market: string;
  ok: boolean;
  balance: number | null;
  currency: string;
  assets: string[];
  /*
    O MOTIVO DA FALHA, e nao so o `ok: false` (12/10/2026).
    ========================================================
    MEDIDO nas capturas do dono: a faixa do terminal mostrava "MEXC / Spot
    indisponível" e "BINANCE / Futuros indisponível" — e nada dizia POR QUE.
    Chave invalida, IP bloqueado, sem permissao de leitura e gateway fora do
    ar produziam a MESMA linha, e o operador nao tinha por onde comecar.

    O gateway devolve o motivo (`{ ok: false, error }` ou HTTP com corpo); o
    `catch` abaixo o engolia e a tela recebia um `ok: false` mudo. Agora o
    motivo viaja junto, e quem mostra e o terminal (ver
    `UniversalLiveTerminal`).
  */
  error?: string | null;
};
export function useAllCryptoAccounts() {
  return useQuery<CryptoAccount[]>({
    queryKey: ['crypto-accounts'],
    queryFn: async (): Promise<CryptoAccount[]> =>
      Promise.all(
        (['mexc', 'binance'] as const).flatMap((broker) =>
          (['crypto-spot', 'crypto-futures'] as const).map(async (market) => {
            const falha = (motivo: string): CryptoAccount => ({
              broker,
              market,
              ok: false,
              balance: null,
              currency: 'USDT',
              assets: [] as string[],
              error: motivo,
            });
            try {
              const d = await get<Json>(`/api/universal/account?broker=${broker}&market=${market}`);
              if (d.ok === false) {
                return falha(String((d as Json).error ?? 'recusado pelo gateway'));
              }
              const acct = (d.account ?? {}) as Json;
              const rawAssets = Array.isArray(d.assets)
                ? d.assets
                : Array.isArray(d.balances)
                  ? d.balances
                  : [];
              const assets = (rawAssets as Array<Json>)
                .map((a) => String(a.asset ?? a.currency ?? ''))
                .filter(Boolean);
              return {
                broker,
                market,
                ok: true,
                balance: Number(acct.balance ?? acct.totalWalletBalance ?? acct.equity ?? 0),
                currency: String(acct.currency ?? 'USDT'),
                assets,
              };
            } catch (e) {
              return falha(e instanceof Error ? e.message : 'Gateway indisponível.');
            }
          }),
        ),
      ),
    refetchInterval: 30_000,
    staleTime: 25_000,
    retry: 0,
  });
}

export type ConnectionStatus = 'conectada' | 'offline' | 'indisponivel' | 'desativada' | 'code_only';

export interface OverviewRow {
  id?: string;
  broker: string;
  market: string;
  active?: boolean;
  status?: ConnectionStatus | string;
  account?: Json;
  positions?: Array<Record<string, unknown>>;
  pnl?: { value?: number | null; available?: boolean };
  error?: string | null;
  source?: string;
}

export interface UniversalOverview {
  ok?: boolean;
  mt5_required?: boolean;
  connections?: OverviewRow[];
  connected?: number;
  source?: string;
}

/**
 * Visão geral das contas conectadas, sem exigir MT5 aberto.
 *
 * MEDIDO nas capturas MT5 de 12/10/2026 (conta 391773676, XMGlobal-MT5 14):
 * o terminal mostra `Observação do Mercado`, gráfico BTCUSD M15, `Caixa de
 * ferramentas` com posição sell 0.01 e faixa `Saldo 11.47 / Capital 16.53 /
 * Margem 0.83 / Livre 15.70 / Nível 1991.57%`. O app lia tudo por
 * `/api/account` + `/api/positions` (MT5 fixo): com o terminal fechado a
 * tela apagava, mesmo com Binance/MEXC conectadas.
 *
 * Esta query lê `/api/universal/overview`, que responde `mt5_required:
 * false` e lista cada conexão com `status` próprio: MT5 pode estar
 * `offline` e a exchange `conectada` na mesma resposta. O gráfico e o
 * terminal usam esta lista como fonte de conta/posição; as rotas MT5
 * antigas ficam só como reserva legada.
 */
export function useUniversalOverview() {
  return useQuery<UniversalOverview>({
    queryKey: ['universal-overview'],
    queryFn: () => get<UniversalOverview>('/api/universal/overview'),
    refetchInterval: 15_000,
    staleTime: 10_000,
    retry: 1,
  });
}

export interface UniversalAccount {
  ok?: boolean;
  broker?: string;
  market?: string;
  account_id?: string;
  account?: Json;
  error?: string;
  status?: string;
}

export interface UniversalPositions {
  ok?: boolean;
  broker?: string;
  market?: string;
  account_id?: string;
  positions?: Array<Record<string, unknown>>;
  error?: string;
  status?: string;
}

/**
 * Conta da corretora ATIVA (qualquer uma), sem MT5 fixo.
 *
 * Sem escopo, sem consulta: pedir `/api/universal/account?broker=` seria
 * consultar com identidade vazia para receber "corretora não suportada" —
 * uma recusa que o operador leria como defeito do servidor (mesma regra
 * do `useCatalogoAtivos`). Vazio aqui é "escolha a corretora".
 */
export function useUniversalAccount(broker: string, market: string, accountId = '') {
  const b = String(broker || '').trim().toLowerCase();
  const m = String(market || '').trim().toLowerCase();
  return useQuery<UniversalAccount>({
    queryKey: ['universal-account', b, m, accountId],
    queryFn: () => {
      const qs = `/api/universal/account?broker=${encodeURIComponent(b)}&market=${encodeURIComponent(m)}${accountId ? `&account_id=${encodeURIComponent(accountId)}` : ''}`;
      return get<UniversalAccount>(qs);
    },
    enabled: Boolean(b && m),
    refetchInterval: 10_000,
    staleTime: 9_000,
    retry: 1,
  });
}

/** Posições da corretora ATIVA (qualquer uma), sem MT5 fixo. */
export function useUniversalPositions(broker: string, market: string, accountId = '') {
  const b = String(broker || '').trim().toLowerCase();
  const m = String(market || '').trim().toLowerCase();
  return useQuery<UniversalPositions>({
    queryKey: ['universal-positions', b, m, accountId],
    queryFn: () => {
      const qs = `/api/universal/positions?broker=${encodeURIComponent(b)}&market=${encodeURIComponent(m)}${accountId ? `&account_id=${encodeURIComponent(accountId)}` : ''}`;
      return get<UniversalPositions>(qs);
    },
    enabled: Boolean(b && m),
    refetchInterval: 10_000,
    staleTime: 9_000,
    retry: 1,
  });
}

// ---------------------------------------------------------------------------
// PLANO LOCAL (Free / VIP / VIPS) — o que destravou, e onde ativar.
//
// MEDIDO (11/10/2026): o 403 `PLAN_REQUIRED` do `/api/auto/start` chegava na
// tela como "Configurado, mas não ligou: recurso nao liberado no plano atual:
// auto_engine" — e o operador não tinha por onde seguir. O gateway já expunha
// as três rotas (`/api/subscriptions/me`, `/plans` e `/activate`), mas o
// frontend não tinha UM consumidor sequer: o bloqueio existia e o caminho do
// desbloqueio não. É o mesmo beco sem saída das mensagens que mandavam para
// uma aba já removida, só que do lado do plano.
//
// Regra que não muda (AGENTS.md 2): ativar plano aqui não destrava saque,
// transferência nem execução real. `live_execution` e `withdrawals_enabled`
// voltam `false` do gateway em TODAS as respostas, e a UI os mostra como
// declaração, não como interruptor.
// ---------------------------------------------------------------------------
export type PlanoCatalogo = {
  id?: string;
  name?: string;
  description?: string;
  reference_price_monthly?: number;
  currency?: string;
  features?: string[];
  entitlements?: Record<string, boolean>;
};
export type AssinaturaPlano = {
  plan_id?: string;
  effective_plan_id?: string;
  status?: string;
  active?: boolean;
  source?: string;
  plan?: PlanoCatalogo;
  entitlements?: Record<string, boolean>;
  integrity_status?: string;
  integrity_verified?: boolean;
  live_execution?: boolean;
  withdrawals_enabled?: boolean;
  billing_status?: string;
};
export function useAssinatura() {
  return useQuery<{ ok?: boolean; subscription?: AssinaturaPlano }>({
    queryKey: ['subscriptions-me'],
    queryFn: () => get<{ ok?: boolean; subscription?: AssinaturaPlano }>('/api/subscriptions/me'),
    refetchInterval: 30_000,
    staleTime: 20_000,
    retry: 1,
  });
}
export function usePlanosCatalogo() {
  return useQuery<{ ok?: boolean; plans?: PlanoCatalogo[] }>({
    queryKey: ['subscriptions-plans'],
    queryFn: () => get<{ ok?: boolean; plans?: PlanoCatalogo[] }>('/api/subscriptions/plans'),
    staleTime: 600_000,
    retry: 1,
  });
}
export type ResultadoAtivacao = {
  ok?: boolean;
  error?: string;
  subscription?: AssinaturaPlano;
};
/**
 * Ativa um plano NESTE DISPOSITIVO. Não há cobrança, não há saque, não há
 * transferência: `activate_local_plan` só grava o registro local com integridade.
 * A recusa (422 para id inválido) volta como `{ ok: false, error }`, nunca throw.
 */
export async function ativarPlanoLocal(planId: string): Promise<ResultadoAtivacao> {
  try {
    const r = await fetch(`${apiBase()}/api/subscriptions/activate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plan_id: planId }),
      signal: AbortSignal.timeout(10_000),
    });
    const d = (await r.json().catch(() => ({}))) as ResultadoAtivacao;
    if (!r.ok || d.ok === false) {
      return { ok: false, error: d.error ?? `HTTP ${r.status}` };
    }
    return d;
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : 'Gateway indisponível.' };
  }
}
