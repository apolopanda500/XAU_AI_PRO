import { describe, it, expect } from 'vitest';
import { linhasMt5, resumoMt5, tipoDaLinha, nomeDoTipo } from './historicoMt5';
import type { Deal } from './historico';

/*
  HISTORICO MT5 — ESTE TESTE TRAVA A CAPTURA DO DONO (05/10/2026)
  ==============================================================
  Fonte: aba Historico do MT5 terminal, conta 391773676 (XMGlobal-MT5 14),
  com o deal 24503922 aberto. As 4 linhas, literais:

      2026.10.04 21:53:54   —   260002613  balance  CD-AST-PIC 265376085           5,52
      2026.10.04 21:53:54   —   260002614  balance  EXP05-AST-PIC 265376085          0,10
      2026.10.04 21:53:55   —   260002615  credit   Credit-In-100%-$100-NewClients  5,62
      2026.10.05 01:46:43   btcusd  24503922  buy   0,01  86394,85  86594,50
                             2026.10.05 02:12:25  86585,35   2,01   0,23%

      Lucro: 2,01  Credito: 5,62  Recarregar: 5,62  Retirada: 0,00  Saldo: 13,25

  TODO deal aqui e montado no formato MEDIDO nessa captura. Um deal inventado
  testaria contra um formato que o MT5 nao produz — que e como os quatro testes
  que gravavam o bug do `papel` no motor passaram sem ver nada (AGENTS.md 6).

  E a regra do projeto: entrada e saida de saldo NAO entram no calculo de
  resultado. Se entrassem, o resumo somaria dinheiro que ENTROU como se fosse
  lucro — e a captura mostra `Lucro: 2,01`, que e a operacao, e nao 13,25.
*/

/** A operacao 24503922: ABERTURA e FECHAMENTO sao DOIS deals do MT5. */
const ABERTURA_24503922: Deal = {
  id: 'entrada-24503922',
  broker: 'mt5',
  symbol: 'btcusd',
  side: 'buy',
  entry: 'IN',
  type: 'BUY',
  volume: 0.01,
  price: 86394.85,
  realizedPnl: 0,
  commission: -0.7,
  executedAt: '2026-10-05T01:46:43Z',
  ticket: 24503921,
  position_id: 24503922,
};

const FECHAMENTO_24503922: Deal = {
  id: 'fechamento-24503922',
  broker: 'mt5',
  symbol: 'btcusd',
  side: 'sell',
  entry: 'OUT',
  type: 'SELL',
  volume: 0.01,
  price: 86585.35,
  realizedPnl: 2.01,
  commission: -0.7,
  executedAt: '2026-10-05T02:12:25Z',
  open_price: 86394.85,
  sl: 86594.5,
  ticket: 24503922,
  position_id: 24503922,
};

/** `CD-AST-PIC 265376085` — deposito de 5,52. */
const DEPOSITO_552: Deal = {
  id: 'dep-552',
  broker: 'mt5',
  symbol: '',
  volume: 0,
  price: 0,
  profit: 5.52,
  executedAt: '2026-10-04T21:53:54Z',
  type: 'BALANCE',
  ticket: 260002613,
  comment: 'CD-AST-PIC 265376085',
  categoria: 'movimentacao',
};

/** `EXP05-AST-PIC 265376085` — deposito de 0,10. */
const DEPOSITO_010: Deal = {
  id: 'dep-010',
  broker: 'mt5',
  symbol: '',
  volume: 0,
  price: 0,
  profit: 0.1,
  executedAt: '2026-10-04T21:53:54Z',
  ticket: 260002614,
  comment: 'EXP05-AST-PIC 265376085',
  categoria: 'movimentacao',
};

/** `Credit-In-100%-$100-NewClients` — credito de 5,62 concedido pela XM. */
const CREDITO_562: Deal = {
  id: 'cred-562',
  broker: 'mt5',
  symbol: '',
  volume: 0,
  price: 0,
  profit: 5.62,
  executedAt: '2026-10-04T21:53:55Z',
  type: 'CREDIT',
  ticket: 260002615,
  comment: 'Credit-In-100%-$100-NewClients',
  categoria: 'movimentacao',
};

/** A conta inteira, na ordem em que o MT5 devolveu. */
const CONTA_391773676: Deal[] = [
  DEPOSITO_552,
  DEPOSITO_010,
  CREDITO_562,
  ABERTURA_24503922,
  FECHAMENTO_24503922,
];

describe('tipoDaLinha — o campo estruturado manda', () => {
  it('le BALANCE e CREDIT, e nao SELL', () => {
    expect(tipoDaLinha(DEPOSITO_552)).toBe('BALANCE');
    expect(tipoDaLinha(CREDITO_562)).toBe('CREDIT');
  });

  it('PROVA NEGATIVA: sem `type`, NUNCA vira SELL por padrao', () => {
    // `SELL` era o valor de tudo que nao era compra. Um deal sem tipo e sem
    // simbolo e movimentacao; virar SELL e o defeito medido.
    const semTipo = { ...DEPOSITO_552, type: undefined };
    expect(tipoDaLinha(semTipo)).toBe('BALANCE');
    expect(tipoDaLinha(semTipo)).not.toBe('SELL');
  });

  it('le o enum numerico do MT5', () => {
    // 2 = BALANCE, 3 = CREDIT, 1 = SELL no enum do MT5.
    expect(nomeDoTipo(2)).toBe('BALANCE');
    expect(nomeDoTipo(3)).toBe('CREDIT');
    expect(nomeDoTipo(1)).toBe('SELL');
  });

  it('codigo desconhecido NAO vira SELL', () => {
    expect(nomeDoTipo(99)).toBe('');
    expect(tipoDaLinha({ ...DEPOSITO_552, type: 99 })).toBe('BALANCE');
  });
});

describe('linhasMt5 — a operacao e UMA linha, como na captura', () => {
  it('a conta inteira vira 4 linhas: 3 movimentacoes + 1 operacao', () => {
    // 5 deals viram 4 linhas porque entrada e fechamento da operacao 24503922
    // sao a MESMA linha na captura. Sao 4 linhas no MT5 tambem.
    const linhas = linhasMt5(CONTA_391773676);
    expect(linhas).toHaveLength(4);
    expect(linhas.filter((l) => l.movimentacao)).toHaveLength(3);
    expect(linhas.filter((l) => !l.movimentacao)).toHaveLength(1);
  });

  it('PROVA NEGATIVA: entrada e fechamento NAO viram duas linhas', () => {
    // Este e o duplicado que o dono pediu para remover. O codigo antigo
    // affirms em comentario que "o MT5 mostra entrada e saida em DUAS linhas" —
    // a captura desmente.
    const linhas = linhasMt5([ABERTURA_24503922, FECHAMENTO_24503922]);
    expect(linhas).toHaveLength(1);
  });

  it('a linha traz horario de ABERTURA e horario de FECHAMENTO', () => {
    const [l] = linhasMt5([ABERTURA_24503922, FECHAMENTO_24503922]);
    // Coluna `Horario` = 01:46:43 (abre). Colunas `Horario | Preco` do
    // segundo par = 02:12:25 e 86585,35 (fecha).
    expect(l.horario).toContain('01:46:43');
    expect(l.horarioFim).toContain('02:12:25');
    expect(l.precoFim).toBe(86585.35);
    expect(l.preco).toBe(86394.85);
  });

  it('o Bilhete e o ticket do FECHAMENTO, como na captura', () => {
    // MEDIDO: na captura, `Bilhete` e 24503922 — que e o ticket do deal de
    // saida. A entrada tem 24503921 e nao aparece.
    const [l] = linhasMt5([ABERTURA_24503922, FECHAMENTO_24503922]);
    expect(l.bilhete).toBe('24503922');
  });

  it('o S/L vem da operacao e a Mudanca e a variacao do preco', () => {
    const [l] = linhasMt5([ABERTURA_24503922, FECHAMENTO_24503922]);
    expect(l.sl).toBe(86594.5);
    // 86585,35 contra 86394,85 = +0,2205%. A captura escreve 0,23%: o MT5
    // arredonda por dentro. A diferenca de 0,01 fica escrita aqui em vez de
    // ajustada no codigo — um arredondamento "para bater com a captura" seria
    // um numero inventado para parecer igual.
    expect(l.mudanca).toBe('0.22%');
    expect(l.volume).toBe(0.01);
  });

  it('PROVA NEGATIVA: o S/L vem do deal que o DECLARA', () => {
    // O MT5 grava o stop pedido na abertura e o repete no fechamento. Se uma
    // rota nova mandar so no fechamento, ler so do primeiro deal deixaria a
    // coluna vazia — e vazia aqui significa "a mercado", que e uma LEITURA
    // ERRADA, nao uma ausencia.
    const linhas = linhasMt5([
      { ...ABERTURA_24503922, sl: undefined },
      { ...FECHAMENTO_24503922, sl: 86594.5 },
    ]);
    expect(linhas[0].sl).toBe(86594.5);
  });

  it('stop ZERO vira null, nao 0', () => {
    // 0 e preco valido em alguns pares e nao existe stop no zero. Mostrar
    // "0,00" sugeriria um stop no zero.
    const linhas = linhasMt5([
      { ...ABERTURA_24503922, sl: 0, tp: 0 },
      { ...FECHAMENTO_24503922, sl: 0, tp: 0 },
    ]);
    expect(linhas[0].sl).toBeNull();
    expect(linhas[0].tp).toBeNull();
  });

  it('posicao ABERTA deixa horario e preco de fechamento VAZIOS', () => {
    // Sem deal de saida no grupo, repetir a hora de abertura diria que a
    // posicao fechou no minuto em que abriu.
    const [l] = linhasMt5([ABERTURA_24503922]);
    expect(l.horario).toContain('01:46:43');
    expect(l.horarioFim).toBe('');
    expect(l.precoFim).toBeNull();
    // E o Bilhete e o ticket da ABERTURA: e o unico que existe quando a
    // posicao nao tem deal de fechamento.
    expect(l.bilhete).toBe('24503921');
  });

  it('movimentacao tem os campos de OPERACAO NULOS, nao zero', () => {
    // `null` e ausencia; 0 e um numero. Um deposito nao tem volume nem preco,
    // e mostrar 0,00 diria que o negocio foi a 0,00 com 0,00 de volume.
    const [l] = linhasMt5([DEPOSITO_552]);
    expect(l.ativo).toBe('');
    expect(l.volume).toBeNull();
    expect(l.preco).toBeNull();
    expect(l.sl).toBeNull();
    expect(l.tp).toBeNull();
    expect(l.horarioFim).toBe('');
    expect(l.precoFim).toBeNull();
    expect(l.lucro).toBeNull();
    expect(l.mudanca).toBe('');
  });

  it('PROVA NEGATIVA: o dado volta NUMERO, nao texto com ponto', () => {
    /*
      A primeira versao devolvia string via `toFixed`, e a tela escrezia
      `86394.85` enquanto o MT5 — e o app, que e pt-BR — escreve `86394,85`.
      Locale nao e decisao de camada de dado. Um texto aqui voltaria a leaky
      com ponto, e um teste que so olhasse o valor passaria.
    */
    const [l] = linhasMt5([ABERTURA_24503922, FECHAMENTO_24503922]);
    expect(typeof l.preco).toBe('number');
    expect(typeof l.volume).toBe('number');
    expect(typeof l.sl).toBe('number');
    expect(typeof l.precoFim).toBe('number');
    expect(l.preco).toBe(86394.85);
    expect(l.precoFim).toBe(86585.35);
  });

  it('PROVA NEGATIVA: movimentacao nao pode ter LUCRO 0,00', () => {
    // "0,00" e um numero medido. Numa movimentacao nao existe resultado: o
    // dinheiro entrou. Escrever 0,00 e o resumo somando zero como se fosse
    // resultado de trading.
    const linhas = linhasMt5([DEPOSITO_552]);
    expect(linhas[0].lucro).toBeNull();
    expect(String(linhas[0].lucro)).not.toBe('0');
  });

  it('PROVA NEGATIVA: tres movimentacoes de 5,52 + 0,10 + 5,62 NAO viram uma', () => {
    // Agrupar por `corretora|ativo` fundiria os tres deals em uma linha, e o
    // operador leria UM deposito onde a corretora registrou TRES. A captura
    // mostra tres linhas.
    const linhas = linhasMt5([DEPOSITO_552, DEPOSITO_010, CREDITO_562]);
    expect(linhas).toHaveLength(3);
  });

  it('o comentario da corretora vai na coluna DEPOIS do bilhete', () => {
    const [l] = linhasMt5([DEPOSITO_552]);
    expect(l.bilhete).toBe('260002613');
    expect(l.comentario).toBe('CD-AST-PIC 265376085');
  });

  it('PROVA NEGATIVA: deal sem `entry` nao ganha IN ou OUT adivinhado', () => {
    // O MT5 sempre manda `entry`. Ausente vira vazio — inventar "IN" mostraria
    // uma abertura que talvez nao tenha acontecido.
    const l = linhasMt5([{ ...ABERTURA_24503922, entry: undefined }])[0];
    expect(l.entrada).toBe('');
  });
});

describe('resumoMt5 — os numeros literais da captura', () => {
  it('reproduz a linha de resumo da captura do MT5', () => {
    // `Lucro: 2,01  Credito: 5,62  Recarregar: 5,62  Retirada: 0,00  Saldo: 13,25`
    const r = resumoMt5(CONTA_391773676, 13.25);
    expect(r.lucro).toBeCloseTo(2.01, 6);
    expect(r.credito).toBeCloseTo(5.62, 6);
    expect(r.recarregar).toBeCloseTo(5.62, 6);
    expect(r.retirar).toBe(0);
    expect(r.saldo).toBe(13.25);
  });

  it('Recarregar e a soma dos DOIS `balance`, e Credito e o `credit`', () => {
    // 5,52 (`CD-AST-PIC`) + 0,10 (`EXP05-AST-PIC`) = 5,62 = "Recarregar: 5,62".
    // E o `credit` de 5,62 ("Credit-In-100%-$100-NewClients") = "Credito: 5,62".
    // Na captura os dois COINCIDEM em 5,62 — e nao e a mesma coisa.
    const r = resumoMt5(CONTA_391773676);
    expect(r.recarregar).toBeCloseTo(5.52 + 0.1, 6);
    expect(r.credito).toBeCloseTo(5.62, 6);
  });

  it('PROVA NEGATIVA: Credito e Recarregar divergem quando o dado diverge', () => {
    // Os dois serem 5,62 na captura e COINCidencia numerica. Com um deposito de
    // 100 eles tem que divergir: 100 e 5,62. Um teste que so fixasse a captura
    // passaria com as duas colunas trocadas.
    const r = resumoMt5([
      { ...DEPOSITO_552, profit: 100 },
      CREDITO_562,
    ]);
    expect(r.recarregar).toBeCloseTo(100, 6);
    expect(r.credito).toBeCloseTo(5.62, 6);
    expect(r.recarregar).not.toBeCloseTo(r.credito, 6);
  });

  it('PROVA NEGATIVA: entrada de saldo NAO entra no lucro', () => {
    // `Lucro: 2,01` e so a operacao. Somar os 11,24 das movimentacoes daria
    // 13,25 — que e o CAPITAL da conta, nao o que o trading produziu.
    const r = resumoMt5(CONTA_391773676);
    expect(r.lucro).toBeCloseTo(2.01, 6);
    expect(r.lucro).not.toBeCloseTo(13.25, 6);
    const somaMov = r.credito + r.recarregar + r.retirar;
    expect(somaMov).toBeCloseTo(11.24, 6);
    expect(r.lucro + somaMov).not.toBeCloseTo(r.saldo ?? 0, 6);
  });

  it('retirada e negativa e separada de recarga', () => {
    const r = resumoMt5([
      { ...DEPOSITO_552, profit: 100 },
      { ...DEPOSITO_010, profit: -40 },
    ]);
    expect(r.recarregar).toBeCloseTo(100, 6);
    expect(r.retirar).toBeCloseTo(-40, 6);
  });

  it('PROVA NEGATIVA: bonus conta como credito, nao como lucro', () => {
    const r = resumoMt5([{ ...CREDITO_562, type: 'BONUS', profit: 25 }]);
    expect(r.credito).toBeCloseTo(25, 6);
    expect(r.lucro).toBe(0);
  });

  it('comissao e taxa NAO viram movimento de saldo do cliente', () => {
    /*
      MEDIDO: comissao e taxa sao dinheiro que SAI, mas nao e retirada. Sao
      custo de operar. Somar em `retirar` diria ao operador que ele sacou
      dinheiro, o que e falso — e mudaria o que ele le da conta.
    */
    const r = resumoMt5([
      ABERTURA_24503922,
      FECHAMENTO_24503922,
      { ...DEPOSITO_552, type: 'COMMISSION', profit: -1.4 },
    ]);
    expect(r.retirar).toBe(0);
    // Os dois deals da operacao cobraram 0,70 cada — mas como `custos` le o
    // deal `COMMISSION` do tipo, e nao o campo `commission`, o total abaixo e
    // so o deal avulso. Ver a prova negativa seguinte.
    expect(r.custos).toBeCloseTo(-1.4, 6);
    expect(r.lucro).toBeCloseTo(2.01, 6);
    // E o saldo NAO soma comissao: comissao nao e dinheiro que entrou nem saiu
    // da conta, e a coluna Saldo nao e a soma dos deals.
    expect(r.credito + r.recarregar + r.retirar).toBe(0);
  });

  it('PROVA NEGATIVA: o `commission` do deal NAO entra em custos duas vezes', () => {
    /*
      O deal de saida da posicao ja traz `commission: -0.70`, e um deal
      `COMMISSION` avulso traz o mesmo valor. Somar os dois conta DUAS VEZES —
      e nenhum dos dois numeros viria errado sozinho. `custos` le so o deal do
      tipo `COMMISSION`.
    */
    const comDeal = resumoMt5([ABERTURA_24503922, FECHAMENTO_24503922]);
    expect(comDeal.custos).toBe(0);

    const comAvulso = resumoMt5([
      ABERTURA_24503922,
      FECHAMENTO_24503922,
      { ...DEPOSITO_552, id: 'taxa', type: 'COMMISSION', profit: -1.4 },
    ]);
    expect(comAvulso.custos).toBeCloseTo(-1.4, 6);
    expect(comAvulso.custos).not.toBeCloseTo(-2.8, 6);
  });

  it('saldo quando a corretora informa; null quando nao', () => {
    expect(resumoMt5(CONTA_391773676, 13.25).saldo).toBe(13.25);
    // Sem saldo informado, `null` e melhor que somar as movimentacoes e chamar
    // de saldo: saldo e o que a corretora diz, nao o que a tela deduz. MEDIDO:
    // a soma das movimentacoes da 11,24 e o `Saldo: 13,25` da captura e o
    // capital da conta.
    expect(resumoMt5(CONTA_391773676).saldo).toBeNull();
  });

  it('lista vazia nao quebra e devolve zeros', () => {
    expect(resumoMt5([])).toEqual({
      lucro: 0,
      credito: 0,
      recarregar: 0,
      retirar: 0,
      custos: 0,
      saldo: null,
    });
  });
});

describe('mudanca — a celula que o MT5 mostra e o nosso dado nao tem', () => {
  it('calcula quando o gateway traz o preco de abertura', () => {
    // A captura escreve 0,23% na operacao 24503922.
    const [l] = linhasMt5([ABERTURA_24503922, FECHAMENTO_24503922]);
    expect(l.mudanca).toBe('0.22%');
  });

  it('PROVA NEGATIVA: sem `open_price`, a celula fica VAZIA — nunca 0,00%', () => {
    /*
      "0,00%" diria "o preco nao se moveu" para um registro que nao tem como
      saber. Vazio diz a verdade: nao ha o dado.
    */
    const [l] = linhasMt5([
      { ...ABERTURA_24503922, position_id: undefined },
      { ...FECHAMENTO_24503922, open_price: undefined, position_id: undefined },
    ]);
    expect(l.mudanca).not.toContain('0.00%');
  });

  it('PROVA NEGATIVA: movimentacao nunca tem mudanca', () => {
    const [l] = linhasMt5([{ ...DEPOSITO_552, open_price: 100, price: 200 }]);
    expect(l.mudanca).toBe('');
  });
});

describe('agrupamento sem `position_id` — a rede de seguranca', () => {
  it('SEM position_id agrupa pelo primeiro deal livre do par', () => {
    // Duas ordens realmente distintas no mesmo par NAO podem virar uma linha:
    // isso esconderia operacoes de verdade.
    const linhas = linhasMt5([
      { ...ABERTURA_24503922, position_id: undefined },
      { ...FECHAMENTO_24503922, position_id: undefined },
      {
        ...ABERTURA_24503922,
        position_id: undefined,
        ticket: 24503999,
        executedAt: '2026-10-03T10:00:00Z',
      },
      {
        ...FECHAMENTO_24503922,
        position_id: undefined,
        ticket: 24503998,
        executedAt: '2026-10-03T15:00:00Z',
        price: 86000,
        realizedPnl: -20,
      },
    ]);
    expect(linhas).toHaveLength(2);
    expect(linhas.every((l) => l.horarioFim !== '')).toBe(true);
  });

  it('o MESMO par em corretoras diferentes nao se mistura', () => {
    const linhas = linhasMt5([
      { ...ABERTURA_24503922, position_id: undefined },
      { ...FECHAMENTO_24503922, position_id: undefined },
      {
        ...ABERTURA_24503922,
        position_id: undefined,
        broker: 'binance',
        symbol: 'BTCUSDT',
        executedAt: '2026-10-05T01:50:00Z',
      },
    ]);
    expect(linhas).toHaveLength(2);
  });

  it('fechamento parcial nao abre uma operacao nova', () => {
    // Tres deals no mesmo `position_id` e fechamento parcial: uma posicao, tres
    // registros. Uma linha so, com o lucro dos TRES.
    const linhas = linhasMt5([
      ABERTURA_24503922,
      FECHAMENTO_24503922,
      {
        ...FECHAMENTO_24503922,
        id: 'parcial',
        volume: 0.005,
        price: 86600,
        realizedPnl: 1.5,
        executedAt: '2026-10-05T01:55:00Z',
        ticket: 24503923,
      },
    ]);
    expect(linhas).toHaveLength(1);
    expect(linhas[0].lucro).toBeCloseTo(3.51, 6);
  });
});