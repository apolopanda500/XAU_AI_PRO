import { describe, expect, it } from 'vitest';
import { parseAssetCatalog } from './brokerCatalog';

describe('catalogo que alimenta o seletor de par do Robo', () => {
  it('aceita o payload real de /api/universal/assets', () => {
    // MEDIDO na conta 391773676: 1639 ativos. O seletor de par do Robo passa a
    // vir daqui, e nao da lista de modelos -- que, vazia, deixava o Robo sem
    // nenhum par para escolher.
    const payload = {
      assets: [
        { symbol: 'BTCUSD', display_name: 'Bitcoin / US Dollar', availability: 'tradable' },
        { symbol: 'GOLD', availability: 'tradable', digits: 2, volume_step: 0.01 },
      ],
    };
    const linhas = parseAssetCatalog(payload);
    expect(linhas).toHaveLength(2);
    expect(linhas.map((l) => l.symbol)).toEqual(['BTCUSD', 'GOLD']);
  });

  it('payload vazio devolve lista vazia, e nao lanca', () => {
    // O gateway fora responde 401/500. O seletor precisa mostrar "sem par" sem
    // quebrar a tela inteira.
    for (const p of [{}, { assets: [] }, null, undefined, 'texto']) {
      expect(parseAssetCatalog(p)).toEqual([]);
    }
  });

  it('ativo sem simbolo e ignorado, e nao vira par vazio na lista', () => {
    const linhas = parseAssetCatalog({ assets: [{ symbol: '' }, { symbol: '  ' }, null, { symbol: 'EURUSD' }] });
    expect(linhas.map((l) => l.symbol)).toEqual(['EURUSD']);
  });
});
