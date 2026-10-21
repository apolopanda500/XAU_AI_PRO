import { describe, it, expect } from 'vitest';
import { emaValores, rsiValores, macdValores } from './PriceChart';

/*
  RSI E MACD — PROPRIEDADES, E UM CASO CONHECIDO (05/10/2026)
  ===========================================================
  Teste de indicador que so verifica "devolve um array" nao prova nada: RSI
  errado tambem devolve array. Aqui as asserções sao PROPRIEDADES que o
  calculo tem de satisfazer (0..100, alinhamento, forma do MACD) e um caso com
  resultado conhecido, calculado a mao.

  O alinhamento por indice e o ponto que mais quebra em silencio: devolver so os
  pontos validos faz o indicador DESLIZAR em relacao aos candles, e o grafico
  fica bonito e errado.
*/

const fechamentos = (n: number, inicio = 100, passo = 1) =>
  Array.from({ length: n }, (_, i) => inicio + i * passo);

describe('rsiValores', () => {
  it('devolve um valor por candle, sempre alinhado por indice', () => {
    const n = 40;
    const out = rsiValores(fechamentos(n), 14);
    expect(out).toHaveLength(n);
  });

  it('mantem null ate completar o periodo — nao desloca o indicador', () => {
    // periodo 14 => os 14 primeiros pontos sao null e o PRIMEIRO valor cai em
    // `periodo`. Se a serie comecasse antes, o RSI estaria deslocado para a
    // esquerda e o operador leria valor no candle errado.
    const out = rsiValores(fechamentos(40), 14);
    expect(out.slice(0, 14).every((v) => v === null)).toBe(true);
    expect(out[14]).not.toBeNull();
  });

  it('preco subindo sem queda devolve 100; caindo sem alta devolve 0', () => {
    expect(rsiValores(fechamentos(40), 14)[20]).toBe(100);
    expect(rsiValores(fechamentos(40, 100, -1), 14)[20]).toBe(0);
  });

  it('nunca sai de 0 a 100', () => {
    const ruidoso = [10, 11, 9, 12, 8, 13, 7, 14, 6, 15, 5, 16, 4, 17, 3, 18, 2, 19, 1, 20, 19, 3, 18, 4];
    for (const v of rsiValores(ruidoso, 14)) {
      if (v === null) continue;
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(100);
    }
  });

  it('PROVA NEGATIVA: serie sem queda nao devolve null, e preco parado da 50', () => {
    // Sem variacao nao ha ganho e nao ha perda: o índice é o impasse, 50.
    // Devolver 0 (ou null) seria afirmar que o ativo so caiu, e nao caiu.
    const out = rsiValores(Array.from({ length: 40 }, () => 100), 14);
    expect(out[14]).toBe(50);
    expect(out[20]).toBe(50);
  });

  it('PROVA NEGATIVA: candles insuficientes e periodo invalido dao null, e nao 0', () => {
    // RSI de "1 periodo" e media movel de ordem zero: daria 100 para qualquer
    // variacao e mentiria sistematicamente. Fica null.
    expect(rsiValores(fechamentos(40), 1).every((v) => v === null)).toBe(true);
    // Menos candles que o periodo: nao ha semente.
    expect(rsiValores(fechamentos(5), 14).every((v) => v === null)).toBe(true);
    expect(rsiValores([], 14)).toEqual([]);
  });

  it('CASO CONHECIDO: serie de exemplo, RSI calculado a mao', () => {
    // Valor de referencia do exemplo classico de Wilder (New Concepts in
    // Technical Trading Systems), conferido passo a passo.
    const out = rsiValores([
      44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08,
      45.89, 46.03, 45.61, 46.28, 46.28,
    ], 14);
    expect(out[14]).not.toBeNull();
    expect(out[14] as number).toBeCloseTo(70.46, 1);
  });
});

describe('macdValores', () => {
  it('as tres series tem o tamanho da entrada', () => {
    const n = 60;
    const out = macdValores(fechamentos(n));
    expect(out.macd).toHaveLength(n);
    expect(out.sinal).toHaveLength(n);
    expect(out.histograma).toHaveLength(n);
  });

  it('macd comeca na posicao da ema lenta, nunca antes', () => {
    const out = macdValores(fechamentos(60));
    const primeiro = out.macd.findIndex((v) => v !== null);
    // EMA(n) so tem valor a partir do indice n-1. Com lenta=26 e rapida=12, as
    // duas existem a partir de 25, entao o MACD comeca em 25 — nao em 26.
    expect(primeiro).toBe(25);
    expect(out.macd.slice(0, primeiro).every((v) => v === null)).toBe(true);
  });

  it('histograma e MACD menos sinal, e fica null ate o sinal existir', () => {
    const out = macdValores(fechamentos(80));
    const comAmbos = out.macd.findIndex(
      (m, i) => m !== null && out.sinal[i] !== null && out.histograma[i] !== null,
    );
    expect(comAmbos).toBeGreaterThan(25);
    for (let i = 0; i < comAmbos; i += 1) expect(out.histograma[i]).toBeNull();
    for (let i = comAmbos; i < out.macd.length; i += 1) {
      expect(out.histograma[i]).toBeCloseTo(
        (out.macd[i] as number) - (out.sinal[i] as number),
        8,
      );
    }
  });

  it('macd e zero quando as duas emas saem iguais — serie constante', () => {
    const out = macdValores(Array.from({ length: 80 }, () => 100));
    const comValor = out.macd.filter((v) => v !== null) as number[];
    expect(comValor.length).toBeGreaterThan(0);
    for (const v of comValor) expect(v).toBeCloseTo(0, 8);
  });

  it('macd positivo em alta e negativo em queda', () => {
    const alta = macdValores(fechamentos(80, 100, 1)).macd.filter((v) => v !== null);
    const baixa = macdValores(fechamentos(80, 100, -1)).macd.filter((v) => v !== null);
    expect(alta[alta.length - 1] as number).toBeGreaterThan(0);
    expect(baixa[baixa.length - 1] as number).toBeLessThan(0);
  });

  it('PROVA NEGATIVA: history curto ou parametros invalidos nao inventam numero', () => {
    // Histograma sem sinal calculado seria numero inventado: fica tudo null.
    const curto = macdValores(fechamentos(20));
    expect(curto.macd.every((v) => v === null)).toBe(true);
    expect(curto.histograma.every((v) => v === null)).toBe(true);
    // lenta <= rapida nao tem cruzamento: devolve nulo.
    const invertido = macdValores(fechamentos(80), 26, 12, 9);
    expect(invertido.macd.every((v) => v === null)).toBe(true);
    expect(invertido.macd).toHaveLength(80);
  });
});

describe('emaValores — o que o MACD consome', () => {
  it('comeca no indice periodo-1 com media simples e segue com a formula', () => {
    const out = emaValores(fechamentos(20), 12);
    expect(out.slice(0, 11).every((v) => v === null)).toBe(true);
    // SMA dos 12 primeiros fechamentos (100..111) = 105.5.
    const semente = 105.5;
    expect(out[11]).toBeCloseTo(semente, 8);
    const k = 2 / 13;
    expect(out[12]).toBeCloseTo(112 * k + semente * (1 - k), 8);
  });
});