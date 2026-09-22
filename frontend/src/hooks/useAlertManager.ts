// Hook de gerenciamento de alertas para XAU AI PRO
// Alert management hook

import { useState, useCallback, useEffect } from 'react';
import { useAppStore } from './useAppStore';
import type { Quote } from './useAppStore';

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
