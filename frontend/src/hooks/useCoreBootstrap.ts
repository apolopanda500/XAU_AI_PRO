import { useEffect, useRef, useState } from 'react';

// Detecta se o frontend esta rodando dentro do webview do Tauri
const isTauri = (): boolean =>
  typeof window !== 'undefined' &&
  ('__TAURI_IPC__' in window || '__TAURI__' in window || '__TAURI_INTERNALS__' in window);

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

    if (!isTauri()) {
      // Rodando no navegador (vite dev sem Tauri): Core deve ser iniciado manualmente
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
