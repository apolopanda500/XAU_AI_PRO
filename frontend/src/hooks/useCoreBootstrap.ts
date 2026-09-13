import { useEffect, useRef, useState } from 'react';
import { invoke } from '@tauri-apps/api/tauri';

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

    setCoreStatus('starting');
    invoke('start_core')
      .then(() => {
        setCoreStatus('started');
        console.log('[Core] Rust Core iniciado pelo Tauri');
      })
      .catch((err) => {
        setCoreStatus('error');
        console.error('[Core] Falha ao iniciar Rust Core via Tauri:', err);
      });
  }, []);

  return { coreStatus };
}
