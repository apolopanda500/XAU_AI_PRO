// Hook WebSocket do protocolo v1 (XAU AI PRO Core).
// Handshake Hello, heartbeat com latencia e reconexao com backoff.

import { useEffect, useRef, useCallback } from 'react';
import { apiBase, wsUrl } from '../lib/api';
import { useAppStore } from './useAppStore';
import {
  PROTOCOL_VERSION,
  WS_PING_INTERVAL_MS,
  DEFAULT_SYMBOLS,
  type WsMessageV1,
} from '../lib/protocol';

const getWsUrl = (): string => wsUrl();
const nowMs = (): number => Date.now();

// Símbolos ativos: watchlist informada pelo painel ou o padrão do protocolo.
const desiredSymbols = (): string[] => {
  const wanted = useAppStore.getState().subscribeSymbols;
  return wanted.length ? wanted : DEFAULT_SYMBOLS;
};

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
    setQuotes,
    setWsConnected,
    setAccount,
    setPositions,
    setSystemState,
  } = useAppStore();
  const quoteBufferRef = useRef<Map<string, WsMessageV1>>(new Map());
  const renderFrameRef = useRef<number | null>(null);
  // Ultima lista enviada ao Core; evita Subscribe redundante a cada clique.
  const subscribedRef = useRef<string[]>([]);

  const scheduleQuoteFlush = useCallback(() => {
    if (renderFrameRef.current !== null) return;
    renderFrameRef.current = window.requestAnimationFrame(() => {
      renderFrameRef.current = null;
      const buffered = quoteBufferRef.current;
      if (!buffered.size) return;
      const current = useAppStore.getState().quotes;
      const next = new Map(current.map((quote) => [quote.symbol, quote]));
      buffered.forEach((message, symbol) => next.set(symbol, message as never));
      quoteBufferRef.current = new Map();
      setQuotes(Array.from(next.values()) as never);
    });
  }, [setQuotes]);

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
          {
            // Subscribe dinâmico: watchlist atual (ou padrão do protocolo) no handshake.
            const symbols = desiredSymbols();
            subscribedRef.current = symbols;
            ws.send(JSON.stringify({ type: 'Subscribe', symbols }));
          }
          break;
        case 'Quote':
          quoteBufferRef.current.set(String((msg as unknown as { symbol?: string }).symbol ?? ''), msg);
          scheduleQuoteFlush();
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
    [scheduleQuoteFlush, setWsConnected, setAccount, setPositions, setSystemState],
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

  // Reaplica subscriptions quando a watchlist muda (diff minimo Subscribe/Unsubscribe).
  const applySubscriptions = useCallback((symbols: string[]) => {
    const ws = wsRef.current;
    const next = symbols.filter(Boolean);
    if (!ws || ws.readyState !== WebSocket.OPEN || !helloOk.current || !next.length) return;
    const current = subscribedRef.current;
    const add = next.filter((s) => !current.includes(s));
    const remove = current.filter((s) => !next.includes(s));
    if (!add.length && !remove.length) return;
    if (add.length) ws.send(JSON.stringify({ type: 'Subscribe', symbols: add }));
    if (remove.length) ws.send(JSON.stringify({ type: 'Unsubscribe', symbols: remove }));
    subscribedRef.current = next;
  }, []);

  useEffect(() => {
    connectWebSocket();
    return () => {
      stopPing();
      if (renderFrameRef.current !== null) window.cancelAnimationFrame(renderFrameRef.current);
      quoteBufferRef.current.clear();
      retryRef.current = 999;
      if (wsRef.current) wsRef.current.close();
    };
  }, [connectWebSocket]);

  return { wsRef, connectWebSocket, applySubscriptions };
}
