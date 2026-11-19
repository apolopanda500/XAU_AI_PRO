// Auto-vínculo de símbolo para o gráfico — 100% dinâmico, nada fixo.
//
// Regra do repositório: NENHUM ativo pode ser presumido no código. Este
// hook liga o gráfico ao primeiro símbolo útil que o GATEWAY entrega, na
// ordem:
//   1. símbolo de uma posição aberta (o que mais importa na tela do dono),
//   2. o primeiro símbolo ativo do catálogo conectado,
//   3. qualquer símbolo do catálogo (se nenhum estiver flagrado ativo),
//   4. nada — sem dados, a tela fica vazia por REUSA e não por omissão.
//
// Também mantém o feed de candles vivo enquanto a aba estiver visível.
// Nenhuma função aqui inventa símbolo nem símbolo vazio.
import { useEffect, useRef } from 'react';

export interface LiveCatalogEntry {
  symbol: string;
  active?: boolean;
  spread?: number;
}

export interface UseAlwaysLiveChartOptions {
  selectedSymbol: string;
  catalog: LiveCatalogEntry[];
  openPositionSymbols: string[];
  onSelectSymbol: (symbol: string) => void;
  onRefreshCandles: (symbol: string) => void;
  refreshIntervalMs?: number;
}

export function useAlwaysLiveChart({
  selectedSymbol,
  catalog,
  openPositionSymbols,
  onSelectSymbol,
  onRefreshCandles,
  refreshIntervalMs = 1500,
}: UseAlwaysLiveChartOptions): string {
  const autoBoundRef = useRef(false);

  // 1) Auto-vínculo uma única vez (quando ainda não há seleção).
  useEffect(() => {
    if (selectedSymbol) {
      autoBoundRef.current = true;
      return;
    }
    if (autoBoundRef.current) return;

    const posicional = openPositionSymbols.map((s) => String(s).trim()).find(Boolean);
    const catalogActive = catalog.find((item) => item.active !== false && String(item.symbol).trim());
    const catalogAny = catalog.find((item) => String(item.symbol).trim());
    const priority = posicional || catalogActive?.symbol || catalogAny?.symbol || '';

    if (priority && priority !== selectedSymbol) {
      autoBoundRef.current = true;
      onSelectSymbol(priority);
    }
  }, [selectedSymbol, catalog, openPositionSymbols, onSelectSymbol]);

  // 2) Feed de candles sempre vivo enquanto a aba estiver visível.
  useEffect(() => {
    if (!selectedSymbol) return;
    onRefreshCandles(selectedSymbol);
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') {
        onRefreshCandles(selectedSymbol);
      }
    }, refreshIntervalMs);
    return () => window.clearInterval(timer);
  }, [selectedSymbol, onRefreshCandles, refreshIntervalMs]);

  return selectedSymbol;
}
