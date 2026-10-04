// Testes do catalogo de corretoras do front.
//
// O front mantinha uma lista fixa de simbolos por corretora (BTCUSDT, ETHUSDT,
// ...) que nenhuma API confirmava, e so offercia MT5, MEXC e Binance. Com a
// OKX e a Bybit promoted to active no gateway, a lista virou codigo morto e
//CXigava a procedencia dos dados. O catalogo agora vem de
// /api/universal/assets e e normalizado para a forma canonica do app.
import { describe, expect, it } from 'vitest';
import {
  BROKERS,
  MARKETS_BY_BROKER,
  MARKET_LABELS,
  brokerLabel,
  compatibleMarket,
  isTradable,
  normalizeSymbol,
  parseAssetCatalog,
  restrictionLabel,
} from './brokerCatalog';

describe('corretoras oferecidas', () => {
  it('cobre as cinco corretoras com leitura real', () => {
    expect(BROKERS.map((b) => b.id)).toEqual(['mt5', 'binance', 'mexc', 'bybit', 'okx']);
  });

  it('toda corretora offered tem mercados declarados', () => {
    for (const broker of BROKERS) {
      expect((MARKETS_BY_BROKER[broker.id] ?? []).length).toBeGreaterThan(0);
    }
  });

  it('rotulo legivel e fallback para corretora desconhecida', () => {
    expect(brokerLabel('okx')).toBe('OKX');
    expect(brokerLabel('xmglobal')).toBe('XMGLOBAL');
  });
});

describe('normalizeSymbol', () => {
  it('canonicaliza o par com hifen da OKX', () => {
    expect(normalizeSymbol('BTC-USDT')).toBe('BTCUSDT');
  });

  it('canonicaliza o swap de futuros da OKX', () => {
    // O sufixo precisa ser removido antes de apagar o hifen, senao vira BTCUSDTSWAP.
    expect(normalizeSymbol('BTC-USDT-SWAP')).toBe('BTCUSDT');
    expect(normalizeSymbol('BTC_USDT_SWAP')).toBe('BTCUSDT');
  });

  it('canonicaliza o par com barra', () => {
    expect(normalizeSymbol('ETH/BTC')).toBe('ETHBTC');
  });

  it('remove sufixo de contrato perpetuo', () => {
    expect(normalizeSymbol('BTCUSDT.P')).toBe('BTCUSDT');
    expect(normalizeSymbol('BTCUSDT.PERP')).toBe('BTCUSDT');
  });

  it('preserva o par ja canonico', () => {
    expect(normalizeSymbol('btcusdt')).toBe('BTCUSDT');
    expect(normalizeSymbol('  XAUUSD  ')).toBe('XAUUSD');
  });
});

describe('compatibleMarket', () => {
  it('mantem o mercado quando a corretora suporta', () => {
    expect(compatibleMarket('okx', 'crypto-futures')).toBe('crypto-futures');
  });

  it('troca para um mercado suportado quando nao cabe', () => {
    expect(compatibleMarket('okx', 'forex')).toBe('crypto-spot');
    expect(compatibleMarket('bybit', 'metals')).toBe('crypto-spot');
  });
});

describe('parseAssetCatalog', () => {
  const payload = {
    source: 'okx_api',
    assets: [
      {
        symbol: 'BTC-USDT',
        display_name: 'Bitcoin',
        availability: 'available',
        restrictions: [],
        digits: 2,
        point: 0.1,
        volume_step: 0.0001,
        trade_mode: 0,
      },
      {
        symbol: 'OLD-USDT',
        availability: 'unavailable',
        restrictions: ['symbol_disabled'],
        trade_mode: 0,
      },
      {
        symbol: 'XAU-USD-SWAP',
        availability: 'restricted',
        restrictions: ['long_only'],
        trade_mode: 1,
      },
    ],
  };

  it('extrai os ativos e normaliza o simbolo', () => {
    const rows = parseAssetCatalog(payload);
    expect(rows.map((r) => r.symbol)).toEqual(['BTCUSDT', 'OLDUSDT', 'XAUUSD']);
  });

  it('preserva as restricoes declaradas pela corretora', () => {
    const rows = parseAssetCatalog(payload);
    expect(rows[1].restrictions).toEqual(['symbol_disabled']);
    expect(rows[2].restrictions).toEqual(['long_only']);
  });

  it('preserva os parametros de contrato quando existem', () => {
    const rows = parseAssetCatalog(payload);
    expect(rows[0].digits).toBe(2);
    expect(rows[0].point).toBe(0.1);
    expect(rows[0].volumeStep).toBe(0.0001);
  });

  it('nao inventa ativo a partir de payload invalido', () => {
    expect(parseAssetCatalog(null)).toEqual([]);
    expect(parseAssetCatalog({})).toEqual([]);
    expect(parseAssetCatalog({ assets: 'nao-e-lista' })).toEqual([]);
    expect(parseAssetCatalog({ assets: [null, 7, {}, { symbol: '' }] })).toEqual([]);
  });

  it('ativo sem informacao de disponibilidade fica unverified', () => {
    const rows = parseAssetCatalog({ assets: [{ symbol: 'BTCUSDT' }] });
    expect(rows[0].availability).toBe('unverified');
  });
});

describe('isTradable', () => {
  const base = {
    symbol: 'X',
    displayName: null,
    restrictions: [],
    digits: null,
    point: null,
    volumeStep: null,
    volumeMin: null,
    volumeMax: null,
    tradeMode: null,
  };

  it('ativo disponivel e operavel', () => {
    expect(isTradable({ ...base, availability: 'available' })).toBe(true);
    expect(isTradable({ ...base, availability: 'unverified' })).toBe(true);
  });

  it('ativo desativado na corretora nao e operavel', () => {
    expect(isTradable({ ...base, availability: 'unavailable' })).toBe(false);
    expect(
      isTradable({ ...base, availability: 'available', restrictions: ['symbol_disabled'] }),
    ).toBe(false);
  });

  it('ativo com restricao de direcao continua selecionavel', () => {
    // long_only nao impede operar: impede apenas vender.
    expect(isTradable({ ...base, availability: 'restricted', restrictions: ['long_only'] })).toBe(
      true,
    );
  });
});

describe('restrictionLabel', () => {
  it('traduz as restricoes conhecidas', () => {
    expect(restrictionLabel('long_only')).toBe('somente compra');
    expect(restrictionLabel('short_only')).toBe('somente venda');
    expect(restrictionLabel('close_only')).toBe('somente fechamento');
    expect(restrictionLabel('trading_disabled')).toBe('negociação desativada');
  });

  it('nao engole restricao desconhecida', () => {
    expect(restrictionLabel('regra_nova_2026')).toBe('regra_nova_2026');
  });
});

describe('rotulos de mercado', () => {
  it('todos os mercados das corretoras tem rotulo', () => {
    for (const markets of Object.values(MARKETS_BY_BROKER)) {
      for (const market of markets) {
        expect(MARKET_LABELS[market], `mercado sem rotulo: ${market}`).toBeTruthy();
      }
    }
  });
});
