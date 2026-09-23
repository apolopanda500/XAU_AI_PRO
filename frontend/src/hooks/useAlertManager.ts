// Hook de gerenciamento de alertas para XAU AI PRO.
// Persistência em localStorage + avaliação contra cotações reais do store
// + notificação nativa via lib/notify (Tauri, com fallback silencioso web).
import { useState, useCallback, useEffect, useRef } from 'react';
import { useAppStore } from './useAppStore';
import type { Quote } from './useAppStore';
import { notify } from '../lib/notify';
import { apiBase } from '../lib/api';

export type AlertType = 'price_above' | 'price_below' | 'spread_above' | 'time';

export interface Alert {
  id: string;
  type: AlertType;
  symbol: string;
  condition: string;
  value: number;
  active: boolean;
  createdAt: Date;
  triggeredAt: Date | null;
  timesTriggered: number;
  notified: boolean;
}

export interface AlertManager {
  alerts: Alert[];
  activeAlerts: Alert[];
  recentlyTriggered: Alert[];
  createAlert: (alert: Omit<Alert, 'id' | 'createdAt' | 'triggeredAt' | 'timesTriggered' | 'notified'>) => Alert;
  removeAlert: (id: string) => void;
  toggleAlert: (id: string) => void;
  editAlert: (id: string, updates: Partial<Alert>) => void;
  getSelectedQuote: () => Quote | undefined;
}

const ALERTS_KEY = 'xau_ai_pro_alerts';

export function useAlertManager(): AlertManager {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const quotes = useAppStore((s) => s.quotes);
  const selectedSymbol = useAppStore((s) => s.selectedSymbol);
  
  // Carregar alertas do localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(ALERTS_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as Alert[];
        setAlerts(parsed.map(a => ({
          ...a,
          createdAt: new Date(a.createdAt),
          triggeredAt: a.triggeredAt ? new Date(a.triggeredAt) : null,
        })));
      }
    } catch (e) {
      console.error('[useAlertManager] Erro ao carregar:', e);
    }
  }, []);
  
  // Salvar alertas
  const saveAlerts = useCallback((newAlerts: Alert[]) => {
    localStorage.setItem(ALERTS_KEY, JSON.stringify(newAlerts));
    setAlerts(newAlerts);
  }, []);
  
  // Criar alerta
  const createAlert = useCallback((data: Omit<Alert, 'id' | 'createdAt' | 'triggeredAt' | 'timesTriggered' | 'notified'>): Alert => {
    const newAlert: Alert = {
      ...data,
      id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
      createdAt: new Date(),
      triggeredAt: null,
      timesTriggered: 0,
      notified: false,
    };
    saveAlerts([newAlert, ...alerts]);
    return newAlert;
  }, [alerts, saveAlerts]);
  
  // Remover alerta
  const removeAlert = useCallback((id: string) => {
    saveAlerts(alerts.filter(a => a.id !== id));
  }, [alerts, saveAlerts]);
  
  // Ativar/desativar
  const toggleAlert = useCallback((id: string) => {
    saveAlerts(alerts.map(a => 
      a.id === id ? { ...a, active: !a.active, notified: false } : a
    ));
  }, [alerts, saveAlerts]);
  
  // Editar
  const editAlert = useCallback((id: string, updates: Partial<Alert>) => {
    saveAlerts(alerts.map(a => a.id === id ? { ...a, ...updates } : a));
  }, [alerts, saveAlerts]);
  
  // Obter cotação selecionada
  const getSelectedQuote = useCallback((): Quote | undefined => {
    return quotes.find(q => q.symbol === selectedSymbol);
  }, [quotes, selectedSymbol]);
  
  const activeAlerts = alerts.filter((a) => a.active);
  const recentlyTriggered = alerts
    .filter((a) => a.triggeredAt)
    .sort((a, b) => (b.triggeredAt?.getTime() || 0) - (a.triggeredAt?.getTime() || 0))
    .slice(0, 10);

  // Avaliação automática: a cada tick de cotação, verifica alertas ativos
  // contra preço/spread reais e dispara notificação nativa (1x por ativação).
  const quotesRef = useRef(quotes);
  quotesRef.current = quotes;
  useEffect(() => {
    const check = (list: Alert[]) => {
      const qs = quotesRef.current;
      if (!qs.length) return;
      let changed = false;
      const next = list.map((a) => {
        if (!a.active || a.notified) return a;
        const q = qs.find((ql) => ql.symbol === a.symbol);
        if (!q) return a;
        const hit =
          (a.type === 'price_above' && q.price >= a.value) ||
          (a.type === 'price_below' && q.price <= a.value) ||
          (a.type === 'spread_above' && q.spread >= a.value);
        if (!hit) return a;
        changed = true;
        void notify(
          `Alerta ${a.symbol}`,
          `${a.type.replace('_', ' ')}: ${q.price} (alvo ${a.value})`,
        );
        return { ...a, triggeredAt: new Date(), timesTriggered: a.timesTriggered + 1, notified: true };
      });
      if (changed) saveAlerts(next);
    };
    check(alerts);
    // Reavalia quando quotes mudam (ticks do Core via WebSocket).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quotes]);

  // Alerta de evento econômico: a cada 60s consulta /api/economic/alerts
  // e dispara notificação nativa 1x por evento (janela de 6h).
  const notifiedEventsRef = useRef<Set<string>>(new Set());
  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch(`${apiBase()}/api/economic/alerts?hours=6&tz=BRT`, {
          signal: AbortSignal.timeout(8000),
        });
        const d = (await r.json()) as { events?: Array<{ title?: string; when?: string; currency?: string; impact?: string }> };
        if (!r.ok || !d.events?.length) return;
        for (const e of d.events) {
          const key = `${e.title}-${e.when}`;
          if (notifiedEventsRef.current.has(key)) continue;
          notifiedEventsRef.current.add(key);
          void notify(
            `Evento econômico ${e.currency ?? ''} (${e.impact ?? 'alto'})`,
            `${e.title ?? 'Evento'} às ${e.when ?? 'agora'}`,
          );
        }
      } catch {
        // Gateway offline: sem alerta, sem erro na UI.
      }
    };
    void check();
    const t = window.setInterval(check, 60000);
    return () => window.clearInterval(t);
  }, []);

  return {
    alerts,
    activeAlerts,
    recentlyTriggered,
    createAlert,
    removeAlert,
    toggleAlert,
    editAlert,
    getSelectedQuote,
  };
}
