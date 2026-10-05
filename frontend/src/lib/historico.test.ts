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
  type Deal,
} from './historico';

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
