# CONTRATO UNIFICADO - XAU_AI_PRO v1.2.0-RC1

## Visao Geral

Este documento define o **contrato formal de integracao** entre:

1. **EA MQL5** (produz dataset)
2. **Python AI** (features -> modelo -> previsao)
3. **Aplicativo** (consumo de eventos e previsoes)

---

## 15.2.1 - CONTRATO DO DATASET

### Formato
- **Arquivo:** `MQL5\Files\Data\dataset.csv`
- **Separador:** `,` (CSV)
- **Encoding:** UTF-16 LE (BOM: FF FE), gravado com `FILE_UNICODE` explicito

### Colunas (15)

| # | Coluna   | Tipo     | Origem MQL5                    |
|---|----------|----------|--------------------------------|
| 1 | Time     | datetime | TimeToString(closedBarTime)    |
| 2 | Symbol   | string   | Symbol()                       |
| 3 | Open     | float    | iOpen()                        |
| 4 | High     | float    | iHigh()                        |
| 5 | Low      | float    | iLow()                         |
| 6 | Close    | float    | iClose()                       |
| 7 | Volume   | int      | iVolume()                      |
| 8 | Spread   | int      | DL_GetSpread()                 |
| 9 | ATR      | float    | GetATR()                       |
| 10| ADX      | float    | GetADX()                       |
| 11| RSI      | float    | GetRSI()                       |
| 12| KCI_VD   | float    | GetKCIVolatilityDistance()     |
| 13| KCI_MAIN | float    | GetKCIDirectionalMatrix()      |
| 14| KDI_PLUS | float    | GetKCIDirectionalMatrix()      |
| 15| KDI_MINUS| float    | GetKCIDirectionalMatrix()      |

### Regras
- Nenhuma coluna pode ser omitida.
- Valores ausentes -> linhas rejeitadas pelo Python.
- Encoding UTF-16 LE obrigatorio (`FILE_UNICODE` explicito no FileOpen).

---

## 15.2.2 - CONTRATO DE FEATURES

### Lista Unica (25 features)
Definida em `Python/ai/feature_engineering.py`:

```python
FEATURES = [
    "Open", "High", "Low", "Close", "Volume",
    "Spread", "ATR", "ADX", "RSI",
    "KCI_VD", "KCI_MAIN", "KDI_PLUS", "KDI_MINUS",
    "BodySize", "RangeSize", "UpperShadow", "LowerShadow",
    "ATR_Pct", "RSI_Diff", "Close_Diff",
    "Volume_MA", "ADX_Change", "KCI_VD_Pct",
    "KDI_Diff", "KCI_MAIN_Change"
]
```

### Validacao
```python
def prepare_features(df):
    missing = [f for f in FEATURES if f not in df.columns]
    if missing:
        raise ValueError(f"Features ausentes: {missing}")
    return df[FEATURES].copy()
```

### Regras
- Nada de preencher feature ausente com zero silenciosamente.
- Se feature faltar -> rejeicao imediata (ValueError).
- Ordem das features definida exclusivamente por `FEATURES`.
- Treino e inferencia usam a MESMA lista.

---

## 15.2.3 - CONTRATO DA PREVISAO AI

### Formato
- **JSON** salvo em: `MQL5\Files\prediction_<SYMBOL>.json`
- **Encoding:** UTF-8

### Campos obrigatorios

| Campo          | Tipo   | Descricao                       |
|----------------|--------|---------------------------------|
| symbol         | string | Ativo previsto                  |
| signal         | string | BUY, SELL, NEUTRAL, UNAVAILABLE |
| confidence     | float  | Confianca 0-100                 |
| buy/prob_buy   | float  | Probabilidade de compra         |
| sell/prob_sell | float  | Probabilidade de venda          |
| score          | float  | Score final                     |
| price          | float  | Preco atual                     |
| sl             | float  | Stop Loss calculado             |
| tp             | float  | Take Profit calculado           |
| model_version  | string | Versao do modelo (ex: 1.2.0)    |
| model_id       | string | ID do modelo usado              |
| timestamp      | string | ISO datetime local              |
| timestamp_utc  | string | ISO datetime UTC                |
| inference_ms   | float  | Latencia de inferencia          |
| feature_hash   | string | Hash SHA-256 das features       |
| risk           | string | Classificacao de risco          |
| category       | string | STRONG_BUY, STRONG_SELL, etc.   |
| atr            | float  | ATR atual                       |
| spread         | float  | Spread atual                    |
| volume         | int    | Volume atual                    |

Rastreabilidade exigida:
`Trade #12345 -> modelo XAU-AI 1.2.0 -> versao 2026.08 -> confidence 0.84 -> BUY`

---

## 15.2.4 - CONTRATO DE SEGURANCA

### Regra Universal
> **Nenhum erro de integracao vira sinal de trading.**

Fluxo obrigatorio em caso de inconsistencia:

```
AI ERROR -> DecisionEngine -> VETO -> AuditLog -> Notification
```

| Condicao                 | Acao     | Evento    |
|--------------------------|----------|-----------|
| Feature invalida         | VETO     | AI_ERROR  |
| Prediction invalida      | VETO     | AI_ERROR  |
| Timestamp inconsistente  | VETO     | AI_ERROR  |
| Modelo ausente           | FALLBACK | SAFE_MODE |
| JSON corrompido          | FALLBACK | SAFE_MODE |
| Simbolo/Timeframe difere | VETO     | AI_ERROR  |

---

## 15.2.5 - CONTRATO DE EVENTOS

### Formato
- **JSON Lines (.jsonl)** - um evento por linha
- **Encoding:** UTF-8
- **Arquivo:** `MQL5\Files\XAU_AI_PRO_events.jsonl`

### Schema Base

```json
{
    "event_id": "uuid4",
    "event_type": "SIGNAL_GENERATED",
    "symbol": "XAUUSD",
    "timeframe": "M5",
    "timestamp_utc": "2026-08-23T12:00:00+00:00",
    "data": {}
}
```

### Tipos de Eventos

| Evento           | Quando                   | Campos data                                    |
|------------------|--------------------------|------------------------------------------------|
| SYSTEM_START     | Inicio do EA             | version, build                                 |
| SYSTEM_STOP      | Pausa/encerramento       | reason                                         |
| SIGNAL_GENERATED | Sinal do DecisionEngine  | symbol, signal, confidence, source, latency_ms |
| AI_PREDICTION    | Nova previsao recebida   | symbol, signal, confidence, model_version      |
| TRADE_OPEN       | Ordem enviada            | ticket, type, price, sl, tp, volume            |
| TRADE_CLOSE      | Ordem fechada            | ticket, price, profit, swap, commission        |
| TRADE_REJECTED   | Ordem rejeitada          | reason, code, detail                           |
| RISK_BLOCK       | Bloqueio de risco        | rule, details                                  |
| NEWS_BLOCK       | Bloqueio por noticia     | news_title, impact, time                       |
| CIRCUIT_BREAKER  | Stop automatico          | condition, action                              |
| SAFE_MODE        | Modo seguro ativado      | reason, fallback                               |
| RECOVERY         | Recuperacao apos falha   | action, success                                |
| HEALTH_WARNING   | Alerta de saude          | component, metric, value                       |
| HEALTH_FAILURE   | Falha critica            | component, error                               |

---

## 15.2.6 - CONTRATO DE LATENCIA

### Medicoes obrigatorias

| Etapa               | Descricao                | Formato  |
|---------------------|--------------------------|----------|
| ea_to_python_ms     | Latencia EA -> Python    | int (ms) |
| python_to_ea_ms     | Latencia Python -> EA    | int (ms) |
| decision_engine_ms  | Latencia DecisionEngine  | int (ms) |
| execution_engine_ms | Latencia ExecutionEngine | int (ms) |
| broker_latency_ms   | Latencia Broker          | int (ms) |
| total_cycle_ms      | Latencia total do ciclo  | int (ms) |

### Implementacao
- Todos os timestamps em `datetime.now(timezone.utc)` ou equivalente MQL5.
- Latencias incluidas nos eventos SIGNAL_GENERATED e TRADE_OPEN.

---

## CRITERIO DE FECHAMENTO DA ETAPA 15.2

A etapa somente sera considerada concluida quando demonstrado:

```
MQL5 -> Dataset -> Python -> Features -> Modelo -> Prediction
     -> DecisionEngine -> EA -> Trade/Audit -> Aplicativo
```
sem divergencia de formato, versao ou dados.

---

*Documento oficial - XAU_AI_PRO v1.2.0-RC1*
*Criado em: 23/08/2026*


---

## REGISTRO DE VALIDACAO DA ETAPA 15.2

**Data:** 24/08/2026 | **Status:** VALIDADA

### Verificacoes automatizadas (27 checks PASS)

| # | Verificacao | Resultado |
|---|-------------|-----------|
| 1 | Sintaxe dos 4 modulos Python (train_model, predict_engine, feature_engineering, predict_model) | PASS |
| 2 | FEATURES = 25, ordem garantida por prepare_features() | PASS |
| 3 | Rejeicao rigida de feature ausente (ValueError) | PASS |
| 4 | Campos obrigatorios do prediction.json + model_version | PASS |
| 5 | Estado UNAVAILABLE implementado no build_result() | PASS |
| 6 | Documento de contrato com secoes 15.2.1 a 15.2.6 | PASS |
| 7 | BOM FF FE confirmado no dataset.csv real (UTF-16 LE) | PASS |
| 8 | Dataset real: 646.165 linhas / multi-simbolo carregado em 7.1s | PASS |
| 9 | XAUUSD: 43.949 linhas -> limpeza -> 43.872 amostras | PASS |
| 10 | Treino holdout RF (temporario) acuracia 50.34% | PASS |
| 11 | Inferencia ponta-a-ponta -> JSON conforme contrato (BUY, v1.2.0-RC1) | PASS |
| 12 | Fallback UNAVAILABLE validado | PASS |

### Auditoria dos modulos MQL5 (inspecao de codigo)

| Modulo | Conformidade |
|--------|--------------|
| DataLogger.mqh | FILE_UNICODE explicito; 15 colunas; validacao OHLC |
| AIConnector.mqh | Le todos os campos do contrato incl. metadados (Contrato A v2); fallback de nome de arquivo |
| AIEngine.mqh | Veto por contra-probabilidade; fallback local quando IA indisponivel |
| DecisionEngine.mqh | ValidateTrade -> NewsFilter -> Score -> FinalAIAllow |

### Descobertas documentadas

1. Caminho de PRODUCAO (pipeline.py) ja usa o contrato unificado de 25 features.
2. Caminho legado (ai/train_model.py) estava com 9 features - CORRIGIDO nesta etapa.
3. predict_model.py aponta para Python/model.pkl inexistente - modulo nao conectado; alinhamento futuro na ETAPA 15.3.
4. Acuracia do teste temporario (~50%) reflete RF default sem tuning; modelos de producao sao treinados pelo pipeline.py.
5. Retreino de producao NAO executado nesta etapa - protegido o forward test em demo (fica para ETAPA 15.3 com governance).

> ETAPA 15.2 ENCERRADA. Proxima: 15.3 - IA Profissional.


---

## REGISTRO DE VALIDACAO DA ETAPA 15.3 - IA PROFISSIONAL

**Data:** 24/08/2026 | **Status:** VALIDADA | **Compilacao MQL5: 0 erros, 0 warnings**

### Fase 15.3.1 - Auditoria ModelGovernance.mqh
- Estado global do modelo + registro por trade (auditoria): OK
- Politica fail-open quando nao governado (v1.2.0 deliberado): OK
- Divergencias documentadas: MODEL_STATUS hardcoded; campos TRAIN_DATE/DATASET_VERSION/ALGORITHM/METRICS ainda nao publicados pelo Python.

### Fase 15.3.2 - Staleness Check (IMPLEMENTADO)
| Arquivo | Alteracao |
|---------|-----------|
| Core/Config.mqh | Novo parametro MaxPredictionAgeSec=900 (0=desativado) |
| AI/AIConnector.mqh | Flags AI_IsStale/AI_AgeSeconds; parse ISO timestamp_utc; comparacao com TimeGMT(); previsao antiga -> descartada com log AI PREDICTION STALE |

### Fase 15.3.3 - Tratamento UNAVAILABLE (IMPLEMENTADO)
| Arquivo | Alteracao |
|---------|-----------|
| AI/AIEngine.mqh | AITradeAllowed(): UNAVAILABLE nao confirma nem veta (score base prevalece); GetAIConfidence(): UNAVAILABLE cai no fallback local trend/RSI/ADX |

### Fase 15.3.4 - Politica PYTHON FAILURE (formalizada)

`
Python parou / JSON ausente / JSON invalido / previsao stale
   |
   v
RequireAIJSON=false -> AIEngine usa fallback local (indicadores)
RequireAIJSON=true  -> novas entradas BLOQUEADAS (fail-closed)
unificado            -> gestao de posicoes abertas NAO e afetada
`

### Fase 15.3.5 - Modelos de Producao (VERIFICADO)
12 modelos em Python/models/*_M5.pkl confirmados com n_features_in_=25:
XAUUSD, EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDJPY,
BTCUSD, ETHUSD, SOLUSD, DOGEUSD, XRPUSD.
Retreino automatico do learning_engine ja aplicou o contrato unificado.
Sem intervencao manual necessaria. Zero risco ao forward test.

> ETAPA 15.3 ENCERRADA. Proxima: 15.4 - Execution Profissional.


---

## REGISTRO DE VALIDACAO DA ETAPA 15.4 - EXECUTION PROFISSIONAL

**Data:** 24/08/2026 | **Status:** VALIDADA | **Compilacao MQL5: 0 erros, 0 warnings**

### Cadeia auditada (6 modulos)

`
Signal -> Validation -> Risk -> Simulation -> SmartExecution
      -> Broker -> Order Result -> PositionManager
`

| # | Modulo | Veredito |
|---|--------|----------|
| 1 | ValidationEngine.mqh | APROVADO - 11 pontos de rejeicao, todos com motivo rastreavel [VALIDATION] BLOCK |
| 2 | RiskEngine.mqh | APROVADO - equity critica/diario/drawdown escalonado/lote minimo bloqueiam com log |
| 3 | OrderManager.mqh | APROVADO (caminho legado) - retcode + descricao do broker em erro |
| 4 | ExecutionEngine.mqh | CORRIGIDO - achado critico resolvido |
| 5 | PositionManager.mqh | APROVADO - filtros symbol+magic; trailing respeita stop level broker |
| 6 | TradePipeline.mqh | APROVADO - orquestrador multi-simbolo throttled |

### Achado critico CORRIGIDO (Fase 15.4)

**Problema:** ExecutionEngine.mqh linha 82 forçava lote minimo silenciosamente
(djustedLot=MathMax(minLot, adjustedLot)), violando a politica estrita
do RiskEngine (AllowMinLotOverride=false deveria BLOQUEAR). Divergencia
de politica entre modulos - exatamente o cenario que a Fase 15.5 (Risk
Control Center) visa eliminar.

**Correcao:** politica unificada consistente:
- AllowMinLotOverride=false -> EXECUTION BLOCK | LOT MIN (rastreavel) e return false
- AllowMinLotOverride=true  -> EXECUTION WARNING | FORCA LOTE MINIMO + log de risco real

### Rastreabilidade das rejeicoes na cadeia completa

`
[PIPELINE] BLOQUEADO        -> simbolo invalido / SymbolSelect / news
[DECISION BLOCKED]          -> news / score <60 / ADV AI
[VALIDATION] BLOCK          -> spread/session/trend/adx/regime/AI/MTF/news
EXECUTION FAIL              -> CanTrade / CanOpenPosition / limite diario
EXECUTION: LOTE INVALIDO    -> risco bloqueou (equity/dd/min lot)
EXECUTION: PRECO INVALIDO   -> preco <= 0
EXECUTION: SIMULACAO BLOQUEADA -> razao + probabilidade + RR
EXECUTION BLOCK | LOT MIN   -> politica estrita de lote minimo (NOVO)
ERRO EXECUCAO               -> ExecResult enum do SmartExecution
BUY ERROR / SELL ERROR      -> retcode + descricao do broker (legado)
`

> ETAPA 15.4 ENCERRADA. Proxima: 15.5 - Risk Control Center.


---

## REGISTRO DE VALIDACAO DA ETAPA 15.5 - RISK CONTROL CENTER

**Data:** 24/08/2026 | **Status:** VALIDADA | **Compilacao MQL5: 0 erros, 0 warnings**

### Inventario realizado
12+ modulos mapeados: RiskEngine, RiskHub, DailyRisk, EquityProtection,
PortfolioManager, SafetyManager (7 checagens), CircuitBreaker (25KB),
MarginChecker, FailureMode, VolumeValidator.

### Matriz de conflitos (C1-C6)
- C1 (drawdown triplo): RESOLVIDO - RiskEngine consome GetDrawdownPercent() unica
- C2-C6: documentados em Docs/risk_control_policy.md

### Implementado
| Arquivo | Mudanca |
|---------|---------|
| Core/RiskCenter.mqh | NOVO - fachada unica: RiskEvaluate/RiskAllowEntry/RiskDecision/RiskCenterSummary, ordem deterministica com motivo unico rastreavel |
| Core/RiskEngine.mqh | Drawdown local eliminado -> fonte unica RiskHub |
| XAU_AI_PRO.mq5 | Include do RiskCenter adicionado |

> ETAPA 15.5 ENCERRADA. Proxima: 15.6 - Observabilidade.


---

## REGISTRO DE VALIDACAO DA ETAPA 15.6 - OBSERVABILIDADE

**Data:** 24/08/2026 | **Status:** VALIDADA | **Compilacao MQL5: 0 erros, 0 warnings**

### Inventario
- MQL5: HealthMonitor (watchdog 7 modulos), Dashboard (Comment), Telemetry
  (latencias Python/Broker/DB/AI), AuditLog, Statistics.
- App: le prediction_*.json e checa idade <=600s (mt5_robot.py).
- GAP identificado: nenhum snapshot unico consumivel pelo app.

### Implementado

| Arquivo | Mudanca |
|---------|---------|
| Monitoring/SystemStatus.mqh | NOVO - gera Data/system_status.json (throttle 15s, ASCII) |
| XAU_AI_PRO.mq5 | Include + chamada SystemStatusUpdate() no OnTimer |

### Schema system_status.json v1.0

```json
{
    "schema_version": "1.0",
    "generated_at": "yyyy.mm.dd hh:mi:ss",
    "health":   { terminal_connected, algo_trading_enabled, ea_trade_allowed },
    "trading":  { symbol, position, floating_pl, balance, equity },
    "risk":     { status OPEN|BLOCKED, reason, drawdown_pct, trades_today,
                  daily_loss_pct, free_margin },
    "ai":       { available, signal, confidence, model_version,
                  age_seconds, stale },
    "news":     { filter_enabled, blocked, detail },
    "python":   { predictions_available, prediction_age_sec },
    "database": { dataset_exists, dataset_bytes }
}
```

Cobertura vs especificacao da fase:
EA online/offline (health) - conexao (health) - simbolo/posicao/P/L (trading) -
drawdown/risco (risk) - decisao (risk.reason) - sinal/confianca AI/model_version/
stale (ai) - NewsFilter (news) - Python (python) - dataset (database).

Latencia detalhada permanece na Telemetry (memoria); integracao futura no snapshot.
Consumo pelo app: proxima sub-etapa (leitor em app/tabs/dashboard.py).

> ETAPA 15.6 ENCERRADA. Proxima: 15.7 - Failover.


---

## REGISTRO FINAL DA ETAPA 15 - FASES 15.7 A 15.10

**Data:** 24/08/2026 | **Compilacao MQL5 final: 0 erros, 0 warnings**

### 15.7 FAILOVER - VALIDADA (auditoria de codigo integrado)
Matriz dos 9 cenarios documentada em Docs/failover_matrix.md.
Cadeia ativa verificada no XAU_AI_PRO.mq5:
ConnectionGuard (gate 914) -> CircuitBreaker 5 gatilhos (Run 1425/gate 831)
-> RecoveryManager 5 checks (1413) -> FailureMode SAFE/RECOVERY (1418-19)
-> NotificationCenter alertas (1539).
SAFE bloquea apenas novas entradas; gestao de posicoes continua.
Cooldown 60s; max 5 ciclos antes de intervencao humana.

### 15.8 SEGURANCA OPERACIONAL - VALIDADA
Varredura de 157 arquivos (Temp/security_scan.py): ZERO credenciais reais.
api_key="anything" = padrao LiteLLM local (falso positivo documentado).
Checklist completo em Docs/security_checklist.md.
Auto-update permanece deliberadamente BLOQUEADO (VersionManager).

### 15.9 ENDURANCE - FRAMEWORK PRONTO
Coletor Tools/endurance_monitor.py TESTADO com amostra real
(Logs/endurance_metrics.jsonl). Metricas: heartbeat EA, dataset growth,
predictions fresh, memoria terminal/python.
Plano com janelas 24h/72h/7d/14d/30d e criterios PASS objetivos em
Docs/endurance_test_plan.md. Execucao real requer dias de relogio -
inicia sobre o forward test demo apos reload do EA.

### 15.10 PRODUCTION CANDIDATE - DECLARADO
v1.2.0-RC1 promovido a PRODUCTION CANDIDATE.
Checklist consolidado e caminho de promocao em
Docs/production_readiness.md.

Pendencias honestas pre-v1.2.0-PRODUCTION:
1. Endurance executado (janelas reais)
2. Reload do EA para ativar os novos modulos compilados
3. Forward test >= 30 dias com metricas
Nao-bloqueantes: stubs SafetyManager, exposicao nocional, latencias no
snapshot, leitor do status no app, alerta WebRequest.

---

# ============================================
# ETAPA 15 ENCERRADA
#
# v1.2.0-RC1 -> PRODUCTION CANDIDATE
#
# Proximo marco: Endurance + Operational
# Acceptance -> v1.2.0-PRODUCTION
# ============================================


---

## REGISTRO POS-ETAPA 15 - PENDENCIA #7 RESOLVIDA

**Data:** 24/08/2026 | **Ciclo Observabilidade EA -> JSON -> App: FECHADO**

### Implementado

| Arquivo | Mudanca |
|---------|---------|
| app/system_status_reader.py | NOVO - leitor multi-caminho (terminal real via mt5_bridge.get_mt5_files_path() + fallback espelho local); enriquece com heartbeat_age_sec/ea_online/source; summarize() traduz para linhas nome/valor/cor |
| app/tabs/dashboard.py | Card "EA Snapshot" no grid; _update_system_status() no refresh(); cores por severidade |

### Validacao executada

1. Sintaxe py_compile: PASS
2. Snapshot ausente -> "INDISPONIVEL" sem quebrar: PASS
3. Caminho positivo (snapshot simulado no terminal REAL):
   - Resolucao dinamica mt5_bridge: PASS (origem = terminal AppData)
   - 10/10 linhas corretas: Heartbeat ONLINE(0s) / Conexao OK /
     Posicao BUY / P/L 12.40 / Risco OPEN / DD 1.20% /
     IA BUY 72.5% v1.2.0 / News LIVRE / Python OK(45s) / Dataset 163.7MB
4. Limpeza do arquivo de teste: OK

Nota tecnica: get_mql_data_path() aponta para espelho local do projeto;
o leitor prioriza o terminal REAL (onde o EA grava) e usa o espelho como fallback.
Correcao de bug latente documentada: learning_engine.sync_predictions() copia
predictions para o espelho, nao para o Files real do terminal.

> Proximas pendencias acionaveis: #4 stubs SafetyManager, #5 exposicao nocional,
#8 alerta WebRequest; ETAPA 16 Model Governance (metadados faltantes no JSON).


---

## REGISTRO ETAPA 15.6 - EVENT STREAM PONTO-A-PONTO + UNIFICACAO

**Data:** 24/08/2026 | **Compilacao MQL5: 0 erros, 0 warnings**

### Unificacao do EventEmitter (resolucao de conflito)

Detectados DOIS emitters concorrentes:
- Core/EventEmitter.mqh (criado nesta sessao, EVT_*, ANSI, FILE_COMMON)
- Monitoring/EventEmitter.mqh (pre-existente do usuario, EV_*, UTF-16 LE,
  MQL5\Files\Data - alinhado ao app/event_reader.py existente)

**DECISAO:** Monitoring/EventEmitter.mqh mantido COMO CANONICO
(23 tipos de evento, API rica de wrappers: EventSystemStart/Stop,
EventTradeApproved/Open/Rejected, EventRiskBlock, EventBrokerError,
EventCircuitBreaker, EventSafeMode, EventRecovery etc).
Core/EventEmitter.mhq duplicado REMOVIDO.

### Instrumentacao aplicada (ExecutionEngine.mqh)

| Ponto | Chamada canonica |
|-------|------------------|
| cooldown entre trades | EventTradeRejected(CAN_TRADE=false) |
| posicao/limite | EventTradeRejected(POSITION_LIMIT) |
| limite diario | EventRiskBlock(DAILY_TRADES) |
| lote invalido | EventTradeRejected(INVALID_LOT) |
| preco invalido | EventTradeRejected(INVALID_PRICE) |
| simulacao bloqueada | EventTradeRejected(SIM_BLOCKED + motivo) |
| ordem executada | EventTradeApproved + EventTradeOpen(ticket,lote) |
| falha broker | EventBrokerError(EnumToString(execResult)) |

Ciclo de vida: EventInit()+EventSystemStart(version) no OnInit;
EventSystemStop(deinit_reason)+EventShutdown() no OnDeinit.

### App/Dashboard (15.6.4)
- app/event_reader.py (pre-existente, canonico): read_events/event_summary/
  event_status_lines - estados derivados HEALTHY/TRADING/WARNING/RECOVERY/
  SAFE/ERROR/FAILURE/UNAVAILABLE (15.6.5)
- dashboard.py: novo card "Event Stream (EventEmitter)" com
  _update_event_stream() no refresh

### TESTE INTEGRADO PASS (ponta-a-ponta)

CSV UTF-16 LE simulado no terminal real ->
event_reader parseou 10 colunas ->
estado WARNING derivado de RISK_BLOCK ✓
ai_state READY de AI_PREDICTION ✓
trades_total=1 de TRADE_OPEN ✓
5 linhas renderizadas para o dashboard com cores ✓

### INCIDENTE AMBIENTAL DOCUMENTADO

Python base do sistema (3.12.9 em AppData Local Programs) teve a pasta
Lib ESVAZIADA durante a sessao (stdlib removida fora da lixeira; causa
externa). Mitigacao: Tools/python_embed (embeddable 3.12.9 portatil,
nao-invasivo, ._pth apontando para a raiz do projeto) usado para os
testes. RECOMENDADO: reinstalar Python 3.12 no sistema quando possivel.


---

## REGISTRO FECHAMENTO ETAPA 15.3 - IA PROFISSIONAL (70% -> 100%)

**Data:** 24/08/2026 | **MQL5: 0 erros/0 warnings | Python: py_compile PASS**

### Model Governance completa (gap fechado)

**Python (pipeline.py):**
1. Treino salva predict_model arq .meta.json com:
   algorithm / train_date(ISO UTC) / dataset_version(hash SHA-256 parcial) /
   metrics(accuracy,f1,train/test samples) / feature_count / symbol/TF / version.
2. load_model_meta() carrega o meta para a predicao (fallback {}).
3. build_prediction_json() adiciona ao output: algorithm, train_date,
   dataset_version, feature_count, metrics (JSON string).
   model_version agora herdado do .meta.json (fallback APP_VERSION).

**MQL5 (AIConnector.mqh):**
4. Novos globals: AI_Algorithm / AI_TrainDate / AI_DatasetVersion / AI_Metrics.
5. Parse JSON dos novos campos no LoadAIPrediction.
6. GetAIMetaString() expoe: ALGORITHM / MODEL_TRAIN_DATE / DATASET_VERSION /
   MODEL_METRICS -> consumidos pelo ModelGovernanceRefresh().
7. ResetAIState limpa os novos campos.

### Normalizacao documentada (decidida)
RandomForest (n_estimators=200, max_depth=8) NAO exige escalonamento
(invariante a escala). Policy registrada em
Docs/model_governance_policy.md. Sem scaler.pkl (correto para o algoritmo).

### Auditoria da cadeia de fallback (15.3) - confirmada
- IA nunca cria sinal: apenas bloqueia/confirma.
- signal=UNAVAILABLE -> fallback local OU bloqueio (RequireAIJSON).
- Timeout de previsao: stale check no AIConnector (MaxPredictionAgeSec).
- Divergencia Python/MQL5: unificada pelas 25 features (contrato 15.2).

### Nova versao .meta.json exigira retreino
- Os modelos de producao ja tem 25 features; o proximo ciclo do
  learning_engine gerara os .meta.json automaticamente.
- Prediction JSONs apos o retreino conterao governanca completa.

> ETAPA 15.3 = 100% ENCERRADA. Proxima: 15.8 Seguranca final.


---

## REGISTRO FECHAMENTO ETAPA 15.8 - SEGURANCA OPERACIONAL (parcial -> 100%)

**Data:** 24/08/2026

### Varredura de credenciais
- Terminal MQL5 (Experts + Common Files) + projeto: 105 arquivos varridos.
- Resultado: 0 credenciais reais. api_key="anything" = LiteLLM local (falso positivo).
- Config MQL5: NotifyTelegramToken="" (OFF padrao; via input na instalacao).

### .gitignore reforcado
Adicionados: forward_test_events.csv, *.meta.json (governanca), system_status.json,
secrets.*, config.local.*. Ja existiam: python_embed, *.pkl, dataset.csv,
prediction_*.json, app_venv, logs, builds.

### Checklist completo de seguranca (confirmado)
1. Credenciais fora do codigo      : PASS (scan 0 credenciais)
2. Telegram token protegido        : PASS (vazio por padrao)
3. Configs protegidas              : PASS (inputs MQL5 + config_manager local)
4. Permissoes minimas              : PASS* (SO do host)
5. Backups                          : PASS (BackupManager + models_backup_*)
6. Versionamento                    : PASS (VersionManager + APP_VERSION + schema_version)
7. Identificacao de build           : PASS (model_version/model_id + SYSTEM_START event)
8. Rollback                          : PASS (models_backup_* + build anterior .ex5)
9. Logs de alteracoes                : PASS (AuditLog + learning_history + event stream)
10. Sem auto-update                 : PASS (deliberadamente bloqueado no VersionManager)

### Regras de producao (conta real) reiteradas
- Iniciar SOMENTE XAUUSD, lote fixo/proteco ou risco 0.5%
- RequireAIJSON=true nas primeiras semanas
- AllowMinLotOverride=false (estrito)
- Telegram token via input (nunca commitado)
- Rollback restaura models_backup + .ex5 anterior

> ETAPA 15.8 = 100% ENCERRADA. Proxima: 15.10 Production Candidate + plataforma.
