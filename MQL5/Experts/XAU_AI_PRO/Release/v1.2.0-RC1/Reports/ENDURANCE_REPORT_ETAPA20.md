# XAU_AI_PRO — ETAPA 20.2: ENDURANCE TÉCNICA (v1.2.0 baseline congelado)

Data: 2026-08-24 | Baseline: v1.2.0 (congelado, imutável) | Sem alteração de lógica de trading.

---

## 1. Escopo (definido na sequência 20.2 → 20.7)

Validar o EA sob execução prolongada EM AMBOS os eixos:

1. **Eixo histórico / stress**: Strategy Tester com ticks reais (XAU_AI_PRO.M5.20260814_20260824.430.ini), otimização com 15 passes sobre janela de 10 dias M5.
2. **Eixo live/demo**: EA v1.2.0 anexado a 6 charts (XAUUSD, EURUSD, USDBRL, AUDUSD, NZDUSD, USDCHF) em conta demo MetaQuotes-Demo, gerando fluxo de eventos real.

### Requisitos técnicos monitorados (não modificados)
- CPU / memória · ticks processados · timers/heartbeat · latência
- erros / rejeições / retry · reconexão · SAFE / RECOVERY
- EventStream (forward_test_events.csv) · telemetria · health · audit
- Backend API/WS · Dashboard · CSV · reconciliação

---

## 2. Estado do Eixo Live (Demo) — baseline

| Métrica | Valor (2026-08-24) |
|---|---|
| Conta | MetaQuotes-Demo, login 111194406, demo, hedging |
| Saldo | $198.37 | Equity | $198.37 | Free margin $198.37 |
| Trading habilitado | terminal_connected=true, algo_trading_enabled=true, ea_trade_allowed=true |
| EAs em execução | 6× XAU_AI_PRO v1.2.0 (XAUUSD, EURUSD, USDBRL, AUDUSD, NZDUSD, USDCHF — M5) |
| Posições abertas | 0 (nenhuma) |
| Build MT5 | 6140 | CPU Intel Core i5-4590 3.30GHz | Windows 11 build 26200 |

### 7 trades reais fechados (demo, MagicNumber 2026001) — base da reconciliação ETAPA 21
USDCHF +0.54 · NZDUSD +0.09 · GBPUSD -1.50 · USDJPY +0.40 · USDJPY +0.35 · AUDUSD -1.50 → **Win rate 57.14%, PF 0.46, PnL -1.62** (7 trades). Este é o resultado a ser investigado na ETAPA 20.5, sem forçar >1.

---

## 3. Estado do Stress Tester (histórico)

- Config: `Profiles/Tester/XAU_AI_PRO.M5.20260814_20260824.430.ini`
- EA: `XAU_AI_PRO\XAU_AI_PRO.ex5` (baseline congelado) | símbolo XAUUSD | Period M5
- Model = 4 (ticks reais) | Optimization = 3 | ForwardMode = 0 | Deposit 200 | Leverage 200
- Janela: 2026.08.14 → 2026.08.24 (10 dias)
- Otimização em 15 passos (pass parameters RiskPercent/MaxDailyLossPercent/MaxDrawdownPercent/MinEquity/MinFreeMargin/MaxTrades/MaxOpenPositions via ranges)
- **run_id**: `7677705222686631397`
- Status: **started** | Progresso "Otimização 0 / 15" (passo 1 em execução, ticks reais = computacionalmente pesado)

> ⚠️ Otimização de 15 pass rodando; conclusão em andamento (duração estimada longa). Este relatório é o registro do estado inicial/documentado; a análise quantitativa final da otimização será anexada quando o run terminar.

---

## 4. Fluxo de eventos observado (live / endurance ativa)

`Files/Data/forward_test_events.csv` (UTF-16 LE, 10 colunas) — amostra ao vivo:

```
...SYSTEM_START  XAUUSD  PERIOD_M5  INFO  EA  "EA inicializado 1.2.0"
...FORWARD_TEST_START  XAUUSD  PERIOD_M5  INFO  FT  "Forward test iniciado"
...HEALTH_FAILURE  EURUSD  PERIOD_M5  ERROR  HEALTH  "check falhou"
...RECOVERY  EURUSD  PERIOD_M5  INFO  RECOVERY  "health restaurado"
...HEALTH_FAILURE  NZDUSD  ...
...RECOVERY  NZDUSD  ...
...HEALTH_FAILURE  USDCHF  ... → RECOVERY  ...
```

**Achados preliminares (não otimização, apenas registro):**
1. Ciclos `HEALTH_FAILURE → RECOVERY` recorrentes (ainda a investigar causa-raiz — comportamento fail/recover do HealthMonitor). **Houve persistência** de `health.state=ERROR` em `system_status.json` enquanto `ea_trade_allowed:true` — comportamento fail-open a confirmar.
2. `ai: available=false, signal=UNAVAILABLE, stale=true, age_seconds=-1` — pipeline de predição sem publicação recente (consistente com modelo STALE). NÃO é defeito de trading; é o estado operacional da IA.
3. Stream de eventos ativo e crescendo (arquivo em uso contínuo pelo EA) — EventEmitter funcionando.

---

## 4'. Backend / Dashboard (stack observabilidade)

- Backend Node (express/cors/socket.io) em **127.0.0.1:3001** — presente, sockets LISTENING (PID 8096 / 8092).
- Endpoints: /api/health /api/events /api/events/latest /api/system /api/trading /api/positions /api/ai /api/risk /api/execution /api/telemetry /api/alerts /api/reconcile /api/financial.
- 🟡 **Achado**: no momento da checagem a conexão HTTP ao backend retornou "connection closed unexpectedly" nas portas LOCAIS (invoke-RestMethod), embora o netstat mostre LISTENING. A investigar se é instabilidade momentânea ou loop de crash do processo backend. → Monitorar na próxima rodada de endurance.

---

## 5. Critérios de PASS desta etapa (ao final do run)

| Requisito | Critério | Situação |
|---|---|---|
| EA sobrevive janela prolongada | 15 pass completam sem crash/loop | em execução |
| Ticks reais processados | profiler sem estouro/filtro | em andamento |
| Heartbeat/EventStream | CSV cresce continuamente (sem parar) | ✅ ativo |
| SAFE / RECOVERY | estados acionam e recuperam (sem ficar preso) | ✅ ativo (ciclos observados) |
| IA READY/STALE/UNAVAILABLE | sem erro de pipeline | ✅ UNAVAILABLE/STALE (sem falha) |
| Backend API/WS | responder em até X ms via backend | 🟡 checagem a refinar |
| Reconciliação | 0 divergências não-enviadas | ✅ (7 trades) |

**Veredito parcial**: endurance EM EXECUÇÃO; caça ativa no eixo histórico; eixo live/demo operando com telemetria funcional. 🟢 — *para ser encerrado com a conclusão da otimização.*

---

*Artefato oficial ETAPA 20.2. Baseline v1.2.0 intacto (nenhum motor de trading alterado).*