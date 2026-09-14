// Contrato TypeScript do protocolo v1 — espelho de core/src/protocol/mod.rs.
// Gerado manualmente; qualquer mudança no Rust exige atualização aqui.
// Envelope: `{ "protocol": "xau-ai-pro/1", "type": "<Variante>", ... }`

export const PROTOCOL_VERSION = '1.0.0';
export const PROTOCOL_ENVELOPE = 'xau-ai-pro/1';
export const WS_PING_INTERVAL_MS = 30000;
export const DEFAULT_SYMBOLS = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD'];

export type ClientKind = 'react' | 'ea_mt5' | 'cli' | 'unknown';

export interface HelloMessage {
  version: string;
  core_version: string;
  symbols: string[];
  ping_interval_ms: number;
}

export interface PongMessage {
  request_id: string;
  ts_ms: number;
  server_ts_ms: number;
}

export interface ProtocolError {
  code: string;
  message: string;
  request_id?: string | null;
}

/** Códigos de erro estáveis do protocolo v1. */
export const ErrorCodes = {
  BAD_REQUEST: 'BAD_REQUEST',
  VERSION_MISMATCH: 'VERSION_MISMATCH',
  MT5_OFFLINE: 'MT5_OFFLINE',
  ORDER_REJECTED: 'ORDER_REJECTED',
  NOT_FOUND: 'NOT_FOUND',
  INTERNAL: 'INTERNAL',
} as const;

export interface OrderRequestPayload {
  symbol: string;
  side: string;
  volume: number;
  sl?: number | null;
  tp?: number | null;
  magic?: number | null;
}

export interface OrderCommandPayload extends OrderRequestPayload {
  request_id: string;
}

export interface OrderResponsePayload {
  success: boolean;
  ticket: number;
  message: string;
  request_id?: string | null;
}

/** Mensagens Core → cliente (campo `type` discrimina). */
export type WsMessageV1 =
  | ({ type: 'Hello' } & HelloMessage)
  | ({ type: 'Quote' } & Record<string, unknown>)
  | ({ type: 'Account' } & Record<string, unknown>)
  | ({ type: 'PositionUpdate' } & Record<string, unknown>)
  | ({ type: 'OrderResponse' } & OrderResponsePayload)
  | ({ type: 'SystemState' } & Record<string, unknown>)
  | ({ type: 'Pong' } & PongMessage)
  | ({ type: 'Error' } & ProtocolError);
