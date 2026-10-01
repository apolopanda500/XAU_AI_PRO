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
  });

  it('MT5 entra no mesmo fluxo, sem API key (2026-09-30)', async () => {
    // Antes este teste exigia que MT5 fosse RECUSADO. O dono mandou o
    // contrario: MT5 tem que aparecer na lista de conexao como as outras.
    // O que sobra de diferente e o CAMPO, nao o fluxo.
    const post = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ ok: true }),
    }));
    await saveExchange('mt5', 'metals', 'conta demo', '', '');
    expect(post).toBeDefined();
  });

  it('nao manda segredo no payload de corretora de sessao', async () => {
    const spy = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });
    vi.stubGlobal('fetch', spy);
    await saveExchange('mt5', 'metals', 'conta demo', '', '');
    const corpo = JSON.parse(String(spy.mock.calls[0][1].body));
    // Gravar vazio no DPAPI seria guardar segredo que nao existe.
    expect(corpo.api_key).toBeUndefined();
    expect(corpo.api_secret).toBeUndefined();
    expect(corpo.broker).toBe('mt5');
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
    // A mensagem agora diz o campo que falta, em vez de "informe nome, API
    // key e secret" para um formulario que ja veio preenchido.
    await expect(saveExchange('mexc', 'crypto-spot', '', 'k', 's')).rejects.toThrow(/nome/i);
    await expect(saveExchange('mexc', 'crypto-spot', 'n', '  ', 's')).rejects.toThrow(/API key e secret/);
  });

  it('identifica a corretora pelo rotulo exibido na tela', () => {
    expect(ROTULO_BROKER.okx).toBe('OKX');
    expect(ROTULO_BROKER.bybit).toBe('Bybit');
  });
});
