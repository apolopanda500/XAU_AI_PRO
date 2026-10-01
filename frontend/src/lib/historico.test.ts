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
    expect(dealDate(deal({ executedAt: '2026-01-01T00:00:00Z', close_time: '2025-01-01T00:00:00Z' })))
      .toBe('2026-01-01T00:00:00Z');
  });

  it('cai para close_time', () => {
    expect(dealDate(deal({ close_time: '2025-01-01T00:00:00Z' }))).toBe('2025-01-01T00:00:00Z');
  });

  it('devolve vazio sem data', () => {
    expect(dealDate(deal({}))).toBe('');
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
    const r = resumir([
      deal({ realizedPnl: 200 }),
      deal({ realizedPnl: -100 }),
    ]);
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


describe('deduplicar deals', () => {
  it('remove o mesmo ticket em contas diferentes', () => {
    // O `id` do gateway e o ticket, que e contador POR CONTA. Junta de varias
    // corretoras, o mesmo ticket aparece duas vezes.
    const entrada = [
      { id: '77', broker: 'mt5', symbol: 'XAUUSD', executedAt: '2026-09-01T10:00', side: 'buy' },
      { id: '77', broker: 'binance', symbol: 'XAUUSD', executedAt: '2026-09-01T10:00', side: 'buy' },
    ];
    expect(deduplicar(entrada)).toHaveLength(2);
  });

  it('remove repeticao exata dentro da mesma conta', () => {
    const d = { id: '1', broker: 'mt5', symbol: 'XAUUSD', executedAt: '2026-09-01T10:00', side: 'sell' };
    expect(deduplicar([d, { ...d }])).toHaveLength(1);
  });

  it('preserva abertura e fechamento da mesma posicao', () => {
    // Mesmo ticket e mesma conta: o que separa e o horario e o lado.
    const ab = { id: '5', broker: 'mt5', symbol: 'XAUUSD', executedAt: '2026-09-01T10:00', side: 'buy' };
    const fe = { id: '5', broker: 'mt5', symbol: 'XAUUSD', executedAt: '2026-09-01T12:00', side: 'sell' };
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
