// @vitest-environment jsdom
// Testes do módulo central de API (desktop local / Android remoto).
// Usa stubs de storage: a lógica sob teste é a cadeia de prioridade, não o storage em si.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiBase, wsUrl } from './api';

type FakeStorage = { getItem: (key: string) => string | null };

function stubWindowWithStorage(storage: FakeStorage | undefined, userAgent = ''): void {
  vi.stubGlobal('window', storage ? { localStorage: storage } : {});
  vi.stubGlobal('navigator', { userAgent });
}

afterEach(() => { vi.unstubAllGlobals(); });

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