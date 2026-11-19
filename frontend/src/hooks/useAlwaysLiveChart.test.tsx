import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useAlwaysLiveChart } from './useAlwaysLiveChart';

describe('useAlwaysLiveChart — 100% dinâmico', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('nunca presume ativo quando catálogo e posições estão vazios', () => {
    const onSelectSymbol = vi.fn();
    const onRefreshCandles = vi.fn();

    renderHook(() =>
      useAlwaysLiveChart({
        selectedSymbol: '',
        catalog: [],
        openPositionSymbols: [],
        onSelectSymbol,
        onRefreshCandles,
      }),
    );

    expect(onSelectSymbol).not.toHaveBeenCalled();
    expect(onRefreshCandles).not.toHaveBeenCalled();
  });

  it('prioriza o símbolo da posição aberta', () => {
    const onSelectSymbol = vi.fn();
    renderHook(() =>
      useAlwaysLiveChart({
        selectedSymbol: '',
        catalog: [{ symbol: 'ATIVO_A' }, { symbol: 'ATIVO_B' }],
        openPositionSymbols: ['ATIVO_B'],
        onSelectSymbol,
        onRefreshCandles: vi.fn(),
      }),
    );
    expect(onSelectSymbol).toHaveBeenCalledWith('ATIVO_B');
  });

  it('prefere o primeiro símbolo ativo do catálogo sem posição aberta', () => {
    const onSelectSymbol = vi.fn();
    renderHook(() =>
      useAlwaysLiveChart({
        selectedSymbol: '',
        catalog: [
          { symbol: 'PAR_INATIVO', active: false },
          { symbol: 'PAR_ATIVO', active: true },
        ],
        openPositionSymbols: [],
        onSelectSymbol,
        onRefreshCandles: vi.fn(),
      }),
    );
    expect(onSelectSymbol).toHaveBeenCalledWith('PAR_ATIVO');
  });

  it('mantém o feed vivo enquanto o símbolo está selecionado', () => {
    const onRefreshCandles = vi.fn();
    renderHook(() =>
      useAlwaysLiveChart({
        selectedSymbol: 'SIMBOLO_DINAMICO',
        catalog: [{ symbol: 'SIMBOLO_DINAMICO' }],
        openPositionSymbols: [],
        onSelectSymbol: vi.fn(),
        onRefreshCandles,
        refreshIntervalMs: 1000,
      }),
    );
    expect(onRefreshCandles).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(3000);
    expect(onRefreshCandles).toHaveBeenCalledTimes(4);
  });
});
