// A regra do par na tela, medida direto na funcao e nos tres leitores.
//
// MEDIDO 22/10/2026 no app instalado: barra `BTCUSD`, seletor `XAUUSD`, grafico
// `XAUUSD` sob um cabecalho `BTCUSD`. Nenhum dos tres podia ser acusado
// isoladamente: cada componente escolhia sozinho entre o par GRAVADO no motor e
// a escolha do operador. A funcao existe para haver UMA resposta.
import { describe, expect, it } from 'vitest';
import { parNaTela, ehClasseDeModelo } from '../lib/parNaTela';

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

/*
  O NOME DO MODELO NAO E UM PAR (12/11/2026)
  ===========================================
  MEDIDO no app instalado 1.2.182, texto lido da tela as 23:50:

    Gráfico indisponível: nenhuma fonte publica respondeu para MULTI_METALS M5
    (binance: sem equivalente para este par ou perodo; yahoo: ...; frankfurter: ...)

  `MULTI_METALS` e o `symbol` do `MULTI_METALS.meta.json` — o nome do MODELO de
  classe, que `ListaModelos.escolher` gravava como par. O backend recusa esse
  nome como ativo (medido: `simbolo_valido` -> False, `classe_de` -> OUTROS,
  `_tentativas_multi` -> []), e o modelo de classe entra SOZINHO para o ativo
  real (`_tentativas_multi('XAUUSD','M5')` -> `MULTI_METALS`).

  Aqui ficam as duas provas: a classe nunca vira par, e um par de verdade
  continua passando.
*/
describe('parNaTela: nome de modelo de classe nao e par', () => {
  it('motor LIGADO com nome de modelo cede para a escolha real da tela', () => {
    expect(parNaTela({ ativo: true, simbolo: 'MULTI_METALS' }, 'XAUUSD')).toBe('XAUUSD');
    expect(parNaTela({ ativo: true, simbolo: 'MULTI_FIAT' }, 'EURUSD')).toBe('EURUSD');
  });

  it('PROVA NEGATIVA: so nome de modelo em toda parte devolve VAZIO', () => {
    // Recusa com motivo, nunca um "par" que nenhuma corretora cota.
    expect(parNaTela({ ativo: true, simbolo: 'MULTI_METALS' }, 'MULTI_METALS')).toBe('');
    expect(parNaTela({ ativo: false, simbolo: 'MULTI_CRYPTO' }, 'multi_crypto')).toBe('');
    expect(parNaTela({ ativo: true, simbolo: 'MULTI_METALS' }, '')).toBe('');
  });

  it('ehClasseDeModelo casa o prefixo do artefato, e nao palavra solta', () => {
    expect(ehClasseDeModelo('MULTI_METALS')).toBe(true);
    expect(ehClasseDeModelo(' multi_fiat ')).toBe(true);
    // Ativo de verdade nao e classe, mesmo com MULTI no meio do nome.
    expect(ehClasseDeModelo('XAUUSD')).toBe(false);
    expect(ehClasseDeModelo('MULTI')).toBe(false);
    expect(ehClasseDeModelo('XMULTI_USD')).toBe(false);
    expect(ehClasseDeModelo('')).toBe(false);
    expect(ehClasseDeModelo(null)).toBe(false);
  });
});
