import { describe, it, expect } from 'vitest';
import { normalizeTheme } from './useTheme';

describe('normalizeTheme - migracao dos IDs com nome de ativo', () => {
  it('o ID velho vira o novo, e a preferencia nao  perdida', () => {
    expect(normalizeTheme('xau_dark')).toBe('dourado_dark');
    expect(normalizeTheme('btc_dark')).toBe('laranja_dark');
  });
  it('o ID novo passa direto', () => {
    expect(normalizeTheme('dourado_dark')).toBe('dourado_dark');
    expect(normalizeTheme('laranja_dark')).toBe('laranja_dark');
  });
  it('ID desconhecido continua caindo em dark', () => {
    expect(normalizeTheme('nao-existe')).toBe('dark');
  });
});
