import { describe, expect, it } from 'vitest';
import { filtrarEventosAtivos, type TerminalEventRow } from './terminalFeed';

const linha = (source: string): TerminalEventRow => ({
  id: `id-${source}`,
  source,
  info: `info ${source}`,
  at: new Date('2026-11-18T20:40:25Z'),
  kind: 'INFO',
});

describe('filtrarEventosAtivos', () => {
  it('mantem MT5 e MOTOR sempre', () => {
    const rows = [linha('MT5'), linha('MOTOR')];
    expect(filtrarEventosAtivos(rows).map((r) => r.source)).toEqual(['MT5', 'MOTOR']);
  });

  it('esconde MEXC/BINANCE/BYBIT/OKX quando nao ha conta ativa', () => {
    const rows = [
      linha('MT5'),
      linha('MEXC'),
      linha('BINANCE'),
      linha('BYBIT'),
      linha('OKX'),
    ];
    expect(filtrarEventosAtivos(rows).map((r) => r.source)).toEqual(['MT5']);
  });

  it('mostra a corretora planejada quando a conta esta ok no gateway', () => {
    const rows = [linha('MEXC'), linha('BINANCE')];
    expect(filtrarEventosAtivos(rows, ['mexc']).map((r) => r.source)).toEqual(['MEXC']);
  });

  it('e insensivel a caixa e espacos no nome do broker', () => {
    const rows = [linha(' MEXC '.trim())];
    expect(filtrarEventosAtivos(rows, [' Mexc ']).map((r) => r.source)).toEqual(['MEXC']);
  });

  it('mantem fontes desconhecidas (logcat de sistema)', () => {
    expect(filtrarEventosAtivos([linha('SISTEMA')]).map((r) => r.source)).toEqual(['SISTEMA']);
  });
});
