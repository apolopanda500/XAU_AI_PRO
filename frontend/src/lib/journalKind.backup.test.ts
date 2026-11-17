/**
 * A linha `[BACKUP] snapshots antigos removidos=N` é a rotina normal de
 * rotação de backups, e não um incidente.
 *
 * MEDIDO na Tela 2 do Trading Desk (log ao vivo): a mensagem
 * `[BACKUP] snapshots antigos removidos=1` aparecia em vermelho como ERROR,
 * porque a etiqueta `BACKUP` mapeia para ERROR no classificador e a linha não
 * tem palavra de veredito. O operador via um erro que não aconteceu.
 *
 * A separação que importa: remoção rotineira de snapshots velhos é INFO, e
 * FALHA medida com números continua ERROR (`[BACKUP] FAIL | copiados=9 |
 * falhas=98`). O par de testes abaixo trava os dois lados para que o conserto
 * não vire "tudo é INFO".
 */
import { describe, expect, it } from 'vitest';
import { classificarJournal } from './journalKind';

describe('a rotina de rotação de backup não é erro', () => {
  it('snapshots antigos removidos=1 é INFO', () => {
    expect(classificarJournal('[BACKUP] snapshots antigos removidos=1')).toBe('INFO');
  });

  it('snapshots antigos removidos=0 é INFO', () => {
    expect(classificarJournal('XR 0 [BACKUP] snapshots antigos removidos=0')).toBe('INFO');
  });

  it('removidos=3 também é INFO (mais de um snapshot antigo saiu)', () => {
    expect(classificarJournal('[BACKUP] snapshots antigos removidos=3')).toBe('INFO');
  });
});

describe('a falha real de backup continua ERROR', () => {
  it('FAIL com falhas>=1 é ERROR', () => {
    expect(classificarJournal('[BACKUP] FAIL | copiados=9 | falhas=98')).toBe('ERROR');
  });

  it('FAIL é ERROR mesmo sem removidos na linha', () => {
    expect(classificarJournal('[BACKUP] FAIL | falhas=2')).toBe('ERROR');
  });
});
