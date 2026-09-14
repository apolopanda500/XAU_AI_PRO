// Hook WebSocket do protocolo v1 (XAU AI PRO Core).
// Handshake Hello, heartbeat com latencia e reconexao com backoff.

import { useEffect, useRef, useCallback } from 'react';
import { useAppStore } from './useAppStore';
import {
  PROTOCOL_VERSION,
  WS_PING_INTERVAL_MS,
  type WsMessageV1,
} from '../lib/protocol';

const getWsUrl = (): string => 'ws://127.0.0.1:9002/ws/market';
const nowMs = (): number => Date.now();

const newRequestId = (): string =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.floor(Math.random() * 1e9)}`;

export function useMarketWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<number>(0);
  const pingTimer = useRef<number | null>(null);
  const helloOk = useRef<boolean>(false);
  const {
    addQuote,
    setWsConnected,
    setAccount,
    setPositions,
    setSystemState,
  } = useAppStore();

  const stopPing = () => {
    if (pingTimer.current !== null) {
      window.clearInterval(pingTimer.current);
      pingTimer.current = null;
    }
  };

  const startPing = useCallback((ws: WebSocket) => {
    stopPing();
    pingTimer.current = window.setInterval(() => {
      if (ws.readyState !== WebSocket.OPEN || !helloOk.current) return;
      ws.send(
        JSON.stringify({
          type: 'Ping',
          request_id: newRequestId(),
          ts_ms: nowMs(),
        }),
      );
    }, WS_PING_INTERVAL_MS);
  }, []);

  const handleMessage = useCallback(
    (msg: WsMessageV1, ws: WebSocket) => {
      switch (msg.type) {
        case 'Hello':
          helloOk.current = true;
          retryRef.current = 0;
          setWsConnected(true);
          ws.send(
            JSON.stringify({
              type: 'Subscribe',
              symbols: ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD'],
            }),
          );
          break;
        case 'Quote':
          addQuote(msg as never);
          break;
        case 'Account':
          setAccount(msg as never);
          break;
        case 'PositionUpdate': {
          const { positions } = useAppStore.getState();
          const ticket = (msg as unknown as { ticket: number }).ticket;
          setPositions([
            ...positions.filter((p) => p.ticket !== ticket),
            msg as never,
          ]);
          break;
        }
        case 'SystemState':
          setSystemState(msg as never);
          break;
        case 'OrderResponse':
          break;
        case 'Pong': {
          const rtt = nowMs() - msg.ts_ms;
          console.debug('[WS] latencia:', rtt, 'ms');
          break;
        }
        case 'Error':
          console.warn('[WS] erro do Core:', msg.code, msg.message);
          break;
      }
    },
    [addQuote, setWsConnected, setAccount, setPositions, setSystemState],
  );

  const connectWebSocket = useCallback(() => {
    const attempt = retryRef.current;
    const delay = Math.min(1000 * 2 ** attempt, 30000);
    if (attempt > 0) console.log(`[WS] reconectando em ${delay}ms`);

    window.setTimeout(() => {
      const ws = new WebSocket(getWsUrl());
      wsRef.current = ws;
      helloOk.current = false;

      ws.onopen = () => {
        console.log('[WS] conectado; handshake Hello v1');
        ws.send(
          JSON.stringify({
            type: 'Hello',
            client: 'react',
            version: PROTOCOL_VERSION,
          }),
        );
        startPing(ws);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WsMessageV1;
          if (!msg || typeof msg.type !== 'string') {
            console.warn('[WS] mensagem sem type; ignorada');
            return;
          }
          handleMessage(msg, ws);
        } catch (e) {
          console.error('[WS] erro ao parsear mensagem:', e);
        }
      };

      ws.onclose = () => {
        stopPing();
        setWsConnected(false);
        helloOk.current = false;
        retryRef.current += 1;
        connectWebSocket();
      };

      ws.onerror = (error) => {
        console.error('[WS] erro:', error);
      };
    }, delay);
  }, [handleMessage, startPing, setWsConnected]);

  useEffect(() => {
    connectWebSocket();
    return () => {
      stopPing();
      retryRef.current = 999;
      if (wsRef.current) wsRef.current.close();
    };
  }, [connectWebSocket]);

  return { wsRef, connectWebSocket };
}
