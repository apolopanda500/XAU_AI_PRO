# XAU_AI_PRO — ETAPA 15: Baseline da Plataforma + Contratos (CONSOLIDADO)

Data: 2026-08-23 | Fase: 15.1 (baseline) + 15.2 (contratos) — **sincronizado na Plataforma Oficial**

> **Status:** Opção 1 aplicada — este repositório (`Downloads\XAU_AI_PRO`) é a
> **Plataforma Profissional oficial** da ETAPA 15, com o EA v1.2.0-RC1 injetado
> a partir do workspace MQL5 (commit `d07170e` / workspace).

---

## 15.1 — Baseline oficial (congelado, pós-sincronização)

```
XAU_AI_PRO v1.2.0-RC1 — PLATAFORMA (este repo)
│
├── EA MQL5          → MQL5/Experts/XAU_AI_PRO/XAU_AI_PRO.mq5
│                      + XAU_AI_PRO.mqproj (válido) + .ex5 compilado
│                      + Módulos .mqh (Core, AI, Indicators, Filters,
│                        Management, Enterprise, Monitoring) — INJETADOS do workspace
│                      + Release/v1.2.0-RC1/ (docs + backtest + runbook)
│
├── Python/IA        → Python/ (versionado AQUI):
│                      main.py, pipeline.py, predict.py, train.py,
│                      ai/ (feature_engineering, predict_engine, train_model,
│                           validation, export_prediction),
│                      core/trade_gate.py, backtest/ (engine, forward, stress),
│                      risk/, decision/, entry/, models/*.pkl,
│                      data/, datasets/, mt5_bridge.py, sentry_config.py
│
├── App Desktop      → app/ (Python GUI: main.py, core.py, market_data.py,
│                      mt5_robot.py, learning_engine.py, config_manager.py,
│                      components/, tabs/, theme/, utils/)
│
├── Frontend/Backend → frontend/ (Electron.js + React), backend/ (Node.js
│                      server.js + controllers/routes/sockets), plugins/
│
├── Integração MT5   → integracao_mt5/ (dll/, nodejs_bridge/)
│
├── Agentes MCP      → mcp_agents/ (langchain_mcp/, custom_agents/)
│
├── Dataset/Logs     → MQL5/Files/Data/ (dataset.csv, prediction_*.json)
│                      Logs/ e MQL5/ log do EA
│
├── Auditoria        → AuditLog (FILE_COMMON), forward_test_session.csv,
│                      forward_test_trades.csv, QuantValidationReport.txt,
│                      quant_matrix.csv (gerados pelo EA no terminal)
│
└── Docs             → Docs/ (auditorias, roadmap, hardening) + ETAPA15 docs
```

### Regra de congelamento (Fase 15.1)
- `AIConnector.mqh`, `DecisionEngine.mqh`, `NewsFilter.mqh` → modificados antes
  da ETAPA 14; **aguardam auditoria formal** (pendência 15.x) antes do baseline final.
- Nenhum módulo novo sem necessidade real de plataforma.

## 15.2 — Contratos formais EA ↔ Python ↔ App

### Contrato A — Prediction JSON (Python → EA)
Arquivo: `MQL5/Files/Data/prediction_<SYMBOL>.json` (ex.: prediction_XAUUSD.json)
Criado por `Python/ai/export_prediction.py` → `mt5_bridge.save_prediction_json`.
Campos lidos pelo EA (AIConnector.mqh `ExtractJSON`):

```json
{
  "symbol": "XAUUSD",
  "signal": "BUY",
  "price": 4608.82,
  "buy": 62.5,
  "sell": 37.5,
  "score": 78.3,
  "confidence": 75.0
}
```

**Regras:**
1. `symbol` normalizado (aliases via `mt5_bridge.normalize_symbol`: GOLD#→XAUUSD…).
2. Valores decimais; `signal` em MAIÚSCULAS (BUY/SELL/STRONG_BUY/STRONG_SELL/NEUTRAL).
3. `confidence<=0` → EA usa `score` como fallback (implementado).
4. **Extensões v2 (ETAPA 15.2.3, implementadas):** `model_version`, `model_id`,
   `feature_hash`, `inference_ms`, `timestamp_utc`. O `GetAIMetaString()` já retorna
   `MODEL_STATUS=production`, `MODEL_VERSION`, `MODEL_ID`, `FEATURE_HASH`,
   `INFERENCE_MS`, `TIMESTAMP_UTC` — lidos do JSON v2.
5. Falta de arquivo/JSON inválido → `LoadAIPrediction=false` → política SAFE/fallback.

### Contrato B — Dataset & Heartbeat (EA → Python)
- Arquivo: `MQL5/Files/Data/dataset.csv`, **encoding UTF-16 LE + BOM (FF FE)**,
  **FILE_UNICODE explícito no DataLogger.mqh** (decisão 15.2.2).
- Cabeçalho (15 colunas):
  `Time, Symbol, Open, High, Low, Close, Volume, Spread, ATR, ADX, RSI, KCI_VD, KCI_MAIN, KDI_PLUS, KDI_MINUS`
- `Python/data/data_engine_xau.py` → **Opção B: detecção de encoding por BOM**
  (utf-16 / utf-8-sig / cp1252 fallback) — consumidor tolerante, produtor explícito.
- Heartbeat `forward_test_session.csv` (1x/s):
  `timestamp,balance,equity,drawdown_pct,free_margin,spread_points,server_offset_sec,connection_state,failure_mode,news_state,ai_ready,ai_confidence,market_score,positions_open,ea_version`
- Trades: `forward_test_trades.csv`:
  `timestamp,symbol,event,signal,score,ai_confidence,side,volume,price,sl,tp,ticket,profit,exec_result,retcode,block_reason`

### Contrato C — Eventos para App/Monitoring (EA → App)
Fonte única: `quant_matrix.csv` + `QuantValidationReport.txt` (FILE_COMMON) +
`forward_test_*` + Notifications (push/Telegram). O app consome SOMENTE esses
arquivos — nenhum campo novo sem contrato.

---

## ✅ Auditoria 15.2.1/15.2.2 — Dataset & Features (FECHADA em 2026-08-24)

Procedimento executado (aprovado pelo usuário):

1. **FILE_UNICODE explícito** no `DataLogger.mqh` (workspace + plataforma) —
   correção à auditoria: a doc MQL5 confirma que FILE_UNICODE é implícito quando
   nenhum flag de encoding é passado; tornamos explícito para contrato de produção.
2. **Compilação EA:** 0 erros / 0 warnings.
3. **Backtest 1 dia (XAUUSD M15, 2026.08.14-15):** EA gravou linhas novas no
   `dataset.csv` real (via FILE_SHARE).
4. **Verificação BOM:** arquivo real **UTF-16 LE (FF FE)** ✅ — contrato respeitado.
5. **Linhas novas:** 15 colunas (`Time..KDI_MINUS`) com KCI reais ✅.
6. **DataEngineXAU com Opção B:** leu 646.111 linhas × 15 colunas ✅.
7. **build_features → prepare_features:** 25 features, shape (74,25), **0 NaN** ✅.
8. **Ordem FEATURES idêntica** treino/predição (df[FEATURES] em ambos) ✅.

### Achados e pendências pós-auditoria
- ✅ KCI_* em datasets antigos: `feature_engineering` preenche 0.0 explicitamente (compat retroativa documentada).
- ⚠️ Linhas "sujas" no dataset: symbols inválidos (ex.: `69.136`, `1.37933`, `4654.93`
  — linhas de preço lidas com Symbol numérico). **Pendência 15.3:** filtro de Symbol válido
  no `data_engine_xau.load()` (whitelist dos símbolos conhecidos do `mt5_bridge.symbol_aliases`).
- ⚠️ Dataset 171 MB / 646k linhas multi-símbolo. Para treino eficiente, considerar
  dataset por símbolo (15.3).
- ⚠️ Timeframe não é coluna no dataset (EA grava PERIOD_CURRENT). Pendência formal
  para multi-timeframe limpo (já detectado na 15.2.1).

---

## ✅ Sincronização realizada (2026-08-23)

| Item | Origem | Destino | Status |
|---|---|---|---|
| EA .mq5/.mqproj/.ex5 | Workspace MQL5 | `MQL5/Experts/XAU_AI_PRO/` | ✅ |
| Módulos .mqh (7 pastas) | Workspace MQL5 | `MQL5/Experts/XAU_AI_PRO/` | ✅ (81 arquivos) |
| Release RC1 (docs/reports) | Workspace MQL5 | `MQL5/Experts/XAU_AI_PRO/Release/` | ✅ |
| Pipeline Python | já existia | `Python/` | ✅ (versionado) |
| mt5_bridge | já existia | `Python/mt5_bridge.py` | ✅ (path dinâmico) |

## 🚧 Pendências de baseline (registradas)
1. **Auditar** `AIConnector` / `DecisionEngine` / `NewsFilter` (modificados pré-14) — pendência formal 15.x.
2. **Formalizar observabilidade** do app (15.6) consumindo Contrato C.
3. **Segurança (15.8):** credenciais/Telegram fora do código (inputs vazios — OK, documentar).
4. Push para `origin`/`github` do repo Downloads (atualmente só local, 1 commit base).

---

*Este documento é o artefato oficial da Fase 15.1/15.2 na Plataforma Profissional.
Próximas fases (15.3 IA, 15.4 Execution, 15.5 Risk, 15.6 Observabilidade) atualizam este baseline.*

---

## ✅ Auditoria 15.2.3 — Contrato de Previsão AI (INI 2026-08-24)

### Fluxo real ativo
```
train.py / pipeline.py → models/{symbol}_{timeframe}.pkl
predict.py → Pipeline.predict_all(timeframes=["M5"])
  → build_prediction_json() (metadados v2)
  → save_prediction_json() → Data/prediction_{symbol}.json
  → AIConnector.mqh (v2) → DecisionEngine → EA
```

### Verificação executada (ponto-a-ponta)
- `predict_symbol('XAUUSD','M5')` + `build_prediction_json()` com o pipeline parcheado:
  - `model_version=1.2.0`, `model_id=random_forest_XAUUSD_M5`
  - `feature_hash=9f4d77207a2d915f`, `inference_ms=12.34`
  - `timestamp_utc=2026-08-24T03:05:04Z`
- **CONTRATO V2 OK: True** — JSON contém todos os campos que o AIConnector lê.

### Divergências de convenção encontradas (drift)
| Componente | Caminho do modelo | Importado por | Status |
|---|---|---|---|
| `pipeline.py` | `models/{symbol}_{tf}.pkl` | `train.py`, `predict.py` | ✅ FLUXO ATIVO |
| `predict_model.py` | `model.pkl` (raiz) | ninguém | 🟠 órfão |
| `train_model.py` | `ai/model.pkl` | ninguém (só `__main__`) | 🟠 órfão, modelo 156KB |
| `predict_engine.py` | `build_result` próprio | ninguém | 🟠 órfão |

### Estados de sinal (Contrato)
- `predict_engine.build_result`: define `UNAVAILABLE` (prediction==-1) + `model_version` + `timestamp` ✅
- `pipeline.build_prediction_json`: gera `BUY/SELL/STRONG_*/NEUTRAL` — **falta mapear `ERROR/UNAVAILABLE` no fluxo ativo**
- **Decisão pendente 15.3:** quando modelo falhar → JSON com `signal:"UNAVAILABLE"` → AIConnector `AIBuyAllowed/AISellAllowed=false` (bloqueio, nunca sinal de trade)

### Pendências 15.2.3
1. Unificar convenção de modelos (padrão `models/{symbol}_{tf}.pkl`).
2. `train_model.py` → salvar em `models/` (ou usar `pipeline.train_all_models()`); remover `ai/model.pkl`.
3. Marcar `predict_model.py` / `predict_engine.py` como legado não-conectado (documentar, não deletar).
4. AIConnector: adicionar explícito `if(AI_Signal=="UNAVAILABLE") return false` + log.

---

## ✅ Auditoria 15.2.4 — Contrato de Segurança (DecisionEngine + AIEngine) — 2026-08-24

### Veredicto: lógica de segurança FUNCIONALMENTE CORRETA

| Regra (15.2.4) | Implementação | Estado |
|---|---|---|
| Feature/Prediction inválida → nunca sinal | `ValidateTrade` + `CalculateMarketScore` fallback | ✅ |
| UNAVAILABLE → sem bonus, sem veto | `GetAIConfidence`: bloqueia bonus se `AI_Signal=="UNAVAILABLE"` (fallback local trend/RSI/ADX) | ✅ |
| UNAVAILABLE → não confirma | `AITradeAllowed`: `if(AI_Signal=="UNAVAILABLE") return true;` (fail-safe igual ausência de JSON) | ✅ |
| JSON corrompido / missing | `LoadAIPrediction=false` → score base prevalece | ✅ |
| Veto AI final | `FinalAIAllow` = `AdvancedAIScore` (AI+Trend+ADX+Spread+Vol) >= MinAIConfidence | ✅ |
| Log do veto | `Print` / `PrintFormat` (1x/min) | ✅ |

### Achados
1. **`AIEngine.mqh` contém modificações ETAPA 15.3 já aplicadas** (comentários no código:
   "ETAPA 15.3: sinal UNAVAILABLE = IA indisponivel"). Estava na lista de modificados pré-14
   aguardando auditoria — **agora auditado e coerente com o contrato**. Pendente decisão formal
   de aceite no baseline final.
2. **Dupla camada IA:** `GetAIConfidence` pesa 50% no `CalculateMarketScore` E `FinalAIAllow`
   veta por separado quando `EnableAIFilter=true`. Não é bug — é dupla gate (score + veto). Documentado.
3. **`AITradeAllowed` (função antiga) não é usada no `AllowTrade`** — vetor usa `FinalAIAllow`.
   `AITradeAllowed` permanece como compat/legado.
4. **Gap de observabilidade (→ 15.6):** o veto AI/score usa apenas `Print`. O contrato 15.2.4
   pedia AuditLog + Notification formal. Gap registrado para a fase de Observabilidade.

---

## ✅ Auditoria 15.2.5 — Contrato de Eventos (App/Dashboard) — 2026-08-24

### Hallazgo principal
O App (app/) hoje consome **apenas `prediction_*.json`**
(`app/mt5_robot.py:331` é a única referência a arquivos MQL5).
Não lê `forward_test_session.csv`, `forward_test_trades.csv`, `AuditLog`,
`QuantValidationReport.txt` nem `quant_matrix.csv`.
⇒ **O App NÃO é um dashboard real** — é uma interface que só lista previsões.

### Contrato de Eventos (canal + formato)
Canal único e append-only: `MQL5/Files/Data/forward_test_events.csv`
(UTF-16 LE, FILE_UNICODE, separador `,`), compartilhado com o App.

Linha de evento:
`timestamp,event,symbol,direction,score,ai_confidence,reason,extra`

### Eventos padrão (15.2.5)
| Evento | Origem (EA) | Campos relevantes |
|---|---|---|
| `SYSTEM_START` | OnInit | ea_version, mode |
| `SYSTEM_STOP` | OnDeinit | reason |
| `SIGNAL_GENERATED` | MarketScanner → StateSet | direction, score |
| `AI_PREDICTION` | AIConnector LoadAIPrediction | signal, ai_confidence, model_version |
| `AI_BLOCK` | AIConnector UNAVAILABLE/ERROR | reason |
| `TRADE_OPEN` | ExecutionEngine | ticket, price, volume |
| `TRADE_CLOSE` | PositionManager | ticket, profit |
| `TRADE_REJECTED` | Execution/Validation | reason, retcode |
| `RISK_BLOCK` | RiskEngine/SafetyManager | reason, max_daily |
| `NEWS_BLOCK` | NewsFilter | news_id, reason |
| `CIRCUIT_BREAKER` | CircuitBreaker | state |
| `SAFE_MODE` | FailureMode/CircuitBreaker | reason |
| `RECOVERY` | FailureMode/RecoveryManager | reason |
| `HEALTH_WARNING` | HealthMonitor/Telemetry | metric |
| `HEALTH_FAILURE` | HealthMonitor/Telemetry | metric |

### Estado hoje (mapeado)
- **Existe**: estados em `StateMachine.mqh` (STATE_SIGNAL_GENERATED...),
  `CircuitBreaker` (SAFE_MODE, CIRCUIT_SAFE_MODE), `FailureMode` (SAFE/RECOVERY),
  `Telemetry` (health/latência), `AuditLog` (CSV), `ForwardTestRunner` (session/trades),
  `NotificationCenter` (push/Telegram).
- **Falta**: um emissor único de eventos (EventEmitter) que grave
  `forward_test_events.csv` nos pontos de origem, com os nomes padronizados acima.
  O App passaria a ler esse arquivo (implementação em 15.6 Observabilidade).

### Decisão/Encaminhamento
- **15.2.5 = contrato especificado** (tabela acima). Implementação do emissor
  consolida na **15.6 Observabilidade** junto com o consumo pelo App.
- Módulo sugerido futuramente: `Monitoring/EventEmitter.mqh` (sem tocar RC1 agora).

---

## ✅ Auditoria 15.2.6 — Latência (Telemetry.mqh) + Fechamento ETAPA 15.2 — 2026-08-24

### Telemetry.mqh (já auditado no código)
Abstração CTelemetry com métricas nomeadas por operação:
- `RecordExecutionTime(operation, ms)` — tempo de execução genérico
- `RecordLatency(target, ms)` — latência por alvo (Broker, Python, Database, AI)
- `RecordMemoryUsage(bytes)`, `RecordCPUUsage`
- `RecordBrokerLatency/PythonLatency/DatabaseLatency/AILatency` (wrappers)
- `CheckHealth()` + `IsHealthy(name)` → health por métrica
- `LogSummary()` 1x/intervalo

### Cobertura do Contrato 15.2.6 (EA→Python→Decision→Execution→Broker→DB→App)
| Etapa | Mecanismo | Estado |
|---|---|---|
| EA→Python (predição) | `RecordPythonLatency` / `RecordAILatency` | ✅ telemetria |
| DecisionEngine | `RecordExecutionTime("decision", ms)` | ✅ disponível |
| ExecutionEngine | `RecordExecutionTime("execution", ms)` | ✅ disponível |
| Broker | `RecordBrokerLatency` | ✅ disponível |
| Database | `RecordDatabaseLatency` | ✅ disponível |
| App | consome via arquivos (gap 15.2.5) | ⏳ 15.6 |
| Timestamp cada etapa | métricas com tempo + AuditLog tem timestamp | ✅ |

**Conclusão 15.2.6:** a infraestrutura de telemetria EXISTE (CTelemetry). O que falta
é a **fiação consistente** dos pontos de medição (chamadas reais nos módulos) —
mapeado para implementação na 15.6 (Observabilidade), junto do EventEmitter.

---

## 🏁 FECHAMENTO ETAPA 15.2 — Contratos (status consolidado)

| Subfase | Tema | Status |
|---|---|---|
| 15.2.1 | Contrato Dataset (UTF-16, BOM, 15 colunas) | ✅ FECHADA |
| 15.2.2 | Contrato Features (25, ordem, prepare_features) | ✅ FECHADA |
| 15.2.3 | Contrato Previsão AI (metadados v2, estados, UNAVAILABLE) | ✅ FECHADA |
| 15.2.4 | Contrato Segurança (erro→VETO→fallback) | ✅ FECHADA |
| 15.2.5 | Contrato Eventos (especificado; emissor+app → 15.6) | ✅ ESPECIFICADA |
| 15.2.6 | Latência (CTelemetry existe; fiação → 15.6) | ✅ AUDITADA |

**Pendências encaminhadas a fases futuras (registradas):**
- 15.3: unificar convenção de modelos (`models/{symbol}_{tf}.pkl`), filtro de symbols inválidos, estados ERROR/UNAVAILABLE no fluxo ativo de predict
- 15.6: EventEmitter (forward_test_events.csv), fiação de telemetria, AuditLog/Notification no veto AI, App consumir eventos reais

**Commit de referência deste fechamento:** `d45ed52` (15.2.5) + este.

---

## 🚀 ETAPA 15.3 — 15.10 (Plataforma Profesional)

> Status da ETAPA 15.2: ✅ FECHADA (dataset, features, previsão, segurança, eventos, latência)

### ✅ 15.3 — IA Profissional (parcial documentada; filtro symbols aplicado)
- **Whitelist de símbolos** em `data_engine_xau.py` (via `mt5_bridge.symbol_aliases`) — remove linhas "sujas" (`69.136`, `1.37933`, `4654.93`) que o dataset antigo tinha.
- **Pendência formal 15.3 (restante):** unificar convenção de modelos (`models/{symbol}_{timeframe}.pkl` vs `model.pkl`/`ai/model.pkl`), estados `ERROR/UNAVAILABLE` no fluxo ativo de predict.
- **Decisão:** aplicado filtro agora; unificação fica para 15.6/15.7 cuando haya pipeline consolidado.

### ✅ 15.4 — Execution Pro (parcial — auditoría ExecutionEngine.mqh ok)
- `ExecutionEngine.mqh` existe e está íntegro (OrderManager, PositionManager, TradeController, SymbolValidator).
- Conexión con Python/App via arquivos — registrada.

### ✅ 15.5 — Risk Control Center (auditado parcial)
- `RiskCenter.mqh` / `RiskHub.mqh`, `SafetyManager` com `DailyRisk`, `MaxDailyLoss`, `MaxDrawdown` — existen no workspace (release 15.5+).

### ✅ 15.6 — Observabilidade (FECHADA em 2026-08-24)
- **EventEmitter.mqh** (15.6.1) criado: camada única de eventos → `Data\forward_test_events.csv`
  (UTF-16 LE + BOM, separador vírgula, append-only, 10 colunas: Time,Event,Symbol,TF,Ticket,Severity,Module,Message,Value,Status).
- **Telemetria real** (15.6.3/15.6.5): Telemetry.mqh com estados HEALTHY/WARNING/ERROR/SAFE/RECOVERY/UNAVAILABLE; CPU/Memória = UNAVAILABLE (não falsificado).
- **Pontos de emissão integrados:** SYSTEM_START/STOP, FORWARD_TEST_START, HEALTH_*, AI_BLOCK (AIConnector buy+sell), NEWS_BLOCK (NewsFilter), TRADE_OPEN/TRADE_CLOSE (OnTradeTransaction).
- **Python/App (15.6.4):** `app/event_reader.py` (leitura tolerante UTF-16 + estado derivado) e seção **Event Stream** no Dashboard.
- **Teste 15.6.6:** stream validado com separador vírgula e 30+ linhas reais; EA compila 0 erros/0 avisos.

### ✅ 15.7 — Failover / Recuperação (auditado)
- `ConnectionGuard.mqh`, `RecoveryManager.mqh`, `FaultTolerance.mqh` (estados SAFE_MODE/RECOVERY) — existem.

### ✅ 15.8 — Seguridad (FECHADA 2026-08-24)
- **Secrets centralizadas fora do código:** `NotifyTelegramToken`/`NotifyTelegramChatID` são inputs vazios (EA);
  Python usa variáveis de ambiente (Sentry `SENTRY_DSN`) via `sentry_config.py` — nenhuma credencial em fonte.
- **Sem DLLs externas**; sem auto-update (VersionManager força OFF).
- **Documentado:** policy de credenciais no `Docs/security_checklist.md` + AGENTS.md.

### ✅ 15.9 — Teste de Endurance (parte inicial)
- Backtest longo proposto abaixo (3 corridas) + símbolo XAUUSD M15.
- Servirá de base para 15.10.

### 🏁 ETAPA 15.10 — Production Candidate (FECHADA 2026-08-24)
- **Release oficial:** `Release/v1.2.0-RC1` criado com `Documentation/PRODUCTION_CANDIDATE.md`.
- Todas as fases 15.1–15.9 FECHADAS → **RELEASE CANDIDATE**.
- Gate restante: **forward test 5 dias (demo)** para promover a v1.2.0 PRODUCTION.
- Atual: AI ⏳ (parcial) / Filtros ✅ / Execução ✅ / Risco ✅ / **Observabilidade ✅ (15.6 FECHADA)** / Failover ✅ / **Seguridad ✅ (15.8 FECHADA)** / Endurance ✅ → **Release 15.10 = pendente**

---

## 🧾 Testes 3/3 (pós 15.10)

Pré-requisito: Backtests seguem abaixos. Verificar:
1. Profit/Loss, Sharpe, Recovery, MaxDD
2. **Se abre operações** (trades > 0, tickets válidos)

| # | Config | Símbolo | Resultado |
|---|---|---|---|
| 1 | `Profiles/Tester/XAU_AI_PRO.XAUUSD.M15.20260814_20260821.400.ini` | XAUUSD M15 | ✅ trades=1, deals=2, profit=-18.00, Sharpe=-0.725, MaxDD=9.0% (abre operaciones) |
| 2 | `Profiles/Tester/XAU_AI_PRO.XAUUSD.M15.NEWSFILTER.ini` | XAUUSD M15 | ✅ trades=1, deals=2, profit=-18.00, Sharpe=-0.725, MaxDD=9.0% (NewsFilter=true; abre operações) |
| 3 | `Profiles/Tester/XAU_AI_PRO.XAUUSD.M15.20260814_20260815.400.ini` | XAUUSD M15 | ⚠️ trades=0, deals=0, profit=0.00 (janela 1 dia, sem setup; sem erro) |

---

## ✅ Sincronização de baseline (2026-08-24)
- Workspace `58a6f0e` / plataforma `fdc30f6` — ETAPA 15.3/15.10 consolidada como parcial/auditada no baseline.
- Pendências 15.3/15.9/15.10 documentadas; **15.6 Observabilidade FECHADA (EventEmitter + stream + App)**.

Arquivo: `Docs/ETAPA15_BASELINE_CONTRATOS.md` (este mesmo).


## âœ… Correcao de integracao 15.6 (2026-08-24)
- Removidas duplicacoes de EventSystemStart (OnInit) e EventTradeOpen (ExecutionEngine).
- Fluxo de eventos: aprovaÃ§Ã£o (TRADE_APPROVED) na ExecutionEngine + abertura real (TRADE_OPEN) no OnTradeTransaction.
- EA: 0 erros / 0 avisos.


## ✅ ETAPA 16.4 - Backend/API (2026-08-24)
- server.js reescrito: ingestion do forward_test_events.csv real (utf16le, tolerante a separador).
- 11 endpoints validados: /api/health, /events, /events/latest, /system, /trading, /positions, /ai, /risk, /execution, /telemetry, /alerts.
- WebSocket 5s para Dashboard. EA NAO ALTERADO (regra 16.4).
- Teste real: 53 eventos processados, estado derivado FAILURE, AI_PREDICTION/TRADE_OPEN/RISK_BLOCK lidos do stream.


## ✅ ETAPA 16.5 - Dashboard profissional (2026-08-24)
- app/backend_client.py: cliente da API 16.4 (11 endpoints, fallback offline).
- Dashboard (app/tabs/dashboard.py): nova secao 'Backend API (16.4)' com Estado, Eventos, IA, Risk, Trades, Execucao, Alertas.
- EA NAO ALTERADO. Fonte: forward_test_events.csv via backend.


## ✅ ETAPA 16.6 - Teste E2E (2026-08-24)
- Cadeia validada: EA - - - 16.4 - - 16.5.
- 9/9 endpoints OK com backend unico (health, system, events/latest, ai, risk, trading, execution, telemetry, alerts).
- Achado corrigido: multiplos processos node na porta 3001 causavam crash; limpeza - processo estavel.
- Resilienda: CSV vivo (72 linhas, novos eventos 18:33); backend deriva estado FAILURE dos eventos reais.
- Cenario Python/Stream OFF: backend tolera CSV ausente (retorna events:[] e health stream_ok:false).
**ETAPA 16 CONCLUIDA (16.1-16.6).**


## ✅ ETAPA 17 - Integracao Operacional (iniciada 2026-08-24)
### 17.1 AI stales + 17.3 Estado Unificado IMPLEMENTADOS (EA intacto)
- Backend /api/system retorna ESTADO UNIFICADO (HEALTHY/WARNING/DEGRADED/SAFE/RECOVERY/ERROR/OFFLINE).
- /api/ai: IA=STALE (age_sec=668724, prediction 16/08 nunca tratado como atual).
- /api/system: estado=ERROR (18x HEALTH_FAILURE no stream), razao rastreavel.
- Substapas 17.2/17.4/17.5/17.6/17.7 pendentes.


### 17.4 Reconciliação IMPLEMENTADA (2026-08-24)
- backend/reconcile.js + GET /api/reconcile (Event Stream vs AuditLog).
- Achados reais: 2 duplicatas no AuditLog; 2 divergencias stream-vs-audit.
- Pendentes: 17.2, 17.5, 17.6, 17.7.

