import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useCatalogoAtivos } from './useCatalogoAtivos';

/*
  O CATALOGO SEM MERCADO (07/10/2026)
  ===================================

  O defeito que este arquivo trava, medido na conta 391773676
  (XMGlobal-MT5 14) com o motor DESLIGADO, que e quando
  `auto.market` chega vazio:

    backend _universal_assets("mt5", "")             -> 1639 ativos
    backend _universal_candles("mt5","","BTCUSD","M1") -> 20 candles, ok

  O gateway tem reserva: `_universal_scope` troca mercado vazio por
  "other" no MT5 e "crypto-spot" nas exchanges. O hook nao tinha
  essa reserva: com `market === ""` ele fazia `setAtivos([])` sem
  consultar. A cadeia do defeito era

    auto.market="" -> catalogo vazio -> fichaDoAtivo=null
      -> mercadoDoAtivo(undefined)=null -> market=""
      -> getCandles -> normalizeMarketSource("mt5","")=null
      -> throw "Identidade de mercado invalida"

  O throw e no FRONTEND, antes de qualquer chamada ao gateway. Na
  tela aparecia "Grafico indisponivel: Identidade de mercado
  invalida" e "BTCUSD sem candles reais para M1", com 0 candles.
*/

let fetchMock: ReturnType<typeof vi.fn>;

const CATALOGO = {
  assets: [
    {
      symbol: 'BTCUSD',
      asset_class: 'crypto',
      contract_size: 1.0,
      model_symbol: null,
      volume_min: 0.01,
      volume_max: 80,
    },
    {
      symbol: 'GOLD',
      asset_class: 'metal',
      contract_size: 100.0,
      model_symbol: 'XAUUSD',
      volume_min: 0.01,
      volume_max: 50,
    },
  ],
};

beforeEach(() => {
  localStorage.clear();
  fetchMock = vi.fn(async () => ({
    ok: true,
    json: async () => CATALOGO,
  }));
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useCatalogoAtivos', () => {
  it('consulta o catalogo com o mercado que recebeu', async () => {
    const { result } = renderHook(() => useCatalogoAtivos('mt5', 'crypto-spot'));

    await waitFor(() => expect(result.current.length).toBe(2));
    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain('broker=mt5');
    expect(url).toContain('market=crypto-spot');
  });

  it('CONSULTA com mercado vazio e devolve a ficha (a correcao)', async () => {
    const { result } = renderHook(() => useCatalogoAtivos('mt5', ''));

    await waitFor(() => expect(result.current.length).toBe(2));
    expect(String(fetchMock.mock.calls[0][0])).toContain('market=');

    const btc = result.current.find((a) => a.symbol === 'BTCUSD');
    expect(btc?.assetClass).toBe('crypto');
    expect(btc?.contractSize).toBe(1.0);
  });

  /*
    PROVA NEGATIVA. Com o `if (!market) { setAtivos([]); return undefined; }`
    que existia antes, `fetchMock` NUNCA era chamado e `result.current` ficava
    vazio para sempre. Este caso reprova naquela versao.
  */
  it('PROVA NEGATIVA: sem a correcao o catalogo nunca era consultado', async () => {
    const { result } = renderHook(() => useCatalogoAtivos('mt5', ''));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock.mock.calls.length).toBeGreaterThan(0);
    expect(result.current.length).toBe(2);
  });

  it('cada mudanca de mercado refaz a consulta', async () => {
    const { result, rerender } = renderHook(
      ({ m }: { m: string }) => useCatalogoAtivos('mt5', m),
      { initialProps: { m: '' } },
    );

    await waitFor(() => expect(result.current.length).toBe(2));
    const antes = fetchMock.mock.calls.length;

    rerender({ m: 'metals' });
    await waitFor(() => expect(fetchMock.mock.calls.length).toBe(antes + 1));
    expect(String(fetchMock.mock.calls[antes][0])).toContain('market=metals');
  });

  it('falha de rede deixa o catalogo vazio, sem estourar', async () => {
    fetchMock.mockRejectedValueOnce(new Error('sem rede'));
    const { result } = renderHook(() => useCatalogoAtivos('mt5', ''));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(result.current).toEqual([]);
  });
});