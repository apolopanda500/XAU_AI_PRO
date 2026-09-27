// @vitest-environment jsdom
// Testes da configuracao de gateway em runtime (Android).
//
// Lacuna real: `apiBase()` lia a chave `xau-api-base` do localStorage mas
// nenhuma tela a escrevia. O APK caia em 127.0.0.1 e o usuario nao tinha como
// corrigir sem recompilar. No emulador, `10.0.2.2` e o alias do host.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  CHAVE_API_BASE,
  CHAVE_WS_URL,
  HOST_EMULADOR,
  alertaSeguranca,
  gatewayConfigurado,
  limparGateway,
  normalizeOrigin,
  normalizeWsUrl,
  salvarGateway,
  testarGateway,
} from './gatewayConfig';

function comArmazenamento() {
  const store = new Map<string, string>();
  vi.stubGlobal('window', {
    localStorage: {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => { store.set(k, v); },
      removeItem: (k: string) => { store.delete(k); },
    },
  } as unknown as Window);
  return store;
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('normalizeOrigin', () => {
  it('aceita origem com protocolo e devolve sem barra', () => {
    expect(normalizeOrigin('https://gateway.exemplo.com/')).toBe('https://gateway.exemplo.com');
    expect(normalizeOrigin('http://10.0.2.2:9001')).toBe('http://10.0.2.2:9001');
  });

  it('recusa entrada sem protocolo ou vazia', () => {
    expect(normalizeOrigin('gateway.exemplo.com')).toBe('');
    expect(normalizeOrigin('')).toBe('');
    expect(normalizeOrigin('   ')).toBe('');
    expect(normalizeOrigin('https://')).toBe('');
  });
});

describe('normalizeWsUrl', () => {
  it('deriva wss de https quando nao informado', () => {
    expect(normalizeWsUrl('', 'https://gw.exemplo.com')).toBe('wss://gw.exemplo.com/ws/market');
  });

  it('deriva ws de http quando nao informado', () => {
    expect(normalizeWsUrl('', 'http://10.0.2.2:9001')).toBe('ws://10.0.2.2:9001/ws/market');
  });

  it('preserva o WS informado', () => {
    expect(normalizeWsUrl('wss://outro.exemplo.com/ws', 'https://gw.exemplo.com')).toBe('wss://outro.exemplo.com/ws');
  });

  it('recusa WS com protocolo errado', () => {
    expect(normalizeWsUrl('https://gw.exemplo.com/ws', 'https://gw.exemplo.com')).toBe('');
    expect(normalizeWsUrl('lixo', 'https://gw.exemplo.com')).toBe('');
  });
});

describe('salvarGateway', () => {
  it('grava origem e ws derivados', () => {
    const store = comArmazenamento();
    const r = salvarGateway('https://gw.exemplo.com', '');
    expect(r.ok).toBe(true);
    expect(store.get(CHAVE_API_BASE)).toBe('https://gw.exemplo.com');
    expect(store.get(CHAVE_WS_URL)).toBe('wss://gw.exemplo.com/ws/market');
  });

  it('nao grava nada quando a origem e invalida', () => {
    const store = comArmazenamento();
    const r = salvarGateway('gw.exemplo.com', '');
    expect(r.ok).toBe(false);
    expect(store.has(CHAVE_API_BASE)).toBe(false);
  });

  it('nao grava nada quando o ws e invalido', () => {
    const store = comArmazenamento();
    const r = salvarGateway('https://gw.exemplo.com', 'nao-e-url');
    expect(r.ok).toBe(false);
    expect(store.has(CHAVE_API_BASE)).toBe(false);
  });

  it('le de volta o que foi gravado', () => {
    comArmazenamento();
    salvarGateway('https://gw.exemplo.com', '');
    expect(gatewayConfigurado().apiBase).toBe('https://gw.exemplo.com');
  });

  it('limpar remove as duas chaves', () => {
    const store = comArmazenamento();
    salvarGateway('https://gw.exemplo.com', '');
    limparGateway();
    expect(store.has(CHAVE_API_BASE)).toBe(false);
    expect(store.has(CHAVE_WS_URL)).toBe(false);
    expect(gatewayConfigurado()).toEqual({ apiBase: '', wsUrl: '' });
  });

  it('sobrevive a storage bloqueado', () => {
    vi.stubGlobal('window', {
      get localStorage(): Storage { throw new Error('bloqueado'); },
    } as unknown as Window);
    expect(salvarGateway('https://gw.exemplo.com', '').ok).toBe(false);
    expect(() => gatewayConfigurado()).not.toThrow();
    expect(() => limparGateway()).not.toThrow();
  });
});

describe('alertaSeguranca', () => {
  it('no desktop nao alerta', () => {
    expect(alertaSeguranca('http://qualquer.coisa', false)).toBeNull();
  });

  it('no mobile alerta contra http remoto', () => {
    expect(alertaSeguranca('http://gw.exemplo.com', true)).toMatch(/TLS/i);
  });

  it('no mobile aceita loopback do emulador e do device', () => {
    expect(alertaSeguranca(HOST_EMULADOR, true)).toBeNull();
    expect(alertaSeguranca('http://127.0.0.1:9001', true)).toBeNull();
  });

  it('aceita https em qualquer plataforma', () => {
    expect(alertaSeguranca('https://gw.exemplo.com', true)).toBeNull();
  });
});

describe('testarGateway', () => {
  it('401 conta como gateway vivo e autenticado', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }));
    const r = await testarGateway('https://gw.exemplo.com');
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.detalhe).toMatch(/401/);
  });

  it('2xx tambem conta como vivo', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200 }));
    expect((await testarGateway('https://gw.exemplo.com')).ok).toBe(true);
  });

  it('origem invalida nem chega na rede', async () => {
    const mock = vi.fn();
    vi.stubGlobal('fetch', mock);
    const r = await testarGateway('sem-protocolo');
    expect(r.ok).toBe(false);
    expect(mock).not.toHaveBeenCalled();
  });

  it('conexao recusada sugere o alias do emulador', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    const r = await testarGateway('http://127.0.0.1:9001');
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.dica).toMatch(/10\.0\.2\.2/);
  });

  it('404 sugere checar a porta do gateway', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404 }));
    const r = await testarGateway('https://site.exemplo.com');
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.dica).toMatch(/porta/);
  });

  it('chama o caminho de health do gateway', async () => {
    const mock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal('fetch', mock);
    await testarGateway('https://gw.exemplo.com');
    expect(mock.mock.calls[0][0]).toBe('https://gw.exemplo.com/api/health');
  });
});

describe('alias do emulador', () => {
  it('aponta para a porta do gateway no host', () => {
    expect(HOST_EMULADOR).toBe('http://10.0.2.2:9001');
  });
});
