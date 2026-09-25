import { useEffect, useRef, useState } from 'react';
import { isMobileRuntime } from '../lib/api';
import { isTauri } from '../lib/tauri';

export type CoreStatus = 'idle' | 'starting' | 'started' | 'fallback' | 'error';

/**
 * Inicia o Rust Core (xau-ai-pro-core.exe) via comando Tauri `start_core`.
 * O WebSocket do useMarketWebSocket ja possui retry de 3s, entao assim que
 * o Core abrir a porta 9002 a conexao acontece automaticamente.
 */
export function useCoreBootstrap() {
  const [coreStatus, setCoreStatus] = useState<CoreStatus>('idle');
  const attemptedRef = useRef(false);

  useEffect(() => {
    if (attemptedRef.current) return;
    attemptedRef.current = true;

    if (isMobileRuntime()) {
      setCoreStatus('fallback');
      console.info('[Core] mobile usa gateway remoto configurável');
      return;
    }
    if (!isTauri()) {
      setCoreStatus('fallback');
      console.warn(
        '[Core] Ambiente sem Tauri detectado - inicie o core manualmente (core\\target\\release\\xau-ai-pro-core.exe)'
      );
      return;
    }

    // O Tauri inicia o Core uma única vez no hook `setup`. Não invoque
    // `start_core` aqui: o WebView pode montar este hook mais de uma vez.
    setCoreStatus('started');
    console.log('[Core] inicialização delegada ao setup do Tauri');
  }, []);

  return { coreStatus };
}
