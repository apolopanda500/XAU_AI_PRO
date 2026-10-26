import { describe, expect, it } from 'vitest';
import { bollingerValores, smaValores, vwapValores } from './indicadores';

/*
  OS INDICADORES NOVOS (23/10/2026).

  O que estes testes protegem, alem da conta:
    - `null` e AUSENCIA: nada de `0` no lugar de "ainda nao da para calcular";
    - janela incompleta NAO produz numero (era o defeito do RSI "de 1");
    - VWAP sem volume nao vira media aritmetica disfarcada.
*/

describe('SMA', () => {
  it('primeiros pontos sao null ate fechar a janela', () => {
    const v = smaValores([1, 2, 3, 4, 5], 3);
    expect(v.slice(0, 2)).toEqual([null, null]);
    expect(v.slice(2)).toEqual([2, 3, 4]);
  });

  it('periodo invalido devolve tudo null, e nao o proprio preco', () => {
    expect(smaValores([1, 2, 3], 1)).toEqual([null, null, null]);
  });
});

describe('Bollinger', () => {
  it('media, superior e inferior alinhadas por indice', () => {
    const fechas = Array.from({ length: 25 }, (_, i) => 100 + i);
    const b = bollingerValores(fechas, 20, 2);
    expect(b.media.length).toBe(25);
    expect(b.superior[18]).toBeNull();
    expect(b.media[19]).toBeCloseTo(109.5, 6);
    // Serie perfeitamente crescente: a banda abre exatamente o desvio padrao.
    expect((b.superior[19] as number) - (b.media[19] as number)).toBeGreaterThan(0);
    expect(b.inferior[19]).toBeLessThan(b.media[19] as number);
  });

  it('desvio zero nao inventa banda colada na media', () => {
    const b = bollingerValores([1, 2, 3, 4], 3, 0);
    expect(b.superior.every((v) => v === null)).toBe(true);
  });
});

describe('VWAP', () => {
  it('pondera pelo volume', () => {
    const v = vwapValores([
      { high: 10, low: 10, close: 10, volume: 1 },
      { high: 20, low: 20, close: 20, volume: 3 },
    ]);
    expect(v[0]).toBeCloseTo(10, 6);
    expect(v[1]).toBeCloseTo((10 * 1 + 20 * 3) / 4, 6);
  });

  it('sem volume devolve null em vez de media aritmetica', () => {
    const v = vwapValores([
      { high: 1, low: 1, close: 1, volume: 0 },
      { high: 2, low: 2, close: 2, volume: 0 },
    ]);
    expect(v).toEqual([null, null]);
  });
});
