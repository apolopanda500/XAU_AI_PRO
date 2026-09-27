// Guarda contra divergencia de versao entre o que a interface exibe e o que o
// app realmente e. A versao da UI ficou congelada em 1.2.0 enquanto o build ja
// era 1.2.3; estes testes impedem que a versao hardcoded volte.
import { describe, expect, it } from 'vitest';
import { APP_VERSION } from './version';
import pkg from '../package.json';

describe('versao do app', () => {
  it('a versao exibida e a do package.json', () => {
    expect(APP_VERSION).toBe(pkg.version);
  });

  it('tem o formato semantico completo', () => {
    expect(APP_VERSION).toMatch(/^\d+\.\d+\.\d+$/);
  });
});
