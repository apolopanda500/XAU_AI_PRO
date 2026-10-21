import { describe, expect, it } from 'vitest';
import { normalizarDecisao } from './UniversalLiveTerminal';

// A COLUNA "DECISAO" MOSTRVA "--" E "SEM SINAL" (04/10/2026)
// ============================================================
// A tela lia `d.ts`, `d.side` e `d.simbolo`. O `Decisao` do backend manda
// `timestamp`, `sinal` e `symbol`. Nenhum dos tres nomes do painel existe no
// payload, entao:
//
//   rotulo  -> "--"          (simbolo e timeframe vazios)
//   resposta-> "sem sinal"   (sinal undefined)
//   quando  -> hora atual    (new Date(undefined) e invalido -> now)
//
// E a MESMA classe dos bugs de `volume`/`quantity`: dois lados do mesmo dado
// falando idiomas diferentes, e o build nao acusa nada porque TypeScript nao
// valida dado vindo de `JSON.parse`.

const DO_BACKEND = {
  timestamp: '2026-10-04T22:00:00+00:00',
  symbol: 'XAUUSD',
  timeframe: 'H1',
  agir: false,
  motivo: 'edge +0.1087 acima do minimo',
  sinal: 'BUY',
  confianca: 44.2,
  edge: 0.1087,
  modelo: 'RandomForestClassifier',
};

describe('normalizarDecisao', () => {
  it('le o payload real do backend', () => {
    const d = normalizarDecisao(DO_BACKEND);
    expect(d.timestamp).toBe('2026-10-04T22:00:00+00:00');
    expect(d.symbol).toBe('XAUUSD');
    expect(d.timeframe).toBe('H1');
    expect(d.sinal).toBe('BUY');
    expect(d.confianca).toBeCloseTo(44.2);
  });

  it('a data do backend e uma data VALIDA', () => {
    // Era isto que sumia: `new Date(undefined)` e invalido e o `at` caia no
    // `now`, entao o operador via a hora da tela em vez da hora do ciclo.
    const d = normalizarDecisao(DO_BACKEND);
    expect(Number.isNaN(new Date(d.timestamp!).getTime())).toBe(false);
  });

  it('aceita o vocabulario antigo da tela', () => {
    const d = normalizarDecisao({
      ts: '2026-10-04T22:00:00+00:00', simbolo: 'XAUUSD', timeframe: 'H1',
      side: 'SELL', confianca: 51.5, motivo: 'x',
    });
    expect(d.timestamp).toBe('2026-10-04T22:00:00+00:00');
    expect(d.symbol).toBe('XAUUSD');
    expect(d.sinal).toBe('SELL');
  });

  it('o canonico vence quando os dois nomes vem', () => {
    // Precedencia FIXA: sem isso o resultado dependeria da ordem das chaves.
    const d = normalizarDecisao({
      ...DO_BACKEND, ts: '1999-01-01T00:00:00+00:00',
      simbolo: 'EURUSD', side: 'SELL',
    });
    expect(d.timestamp).toBe('2026-10-04T22:00:00+00:00');
    expect(d.symbol).toBe('XAUUSD');
    expect(d.sinal).toBe('BUY');
  });

  it('payload vazio nao quebra e nao inventa valor', () => {
    for (const entrada of [null, undefined, {}, 'lixo', 42]) {
      const d = normalizarDecisao(entrada as Record<string, unknown>);
      expect(d.timestamp).toBe('');
      expect(d.sinal).toBe('');
      expect(d.symbol).toBe('');
      expect(d.confianca).toBe(0);
    }
  });

  it('campos em branco viram string vazia, nao "undefined"', () => {
    // `[simbolo, timeframe].filter(Boolean)` com undefined gerava "undefined"
    // na linha do feed.
    const d = normalizarDecisao({ symbol: undefined, timeframe: 'H1' });
    expect(d.symbol).toBe('');
    expect([d.symbol, d.timeframe].filter(Boolean).join(' ')).toBe('H1');
  });
});
