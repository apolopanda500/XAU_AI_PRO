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

// ---------------------------------------------------------------------------
// Sessão de usuário (necessária no Android)
//
// O desktop recebe XAU_GATEWAY_TOKEN do Tauri, que o injeta no fetch. O Android
// não tem esse canal: o usuário faz login e recebe um token de sessão com TTL.
// Sem isto, toda chamada do celular volta 401 mesmo com o gateway configurado.
// ---------------------------------------------------------------------------

const SESSION_KEY = 'xau-session-token';

export function sessionToken(): string {
  return stored(SESSION_KEY);
}

export function setSessionToken(token: string): void {
  try {
    if (typeof window === 'undefined') return;
    if (token) window.localStorage.setItem(SESSION_KEY, token);
    else window.localStorage.removeItem(SESSION_KEY);
  } catch {
    // localStorage indisponível: o app segue sem sessão persistida.
  }
}

export function clearSessionToken(): void {
  setSessionToken('');
}

export type LoginResult =
  | { ok: true; userId: number; expiresIn: number }
  | { ok: false; error: string };

// Type guard explicito. O tsconfig roda com "strict": false, e sem
// strictNullChecks o TypeScript nao estreita a uniao discriminada por
// `if (r.ok)`. O guard resolve sem precisar mexer no strict do projeto.
export function isLoginError(r: LoginResult): r is { ok: false; error: string } {
  return r.ok === false;
}

/** Troca email+senha por um token de sessão. Não lança em erro de credencial. */
export async function loginUser(email: string, password: string): Promise<LoginResult> {
  // trim defensivo: espaço em branco colado pelo teclado do celular é causa
  // clássica de login recusado, e o gateway normaliza mas a UX fica ruim.
  const emailLimpo = email.trim();
  try {
    const res = await fetch(`${apiBase()}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: emailLimpo, password }),
      signal: AbortSignal.timeout(10_000),
    });
    const data = (await res.json().catch(() => ({}))) as {
      ok?: boolean;
      token?: string;
      user_id?: number;
      expires_in?: number;
      error?: string;
    };
    if (!res.ok || !data.ok || !data.token) {
      return { ok: false, error: data.error ?? `login recusado (${res.status})` };
    }
    setSessionToken(data.token);
    return {
      ok: true,
      userId: Number(data.user_id ?? 0),
      expiresIn: Number(data.expires_in ?? 0),
    };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : 'falha de rede' };
  }
}

/** Encerra a sessão no gateway e descarta o token local. */
export async function logoutUser(): Promise<void> {
  const token = sessionToken();
  if (token) {
    try {
      await fetch(`${apiBase()}/api/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(5_000),
      });
    } catch {
      // Mesmo sem resposta do gateway, o token local é descartado.
    }
  }
  clearSessionToken();
}

/** Verdadeiro quando a requisição é para o gateway, local ou remoto. */
export function isGatewayRequest(input: unknown): boolean {
  const raw =
    typeof Request !== 'undefined' && input instanceof Request ? input.url : String(input);
  if (!/^https?:\/\//i.test(raw)) return false;
  try {
    const url = new URL(raw);
    const local =
      url.port === '9001' && (url.hostname === '127.0.0.1' || url.hostname === 'localhost');
    return local || url.origin === new URL(apiBase()).origin;
  } catch {
    return false;
  }
}


