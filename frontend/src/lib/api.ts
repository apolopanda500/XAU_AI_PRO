// Configuração única de API do frontend: localhost no desktop, configurável no Android.
// Prioridade: localStorage (ajuste em runtime) → variável VITE_* (build) → localhost (desktop).
//
// Android: o WebView não pode usar 127.0.0.1 (o gateway roda no PC/VPS do trader).
// Definir VITE_API_BASE/VITE_WS_URL no build (.env.production) OU ajustar em runtime
// pela tela de conexão (localStorage 'xau-api-base' / 'xau-ws-url').
type ViteEnv = { env?: Record<string, string | undefined> };
const viteEnv: ViteEnv = (import.meta as unknown as ViteEnv) ?? {};

function stored(key: string): string {
  try {
    // window.localStorage explícito: evita colisão com o localStorage experimental do Node 26 em testes.
    return typeof window !== 'undefined' ? window.localStorage.getItem(key) ?? '' : '';
  } catch {
    return '';
  }
}

// Detecta plataforma mobile (Tauri injeta o user-agent do Android/iOS).
export function isMobileRuntime(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /android|iphone|ipad|ipod/i.test(navigator.userAgent);
}

// Base HTTP do gateway.
//   Desktop: 127.0.0.1:9001 (gateway local empacotado com o app)
//   Android: VITE_API_BASE (servidor remoto) — fallback para o gateway padrão.
export function apiBase(): string {
  const explicit = stored('xau-api-base') || viteEnv.env?.VITE_API_BASE;
  if (explicit) return explicit;
  // Sem configuração explícita: no desktop o gateway local é o default.
  if (isMobileRuntime()) {
    // Evita apontar para loopback no celular (o gateway não roda no dispositivo).
    console.warn('[api] Android sem VITE_API_BASE/xau-api-base: configure o gateway remoto.');
  }
  return 'http://127.0.0.1:9001';
}

// WebSocket de mercado.
//   Desktop: ws://127.0.0.1:9002/ws/market
//   Android: wss remoto via VITE_WS_URL / localStorage 'xau-ws-url'
export function wsUrl(): string {
  return stored('xau-ws-url') || viteEnv.env?.VITE_WS_URL || 'ws://127.0.0.1:9002/ws/market';
}

