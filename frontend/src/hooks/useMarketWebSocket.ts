import { useEffect, useRef, useCallback } from 'react';
import { useAppStore } from './useAppStore';

// Usa Variaveis de Ambiente do Tauri ou fallback para localhost
const getWsUrl = (): string => {
  const host = (window as any).TAURI_PLATFORM ? '127.0.0.1' : '127.0.0.1';
  const port = (window as any).TAURI_PLATFORM ? '9002' : '9002';
  return `ws://${host}:${port}/ws/market`;
};

export function useMarketWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number | null>(null);
  const { addQuote, setWsConnected, setAccount, setPositions, setOrders, setSystemState } = useAppStore();

  const connectWebSocket = useCallback(() => {
    const wsUrl = getWsUrl();
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WS] Conectado ao Rust Core:', wsUrl);
      setWsConnected(true);

      // Envia subscribe para simbolos
      const { selectedSymbol } = useAppStore.getState();
      ws.send(JSON.stringify({
        type: 'Subscribe',
        symbols: ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD', 'ETHUSD']
      }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === 'Quote') {
          addQuote(msg);
        } else if (msg.type === 'Account') {
          setAccount(msg);
        } else if (msg.type === 'PositionUpdate') {
          const { positions } = useAppStore.getState();
          setPositions([...positions.filter((p) => p.ticket !== msg.ticket), msg]);
        } else if (msg.type === 'OrderResponse') {
          // Tratar resposta de ordem
        } else if (msg.type === 'SystemState') {
          setSystemState(msg);
        }
      } catch (e) {
        console.error('[WS] Erro ao parsear mensagem:', e);
      }
    };

    ws.onclose = () => {
      console.log('[WS] Desconectado. Reconectando em 3s...');
      setWsConnected(false);

      reconnectRef.current = window.setTimeout(() => {
        connectWebSocket();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error('[WS] Erro:', error);
    };
  }, [addQuote, setWsConnected, setAccount, setPositions, setOrders, setSystemState]);

  useEffect(() => {
    connectWebSocket();

    return () => {
      if (reconnectRef.current) {
        clearTimeout(reconnectRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connectWebSocket]);

  return { wsRef, connectWebSocket };
}
