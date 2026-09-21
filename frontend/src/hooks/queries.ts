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
const get = async <T,>(path: string, timeoutMs = 8000): Promise<T> => {
  const r = await fetch(`${API}${path}`, { signal: AbortSignal.timeout(timeoutMs) });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json() as Promise<T>;
};

// Consultas de leitura do gateway (cache compartilhado entre abas; sem comandos).
export function useCoreStatus() {
  return useQuery({ queryKey: ['core-status'], queryFn: () => get<Json>('/api/status'), refetchInterval: 10_000, staleTime: 9_000 });
}
export function useAccount() {
  return useQuery({ queryKey: ['mt5-account'], queryFn: () => get<Json>('/api/account'), refetchInterval: 10_000, staleTime: 9_000 });
}
export function usePositions() {
  return useQuery({ queryKey: ['mt5-positions'], queryFn: () => get<Json>('/api/positions'), refetchInterval: 10_000, staleTime: 9_000 });
}
export type JournalLine = { message?: string; time?: string; timestamp?: string };
export type JournalResponse = { lines?: JournalLine[]; count?: number };
export function useJournal(limit = 10) {
  return useQuery<JournalResponse>({ queryKey: ['mt5-journal', limit], queryFn: () => get<JournalResponse>(`/api/journal?limit=${limit}`), refetchInterval: 10_000, staleTime: 9_000 });
}
// Guardian Engine (gestão contínua de posições DEMO) — status em 5s.
export type GuardianStatus = {
  ok?: boolean; guardian?: string; demo_only?: boolean; interval_sec?: number;
  count?: number; last_tick?: string | null; last_error?: string | null;
  emergency_stop?: boolean; rules?: Record<string, Record<string, unknown>>; state?: Record<string, Record<string, unknown>>;
  last_actions?: Array<Record<string, unknown>>;
};
export function useGuardian() {
  return useQuery<GuardianStatus>({
    queryKey: ['guardian-status'],
    queryFn: () => get<GuardianStatus>('/api/guardian/status'),
    refetchInterval: 5_000, staleTime: 4_000, retry: 1,
  });
}

// Watchdog do EA + telemetria (Fase 3) — estado do EA em 15s.
export type WatchdogStatus = {
  ok?: boolean; state?: 'alive' | 'frozen' | 'stale' | 'missing' | 'unknown';
  heartbeat_age_sec?: number | null; file_age_sec?: number | null; ttl_sec?: number;
  file?: string; payload?: Json; source?: string;
};
export type TelemetryEvent = { ts_iso?: string; kind?: string; severity?: string; data?: Json };
export type TelemetryStatus = {
  ok?: boolean; events?: TelemetryEvent[]; count?: number; total?: number;
  by_kind?: Json; by_severity?: Json; ea?: WatchdogStatus; source?: string;
};
export function useWatchdog() {
  return useQuery<WatchdogStatus>({
    queryKey: ['watchdog-status'],
    queryFn: () => get<WatchdogStatus>('/api/watchdog'),
    refetchInterval: 15_000, staleTime: 14_000, retry: 1,
  });
}
export function useTelemetry(limit = 100) {
  return useQuery<TelemetryStatus>({
    queryKey: ['telemetry', limit],
    queryFn: () => get<TelemetryStatus>(`/api/telemetry?limit=${limit}`),
    refetchInterval: 15_000, staleTime: 14_000, retry: 1,
  });
}

// Histórico de snapshots de saúde (equity/posições/EA ao longo do tempo).
export type TelemetrySnapshot = {
  ts?: number; ts_iso?: string; source?: string; terminal_connected?: boolean;
  equity?: number | null; balance?: number | null; margin_free?: number | null;
  positions?: number; floating_profit?: number | null; ea_state?: string;
};
export type TelemetryHistory = {
  ok?: boolean; snapshots?: TelemetrySnapshot[]; count?: number; last?: TelemetrySnapshot | null;
};
export function useTelemetryHistory(limit = 120) {
  return useQuery<TelemetryHistory>({
    queryKey: ['telemetry-history', limit],
    queryFn: () => get<TelemetryHistory>(`/api/telemetry/history?limit=${limit}`),
    refetchInterval: 60_000, staleTime: 55_000, retry: 1,
  });
}

// Fila persistente de comandos (Fase 4) — comandos DEMO offline reexecutados sozinhos.
export type QueueItem = {
  queue_id?: string; kind?: string; status?: string; attempts?: number;
  last_error?: string | null; created_at?: string; updated_at?: string;
};
export type QueueStatus = {
  ok?: boolean; count?: number; pending?: number; sent?: number;
  failed?: number; skipped?: number; recent?: QueueItem[];
  last_run?: Json; file?: string; source?: string;
};
export function useQueue() {
  return useQuery<QueueStatus>({
    queryKey: ['queue-status'],
    queryFn: () => get<QueueStatus>('/api/queue/status'),
    refetchInterval: 10_000, staleTime: 9_000, retry: 1,
  });
}

// Intent log (auditoria de operações) — últimos intents consolidados em 8s.
export type IntentRow = {
  intent_id: string; kind?: string; ts_iso?: string; status?: string;
  data?: Json; events?: Array<Json>;
};
export type IntentsSnapshot = { ok?: boolean; intents?: IntentRow[]; count?: number; file?: string };
export function useIntents(limit = 25) {
  return useQuery<IntentsSnapshot>({
    queryKey: ['intents-snapshot', limit],
    queryFn: () => get<IntentsSnapshot>(`/api/intents?limit=${limit}`),
    refetchInterval: 8_000, staleTime: 7_000, retry: 1,
  });
}

// POST genérico de comando DEMO (guardian/tick, guardian/set, guardian/remove).
// Retorna { data, busy, run } como o useReconcile: erro vira objeto, nunca throw.
export type CommandResult = { ok?: boolean; error?: string } & Record<string, unknown>;
export function useCommand(route: string, timeoutMs = 15000) {
  const [data, setData] = useState<CommandResult | null>(null);
  const [busy, setBusy] = useState(false);
  const run = useCallback(async (payload: Record<string, unknown> = {}) => {
    if (busy) return null;
    setBusy(true);
    try {
      const r = await fetch(`${API}${route}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload), signal: AbortSignal.timeout(timeoutMs),
      });
      const d = (await r.json()) as CommandResult;
      setData(d);
      return d;
    } catch (e) {
      const d: CommandResult = { ok: false, error: e instanceof Error ? e.message : 'Gateway indisponível.' };
      setData(d);
      return d;
    } finally {
      setBusy(false);
    }
  }, [busy, route, timeoutMs]);
  return { data, busy, run };
}

// Reconciliação manual de intents contra a conta (POST; relatório exibido no painel).
export type ReconcileReport = {
  ok?: boolean; checked?: number; reconciled?: number; unknown?: number;
  still_pending?: number; error?: string;
};
export function useReconcile() {
  const [report, setReport] = useState<ReconcileReport | null>(null);
  const [busy, setBusy] = useState(false);
  const run = useCallback(async () => {
    if (busy) return;
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/intents/reconcile`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}), signal: AbortSignal.timeout(15000),
      });
      const d = (await r.json()) as ReconcileReport;
      setReport(d);
      return d;
    } catch (e) {
      const d: ReconcileReport = { ok: false, error: e instanceof Error ? e.message : 'Gateway indisponível.' };
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
  ts_iso?: string; equity?: number | null; balance?: number | null; positions?: number;
  floating_profit?: number | null; ea_state?: string; terminal_connected?: boolean;
};
export type BootReport = {
  ok?: boolean; mt5_ready?: boolean; error?: string; snapshot?: BootSnapshot | null;
  snapshot_error?: string; source?: string;
};
export function useBoot() {
  return useQuery<BootReport>({
    queryKey: ['boot-report'],
    queryFn: () => get<BootReport>('/api/boot'),
    staleTime: 60_000, retry: 1,
  });
}


// Contas universal (MEXC/Binance · Spot/Futuros) em paralelo — alimenta eventos e patrimônio.
export type CryptoAccount = { broker: string; market: string; ok: boolean; balance: number | null; currency: string; assets: string[] };
export function useAllCryptoAccounts() {
  return useQuery<CryptoAccount[]>({
    queryKey: ['crypto-accounts'],
    queryFn: async (): Promise<CryptoAccount[]> => Promise.all(
      (['mexc', 'binance'] as const).flatMap((broker) =>
        (['crypto-spot', 'crypto-futures'] as const).map(async (market) => {
          try {
            const d = await get<Json>(`/api/universal/account?broker=${broker}&market=${market}`);
            const acct = (d.account ?? {}) as Json;
            const rawAssets = Array.isArray(d.assets) ? d.assets : Array.isArray(d.balances) ? d.balances : [];
            const assets = (rawAssets as Array<Json>).map((a) => String(a.asset ?? a.currency ?? '')).filter(Boolean);
            return {
              broker, market,
              ok: d.ok !== false,
              balance: Number(acct.balance ?? acct.totalWalletBalance ?? acct.equity ?? 0),
              currency: String(acct.currency ?? 'USDT'),
              assets,
            };
          } catch { return { broker, market, ok: false, balance: null, currency: 'USDT', assets: [] as string[] }; }
        }),
      ),
    ),
    refetchInterval: 30_000,
    staleTime: 25_000,
    retry: 0,
  });
}
