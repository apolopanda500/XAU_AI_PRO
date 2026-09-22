// Hook de auto-refresh com tratamento de erros
// Auto-refresh hook with error handling

import { useEffect, useRef, useCallback } from 'react';

export function useAutoRefresh(
  callback: () => void | Promise<void>,
  intervalMs: number,
  enabled: boolean = true,
  immediate: boolean = true
) {
  const callbackRef = useRef(callback);
  const timerRef = useRef<number>();
  const isRunningRef = useRef(false);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  const execute = useCallback(async () => {
    if (isRunningRef.current) return;
    isRunningRef.current = true;
    try {
      await callbackRef.current();
    } catch (error) {
      console.error('[useAutoRefresh] Erro:', error);
    } finally {
      isRunningRef.current = false;
    }
  }, [callbackRef]);

  useEffect(() => {
    if (!enabled) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    // Executar imediatamente na ativação
    if (immediate) {
      execute();
    }

    timerRef.current = window.setInterval(() => {
      execute();
    }, Math.max(1000, intervalMs));

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [enabled, intervalMs, immediate, execute]);

  const refresh = useCallback(() => {
    execute();
  }, [execute]);

  return { refresh };
}
