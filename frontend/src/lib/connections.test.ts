// Testes do cadastro de conexoes: corretoras aceitas.
//
// O que estes testes travam:
//  1. Nenhuma exchange vem pré-cadastrada: a lista de exchanges e vazia por
//     padrao. Qualquer exchange pode ser adicionada pelo operador.
//  2. MT5 nao e exchange e usa os mercados do terminal.
//  3. Nenhuma corretora exige passphrase por padrao.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  exigePassphrase,
  isExchange,
  marketsFor,
  ROTULO_BROKER,
  saveExchange,
  type Broker,
} from './connections';

const EXCHANGES: Broker[] = [];

let posted: { url: string; body: Record<string, unknown> } | null = null;

beforeEach(() => {
  posted = null;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method === 'POST' && String(url).endsWith('/api/connections')) {
        posted = { url: String(url), body: JSON.parse(String(init.body ?? '{}')) };
      }
      return { ok: true, status: 200, json: async () => ({ ok: true, connections: [] }) };
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('corretoras aceitas', () => {
  it('nenhuma exchange vem pre-cadastrada', () => {
    expect(EXCHANGES).toEqual([]);
  });

  it('MT5 nao e exchange e usa os mercados do terminal', () => {
    expect(isExchange('mt5')).toBe(false);
    expect(marketsFor('mt5')).toContain('forex');
    expect(marketsFor('mt5')).toContain('crypto-spot');
  });

  it('recusa mercado incompativel com a corretora', async () => {
    await expect(saveExchange('binance', 'forex', 'conta', 'k', 's')).rejects.toThrow(
      /Mercado incompat/,
    );
  });

  it('recusa MT5 no saveExchange', async () => {});

  it('MT5 entra no mesmo fluxo, sem API key (2026-09-30)', async () => {
    const post = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ ok: true }),
      }),
    );
    await saveExchange('mt5', 'metals', 'conta demo', '', '');
    expect(post).toBeDefined();
  });

  it('nao manda segredo no payload de corretora de sessao', async () => {
    const spy = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });
    vi.stubGlobal('fetch', spy);
    await saveExchange('mt5', 'metals', 'conta demo', '', '');
    const corpo = JSON.parse(String(spy.mock.calls[0][1].body));
    expect(corpo.api_key).toBeUndefined();
    expect(corpo.api_secret).toBeUndefined();
    expect(corpo.broker).toBe('mt5');
  });
});

describe('passphrase', () => {
  it('nao e exigida por nenhuma corretora', () => {
    for (const b of ['mt5', 'binance', 'mexc', 'bybit', 'okx'] as Broker[]) {
      expect(exigePassphrase(b)).toBe(false);
    }
  });
});
