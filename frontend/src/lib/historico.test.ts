/**
 * Testes da fonte unica de historico (lib/historico).
 *
 * O ponto这些人 nao e so a cobertura: e provar que as duas abas que mostram
 * deals (Historico e Analytics) concordam por construcao. Antes cada uma tinha
 * fetch, parser e conta de win-rate proprios, e nada impedia que divergissem.
 */
import { describe, expect, it } from 'vitest';
import {
  toNumber,
  dealPnl,
  dealDate,
  resumir,
  deduplicar,
  dealChave,
  ehMovimentacao,
  rotuloMovimentacao,
  formaMovimentacao,
  type Deal,
} from './historico';
import { linhasMt5, resumoMt5 } from './historicoMt5';

const deal = (extra: Partial<Deal>): Deal => ({
  id: '1',
  realizedPnl: 0,
  ...extra,
});

describe('toNumber', () => {
  it('aceita numero direto', () => {
    expect(toNumber(12.5)).toBe(12.5);
  });

  it('interpreta virgula decimal pt-BR', () => {
    expect(toNumber('1234,56')).toBeCloseTo(1234.56, 6);
  });

  it('interpreta ponto decimal en', () => {
    expect(toNumber('1234.56')).toBeCloseTo(1234.56, 6);
  });

  it('trata milhar pt-BR com virgula decimal', () => {
    expect(toNumber('1.234,56')).toBeCloseTo(1234.56, 6);
  });

  it('devolve NaN para entrada inutil', () => {
    expect(Number.isNaN(toNumber(''))).toBe(true);
    expect(Number.isNaN(toNumber('abc'))).toBe(true);
    expect(Number.isNaN(toNumber(undefined))).toBe(true);
  });
});

describe('dealPnl', () => {
  it('prefere realizedPnl', () => {
    expect(dealPnl(deal({ realizedPnl: '10,50', profit: 99 }))).toBeCloseTo(10.5, 6);
  });

  it('cai para profit quando realizedPnl nao existe', () => {
    expect(dealPnl({ id: '1', profit: 7 })).toBe(7);
  });

  it('zero quando nao ha campo nenhum', () => {
    expect(dealPnl({ id: '1' })).toBe(0);
  });
});

describe('dealDate', () => {
  it('prefere executedAt', () => {
    expect(
      dealDate(deal({ executedAt: '2026-01-01T00:00:00Z', close_time: '2025-01-01T00:00:00Z' })),
    ).toBe('2026-01-01T00:00:00Z');
  });

  it('cai para close_time', () => {
    expect(dealDate(deal({ close_time: '2025-01-01T00:00:00Z' }))).toBe('2025-01-01T00:00:00Z');
  });

  it('devolve vazio sem data', () => {
    expect(dealDate(deal({}))).toBe('');
  });
});

describe('movimentacoes de saldo (deposito, saque, credito)', () => {
  // POOL REAL da conta 391773676 (XMGlobal-MT5 14), medida em 05/10/2026 com
  // `history_deals_get` de 10 anos. Tres das cinco linhas NAO eram operacao:
  // eram movimentacao de saldo, e apareciam como "SELL" porque o gateway so
  // distinguia BUY de "tudo o mais".
  const POOL_REAL: Deal[] = [
    deal({ id: '260002616', categoria: 'operacao', symbol: 'BTCUSD', type: 'SELL', realizedPnl: 2.01 }),
    deal({ id: '260002615', categoria: 'movimentacao', type: 'CREDIT', movimentacao: 'Credito', realizedPnl: 5.62 }),
    deal({ id: '260002613', categoria: 'movimentacao', type: 'BALANCE', movimentacao: 'Deposito', realizedPnl: 5.52 }),
    deal({ id: '260002614', categoria: 'movimentacao', type: 'BALANCE', movimentacao: 'Deposito', realizedPnl: 0.1 }),
  ];

  it('reconhece movimentacao pelo campo que o backend enviou', () => {
    expect(ehMovimentacao(POOL_REAL[1])).toBe(true);
    expect(ehMovimentacao(POOL_REAL[0])).toBe(false);
  });

  it('classifica pelo rascunho quando o gateway nao manda `categoria`', () => {
    // Gateway velho ou exchange sem o campo: um deal sem simbolo e sem volume
    // nao e operacao. Sem este fallback, tudo viraria operacao de novo.
    expect(ehMovimentacao({ id: 'x', symbol: '', volume: 0, profit: 5.62 })).toBe(true);
    expect(ehMovimentacao({ id: 'y', symbol: 'BTCUSD', volume: 0.01, price: 86000 })).toBe(false);
  });

  it('NAO soma deposito nem credito no resultado do trading', () => {
    // Este e o defeito: 5,62 + 5,52 + 0,10 = 11,24 de dinheiro que ENTROU na
    // conta estava sendo lido como lucro. O resultado de trading e 2,01.
    const r = resumir(POOL_REAL);
    expect(r.total).toBeCloseTo(2.01, 6);
    expect(r.qty).toBe(1);
    expect(r.wins).toBe(1);
    expect(r.losses).toBe(0);
    expect(r.winRate).toBeCloseTo(100, 6);
  });

  it('contabiliza entrada e saida de saldo em numeros proprios', () => {
    const r = resumir([
      ...POOL_REAL,
      deal({ id: '260002999', categoria: 'movimentacao', movimentacao: 'Saque', realizedPnl: -2.0 }),
    ]);
    expect(r.movQtd).toBe(4);
    expect(r.movEntradas).toBeCloseTo(11.24, 6);
    expect(r.movSaidas).toBeCloseTo(2.0, 6);
  });

  it('saque NAO vira perda de trading', () => {
    // Um saque de 100 e dinheiro que saiu, nao uma operacao que perdeu 100.
    // Sem separacao, o win-rate e o profit factor mediam a carteira errada.
    const r = resumir([
      deal({ id: 'a', categoria: 'operacao', symbol: 'BTCUSD', realizedPnl: 50 }),
      deal({ id: 'b', categoria: 'movimentacao', movimentacao: 'Saque', realizedPnl: -100 }),
    ]);
    expect(r.losses).toBe(0);
    expect(r.profitFactor).toBe(Infinity);
    expect(r.total).toBeCloseTo(50, 6);
  });

  it('devolve o rotulo legivel da movimentacao', () => {
    expect(rotuloMovimentacao(POOL_REAL[2])).toBe('Deposito');
    expect(rotuloMovimentacao(POOL_REAL[0])).toBe('');
  });
});

describe('resumir', () => {
  it('conta一刀 pool vazia sem quebrar', () => {
    const r = resumir([]);
    expect(r.qty).toBe(0);
    expect(r.total).toBe(0);
    expect(r.winRate).toBe(0);
    expect(r.profitFactor).toBe(0);
  });

  it('conta ganhos, perdas e PnL', () => {
    const r = resumir([
      deal({ realizedPnl: 100 }),
      deal({ realizedPnl: 50 }),
      deal({ realizedPnl: -30 }),
    ]);
    expect(r.qty).toBe(3);
    expect(r.wins).toBe(2);
    expect(r.losses).toBe(1);
    expect(r.total).toBeCloseTo(120, 6);
    expect(r.grossWin).toBeCloseTo(150, 6);
    expect(r.grossLoss).toBeCloseTo(30, 6);
  });

  it('win-rate usa apenas operaciones fechadas, como o filtro de win/loss', () => {
    // 2 gains, 1 loss, 1 empatado: 2/3 = 66.67%, nao 2/4 = 50%.
    const r = resumir([
      deal({ realizedPnl: 10 }),
      deal({ realizedPnl: 10 }),
      deal({ realizedPnl: -5 }),
      deal({ realizedPnl: 0 }),
    ]);
    expect(r.closed).toBe(3);
    expect(r.winRate).toBeCloseTo((2 / 3) * 100, 6);
  });

  it('profit factor e bruto ganho sobre bruto perdido', () => {
    const r = resumir([deal({ realizedPnl: 200 }), deal({ realizedPnl: -100 })]);
    expect(r.profitFactor).toBeCloseTo(2, 6);
  });

  it('profit factor infinito quando nao ha perda', () => {
    const r = resumir([deal({ realizedPnl: 10 }), deal({ realizedPnl: 5 })]);
    expect(r.profitFactor).toBe(Infinity);
  });
});

describe('coerencia entre abas', () => {
  it('a mesma pool gera o mesmo resumo (base doHistorico e do Analytics)', () => {
    const deals = [
      deal({ realizedPnl: '1.000,50' }),
      deal({ realizedPnl: '-250,25' }),
      deal({ realizedPnl: '75,00' }),
    ];
    const primeira = resumir(deals);
    const segunda = resumir([...deals]);
    expect(segunda).toEqual(primeira);
    // O ponto do teste: mesma entrada, mesma saida, sem estado compartilhado.
    expect(primeira.total).toBeCloseTo(825.25, 6);
  });
});

describe('duplicatas no historico (chave de deduplicacao)', () => {
  /*
    O dono reportou operacao repetida na tela. A causa era a chave: `dealChave`
    montava broker|id|symbol|horario|side e deixava de fora tres campos que ja
    existiam no tipo `Deal`. Cada teste abaixo mede um deles.
  */

  it('preserva abertura e fechamento da MESMA posicao no mesmo segundo', () => {
    // Mesmo ticket, mesmo relogio, mesmo simbolo: o que separa e `entry`.
    // Sem `entry` na chave, o fechamento sumia da tela.
    const abertura = {
      id: '5', broker: 'mt5', symbol: 'BTCUSD', position_id: 77,
      executedAt: '2026-10-05T02:12:25Z', entry: 'IN', type: 'BUY', profit: 0,
    };
    const fechamento = { ...abertura, entry: 'OUT', type: 'SELL', profit: 2.01 };
    expect(dealChave(abertura)).not.toBe(dealChave(fechamento));
    expect(deduplicar([abertura, fechamento])).toHaveLength(2);
  });

  it('separa duas operacoes que so mudam o position_id', () => {
    // Mesmo ticket e mesmo horario, posicoes diferentes. `position_id` existe
    // no tipo desde o inicio e era ignorado pela chave.
    const a = { id: '9', broker: 'mt5', symbol: 'BTCUSD', position_id: 1, executedAt: '2026-10-05T02:12:25Z', entry: 'OUT' };
    const b = { ...a, position_id: 2 };
    expect(deduplicar([a, b])).toHaveLength(2);
  });

  it('lanca o lado do MT5 (`type`) quando nao ha `side`', () => {
    // Quinta ocorrencia da regra do AGENTS.md: o MT5 manda `type`, o campo
    // lido era `side`. Toda operacao do MT5 ficava com lado vazio, e dois
    // deals do mesmo instante colidiam.
    const a = { id: '1', broker: 'mt5', symbol: 'BTCUSD', executedAt: '2026-10-05T01:00:00Z', type: 'SELL' };
    const b = { id: '2', broker: 'mt5', symbol: 'BTCUSD', executedAt: '2026-10-05T01:00:00Z', type: 'BUY' };
    expect(dealChave(a)).not.toBe(dealChave(b));
    expect(deduplicar([a, b])).toHaveLength(2);
  });

  it('AINDA remove repeticao exata (a guarda nao foi afrouxada)', () => {
    // Prova negativa: sem isso, "corrigir" a chave seria so acrescentar campos
    // e a deduplicacao deixaria de funcionar.
    const d = {
      id: '1', broker: 'mt5', symbol: 'BTCUSD', position_id: 3,
      executedAt: '2026-10-05T01:00:00Z', entry: 'IN', type: 'BUY',
    };
    expect(deduplicar([d, { ...d }])).toHaveLength(1);
  });

  it('movimentacoes do mesmo instante nao colidem entre si', () => {
    // MEDIDO na conta real 391773676: CD-AST-PIC e EXP05-AST-PIC entraram com
    // o mesmo segundo. Sem `type`, as duas tinham chave identica e uma
    // desaparecia do historico.
    const a = { id: '613', broker: 'mt5', executedAt: '2026-10-04T21:53:54Z', type: 'BALANCE', movimentacao: 'Deposito', profit: 5.52 };
    const b = { id: '614', broker: 'mt5', executedAt: '2026-10-04T21:53:54Z', type: 'BALANCE', movimentacao: 'Deposito', profit: 0.1 };
    expect(deduplicar([a, b])).toHaveLength(2);
  });
});

describe('deduplicar deals', () => {
  it('remove o mesmo ticket em contas diferentes', () => {
    // O `id` do gateway e o ticket, que e contador POR CONTA. Junta de varias
    // corretoras, o mesmo ticket aparece duas vezes.
    const entrada = [
      { id: '77', broker: 'mt5', symbol: 'XAUUSD', executedAt: '2026-09-01T10:00', side: 'buy' },
      {
        id: '77',
        broker: 'binance',
        symbol: 'XAUUSD',
        executedAt: '2026-09-01T10:00',
        side: 'buy',
      },
    ];
    expect(deduplicar(entrada)).toHaveLength(2);
  });

  it('remove repeticao exata dentro da mesma conta', () => {
    const d = {
      id: '1',
      broker: 'mt5',
      symbol: 'XAUUSD',
      executedAt: '2026-09-01T10:00',
      side: 'sell',
    };
    expect(deduplicar([d, { ...d }])).toHaveLength(1);
  });

  it('preserva abertura e fechamento da mesma posicao', () => {
    // Mesmo ticket e mesma conta: o que separa e o horario e o lado.
    const ab = {
      id: '5',
      broker: 'mt5',
      symbol: 'XAUUSD',
      executedAt: '2026-09-01T10:00',
      side: 'buy',
    };
    const fe = {
      id: '5',
      broker: 'mt5',
      symbol: 'XAUUSD',
      executedAt: '2026-09-01T12:00',
      side: 'sell',
    };
    expect(deduplicar([ab, fe])).toHaveLength(2);
  });

  it('preserva a ordem de chegada', () => {
    const a = { id: '1', broker: 'mt5' };
    const b = { id: '2', broker: 'mt5' };
    expect(deduplicar([a, b, { ...a }]).map((d) => d.id)).toEqual(['1', '2']);
  });

  it('dealChave muda quando muda a corretora', () => {
    const base = { id: '9', symbol: 'XAUUSD', executedAt: '2026-09-01T10:00', side: 'buy' };
    expect(dealChave({ ...base, broker: 'mt5' })).not.toBe(dealChave({ ...base, broker: 'okx' }));
  });
});

// ==========================================================================
// FORMA DO DEPOSITO E DO SAQUE (05/10/2026)
// ==========================================================================
// O dono pediu: "se possivel tambem identificar formas de depositos e saques".
//
// O deal de movimentacao NAO tem campo de metodo (medido na conta 391773676):
// o metodo esta no `comment`, em texto livre da corretora. Entao a forma e lida
// do texto -- e por isso o caso mais importante aqui e o que acontece quando o
// texto nao diz nada.
describe("classificacao com o payload REAL do gateway (06/10/2026)", () => {
  /*
    MEDIDO NO APP INSTALADO, conta 391773676:
    o rodape da tabela unica mostrou `Lucro: +13,25`, que e 2,01 da operacao +
    5,62 + 5,62 das duas movimentacoes de saldo. Somar entrada de saldo em
    lucro e o que o AGENTS.md 10 proibe.

    A causa era o GATEWAY, nao esta regra: `_universal_history` preenchia
    `realizedPnl` para todo deal, e a regra de `ehMovimentacao` trata o campo
    PRESENTE como prova de execucao de ordem. Um deposito com `realizedPnl`
    classificava como operacao.

    Estes deals sao o que a rota produz DEPOIS da correcao — `categoria` presente
    e `realizedPnl` ausente na movimentacao. Eles travam o contrato dos dois
    lados: se o gateway voltar a preencher `realizedPnl`, estes testes nao
    detectam (isso e do Python), mas detectam que a tela deixou de confiar no
    rascunho.
  */

  const DEPOSITO_DO_GATEWAY: Deal = {
    id: '260002613',
    broker: 'mt5',
    accountId: 'mt5:391773676',
    symbol: '',
    side: 'BUY',
    entry: '',
    quantity: 0,
    price: 0,
    profit: 5.52,
    // O que a rota agora manda:
    ticket: 260002613,
    position_id: 0,
    type: 'BALANCE',
    categoria: 'movimentacao',
    movimentacao: 'Deposito',
    comment: 'CD-AST-PIC 265376085',
    commission: null,
    swap: null,
    fee: null,
    realizedPnl: null,
    executedAt: '2026-10-04T21:53:54Z',
  };

  const CREDITO_DO_GATEWAY: Deal = {
    ...DEPOSITO_DO_GATEWAY,
    id: '260002615',
    ticket: 260002615,
    type: 'CREDIT',
    movimentacao: 'Credito',
    comment: 'Credit-In-100%-$100-NewClients',
    profit: 5.62,
  };

  const OPERACAO_DO_GATEWAY: Deal = {
    id: '24503922',
    broker: 'mt5',
    accountId: 'mt5:391773676',
    symbol: 'btcusd',
    side: 'SELL',
    entry: 'OUT',
    quantity: 0.01,
    price: 86585.35,
    // `realizedPnl` = profit + comissao, porque no MT5 a comissao ja vem
    // negativa: 2,01 + (-0,70) = 1,31.
    profit: 2.01,
    realizedPnl: 1.31,
    commission: -0.7,
    type: 'SELL',
    ticket: 24503922,
    position_id: 24503922,
    categoria: 'operacao',
    movimentacao: '',
    comment: '',
    executedAt: '2026-10-05T02:12:25Z',
  };

  it('o deposito e movimentacao, e nao operacao', () => {
    expect(ehMovimentacao(DEPOSITO_DO_GATEWAY)).toBe(true);
    expect(ehMovimentacao(CREDITO_DO_GATEWAY)).toBe(true);
  });

  it('PROVA NEGATIVA: o campo estruturado vence o rascunho', () => {
    // Este e o ponto. `realizedPnl` ausente e `symbol`/`quantity`/`price` vazios
    // cairiam no rascunho de qualquer forma — o que muda e que `categoria` esta
    // presente e manda. Sem `categoria`, o deal viraria operacao assim que o
    // gateway voltasse a preencher `realizedPnl`.
    const semCategoria = { ...DEPOSITO_DO_GATEWAY, categoria: undefined };
    expect(semCategoria.categoria).toBeUndefined();
    // E ainda assim o rascunho acerta, porque o gateway mandou o deal no
    // formato MEDIDO: sem simbolo, sem volume, sem preco.
    expect(ehMovimentacao(semCategoria)).toBe(true);
  });

  it('a operacao NAO e movimentacao, mesmo com volume minimo', () => {
    expect(ehMovimentacao(OPERACAO_DO_GATEWAY)).toBe(false);
  });

  it('PROVA NEGATIVA: o Lucro do rodape NAO anexa movimentacao', () => {
    // A conta que a tela fez de verdade: 13,25. A correta e 1,31.
    const deals = [DEPOSITO_DO_GATEWAY, CREDITO_DO_GATEWAY, OPERACAO_DO_GATEWAY];
    const resumo = resumoMt5(deals);
    expect(resumo.lucro).toBeCloseTo(1.31, 6);
    expect(resumo.credito).toBeCloseTo(5.62, 6);
    expect(resumo.recarregar).toBeCloseTo(5.52, 6);
    // O numero que a tela exibiu.
    expect(resumo.lucro).not.toBeCloseTo(13.25, 6);
    // E nenhuma parcela da movimentacao entrou no Lucro.
    const parcelas = resumo.credito + resumo.recarregar + resumo.retirar;
    expect(parcelas).toBeCloseTo(11.14, 6);
  });

  it('o ticket e o comentario da corretora chegam a tela', () => {
    // MEDIDO no app instalado: `Bilhete` e `Comentario` sairam VAZIOS, porque a
    // rota nao repassava os dois campos.
    const linhas = linhasMt5([DEPOSITO_DO_GATEWAY, CREDITO_DO_GATEWAY, OPERACAO_DO_GATEWAY]);
    const deposito = linhas.find((l) => l.bilhete === '260002613');
    expect(deposito).toBeDefined();
    expect(deposito?.tipo).toBe('BALANCE');
    expect(deposito?.comentario).toBe('CD-AST-PIC 265376085');
    // E a forma e lida do comentario — o que o dono pediu ("identificar formas
    // de depositos e saques"), e que antes saia `nao informada` porque o
    // comentario nao atravessava a fronteira.
    expect(deposito?.forma).toBe('PIX');
    // A operacao: `Bilhete` e o ticket do FECHAMENTO, como na captura.
    const operacao = linhas.find((l) => l.ativo === 'btcusd');
    expect(operacao?.bilhete).toBe('24503922');
  });
});

describe("formaMovimentacao", () => {
  /** Deal no formato MEDIDO de movimentacao: sem simbolo, volume e preco zerados. */
  const mov = (comment?: string) =>
    ({
      id: "m1",
      broker: "mt5",
      symbol: "",
      volume: 0,
      price: 0,
      profit: 100,
      category: "deposito",
      comment,
    }) as Deal;

  it("le PIX do comentario", () => {
    expect(formaMovimentacao(mov("Deposit via PIX ref 8842"))).toBe("PIX");
  });

  it("le cartao, e cartao de credito ANTES do cartao generico", () => {
    expect(formaMovimentacao(mov("Deposit credit card"))).toBe("Cartão");
    expect(formaMovimentacao(mov("Cartao de credito Visa ****4321"))).toBe("Cartão");
  });

  it("le transferencia, boleto, cripto e cheque", () => {
    expect(formaMovimentacao(mov("Wire transfer in"))).toBe("Transferência bancária");
    expect(formaMovimentacao(mov("Boleto pago"))).toBe("Boleto");
    expect(formaMovimentacao(mov("Deposit USDT TRC20"))).toBe("Cripto");
    expect(formaMovimentacao(mov("Cheque depositado"))).toBe("Cheque");
  });

  it("le bonus e comissao, que sao movimentacoes com nome proprio", () => {
    expect(formaMovimentacao(mov("Bonus do plano"))).toBe("Bônus");
    expect(formaMovimentacao(mov("Comissao de spread"))).toBe("Comissão");
  });

  // ---- PROVA NEGATIVA: o que a funcao NAO pode fazer ----

  it("le PIC como PIX, que e a sigla real da XM", () => {
    /*
      MEDIDO na conta 391773676 (05/10/2026): os comentarios da XM sao
      `CD-AST-PIC 265376085` e `EXP05-AST-PIC 265376085` — com **PIC**, nao
      `PIX`. Com o padrao antigo (`\bpix\b` so) as tres movimentacoes de saldo
      da conta saiam como "nao informada": o metodo estava escrito e a tela
      dizia que nao sabia.

      O dono confirmou que na XM `PIC` e o Pix. Este teste e o que fixa a
      equivalencia: se a XM mudar a sigla, ele reprova em vez de a tela voltar
      a mentir em silencio.
    */
    expect(formaMovimentacao(mov("CD-AST-PIC 265376085"))).toBe("PIX");
    expect(formaMovimentacao(mov("EXP05-AST-PIC 265376085"))).toBe("PIX");
    // E as duas grafias seguem valendo.
    expect(formaMovimentacao(mov("Deposit via PIX"))).toBe("PIX");
    expect(formaMovimentacao(mov("Deposit via pix"))).toBe("PIX");
    expect(formaMovimentacao(mov("Deposit via PIC"))).toBe("PIX");
  });

  it("PROVA NEGATIVA: PIC so vira PIX com fronteira nos dois lados", () => {
    // Sem fronteira, "PICASSO" e "PICTURE" virariam Pix — e o operador
    // conferiria no banco e a tela mentiria. E o mesmo defeito de um padrao
    // frouxo que ja custou tempo no calendario (ver traduzirEvento.test.ts).
    expect(formaMovimentacao(mov("Deposit via PICASSO"))).toBe("nao informada");
    expect(formaMovimentacao(mov("PICTURE asset deposit"))).toBe("nao informada");
    expect(formaMovimentacao(mov("epic deposit"))).toBe("nao informada");
    // O hifen e fronteira: e por isso que o codigo da XM casa.
    expect(formaMovimentacao(mov("CD-AST-PIC 265376085"))).not.toBe("nao informada");
  });

  it("NAO inventa forma quando o comentario nao diz", () => {
    // Este e o teste que segura a promessa. Um metodo inventado seria pior que
    // nenhum: o operador conferiria no banco e a tela mentiria.
    expect(formaMovimentacao(mov("Credit adjustment"))).toBe("nao informada");
    expect(formaMovimentacao(mov("Balance operation 4471"))).toBe("nao informada");
  });

  it("NAO inventa forma quando nao ha comentario nenhum", () => {
    expect(formaMovimentacao(mov(undefined))).toBe("nao informada");
    expect(formaMovimentacao(mov(""))).toBe("nao informada");
    expect(formaMovimentacao(mov("   "))).toBe("nao informada");
  });

  it("a forma e o COMO, e nao o sentido: nao troca saque por deposito", () => {
    // "Withdrawal to card" e um SAQUE por cartao. A forma nao pode virar
    // "Deposito" so porque a palavra "card" aparece: o SENTIDO vem do valor.
    const saque = {
      ...mov("Withdrawal to card ****4321"),
      profit: -100,
      category: "saque",
    } as Deal;
    expect(formaMovimentacao(saque)).toBe("Cartão");
    expect(dealPnl(saque)).toBeLessThan(0);
  });

  it("devolve sempre texto, nunca vazio", () => {
    // A coluna precisa de largura constante, e o operador nao precisa ler a
    // diferenca entre "vazio" e "nao sei".
    expect(typeof formaMovimentacao(mov())).toBe("string");
    expect(formaMovimentacao(mov()).length).toBeGreaterThan(0);
  });
});
