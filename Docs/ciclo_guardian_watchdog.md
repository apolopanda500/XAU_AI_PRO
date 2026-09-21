# Ciclo Guardian / Watchdog / Fila / Telemetria (gap analysis, Fases 1–4)

## Variaveis de ambiente

| Variavel | Padrao | Efeito |
|---|---|---|
| `XAU_ENABLE_DEMO_ORDERS` | `0` | `1` libera comandos DEMO (Guardian, fila, reconciliacao) |
| `XAU_GATEWAY_TOKEN` | vazio | Token Bearer opcional exigido em todas as rotas (menos `/api/health` e docs) |
| `XAU_RATE_LIMIT` | `0` (ilimitado) | Leituras GET por minuto (gateway stdlib + FastAPI) |
| `XAU_RATE_LIMIT_CMD` | `0` (= `XAU_RATE_LIMIT`) | Comandos nao-GET por minuto, janela separada do polling |
| `XAU_GUARDIAN_INTERVAL` | `1.0` | Segundos entre ticks do Guardian Engine |
| `XAU_GUARDIAN_FILE` | `%APPDATA%\XAU_AI_PRO\guardian_rules.json` | Persistencia das regras do Guardian |
| `XAU_INTENT_FILE` | `%APPDATA%\XAU_AI_PRO\intents.jsonl` | Intent log append-only (Fase 2) |
| `XAU_TELEMETRY_INTERVAL` | `60` | Segundos entre snapshots de saude |
| `XAU_TELEMETRY_FILE` | `%APPDATA%\XAU_AI_PRO\telemetry_history.jsonl` | Historico JSONL de equity/posicoes/EA |
| `XAU_TELEMETRY_MAX_BYTES` | `2097152` (2 MB) | Rotacao simples do historico |
| `XAU_HEARTBEAT_TTL` | `120` | TTL (s) do heartbeat do EA para o watchdog |
| `XAU_QUEUE_FILE` | `%APPDATA%\XAU_AI_PRO\command_queue.json` | Fila persistente de comandos DEMO |
| `XAU_QUEUE_INTERVAL` | `5.0` | Segundos entre ciclos da fila |

## Rotas novas

| Rota | Gateway(s) | Descricao |
|---|---|---|
| `GET /api/guardian/status` | ambos | Regras ativas, estado e ultimo tick |
| `POST /api/guardian/set` | ambos | Ativa regra (breakeven, trailing fixed/step/ATR, parciais TP1–3, profit lock, time exit) |
| `POST /api/guardian/remove` | ambos | Remove regra (posicao continua aberta) |
| `POST /api/guardian/tick` | ambos | Forca um ciclo imediato |
| `GET /api/intents` | ambos | Ultimos intents consolidados |
| `POST /api/intents/reconcile` | ambos | Reconciliacao manual contra a conta |
| `GET /api/queue/status` | ambos | Fila offline (pending/sent/failed/skipped) |
| `GET /api/watchdog` | ambos | Estado do EA (alive/frozen/stale/missing/unknown) |
| `POST /api/watchdog/recovery` | ambos | Relatorio somente-leitura (sem acao automatica) |
| `GET /api/telemetry` | ambos | Eventos recentes (ring 500) |
| `GET /api/telemetry/history` | ambos | Snapshots de equity/posicoes/EA persistidos |

## Boot (backfill do primeiro ciclo)

1. `_ensure_mt5()` (stdlib) → reconciliacao de intents pendentes + evento `boot` na telemetria.
2. `snapshot_metrics("boot")` → primeiro ponto da curva de equity, mesmo com MT5 offline (campos `None`).
3. `boot_report()` (FastAPI) → mesmo backfill, impresso no log como `[gateway] boot: {...}`.
4. Loops idempotentes: `start_guardian_loop()` → `start_queue_loop()` → `start_telemetry_loop()`.

## Testes do ciclo

```powershell
.\.venv\Scripts\python.exe tests/test_guardian_smoke.py
.\.venv\Scripts\python.exe tests/test_watchdog_smoke.py
.\.venv\Scripts\python.exe tests/test_queue_smoke.py
.\.venv\Scripts\python.exe tests/test_telemetry_history_smoke.py
.\.venv\Scripts\python.exe tests/test_queue_gateway_integration.py
```
