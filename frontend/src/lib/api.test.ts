// @vitest-environment jsdom
// Testes do módulo central de API (desktop local / Android remoto).
// Usa stubs de storage: a lógica sob teste é a cadeia de prioridade, não o storage em si.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiBase, isMobileRuntime, wsUrl } from './api';
import { gatewayFetchArgs, isLocalGatewayRequest } from './tauri';

type FakeStorage = { getItem: (key: string) => string | null };

function stubWindowWithStorage(storage: FakeStorage | undefined, userAgent = ''): void {
  vi.stubGlobal('window', storage ? { localStorage: storage } : {});
  vi.stubGlobal('navigator', { userAgent });
}

afterEach(() => { vi.unstubAllGlobals(); });

describe('isMobileRuntime', () => {
  it('detecta Android pelo user agent', () => {
    stubWindowWithStorage(undefined, 'Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36');
    expect(isMobileRuntime()).toBe(true);
  });

  it('não marca desktop como mobile', () => {
    stubWindowWithStorage(undefined, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)');
    expect(isMobileRuntime()).toBe(false);
  });
});

describe('apiBase', () => {
  it('padrão desktop: localhost 9001 quando não há storage', () => {
    stubWindowWithStorage(undefined);
    expect(apiBase()).toBe('http://127.0.0.1:9001');
  });

  it('override em runtime via localStorage (ajuste no app Android)', () => {
    stubWindowWithStorage({ getItem: (k) => (k === 'xau-api-base' ? 'https://gateway.exemplo.com' : null) });
    expect(apiBase()).toBe('https://gateway.exemplo.com');
  });

  it('não quebra se o storage lançar (modo privado/SSR)', () => {
    stubWindowWithStorage({ getItem: () => { throw new Error('bloqueado'); } });
    expect(apiBase()).toBe('http://127.0.0.1:9001');
  });

  it('prioridade: localStorage vence o fallback embutido', () => {
    stubWindowWithStorage({ getItem: (k) => (k === 'xau-api-base' ? 'http://10.0.0.5:9001' : null) });
    expect(apiBase()).toBe('http://10.0.0.5:9001');
  });

  it('Android sem configuracao: avisa e mantem o fallback (sem loopback silencioso)', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    stubWindowWithStorage(undefined, 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36');
    expect(apiBase()).toBe('http://127.0.0.1:9001');
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });

  it('Android com localStorage: usa o gateway remoto (nao o loopback)', () => {
    stubWindowWithStorage(
      { getItem: (k) => (k === 'xau-api-base' ? 'https://gateway.meuserver.com' : null) },
      'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36',
    );
    expect(apiBase()).toBe('https://gateway.meuserver.com');
  });
});

describe('wsUrl', () => {
  it('padrão desktop: ws 9002 market', () => {
    stubWindowWithStorage(undefined);
    expect(wsUrl()).toBe('ws://127.0.0.1:9002/ws/market');
  });

  it('override em runtime para wss remoto (Android)', () => {
    stubWindowWithStorage({ getItem: (k) => (k === 'xau-ws-url' ? 'wss://mercado.exemplo.com/ws' : null) });
    expect(wsUrl()).toBe('wss://mercado.exemplo.com/ws');
  });
});

describe('gateway auth', () => {
  it('aceita somente o gateway HTTP local na porta esperada', () => {
    expect(isLocalGatewayRequest('http://127.0.0.1:9001/api/health')).toBe(true);
    expect(isLocalGatewayRequest('http://localhost:9001/api/health')).toBe(true);
    expect(isLocalGatewayRequest('https://127.0.0.1:9001/api/health')).toBe(false);
    expect(isLocalGatewayRequest('http://127.0.0.1:9002/health')).toBe(false);
    expect(isLocalGatewayRequest('https://gateway.exemplo.com/api/health')).toBe(false);
  });

  it('adiciona o token somente ao gateway local', () => {
    const token = 'a'.repeat(64);
    const [, localInit] = gatewayFetchArgs(
      'http://127.0.0.1:9001/api/account',
      { headers: { 'Content-Type': 'application/json' } },
      token,
    );
    expect(new Headers(localInit?.headers).get('Authorization')).toBe(`Bearer ${token}`);
    expect(new Headers(localInit?.headers).get('Content-Type')).toBe('application/json');

    const [, remoteInit] = gatewayFetchArgs(
      'https://gateway.exemplo.com/api/account',
      undefined,
      token,
    );
    expect(remoteInit).toBeUndefined();
  });
});
