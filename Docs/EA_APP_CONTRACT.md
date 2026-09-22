# Contrato EA - Gateway - App

O EA permanece como autoridade final das operações. O app solicita e monitora; não duplica a lógica de execução.

## Estado enviado pelo EA

- `EA_STATUS`: modo, conexão, AutoTrading, versão e erro atual.
- `HEARTBEAT`: timestamp, uptime, latência e último ciclo.
- `MARKET_STATE`: ativo, timeframe, bid, ask, spread e liquidez.
- `INDICATORS`: EMA, SMA, VWAP, RSI, MACD, ATR, ADX, volume e estrutura.
- `AI_SIGNAL`: direção, confiança, modelo, versão, timestamp e validade.
- `RISK_STATE`: risco percentual, lote, margem, drawdown e limites diários.
- `POSITION_STATE`: ticket, lado, volume, entrada, preço atual, SL, TP e resultado.
- `AUDIT_EVENT`: decisão, motivo, regra aplicada e resultado.

## Comandos aceitos pelo EA

Todo comando deve conter `request_id`, `timestamp`, `symbol`, `source`, `confirm_mode` e `reason`.

- `SYNC_STATE`
- `SET_MODE`
- `SET_SYMBOL`
- `SET_TIMEFRAME`
- `PAUSE_TRADING`
- `RESUME_TRADING`
- `REQUEST_ENTRY`
- `REQUEST_CLOSE`
- `REQUEST_BREAKEVEN`
- `REQUEST_TRAILING`
- `EMERGENCY_STOP`

O EA deve responder `COMMAND_RESULT` com `accepted`, `rejected` ou `executed`, incluindo `request_id`, retcode e motivo. Nenhum comando pode ignorar risco, AutoTrading, margem ou trava de emergência.
