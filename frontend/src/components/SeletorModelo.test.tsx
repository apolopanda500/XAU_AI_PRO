// @vitest-environment jsdom
// O MODELO ESCOLHIDO CONFIGURA O MOTOR (13/10/2026)
// =================================================
// MEDIDO na captura do dono (12:21): modelo H1 escolhido no campo, grafico em
// M1, e a frase "Configurado, mas não ligou: escolha o timeframe antes de
// ligar". O periodo escolhido num campo era ignorado no outro — dois lados do
// mesmo dado discordando (AGENTS.md 5).
//
// O clique no card da lista (`ListaModelos.escolher`) JA configurava par +
// periodo via `/api/auto/config`. Este campo fazia so metade (guardava o id)
// — e metade configurada e o defeito. Agora os dois gestos fazem o mesmo.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, waitFor } from '@testing-library/react';

const M = vi.hoisted(() => ({
  simbolo: 'BTCUSD',
  chamadas: [] as Array<{ url: string; body: unknown }>,
  configResposta: { ok: true } as Record<string, unknown>,
  catalogo: [] as Array<{ symbol: string; modelSymbol?: string | null }>,
}));

vi.mock('../lib/api', () => ({ apiBase: () => 'http://127.0.0.1:9000' }));
vi.mock('../hooks/useAppStore', () => ({
  useAppStore: (s: (x: unknown) => unknown) =>
    s({
      selectedSymbol: M.simbolo,
      setSelectedSymbol: (v: string) => {
        M.simbolo = v;
      },
    }),
}));
vi.mock('../hooks/queries', () => ({
  useAutoState: () => ({ data: { simbolo: 'BTCUSD', timeframe: 'H1' } }),
}));
vi.mock('../hooks/useCatalogoAtivos', () => ({
  useCatalogoAtivos: () => M.catalogo,
}));

const { default: SeletorModelo } = await import('./SeletorModelo');

const MODELOS = [
  { id: 'BTCUSD_H1', symbol: 'BTCUSD', timeframe: 'H1', accuracy: 0.456, edge: 0.122, pkl_present: true, publicable: true },
  { id: 'BTCUSD_H4', symbol: 'BTCUSD', timeframe: 'H4', accuracy: 0.489, edge: 0.155, pkl_present: true, publicable: true },
];

beforeEach(() => {
  M.simbolo = 'BTCUSD';
  M.chamadas = [];
  M.configResposta = { ok: true };
  M.catalogo = [];
  window.localStorage.setItem('xau-active-account', 'binance:crypto-spot');
  vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
    const corpo = init?.body ? JSON.parse(String(init.body)) : null;
    M.chamadas.push({ url: String(url), body: corpo });
    if (String(url).includes('/api/ai/trained')) {
      return { ok: true, json: async () => ({ models: MODELOS }) };
    }
    if (String(url).includes('/api/auto/config')) {
      return { ok: true, json: async () => M.configResposta };
    }
    return { ok: true, json: async () => ({ ok: true }) };
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const campoModelo = () =>
  document.querySelector('[aria-label="Modelo do robo"]') as HTMLSelectElement;

describe('SeletorModelo — escolher o modelo configura par E periodo', () => {
  it('PROVA: escolher o H4 manda o periodo H4 para o motor', async () => {
    render(<SeletorModelo />);
    await waitFor(() => expect(campoModelo()?.options.length).toBeGreaterThan(1));

    fireEvent.change(campoModelo(), { target: { value: 'BTCUSD_H4' } });

    await waitFor(() => {
      const cfg = M.chamadas.find((c) => c.url.includes('/api/auto/config'));
      expect(cfg?.body).toEqual({ simbolo: 'BTCUSD', timeframe: 'H4' });
    });
  });

  it('PROVA NEGATIVA: o motor recusou, e a recusa aparece no campo', async () => {
    // Sem esta linha, o periodo escolhido ia para o motor, o motor recusava
    // (sem limites, sem conta), e a tela nao dizia nada — igual ao card antes
    // da correcao de 05/10/2026.
    M.configResposta = { ok: false, error: 'sem conta ativa' };
    render(<SeletorModelo />);
    await waitFor(() => expect(campoModelo()?.options.length).toBeGreaterThan(1));

    fireEvent.change(campoModelo(), { target: { value: 'BTCUSD_H4' } });

    await waitFor(() =>
      expect(document.querySelector('.robo-par-recusa')?.textContent).toContain('sem conta ativa'),
    );
  });

  it('trocar de par continua zerando o modelo', async () => {
    // Guarda do comportamento antigo: a correcao nova nao pode religar o
    // modelo do par anterior no par novo.
    render(<SeletorModelo />);
    await waitFor(() => expect(campoModelo()?.options.length).toBeGreaterThan(1));
    fireEvent.change(campoModelo(), { target: { value: 'BTCUSD_H4' } });
    await waitFor(() =>
      expect(M.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(true),
    );

    M.chamadas = [];
    const campoPar = document.querySelector('[aria-label="Par para operar"]') as HTMLSelectElement;
    fireEvent.change(campoPar, { target: { value: '' } });
    // Sem par nao ha modelo: nenhuma configuracao sai sem os dois.
    expect(M.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(false);
  });
});

describe('SeletorModelo — GOLD acha os modelos de XAUUSD', () => {
  const OURO = [
    { id: 'XAUUSD_H1', symbol: 'XAUUSD', timeframe: 'H1', accuracy: 0.465, edge: 0.132, pkl_present: true, publicable: true },
  ];

  beforeEach(() => {
    vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
      const corpo = init?.body ? JSON.parse(String(init.body)) : null;
      M.chamadas.push({ url: String(url), body: corpo });
      if (String(url).includes('/api/ai/trained')) {
        return { ok: true, json: async () => ({ models: OURO }) };
      }
      if (String(url).includes('/api/auto/config')) {
        return { ok: true, json: async () => M.configResposta };
      }
      return { ok: true, json: async () => ({ ok: true }) };
    });
  });

  it('PROVA: com GOLD no catalogo apontando para XAUUSD, os modelos aparecem', async () => {
    M.simbolo = 'GOLD';
    M.catalogo = [{ symbol: 'GOLD', modelSymbol: 'XAUUSD' }];
    render(<SeletorModelo />);
    await waitFor(() => expect(campoModelo()?.options.length).toBeGreaterThan(1));
    const opcoes = Array.from(campoModelo().options).map((o) => o.textContent);
    expect(opcoes.join(' ')).toContain('H1');
  });

  it('PROVA NEGATIVA: sem o apelido no catalogo, GOLD continua sem modelo', async () => {
    // O apelido vem do CATALOGO, nunca de regra de nome: sem a linha que
    // declara, nada e inventado — GOLD sem modelo continua sem modelo.
    M.simbolo = 'GOLD';
    M.catalogo = [{ symbol: 'GOLD' }];
    render(<SeletorModelo />);
    await waitFor(() =>
      expect(document.body.textContent).toContain('Nenhum modelo'),
    );
  });
});

describe('SeletorModelo � GOLD declarado com modelo aparece na lista', () => {
  it('has_model true poe o GOLD na lista curta mesmo sem model_symbol', async () => {
    M.simbolo = '';
    M.catalogo = [{ symbol: 'GOLD', modelSymbol: null, hasModel: true } as never];
    render(<SeletorModelo />);
    await waitFor(() => {
      const campo = document.querySelector('[aria-label="Par para operar"]') as HTMLSelectElement | null;
      const opcoes = campo ? Array.from(campo.options).map((o) => o.value) : [];
      expect(opcoes).toContain('GOLD');
    });
  });
});
