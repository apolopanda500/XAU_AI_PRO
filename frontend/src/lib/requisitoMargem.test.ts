/*
  O REQUISITO DE MARGEM (06/10/2026)
  ===================================
  MEDIDO nas capturas da XM (`my.xm.com/pt/symbol-info/BTCUSD`, 20:43 e 20:46):
  `Quantidade 0,01 lotes` · `Requisito de margem $0.85` · barra em `8,01%`.

  ESTE TESTE EXISTE PORQUE O CICIO ANTERIOR DISSE QUE O NUMERO NAO PODIA SER
  ESCRITO. O motivo era certo (nao se escreve numero inventado no painel) e a
  conclusao estava errada: a corretora PUBLICA a alavancagem, e o MT5 a devolve
  em `account_info().leverage` — MEDIDO, `1000` nesta conta.

  Por isso estes numeros sao um TESTE e nao um comentario: se a conta da XM
  deixar de fechar, o teste reprova e o painel deixa de prometer o que a
  corretora promete.

  A CONTA, COM OS TRES NUMEROS DA XM
  ===================================
      contract_size BTCUSD = 1,0        (MEDIDO em `symbol_info`)
      alavancagem        = 1000:1       (MEDIDO no painel `Gerir` da XM)
      entrada            = 85.376,63    (captura da XM)

      nocional   = 0,01 x 1,0 x 85.376,63 = 853,7663
      requisito = 853,7663 / 1000        = 0,8537663  → XM escreve "$0.85"
*/
import { describe, expect, it } from 'vitest';
import { requisitoDeMargem } from './volumeUnidade';

/** Os tres numeros da conta, medidos. */
const ALAVANCAGEM_XM = 1000;
const CONTRATO_BTCUSD = 1;
const CONTRATO_EURUSD = 100_000;
const CONTRATO_GOLD = 100;
const ENTRADA_XM = 85_376.63;

describe('o requisito de margem bate com a conta da XM', () => {
  it('PROVA: 0,01 BTCUSD a 85.376,63 pede 0,85 — o numero da XM', () => {
    const r = requisitoDeMargem(0.01, ENTRADA_XM, CONTRATO_BTCUSD, ALAVANCAGEM_XM);

    // O nocional e o dinheiro que o operador esta realmente expondo.
    expect(r.nocional).toBeCloseTo(853.7663, 4);
    // A XM escreve "$0.85" na captura de 20:43.
    expect(r.valor).toBeCloseTo(0.8537663, 7);
    // Arredondado a duas casas, como a tela mostra.
    expect(Number(r.valor?.toFixed(2))).toBe(0.85);
    expect(r.motivo).toBeNull();
    expect(r.assumido).toBe(false);
  });

  it('PROVA NEGATIVA: sem alavancagem NAO vira 0,00 — vira ausencia', () => {
    /*
      O defeito que este caso impede: com `leverage` ausente, dividir por um
      padrao (1, 10, 100) produziria um numero. E `853,77` e `0,85` sao
      numeros que o operador NAO distingue sem fazer a conta — e o requisito de
      margem e o que decide se ele abre a ordem.

      `null` e a resposta honesta: a tela nao mostra requisito, e o operador
      sabe que o numero nao esta disponivel.
    */
    const r = requisitoDeMargem(0.01, ENTRADA_XM, CONTRATO_BTCUSD, null);

    expect(r.valor).toBeNull();
    expect(r.nocional).toBeNull();
    expect(r.motivo).toContain('alavancagem');
    expect(r.assumido).toBe(true);
  });

  it('o contract_size e o que separa cripto de forex', () => {
    /*
      MEDIDO: BTCUSD tem `contract_size = 1`, EURUSD tem `100.000` e GOLD tem
      `100`. Sem o contrato, o mesmo `0,01` a 85.376,63 daria `853,77` no
      BTCUSD e `85.376.630` no EURUSD — 100.000 vezes mais.

      E A MESMA ALAVANCAGEM, e o risco e incomparavel. Com 1000:1 na conta:
      no BTCUSD o requisito e `0,85` e uma oscilacao de `0,57%` contra o preco
      consome a margem; no EURUSD o requisito e `853,77` — mais que o saldo
      desta conta — e a ordem nunca abre.

      Por isso o requisito de margem no painel e uma INFORMACAO, e nao um
      limite: ele mostra ao operador que `0,01` em EURUSD e 1000 vezes mais
      caro do que `0,01` em BTCUSD, que e o que a unidade `Token(s)` x
      `Lote(s)` sozinha nao diz.

      O teste compara os dois com os MESMOS volume e preco: o unico insumo que
      muda e o contrato, e e ele que tem de mudar o resultado.
    */
    const cripto = requisitoDeMargem(0.01, ENTRADA_XM, CONTRATO_BTCUSD, ALAVANCAGEM_XM);
    const forex = requisitoDeMargem(0.01, ENTRADA_XM, CONTRATO_EURUSD, ALAVANCAGEM_XM);
    const metal = requisitoDeMargem(0.01, ENTRADA_XM, CONTRATO_GOLD, ALAVANCAGEM_XM);

    expect(cripto.valor).toBeCloseTo(0.8537663, 7);
    // 0,01 x 100.000 x 85.376,63 = 85.376.630,00. Um "0,01" em forex expoe
    // 1000 unidades da moeda, e nao 0,01.
    expect(forex.nocional).toBeCloseTo(85_376_630, 0);
    // 0,01 x 100 x 85.376,63 = 85.376,63 — cento vezes menos que forex.
    expect(metal.nocional).toBeCloseTo(85_376.63, 2);

    // 100.000x entre cripto e forex: e o contrato, e nao o preco.
    expect(forex.nocional! / cripto.nocional!).toBeCloseTo(100_000, 3);
  });

  it('PROVA NEGATIVA: sem contract_size o numero NAO e chuto', () => {
    /*
      Este e o caso que o AGENTS.md 9 chama de "numero inventado no painel vira
      limite real". Com `contractSize` ausente e um padrao de `1`, o requisito
      viraria `0,85` — EXATAMENTE o numero certo do BTCUSD, por coincidencia.

      E a coincidencia que torna o defeito perigoso: em BTCUSD o chute da
      certo, o operador ve `0,85`, bate com a XM, e confia. Em EURUSD o mesmo
      chute da `85.376,63`, e o operador so descobre depois de abrir a ordem.

      Por isso `assumido` marca o caso, e por isso o valor e `null`.
    */
    const r = requisitoDeMargem(0.01, ENTRADA_XM, null, ALAVANCAGEM_XM);

    expect(r.valor).toBeNull();
    expect(r.assumido).toBe(true);
    expect(r.motivo).toContain('contrato');
  });

  it('cada insumo ausente e NOMEADO, para a tela dizer o que falta', () => {
    /*
      A XM e o MT5 recusam ordem com um motivo generico. Este o do painel: ele
      diz QUAL campo nao veio, para o operador saber se e a alavancagem da conta
      ou o contrato do ativo.
    */
    expect(requisitoDeMargem(0, ENTRADA_XM, 1, 1000).motivo).toBe('Falta quantidade');
    expect(requisitoDeMargem(0.01, 0, 1, 1000).motivo).toBe('Falta preço');
    const varios = requisitoDeMargem(0.01, ENTRADA_XM, null, null).motivo ?? '';
    expect(varios).toContain('tamanho do contrato');
    expect(varios).toContain('alavancagem');
  });

  it('PROVA NEGATIVA: alavancagem ZERO nao vira divisao por zero', () => {
    // `0 / 0` em JavaScript e `NaN`, e `NaN` no painel vira a palavra "NaN".
    expect(requisitoDeMargem(0.01, ENTRADA_XM, 1, 0).valor).toBeNull();
    expect(requisitoDeMargem(0.01, ENTRADA_XM, 1, -100).valor).toBeNull();
    expect(requisitoDeMargem(0.01, ENTRADA_XM, 0, 1000).valor).toBeNull();
  });

  it('o volume ESCALA o requisito em linha reta', () => {
    // Dez vezes o volume, dez vezes o requisito. E a conferences de que nao ha
    // teto nem piso escondido na conta.
    const um = requisitoDeMargem(0.01, ENTRADA_XM, CONTRATO_BTCUSD, ALAVANCAGEM_XM);
    const dez = requisitoDeMargem(0.1, ENTRADA_XM, CONTRATO_BTCUSD, ALAVANCAGEM_XM);

    expect(dez.nocional! / um.nocional!).toBeCloseTo(10, 6);
    expect(dez.valor! / um.valor!).toBeCloseTo(10, 6);
  });
});