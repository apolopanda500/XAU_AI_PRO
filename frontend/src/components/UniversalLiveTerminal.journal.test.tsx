// @vitest-environment jsdom
/*
  O TIPO DA LINHA NA TELA — caminho inteiro (08/10/2026)
  =====================================================
  MEDIDO na captura de 08/10/2026 14:20, no app instalado, em "Terminal ao
  vivo". Sete checks de saude, TODOS com `OK` no texto, marcados ERROR:

  ```
  14:20:25  ERROR  GD ... XAU_AI_PRO (BTCUSD,M5) AI: OK | Failures: 0 | Error:
  14:20:25  ERROR  CI ... XAU_AI_PRO (BTCUSD,M5) Indicators: OK | Failures: 0 | Error:
  ```

  E, ao mesmo tempo, as DUAS travas que impediram operacao — 63.837 linhas
  `[SAFETY]` e 29.574 `[CIRCUIT]` em 200.185 — apareciam INFO.

  `lib/journalKind.test.ts` trava o classificador. Este trava a TELA: o teste
  unitario passaria mesmo se o componente voltasse a classificar por palavra
  (AGENTS.md §6: o teste precisa exercitar o caminho inteiro).
*/
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';

const estado = vi.hoisted(() => ({
  journal: [] as Array<{ message: string; time?: string }>,
}));

vi.mock('../hooks/queries', () => ({
  useCoreStatus: () => ({ data: { pronto: true, ligado: false } }),
  useAccount: () => ({
    data: { login: 391773676, balance: 15.3, equity: 20.25, margin: 20, margin_free: 0, level: 101 },
  }),
  usePositions: () => ({ data: { positions: [] } }),
  useJournal: () => ({ data: { lines: estado.journal }, isFetching: false }),
  useAllCryptoAccounts: () => ({ data: [] }),
  useAutoState: () => ({ data: null }),
}));

import UniversalLiveTerminal from './UniversalLiveTerminal';

/** As linhas como o MT5 as entrega: codigo, flag, hora, nome, simbolo, mensagem. */
const linha = (msg: string, hora: string) => ({
  time: `2026.10.08 ${hora}`,
  message: `QQ 0 ${hora} XAU_AI_PRO (BTCUSD,M5) ${msg}`,
});

/**
 * O tipo que a TELA pintou na linha que contem `trecho`.
 *
 * Sem `screen.getByText`: o matcher de regex nao entra no tipo desta
 * assinatura, e `tsc --noEmit` e gate. Ler a tabela direto tambem deixa o teste
 * falar do que a tela pintou, e nao do que o classificador devolveu.
 */
const tipoDaLinha = (trecho: string): string => {
  const linha = Array.from(document.querySelectorAll('tr')).find((tr) =>
    (tr.textContent ?? '').includes(trecho),
  );
  if (!linha) throw new Error(`linha nao encontrada na tela: ${trecho}`);
  return linha.querySelector('.ev-kind')?.textContent ?? '';
};

describe('o TIPO na tela vem do valor, nao da palavra', () => {
  beforeEach(() => {
    estado.journal = [
      linha('AI: OK | Failures: 0 | Error:', '14:20:22.295'),
      linha('Indicators: OK | Failures: 0 | Error:', '14:20:22.295'),
      linha('[SAFETY] Free margin low: 0.23/20.00', '14:25:56.931'),
      linha('[CIRCUIT] SPREAD ALTO | USDSEK | Bloqueio delegado ao ValidateTrade', '14:25:57.175'),
      linha('[BACKUP] FAIL | copiados=9 | falhas=98', '14:20:22.295'),
    ];
  });
  afterEach(cleanup);

  it('o check 100% OK NAO aparece como ERROR na tela', () => {
    render(<UniversalLiveTerminal />);
    expect(tipoDaLinha('AI: OK')).toBe('INFO');
    expect(tipoDaLinha('Indicators: OK')).not.toBe('ERROR');
  });

  it('as duas travas aparecem como WARN, nao INFO', () => {
    render(<UniversalLiveTerminal />);
    expect(tipoDaLinha('Free margin low')).toBe('WARN');
    expect(tipoDaLinha('SPREAD ALTO')).toBe('WARN');
  });

  it('a falha com numero aparece como ERROR', () => {
    render(<UniversalLiveTerminal />);
    expect(tipoDaLinha('falhas=98')).toBe('ERROR');
  });

  it('PROVA NEGATIVA: a coluna TIPO existe e mostra os quatro rotulos', () => {
    // Se a coluna sumisse, os tres testes acima passariam por acidente.
    render(<UniversalLiveTerminal />);
    const tipos = Array.from(document.querySelectorAll('.ev-kind')).map((n) => n.textContent);
    expect(tipos).toContain('INFO');
    expect(tipos).toContain('WARN');
    expect(tipos).toContain('ERROR');
  });
});