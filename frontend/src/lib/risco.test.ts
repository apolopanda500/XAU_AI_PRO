import { describe, it, expect } from 'vitest';
import {
  valorDoNivel,
  nivelParaValor,
  valorComSinal,
  contratoUtilizavel,
  SEM_CONTRATO,
} from './risco';

/*
  RISCO EM DINHEIRO — O QUE ESTE TESTO TRAVA (05/10/2026)
  ======================================================
  MEDIDO na propria tela: o campo "Valor no risco (SL)" calculava
  `preco * lote * distancia`. Com os numeros da captura XM:

      BTCUSD 85.865,35 · lote 0,01 · distancia 8,45
      tela   : 7.255,62 USD
      real   :     0,08 USD      -> exagero de 85.865x

  O exagero era exatamente o preco. Estes testes existem para o numero nao
  voltar a ser o preco.
*/

const CRIPTO = { contractSize: 1 };
const FOREX = { contractSize: 100000 };

describe('valorDoNivel', () => {
  it('PROVA NEGATIVA do defeito medido: 8,45 a 0,01 em BTCUSD e 0,08 USD', () => {
    const v = valorDoNivel(85865.35, 85865.35 - 8.45, 0.01, CRIPTO);
    expect(v).not.toBeNull();
    expect(v as number).toBeCloseTo(0.0845, 6);
    // A conta antiga devolvia 7.255,62. Se este numero voltar, o bug voltou.
    expect(v).not.toBeCloseTo(7255.6221, 2);
  });

  it('o valor NAO depende do preco, e sim da DISTANCIA ate o nivel', () => {
    const d = 8.45;
    const a = valorDoNivel(85865.35, 85865.35 - d, 0.01, CRIPTO);
    const b = valorDoNivel(1000, 1000 - d, 0.01, CRIPTO);
    // Precos diferentes, MESMA distancia: o mesmo dinheiro. Era o preco que
    // multiplicava na conta antiga, e por isso o erro crescia com o preco.
    expect(a).toBeCloseTo(b as number, 10);
  });

  it('forex multiplica pelo contrato, e nao pelo preco', () => {
    // 0,0035 de distancia, 0,01 de lote, 100.000 de contrato = 3,50 USD.
    const v = valorDoNivel(1.085, 1.085 - 0.0035, 0.01, FOREX);
    expect(v as number).toBeCloseTo(3.5, 6);
  });

  it('o valor e um ABSOLUTO: o sinal do lado nao muda o tamanho', () => {
    const compra = valorDoNivel(100, 95, 1, CRIPTO);
    const venda = valorDoNivel(100, 105, 1, CRIPTO);
    expect(compra).toBeCloseTo(5, 10);
    expect(venda).toBeCloseTo(5, 10);
  });

  it('PROVA NEGATIVA: sem contrato, nao ha numero', () => {
    // Numero de risco inventado e o pior defeito de uma tela de operacao.
    expect(valorDoNivel(85865.35, 85856.9, 0.01, null)).toBeNull();
    expect(valorDoNivel(85865.35, 85856.9, 0.01, { contractSize: 0 })).toBeNull();
    expect(valorDoNivel(85865.35, 85856.9, 0.01, { contractSize: -1 })).toBeNull();
  });

  it('volume e preco invalidos devolvem null, e nao Infinity nem 0', () => {
    expect(valorDoNivel(100, 95, 0, CRIPTO)).toBeNull();
    expect(valorDoNivel(100, 95, -1, CRIPTO)).toBeNull();
    expect(valorDoNivel(Number.NaN, 95, 1, CRIPTO)).toBeNull();
  });
});

describe('nivelParaValor — o nivel que segue o preco', () => {
  it('compra: o alvo fica ACIMA da entrada; venda, abaixo', () => {
    const compra = nivelParaValor(100, 5, 1, 'compra', CRIPTO);
    const venda = nivelParaValor(100, 5, 1, 'venda', CRIPTO);
    expect(compra).toBeCloseTo(105, 10);
    expect(venda).toBeCloseTo(95, 10);
  });

  it('ida e volta preserva o valor: e o que "manter o valor" significa', () => {
    /*
      ESTE e o teste do que o dono pediu: o VALOR e fixo e o NIVEL e que se
      recalcula. Se o valor nao volta, o usuario Determinou um numero que a
      tela nao cumpre — que e pior que nao ter o campo.
    */
    for (const entrada of [85865.35, 1.085, 2400.5]) {
      for (const valor of [2, 0.0845, 350]) {
        const ficha = entrada > 1000 ? CRIPTO : FOREX;
        const nivel = nivelParaValor(entrada, valor, 0.01, 'compra', ficha);
        expect(nivel).not.toBeNull();
        expect(valorDoNivel(entrada, nivel as number, 0.01, ficha) as number).toBeCloseTo(
          valor,
          8,
        );
      }
    }
  });

  it('o nivel NAO usa o preco atual: a ancora e a entrada', () => {
    /*
      O preco entra como PARAMETRO de proposito. Usar o preco corrente aqui
      mudaria a ancora a cada tick e o valor deslizaria junto com o preco —
      o oposto de "manter o valor predeterminado".
    */
    const a = nivelParaValor(100, 5, 1, 'compra', CRIPTO);
    const b = nivelParaValor(105, 5, 1, 'compra', CRIPTO);
    // Entradas diferentes, mesmo valor: os niveis se deslocam junto com a entrada.
    expect(a).not.toBeCloseTo(b as number, 8);
  });

  it('PROVA NEGATIVA: valor zero ou negativo nao vira nivel', () => {
    // Valor 0 seria nivel = entrada: o stopbornaria na hora. E um nivel acima
    // do entry para uma compra e um TP imediato.
    expect(nivelParaValor(100, 0, 1, 'compra', CRIPTO)).toBeNull();
    expect(nivelParaValor(100, -5, 1, 'compra', CRIPTO)).toBeNull();
  });

  it('PROVA NEGATIVA: volume zero nao divide por zero', () => {
    expect(nivelParaValor(100, 5, 0, 'compra', CRIPTO)).toBeNull();
    expect(nivelParaValor(100, 5, 0, 'compra', null)).toBeNull();
  });
});

describe('valorComSinal e contratoUtilizavel', () => {
  it('venda escreve negativo, compra escreve positivo', () => {
    expect(valorComSinal(5, 'venda')).toBe(-5);
    expect(valorComSinal(5, 'compra')).toBe(5);
  });

  it('null continua null: a tela mostra o texto honesto, nao zero', () => {
    expect(valorComSinal(null, 'venda')).toBeNull();
    expect(SEM_CONTRATO).toBeTruthy();
  });

  it('PROVA NEGATIVA: contrato ausente nao vira 1', () => {
    // Assumir contrato 1 seria assumir que todo ativo e crypto: em forex o
    // numero sairia 100.000 vezes errado, em silencio.
    expect(contratoUtilizavel(null)).toBeNull();
    expect(contratoUtilizavel({ contractSize: null })).toBeNull();
    expect(contratoUtilizavel({ contractSize: 0 })).toBeNull();
    expect(contratoUtilizavel(CRIPTO)).toBe(1);
    expect(contratoUtilizavel(FOREX)).toBe(100000);
  });
});