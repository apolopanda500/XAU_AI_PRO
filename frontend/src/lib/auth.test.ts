// @vitest-environment jsdom
// Testes do fluxo de sessao de usuario (login do app Android).
//
// O ponto sensivel e o interceptor de fetch: no desktop installGatewayAuth so
// cobre 127.0.0.1:9001, entao no Android o token de sessao nao era enviado e
// toda requisicao voltava 401. Estes testes fixam esse comportamento.
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  clearSessionToken,
  isGatewayRequest,
  isLoginError,
  loginUser,
  logoutUser,
  sessionToken,
  setSessionToken,
  type LoginResult,
} from './api';
import { installRemoteGatewayAuth } from './tauri';

type Store = Record<string, string>;

function stubWindow(
  initial: Store = {},
  fetchMock?: unknown,
  userAgent = 'Mozilla/5.0 (Linux; Android 15)',
) {
  const store: Store = { ...initial };
  const localStorage = {
    getItem: (k: string) => (k in store ? store[k] : null),
    setItem: (k: string, v: string) => {
      store[k] = v;
    },
    removeItem: (k: string) => {
      delete store[k];
    },
  };
  // No navegador `fetch` e `window.fetch` sao o mesmo objeto. Com stub de window
  // eles divergem, entao o mock e colocado nos dois: installRemoteGatewayAuth
  // substitui window.fetch, e loginUser chama o fetch global.
  const win: Record<string, unknown> = { localStorage };
  if (fetchMock !== undefined) {
    win.fetch = fetchMock;
    vi.stubGlobal('fetch', fetchMock);
  }
  vi.stubGlobal('window', win as unknown as Window);
  vi.stubGlobal('navigator', { userAgent } as unknown as Navigator);
  return store;
}

/** fetch mock que registra os headers de cada chamada. */
function recordingFetch() {
  const seen: Array<Record<string, string>> = [];
  const mock = vi.fn((_url: string, init: RequestInit = {}) => {
    seen.push(Object.fromEntries(new Headers(init.headers ?? {}).entries()));
    return Promise.resolve(new Response('{}'));
  });
  return { mock, seen };
}

function okLogin(): LoginResult {
  return { ok: true, userId: 1, expiresIn: 3600 };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('armazenamento do token de sessao', () => {
  it('comeca vazio e persiste o que foi gravado', () => {
    stubWindow();
    expect(sessionToken()).toBe('');
    setSessionToken('abc123');
    expect(sessionToken()).toBe('abc123');
  });

  it('clearSessionToken remove o valor', () => {
    stubWindow({ 'xau-session-token': 'abc123' });
    expect(sessionToken()).toBe('abc123');
    clearSessionToken();
    expect(sessionToken()).toBe('');
  });

  it('sobrevive ao storage lancar (modo privado)', () => {
    vi.stubGlobal('window', {
      get localStorage(): Storage {
        throw new Error('bloqueado');
      },
    } as unknown as Window);
    expect(() => setSessionToken('x')).not.toThrow();
    expect(sessionToken()).toBe('');
  });
});

describe('isLoginError', () => {
  it('separa sucesso de erro', () => {
    expect(isLoginError({ ok: true, userId: 1, expiresIn: 1 })).toBe(false);
    expect(isLoginError({ ok: false, error: 'x' })).toBe(true);
  });

  it('o resultado de sucesso tem a forma esperada', () => {
    const r = okLogin();
    expect(r.ok).toBe(true);
  });
});

describe('loginUser', () => {
  it('guarda o token devolvido pelo gateway', async () => {
    const store = stubWindow();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true, token: 'tok-123', user_id: 7, expires_in: 3600 }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const r = await loginUser('  Trader@Exemplo.com  ', 'senha');

    expect(isLoginError(r)).toBe(false);
    expect(store['xau-session-token']).toBe('tok-123');
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('http://127.0.0.1:9001/api/auth/login');
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json');
    // espacos colados pelo teclado do celular sao removidos antes do envio
    expect(JSON.parse(init.body as string)).toEqual({
      email: 'Trader@Exemplo.com',
      password: 'senha',
    });
  });

  it('nao guarda nada quando o gateway recusa as credenciais', async () => {
    const store = stubWindow();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ ok: false, error: 'credenciais invalidas' }),
      }),
    );

    const r = await loginUser('trader@exemplo.com', 'errada');

    expect(isLoginError(r)).toBe(true);
    if (isLoginError(r)) expect(r.error).toBe('credenciais invalidas');
    expect(store['xau-session-token']).toBeUndefined();
  });

  it('nao guarda token quando a resposta vem sem token', async () => {
    const store = stubWindow();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ ok: true }) }),
    );
    const r = await loginUser('trader@exemplo.com', 'senha');
    expect(isLoginError(r)).toBe(true);
    expect(store['xau-session-token']).toBeUndefined();
  });

  it('rede caiu vira erro, nao excecao', async () => {
    stubWindow();
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('ECONNREFUSED')));
    const r = await loginUser('trader@exemplo.com', 'senha');
    expect(isLoginError(r)).toBe(true);
    if (isLoginError(r)) expect(r.error).toBe('ECONNREFUSED');
  });
});

describe('logoutUser', () => {
  it('avisa o gateway e descarta o token local', async () => {
    const store = stubWindow({ 'xau-session-token': 'tok-123' });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await logoutUser();

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok-123');
    expect(store['xau-session-token']).toBeUndefined();
  });

  it('descarta o token mesmo se o gateway nao responder', async () => {
    const store = stubWindow({ 'xau-session-token': 'tok-123' });
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));

    await logoutUser();

    expect(store['xau-session-token']).toBeUndefined();
  });
});

describe('isGatewayRequest', () => {
  it('reconhece o gateway local', () => {
    stubWindow();
    expect(isGatewayRequest('http://127.0.0.1:9001/api/health')).toBe(true);
    expect(isGatewayRequest('http://localhost:9001/api/health')).toBe(true);
  });

  it('reconhece o gateway remoto configurado no Android', () => {
    stubWindow({ 'xau-api-base': 'https://gateway.exemplo.com' });
    expect(isGatewayRequest('https://gateway.exemplo.com/api/assets')).toBe(true);
  });

  it('ignora outra origem', () => {
    stubWindow({ 'xau-api-base': 'https://gateway.exemplo.com' });
    expect(isGatewayRequest('https://outro-site.com/api')).toBe(false);
    expect(isGatewayRequest('https://gateway.exemplo.com.ataque.net/api')).toBe(false);
  });
});

describe('installRemoteGatewayAuth', () => {
  it('injeta o header em chamada remota do gateway', async () => {
    const { mock, seen } = recordingFetch();
    stubWindow({ 'xau-api-base': 'https://gateway.exemplo.com' }, mock);

    installRemoteGatewayAuth(() => 'tok-abc');
    await window.fetch('https://gateway.exemplo.com/api/assets');

    expect(seen[0].authorization).toBe('Bearer tok-abc');
  });

  it('nao envia Authorization sem sessao', async () => {
    const { mock, seen } = recordingFetch();
    stubWindow({ 'xau-api-base': 'https://gateway.exemplo.com' }, mock);

    installRemoteGatewayAuth(() => '');
    await window.fetch('https://gateway.exemplo.com/api/assets');

    expect(seen[0].authorization).toBeUndefined();
  });

  it('preserva headers ja existentes na requisicao', async () => {
    const { mock, seen } = recordingFetch();
    stubWindow({ 'xau-api-base': 'https://gateway.exemplo.com' }, mock);

    installRemoteGatewayAuth(() => 'tok-abc');
    await window.fetch('https://gateway.exemplo.com/api/assets', { headers: { 'X-Trace': 'abc' } });

    expect(seen[0]['x-trace']).toBe('abc');
    expect(seen[0].authorization).toBe('Bearer tok-abc');
  });

  it('passa a enviar o token assim que a sessao comeca, sem reinstalar', async () => {
    const { mock, seen } = recordingFetch();
    stubWindow({ 'xau-api-base': 'https://gateway.exemplo.com' }, mock);

    installRemoteGatewayAuth(sessionToken);

    await window.fetch('https://gateway.exemplo.com/api/assets');
    expect(seen[0].authorization).toBeUndefined();

    setSessionToken('tok-depois-do-login');
    await window.fetch('https://gateway.exemplo.com/api/assets');
    expect(seen[1].authorization).toBe('Bearer tok-depois-do-login');
  });

  it('NAO injeta header em requisicao de outra origem (vazamento de sessao)', async () => {
    const { mock, seen } = recordingFetch();
    stubWindow({ 'xau-api-base': 'https://gateway.exemplo.com' }, mock);

    installRemoteGatewayAuth(() => 'tok-abc');
    await window.fetch('https://outro-site.com/api');

    // O token equivale a acesso ao terminal. Enviar para host desconhecido
    // entregaria a sessao a terceiro.
    expect(seen[0].authorization).toBeUndefined();
  });
});
