// @vitest-environment jsdom
// Sincronizacao MT5 em todos os mercados — prova do helper compartilhado.
//
// O defeito medido no APK 1.2.191: `Sincronizar MT5` registrava so um mercado.
// Aqui a prova exercita o helper REAL com as primitivas de `connections`
// substituidas, para medir quantos POSTs de gravacao e quantos testes de leitura
// acontecem num unico clique. Nao existe `Promise.all` escondido: a ordem e a
// mesma do catalogo, o que torna a falha isolada previsivel.
import { beforeEach, describe, expect, it, vi } from 'vitest';

const M = vi.hoisted(() => ({
  mercados: ['forex', 'metals', 'indices', 'crypto-spot'],
  salvas: [] as Array<{ broker: string; market: string; nome: string; chave: string }>,
  testadas: [] as string[],
  falharSave: [] as string[],
  falharTeste: [] as string[],
}));

const MERCADOS = M.mercados;

vi.mock('./connections', () => ({
  marketsFor: () => M.mercados,
  detectTerminal: async () => ({
    login: 420750145,
    server: 'XMGlobal-MT5 17',
    name: 'Michele Dos Santos',
  }),
  saveExchange: async (broker: string, market: string, nome: string, chave: string) => {
    M.salvas.push({ broker, market, nome, chave });
    if (M.falharSave.includes(market)) throw new Error(`save ${market} recusado`);
    return `mt5:${market}:${nome}`;
  },
  connectionAction: async (id: string) => {
    M.testadas.push(id);
    const market = MERCADOS.find((item) => id.startsWith(`mt5:${item}:`)) ?? '';
    if (M.falharTeste.includes(market)) throw new Error(`leitura ${market} indisponivel`);
  },
}));

import {
  mercadoDoIdMt5,
  resumoSincronizacaoMt5,
  rotuloDaContaMt5,
  sincronizarMercadosMt5,
} from './sincronizarMt5';

beforeEach(() => {
  M.mercados = [...MERCADOS];
  M.salvas = [];
  M.testadas = [];
  M.falharSave = [];
  M.falharTeste = [];
});

describe('sincronizarMercadosMt5', () => {
  it('registra e testa TODOS os mercados em uma chamada, sem segredo', async () => {
    const relatorio = await sincronizarMercadosMt5();

    expect(M.salvas).toHaveLength(MERCADOS.length);
    expect(M.salvas.map((linha) => linha.market)).toEqual(MERCADOS);
    expect(M.salvas.every((linha) => linha.broker === 'mt5')).toBe(true);
    expect(M.salvas.every((linha) => linha.chave === '')).toBe(true);
    expect(M.testadas).toEqual(M.salvas.map((linha) => `mt5:${linha.market}:${linha.nome}`));
    expect(relatorio.registradas).toHaveLength(MERCADOS.length);
    expect(relatorio.validadas).toHaveLength(MERCADOS.length);
    expect(relatorio.falhas).toEqual([]);
    expect(Object.keys(relatorio.ids)).toEqual(MERCADOS);
  });

  it('o rotulo vem da sessao: nome do terminal + servidor, sem nome inventado', async () => {
    expect(rotuloDaContaMt5({ login: 1, server: 'Servidor', name: 'Terminal' })).toBe(
      'Terminal @ Servidor',
    );
    // Nome digitado pelo operador manda; sem ele, o servidor evita rotulos iguais.
    expect(rotuloDaContaMt5({ login: 1, server: 'Servidor' }, 'minha conta', 'outro')).toBe(
      'minha conta',
    );
    expect(rotuloDaContaMt5({ login: 1, server: 'Servidor' }, '', 'outro')).toBe('outro');
    expect(rotuloDaContaMt5({ login: 1, server: '' })).toBe('conta 1');
  });

  it('mercado fora do catalogo nao entra: nenhum ativo presumido', async () => {
    const relatorio = await sincronizarMercadosMt5({ mercados: ['forex', 'mercado-inventado'] });
    expect(relatorio.mercados).toEqual(['forex']);
    expect(M.salvas).toHaveLength(1);
  });

  it('falha isolada: um mercado reprovado nao apaga os outros', async () => {
    M.falharTeste = ['indices'];
    const relatorio = await sincronizarMercadosMt5();

    expect(relatorio.registradas).toHaveLength(MERCADOS.length);
    expect(relatorio.validadas).toHaveLength(MERCADOS.length - 1);
    expect(relatorio.falhas).toEqual([
      { market: 'indices', motivo: 'leitura indices indisponivel' },
    ]);
    const texto = resumoSincronizacaoMt5(relatorio);
    expect(texto).toContain('3/4 leituras validadas');
    expect(texto).toContain('indices (leitura indices indisponivel)');
    expect(texto).toContain('Nenhuma ordem foi enviada.');
    expect(texto).not.toContain('4/4 leituras validadas');
  });

  it('PROVA NEGATIVA: se nada foi registrado, nao ha relatorio de sucesso', async () => {
    M.falharSave = [...MERCADOS];
    await expect(sincronizarMercadosMt5()).rejects.toThrow(/Nenhum mercado MT5 foi registrado/);
    const texto = resumoSincronizacaoMt5({
      conta: { login: 1, server: 'S' },
      rotulo: 'S',
      mercados: MERCADOS,
      ids: {},
      registradas: [],
      validadas: [],
      falhas: MERCADOS.map((market) => ({ market, motivo: 'recusado' })),
    });
    expect(texto).toContain('0/4 mercados registrados');
    expect(texto).not.toContain('4/4');
  });

  it('o ID do relatorio diz qual mercado ficou ativo', async () => {
    const relatorio = await sincronizarMercadosMt5();
    expect(mercadoDoIdMt5(relatorio, relatorio.ids['crypto-spot'])).toBe('crypto-spot');
    expect(mercadoDoIdMt5(relatorio, 'id-que-nao-existe')).toBeUndefined();
  });
});
