// Configuração única de API do frontend: localhost no desktop, configurável no Android.
// Prioridade: localStorage (ajuste em runtime) → variável VITE_* (build) → localhost (desktop).
//
// Android: o WebView não pode usar 127.0.0.1 (o gateway roda no PC/VPS do trader).
// Definir VITE_API_BASE/VITE_WS_URL no build (.env.production) OU ajustar em runtime
// pela tela de conexão (localStorage 'xau-api-base' / 'xau-ws-url').
//
// A PORTA do localhost desktop NÃO morre aqui: vem de `lib/portas.ts`, que a
// pergunta ao Tauri. Ver o motivo medido em `portas.ts`.
import { baseGatewayLocal, ehGatewayLocal, portaGateway, portaWsMercado } from './portas';
// CORRIGIDO 22/11/2026 ("APK nunca liga"): a leitura indireta
// `(import.meta as ViteEnv).env?.VITE_*` NAO e substituida pelo Vite em build —
// ele so injeta referencias LITERAIS `import.meta.env.VITE_*`. Resultado: no
// APK as variaveis do .env.production chegavam vazias e o app caira no
// loopback 127.0.0.1:9001 (que no Android nao e o PC).
//
// Declaracao literal para o TypeScript (sem `any`): o Vite substitui cada
// `import.meta.env.VITE_*` abaixo pelo valor do .env.production no build.
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_WS_URL?: string;
}

function stored(key: string): string {
  try {
    // window.localStorage explícito: evita colisão com o localStorage experimental do Node 26 em testes.
    return typeof window !== 'undefined' ? (window.localStorage.getItem(key) ?? '') : '';
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
//   Desktop: a base que o Tauri mandou no boot (ver `lib/portas.ts`) — e o
//            gateway local empacotado com o app. Sem o Tauri, 127.0.0.1:9001.
//   Android: VITE_API_BASE (servidor remoto) — fallback para o gateway padrão.
//
// MEDIDO em 09/10/2026: aqui estava `'http://127.0.0.1:9001'` escrito à mão,
// e o gateway subindo em 9011. A tela inteira ficava sem back-end — e o
// operador via "Falha ao inicializar o ambiente local seguro", sem nenhuma
// pista de que a porta era o motivo. A porta é uma MEDIDA, e quem mede é o
// Tauri (que lê `XAU_GATEWAY_PORT`). Aqui só se usa o valor que ele mandou.
export function apiBase(): string {
  const explicit = stored('xau-api-base') || import.meta.env.VITE_API_BASE;
  if (explicit) return explicit;
  const local = baseGatewayLocal();
  if (local) return local;
  // Sem configuração explícita: no desktop o gateway local é o default.
  if (isMobileRuntime()) {
    // Evita apontar para loopback no celular (o gateway não roda no dispositivo).
    console.warn('[api] Android sem VITE_API_BASE/xau-api-base: configure o gateway remoto.');
  }
  return `http://127.0.0.1:${portaGateway()}`;
}

// WebSocket de mercado.
//   Desktop: ws://127.0.0.1:<XAU_WS_PORT>/ws/market — o Tauri manda a porta.
//   Android: wss remoto via VITE_WS_URL / localStorage 'xau-ws-url'
//
// MEDIDO em 09/10/2026: aqui estava `ws://127.0.0.1:9002` escrito à mão. O Rust
// já lia `XAU_WS_PORT` — e o compilador acusava `porta_ws is never used`, com
// razão. Funcionava por ACASO, porque o padrão do Rust e o padrão do frontend
// eram o mesmo número; no dia em que a porta fosse movida, o Rust subiria na
// nova e o preço deixaria de atualizar, sem erro nenhum.
export function wsUrl(): string {
  const explicita = stored('xau-ws-url') || import.meta.env.VITE_WS_URL;
  if (explicita) return explicita;
  return `ws://127.0.0.1:${portaWsMercado()}/ws/market`;
}

/**
 * INDICA SE HA SERVIDOR WS REAL CONFIGURADO (22/11/2026).
 * O gateway FastAPI declara `transport: http-polling, websocket: false`: NAO
 * tem rota /ws/market. Sem esta funcao o hook tentava `ws://127.0.0.1:9002`
 * no desktop e `ws://10.0.2.2:9002` no Android, onde nao ha servidor — o
 * resultado era loop de reconexao e aviso de Mixed Content no WebView.
 * Os dados do app vem por HTTP polling; WS e apenas o feed de preco.
 * `true` so quando o usuario/build configurou um WS explicito.
 */
export function temWsConfigurado(): boolean {
  return Boolean(stored('xau-ws-url') || import.meta.env.VITE_WS_URL);
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
  { ok: true; userId: number; expiresIn: number } | { ok: false; error: string };

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
    /*
      Era `url.port === '9001' && loopback`. Com o gateway em 9011 isso dava
      `false` para a própria requisição do app, e o token de sessão deixava de
      ser injetado — o gateway responderia 401 em tudo e o sintoma seria "o app
      perdeu a sessão". `ehGatewayLocal` compara com a base RESOLVIDA.
    */
    return ehGatewayLocal(url) || url.origin === new URL(apiBase()).origin;
  } catch {
    return false;
  }
}
