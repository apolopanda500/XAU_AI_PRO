import { isGatewayRequest } from './api';

// Detecta se o frontend esta rodando dentro do webview do Tauri
export const isTauri = (): boolean =>
  typeof window !== 'undefined' &&
  ('__TAURI_IPC__' in window || '__TAURI__' in window || '__TAURI_INTERNALS__' in window);

type FetchInput = Parameters<typeof fetch>[0];
type FetchInit = Parameters<typeof fetch>[1];

export function isLocalGatewayRequest(input: FetchInput): boolean {
  const raw = typeof Request !== 'undefined' && input instanceof Request
    ? input.url
    : String(input);
  if (!/^https?:\/\//i.test(raw)) return false;
  try {
    const url = new URL(raw);
    return url.protocol === 'http:'
      && url.port === '9001'
      && (url.hostname === '127.0.0.1' || url.hostname === 'localhost');
  } catch {
    return false;
  }
}

export function gatewayFetchArgs(
  input: FetchInput,
  init: FetchInit,
  token: string,
): [FetchInput, FetchInit] {
  if (!token || !isLocalGatewayRequest(input)) return [input, init];
  const requestHeaders = typeof Request !== 'undefined' && input instanceof Request
    ? input.headers
    : undefined;
  const headers = new Headers(requestHeaders);
  new Headers(init?.headers).forEach((value, key) => headers.set(key, value));
  headers.set('Authorization', `Bearer ${token}`);
  return [input, { ...init, headers }];
}

export function installGatewayAuth(token: string): void {
  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const [request, requestInit] = gatewayFetchArgs(input, init, token);
    return originalFetch(request, requestInit);
  };
}

// Injeta o token de sessão em chamadas ao gateway.
//
// installGatewayAuth acima só cobre 127.0.0.1:9001, porque o desktop só fala
// com o gateway local empacotado. No Android o gateway fica no PC/VPS do
// trader, então a URL é remota e aquele interceptor não se aplica — sem isto o
// app Android recebe 401 em toda requisição.
//
// A função de token é consultada a cada requisição (não capturada uma vez),
// para que login e logout tenham efeito imediato sem reinstalar o app.
//
// Só injeta no gateway. Injetar em qualquer URL vazaria o token de sessão para
// terceros (CDN de gráficos, analytics, telemetria) — o token equivale a acesso
// ao terminal, então ele não pode sair para host desconhecido.
export function installRemoteGatewayAuth(getToken: () => string): void {
  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const token = getToken();
    if (!token || !isGatewayRequest(input)) return originalFetch(input, init);
    const requestHeaders = typeof Request !== 'undefined' && input instanceof Request
      ? input.headers
      : undefined;
    const headers = new Headers(requestHeaders);
    new Headers(init?.headers).forEach((value, key) => headers.set(key, value));
    headers.set('Authorization', `Bearer ${token}`);
    return originalFetch(input, { ...init, headers });
  };
}
