// A regra do par na tela, medida direto na funcao e nos tres leitores.
//
// MEDIDO 22/10/2026 no app instalado: barra `BTCUSD`, seletor `XAUUSD`, grafico
// `XAUUSD` sob um cabecalho `BTCUSD`. Nenhum dos tres podia ser acusado
// isoladamente: cada componente escolhia sozinho entre o par GRAVADO no motor e
// a escolha do operador. A funcao existe para haver UMA resposta.
import { describe, expect, it } from 'vitest';
import { parNaTela } from '../lib/parNaTela';

describe('parNaTela: uma regra para a barra, o painel e o grafico', () => {
  it('motor DESLIGADO: a escolha da tela vence o par gravado', () => {
    expect(parNaTela({ ativo: false, simbolo: 'BTCUSD' }, 'XAUUSD')).toBe('XAUUSD');
  });

  it('motor LIGADO: o par que ele opera vence, porque e o que esta acontecendo', () => {
    expect(parNaTela({ ativo: true, simbolo: 'BTCUSD' }, 'XAUUSD')).toBe('BTCUSD');
  });

  it('sem escolha na tela, o par do motor aparece (ele e um dado, nao um default)', () => {
    expect(parNaTela({ ativo: false, simbolo: 'XAUUSD' }, '')).toBe('XAUUSD');
    expect(parNaTela({ ativo: false, simbolo: 'XAUUSD' }, null)).toBe('XAUUSD');
  });

  it('PROVA NEGATIVA: sem escolha e sem motor, o par e VAZIO', () => {
    // AGENTS.md 3: vazio e recusa com motivo. Se esta linha devolvesse um ativo
    // padrao, o painel voltaria a operar o par que ninguem escolheu.
    expect(parNaTela({ ativo: false, simbolo: '' }, '')).toBe('');
    expect(parNaTela(null, undefined)).toBe('');
  });

  it('normaliza caixa sem inventar valor', () => {
    expect(parNaTela({ ativo: false }, ' eurusd ')).toBe('EURUSD');
    expect(parNaTela({ ativo: true, simbolo: 'xauusd' }, '')).toBe('XAUUSD');
  });
});
