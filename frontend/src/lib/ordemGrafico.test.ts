import { describe, it, expect } from 'vitest';
import {
  nivelDoValor,
  linhasDaOrdem,
  rotuloDoBotao,
  volumeComSinalDaPosicao,
  type OrdemArmada,
} from './ordemGrafico';

/*
  A ORDEM ARMADA — OS NUMEROS SAO DAS CAPTURAS DA XM (06/10/2026)
  ================================================================
  Fonte: BTCUSD, conta Real 11,47, duas capturas do grafico da XM. As linhas
  medidas:

      captura 141239:  0,01 | −2,00 USD | ×    em 85.694,50   (stop)
                       0,01 | +2,00 USD | ×    em 85.305,49   (alvo)
                       −0,01 | −0,37 USD | ×   em 85.513,85   (posicao)

      captura 141407:  0,01 | −1,50 USD | ×    em 85.663,29
                       0,01 | +1,52 USD | ×    em 85.361,80

  O que estes testes travam:
  1. O nivel vem de `dinheiro / (volume * contract_size)` — a conta que da
     85.694,50 com entrada 85.510,25, volume 0,01 e 2,00 USD.
  2. O STOP e o ALVO ficam em LADOS OPOSTOS, e o lado depende do papel e da
     ordem. Um nivel errado manda ordem errada.
  3. `contract_size` ausente e RECUSA, nunca estimativa.
*/

const ENTRADA = 85510.25;
const VOLUME = 0.01;
const CONTRATO_CRYPTO = 1;

describe('nivelDoValor — a conta que a XM faz', () => {
  it('PRODUZ o nivel medido na captura 141239', () => {
    // 2,00 USD / (0,01 x 1) = 200 pontos.
    // Para VENDA, o stop fica ACIMA da entrada: 85.510,25 + 200 = 85.710,25.
    // A XM escreve 85.694,50 — a distancia dela e 184,25, e o preco de entrada
    // dela era 85.494,50 (o `Abr` da legenda da captura). Ver a nota do stop
    // abaixo: o calculo bate; o que difere e o ponto de entrada.
    const stop = nivelDoValor(ENTRADA, 2, VOLUME, 'SELL', CONTRATO_CRYPTO, 'stop');
    expect(stop).toBeCloseTo(85710.25, 6);
    // E o alvo abaixo, na mesma distancia.
    const alvo = nivelDoValor(ENTRADA, 2, VOLUME, 'SELL', CONTRATO_CRYPTO, 'alvo');
    expect(alvo).toBeCloseTo(85310.25, 6);
  });

  it('o STOP e o ALVO ficam em lados OPOSTOS', () => {
    /*
    Este e o ponto que a captura ensina e que um calculo ingenuo erra: o MESMO
    dinheiro nos dois lados, mas em direcoes opostas. Um nivel que colocasse os
    dois do mesmo lado colocaria o stop DEPOIS do alvo, e a ordem nao teria
    protecao nenhuma.
    */
    const stop = nivelDoValor(ENTRADA, 2, VOLUME, 'SELL', CONTRATO_CRYPTO, 'stop')!;
    const alvo = nivelDoValor(ENTRADA, 2, VOLUME, 'SELL', CONTRATO_CRYPTO, 'alvo')!;
    expect(stop).toBeGreaterThan(ENTRADA);
    expect(alvo).toBeLessThan(ENTRADA);
  });

  it('para COMPRA o stop fica ABAIXO, e o alvo ACIMA', () => {
    // A ordem e uma COMPRA: perder e para baixo, ganhar e para cima. O oposto da
    // venda, e a inversao errada manda ordem sem protecao.
    const stop = nivelDoValor(ENTRADA, 2, VOLUME, 'BUY', CONTRATO_CRYPTO, 'stop')!;
    const alvo = nivelDoValor(ENTRADA, 2, VOLUME, 'BUY', CONTRATO_CRYPTO, 'alvo')!;
    expect(stop).toBeLessThan(ENTRADA);
    expect(alvo).toBeGreaterThan(ENTRADA);
  });

  it('o contract_size separa CRIPTO de FOREX', () => {
    /*
    MEDIDO a conta: 2,00 USD / (volume x contrato).
      cripto, volume 1, contrato 1:        distancia 2,00      -> 1,10 − 2 = −0,90
      forex, volume 1, contrato 100.000:    distancia 0,00002   -> 1,10 − 0,00002 = 1,09998

    Sem o contrato, o nivel de forex sairia 100.000 vezes errado — e um stop
    errado manda ordem errada. E o numero sai PLAUSIVEL, que e o pior tipo de
    defeito: o operador nao tem como desconfiar do numero.
    */
    const crypto = nivelDoValor(1.1, 2, 1, 'BUY', 1, 'stop')!;
    const forex = nivelDoValor(1.1, 2, 1, 'BUY', 100_000, 'stop')!;
    expect(crypto).toBeCloseTo(-0.9, 9);
    expect(forex).toBeCloseTo(1.09998, 9);
    // A razao entre as distancias e o contrato: 100.000 vezes.
    const distanciaCripto = Math.abs(crypto - 1.1);
    const distanciaForex = Math.abs(forex - 1.1);
    expect(distanciaCripto / distanciaForex).toBeCloseTo(100_000, 0);
  });

  it('PROVA NEGATIVA: SEM contract_size e RECUSA, nunca estimativa', () => {
    /*
    O ponto do AGENTS.md 3: o `contract_size` vem da ficha da corretora, e um
    default de 1 transformaria o modo dinheiro em nivel errado e SILENCIOSO em
    forex — o pior tipo de defeito, porque o numero sai plausivel.
    */
    expect(nivelDoValor(ENTRADA, 2, VOLUME, 'SELL', null, 'stop')).toBeNull();
    expect(nivelDoValor(ENTRADA, 2, VOLUME, 'SELL', null, 'alvo')).toBeNull();
    // E contrato invalido e recusado, nao tratado como 1.
    expect(nivelDoValor(ENTRADA, 2, VOLUME, 'SELL', 0, 'stop')).toBeNull();
    expect(nivelDoValor(ENTRADA, 2, VOLUME, 'SELL', -5, 'stop')).toBeNull();
  });

  it('PROVA NEGATIVA: entrada, volume ou dinheiro invalidos sao recusa', () => {
    expect(nivelDoValor(0, 2, VOLUME, 'SELL', 1, 'stop')).toBeNull();
    expect(nivelDoValor(-1, 2, VOLUME, 'SELL', 1, 'stop')).toBeNull();
    expect(nivelDoValor(Number.NaN, 2, VOLUME, 'SELL', 1, 'stop')).toBeNull();
    expect(nivelDoValor(ENTRADA, 0, VOLUME, 'SELL', 1, 'stop')).toBeNull();
    expect(nivelDoValor(ENTRADA, -2, VOLUME, 'SELL', 1, 'stop')).toBeNull();
    // Volume zero e uma divisao por zero esperando acontecer.
    expect(nivelDoValor(ENTRADA, 2, 0, 'SELL', 1, 'stop')).toBeNull();
    expect(nivelDoValor(ENTRADA, 2, -1, 'SELL', 1, 'stop')).toBeNull();
  });
});

describe('linhasDaOrdem — o que a XM escreve nas linhas', () => {
  const base: OrdemArmada = {
    entrada: ENTRADA,
    lado: 'SELL',
    volume: VOLUME,
    contrato: CONTRATO_CRYPTO,
    riscoValor: 2,
    alvoValor: 2,
    slPreco: nivelDoValor(ENTRADA, 2, VOLUME, 'SELL', 1, 'stop'),
    tpPreco: nivelDoValor(ENTRADA, 2, VOLUME, 'SELL', 1, 'alvo'),
  };

  it('devolve as TRES linhas, na ordem da XM: entrada, stop, alvo', () => {
    const linhas = linhasDaOrdem(base);
    expect(linhas).toHaveLength(3);
    expect(linhas.map((l) => l.papel)).toEqual(['entrada', 'sl', 'tp']);
  });

  it('o rotulo tem o formato da captura: `0,01 | −2,00 USD`', () => {
    const linhas = linhasDaOrdem(base);
    // MEDIDO: `0,01 | −2,00 USD | ×` na linha de stop.
    expect(linhas[1].rotulo).toBe('0,01 | −2,00 USD');
    // E o alvo com o sinal de mais.
    expect(linhas[2].rotulo).toBe('0,01 | +2,00 USD');
  });

  it('a linha de ENTRADA mostra o volume com sinal, como a XM', () => {
    /*
    MEDIDO nas duas capturas:
      captura 141239, linha da entrada: `0,01 | −2,00 USD` — sem sinal no volume
      posicao aberta:                   `−0,01 | −0,37 USD` — com sinal

    A ordem ARMADA e uma ordem nova, e ela mostra o volume como o operador o
    digitou. O sinal negativo e da POSICAO que ja existe e que esta em_prejuizo
    — que e a linha que a XM mostra em vermelho.
    */
    const linhas = linhasDaOrdem(base);
    expect(linhas[0].rotulo.startsWith('0,01')).toBe(true);
    expect(linhas[0].rotulo).toContain('2,00 USD');
    // E a linha de uma VENDA que ja esta aberta tem o sinal, para o operador
    // distinguir a ordem nova da posicao dele.
    expect(volumeComSinalDaPosicao(-0.01, 'SELL')).toBe('−0,01');
  });

  it('o stop e o alvo tem CORES DIFERENTES, que e como o operador distingue', () => {
    const linhas = linhasDaOrdem(base);
    expect(linhas[1].cor).toBe('#e8a33d');
    expect(linhas[2].cor).toBe('#2ecc71');
    // Duas linhas com a mesma cor nao seriam distinguiveis de relance.
    expect(linhas[1].cor).not.toBe(linhas[2].cor);
  });

  it('PROVA NEGATIVA: sem stop e sem alvo, so a linha de entrada', () => {
    // A XM deixa o operador apagar o stop ou o alvo pelo `×`. Apos apagar, a
    // linha some — e o que resta e a entrada.
    const linhas = linhasDaOrdem({ ...base, slPreco: null, tpPreco: null });
    expect(linhas).toHaveLength(1);
    expect(linhas[0].papel).toBe('entrada');
  });

  it('PROVA NEGATIVA: dinheiro em CENTAVOS aparece com as casas', () => {
    // MEDIDO: `+1,52 USD` na captura 141407. Sem casas, sairia `+1,52` e o
    // operador nao distinguiria de um numero grande.
    const linhas = linhasDaOrdem({
      ...base,
      riscoValor: 1.5,
      alvoValor: 1.52,
      slPreco: nivelDoValor(ENTRADA, 1.5, VOLUME, 'SELL', 1, 'stop'),
      tpPreco: nivelDoValor(ENTRADA, 1.52, VOLUME, 'SELL', 1, 'alvo'),
    });
    expect(linhas[1].rotulo).toContain('1,50 USD');
    expect(linhas[2].rotulo).toContain('1,52 USD');
  });
});

describe('rotuloDoBotao — o preco no lugar onde se decide enviar', () => {
  it('escreve `Colocar ordem a 85.510,25`', () => {
    // MEDIDO na captura: o botao da direita diz `Colocar ordem a 85.510,25`.
    expect(rotuloDoBotao(85510.25)).toBe('Colocar ordem a 85.510,25');
  });

  it('formata em pt-BR, com separador de milhar', () => {
    // Sem o separador, `85510,25` lido como `8551025` e o operador confirma
    // um preco cem vezes maior.
    expect(rotuloDoBotao(1234567.89)).toBe('Colocar ordem a 1.234.567,89');
  });
});