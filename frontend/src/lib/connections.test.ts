// Testes do cadastro de conexoes: corretoras aceitas e a passphrase da OKX.
//
// O que estes testes travam:
//  1. Bybit e OKX sao aceitos (antes so havia mt5/binance/mexc, e o backend ja
//     aceitava as quatro exchanges).
//  2. A passphrase so e exigida pela OKX, porque e a unica que o backend recusa
//     sem ela (connection_service.py:21).
//  3. A passphrase viaja no payload apenas quando a corretora exige.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  exigePassphrase, isExchange, marketsFor, ROTULO_BROKER,
  saveExchange, type Broker,
} from './connections';

const EXCHANGES: Broker[] = ['binance', 'mexc', 'bybit', 'okx'];

let posted: { url: string; body: Record<string, unknown> } | null = null;

beforeEach(() => {
  posted = null;
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === 'POST' && String(url).endsWith('/api/connections')) {
      posted = { url: String(url), body: JSON.parse(String(init.body ?? '{}')) };
    }
    return { ok: true, status: 200, json: async () => ({ ok: true, connections: [] }) };
  }));
});

afterEach(() => { vi.unstubAllGlobals(); });

describe('corretoras aceitas', () => {
  it('cobre as quatro exchanges que o backend aceita', () => {
    for (const b of EXCHANGES) {
      expect(isExchange(b)).toBe(true);
      expect(marketsFor(b)).toContain('crypto-spot');
      expect(marketsFor(b)).toContain('crypto-futures');
    }
  });

  it('MT5 nao e exchange e usa os mercados do terminal', () => {
    expect(isExchange('mt5')).toBe(false);
    expect(marketsFor('mt5')).toEqual(['forex', 'metals', 'indices']);
  });

  it('recusa mercado incompativel com a corretora', async () => {
    await expect(saveExchange('bybit', 'forex', 'conta', 'k', 's')).rejects.toThrow(/Mercado incompat/);
  });

  it('recusa MT5 no saveExchange', async () => {
    await expect(
      saveExchange('mt5' as never, 'crypto-spot', 'conta', 'k', 's'),
    ).rejects.toThrow(/sessão do terminal/);
  });
});

describe('passphrase', () => {
  it('e exigida apenas pela OKX', () => {
    expect(exigePassphrase('okx')).toBe(true);
    for (const b of ['binance', 'mexc', 'bybit'] as Broker[]) {
      expect(exigePassphrase(b)).toBe(false);
    }
    expect(exigePassphrase('mt5')).toBe(false);
  });

  it('bloqueia o envio da OKX sem passphrase, antes de chamar o gateway', async () => {
    await expect(saveExchange('okx', 'crypto-spot', 'conta', 'k', 's', '')).rejects.toThrow(/passphrase/i);
    expect(posted).toBeNull();
  });

  it('envia a passphrase da OKX quando informada', async () => {
    const id = await saveExchange('okx', 'crypto-spot', 'conta', 'key1', 'sec1', 'pass1');
    expect(id).toBe('okx:crypto-spot:conta');
    expect(posted?.body.api_passphrase).toBe('pass1');
  });

  it('nao manda api_passphrase nas corretoras que nao exigem', async () => {
    await saveExchange('bybit', 'crypto-spot', 'conta', 'key1', 'sec1');
    expect(posted?.body.api_passphrase).toBeUndefined();
  });

  it('exige nome, key e secret para qualquer exchange', async () => {
    await expect(saveExchange('mexc', 'crypto-spot', '', 'k', 's')).rejects.toThrow(/nome, API key e secret/);
    await expect(saveExchange('mexc', 'crypto-spot', 'n', '  ', 's')).rejects.toThrow(/nome, API key e secret/);
  });

  it('identifica a corretora pelo rotulo exibido na tela', () => {
    expect(ROTULO_BROKER.okx).toBe('OKX');
    expect(ROTULO_BROKER.bybit).toBe('Bybit');
  });
});
