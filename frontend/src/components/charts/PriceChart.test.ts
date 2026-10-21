// EMA do grafico: calculada dos fechamentos reais, sem fonte externa.
import { describe, expect, it } from 'vitest';
import { emaValores } from './PriceChart';

describe('emaValores', () => {
  it('primeiros periodo-1 sao nulos e o primeiro valor e a media', () => {
    const r = emaValores([1, 2, 3, 4, 5], 3);
    expect(r[0]).toBeNull();
    expect(r[1]).toBeNull();
    expect(r[2]).toBeCloseTo(2);
  });

  it('acompanha a direcao sem inventar', () => {
    const r = emaValores([10, 10, 10, 20, 20, 20], 3);
    expect(r[5]).not.toBeNull();
    expect(r[5] as number).toBeGreaterThan(10);
    expect(r[5] as number).toBeLessThan(20);
  });

  it('vazio nao quebra', () => {
    expect(emaValores([], 12)).toEqual([]);
    expect(emaValores([1], 1)).toEqual([null]);
  });
});
