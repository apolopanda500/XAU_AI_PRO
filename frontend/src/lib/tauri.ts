// Detecta se o frontend esta rodando dentro do webview do Tauri
export const isTauri = (): boolean =>
  typeof window !== 'undefined' &&
  ('__TAURI_IPC__' in window || '__TAURI__' in window || '__TAURI_INTERNALS__' in window);
