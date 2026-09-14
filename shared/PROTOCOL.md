# XAU AI PRO — Protocolo v1 (contrato versionado)

Contrato entre **Rust Core**, **frontend React** e **EA MT5**.
Implementacao de referencia: `core/src/protocol/mod.rs`.
Espelhos: `frontend/src/lib/protocol.ts` (TypeScript) e
`MQL5/Include/XAU_AI_PRO/ProtocolV1.mqh` (MQL5).

> Regra: qualquer mudanca no Rust exige atualizacao dos dois espelhos
> no mesmo commit. Divergencia quebra a CI.

## Versao

- Versao atual: **1.0.0** (major 1)
- Envelope na rede: `xau-ai-pro/1`
- WebSocket: `ws://127.0.0.1:9002/ws/market`
- Encoding: JSON UTF-8
- Heartbeat: Ping a cada 30000ms

## Compatibilidade

- Campos novos sao sempre opcionais — clientes antigos ignoram.
- Campos existentes nunca mudam de tipo nem de nome dentro da v1.
- Quebra intencional exige bump para v2; o Core recusa major diferente
  com erro `VERSION_MISMATCH`.

## Handshake (obrigatorio)

1. Cliente abre o WebSocket e envia **primeiro**:
   ```json
   { "protocol": "xau-ai-pro/1", "type": "Hello", "client": "react", "version": "1.0.0" }
   ```
   (`client`: `react` | `ea_mt5` | `cli` | `unknown`)
2. Core valida o major (`1.x` aceito) e responde:
   ```json
   {
     "type": "Hello",
     "version": "1.0.0",
     "core_version": "0.1.0",
     "symbols": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"],
     "ping_interval_ms": 30000
   }
   ```
3. Comandos antes do Hello recebem `BAD_REQUEST`.
4. Sem Hello em 10s, o Core fecha a conexao.

## Comandos (cliente para Core)

| Comando | Campos | Resposta |
|---|---|---|
| `Hello` | `client`, `version` | `Hello` |
| `Subscribe` | `symbols[]` | cotacoes filtradas passam a chegar |
| `Unsubscribe` | `symbols[]` | cotacoes filtradas param de chegar |
| `Ping` | `request_id`, `ts_ms` | `Pong` (eco + `server_ts_ms`) |
| `PlaceOrder` | ordem + `request_id` | `OrderResponse` ou `Error` |
| `ClosePosition` | `ticket`, `request_id` | `Error MT5_OFFLINE` (ate Fase 6) |
| `CancelOrder` | `ticket`, `request_id` | `Error MT5_OFFLINE` (ate Fase 6) |
| `GetAccount` | `request_id` | `Error MT5_OFFLINE` (ate Fase 6) |
| `GetPositions` | `request_id` | `Error MT5_OFFLINE` (ate Fase 6) |

Exemplo — ordem com correlacao:
```json
{
  "protocol": "xau-ai-pro/1",
  "type": "PlaceOrder",
  "symbol": "XAUUSD",
  "side": "buy",
  "volume": 0.10,
  "sl": null,
  "tp": null,
  "magic": 2026001,
  "request_id": "7f3a2b1c-0000-4000-8000-000000000001"
}
```

## Mensagens (Core para cliente)

| Mensagem | Quando |
|---|---|
| `Hello` | resposta ao handshake |
| `Quote` | cotacao de simbolo assinado |
| `Account` | atualizacao da conta (Fase 6) |
| `PositionUpdate` | atualizacao de posicao (Fase 6) |
| `OrderResponse` | `success`, `ticket`, `message`, `request_id` |
| `SystemState` | snapshot de estado do sistema |
| `Pong` | `request_id`, `ts_ms` (eco), `server_ts_ms` |
| `Error` | `code`, `message`, `request_id?` |

## Erros (codigos estaveis)

| Codigo | Significado |
|---|---|
| `BAD_REQUEST` | comando malformado ou fora de ordem |
| `VERSION_MISMATCH` | major do cliente incompativel |
| `MT5_OFFLINE` | bridge/EA indisponivel |
| `ORDER_REJECTED` | validacao de risco recusou |
| `NOT_FOUND` | posicao/ordem/simbolo inexistente |
| `INTERNAL` | falha interna do Core |

## Market Data (exemplos)

Quote:
```json
{
  "type": "Quote",
  "symbol": "XAUUSD",
  "bid": 2350.12,
  "ask": 2350.45,
  "last": 2350.28,
  "volume": 1234.5,
  "high": 2355.00,
  "low": 2345.00,
  "change_pct": 0.15,
  "timestamp": "2026-09-12T23:30:00Z",
  "source": "mt5"
}
```

AccountInfo:
```json
{
  "type": "Account",
  "login": "12345678",
  "balance": 10000.00,
  "equity": 10050.00,
  "margin": 500.00,
  "free_margin": 9550.00,
  "leverage": 100,
  "server": "MetaQuotes-Demo",
  "currency": "USD",
  "profit": 50.00
}
```

Position:
```json
{
  "type": "PositionUpdate",
  "ticket": 123456789,
  "symbol": "XAUUSD",
  "side": "buy",
  "volume": 0.1,
  "open_price": 2345.00,
  "current_price": 2350.28,
  "sl": 2335.00,
  "tp": 2365.00,
  "profit": 52.80,
  "open_time": "2026-09-12T20:00:00Z",
  "magic": 2026001
}
```
