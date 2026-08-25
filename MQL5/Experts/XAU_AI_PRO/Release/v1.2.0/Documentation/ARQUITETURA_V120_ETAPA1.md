# ARQUITETURA XAU_AI_PRO — MAPEAMENTO ETAPA 1 (21/08/2026)

**Baseline:** v1.2.0 (auditoria de 18/08) + correções v1.2.1/v1.2.2 desta sessão.
**Escopo:** inventário completo, grafo de dependências, símbolos públicos, órfãos e anomalias.
**Regra da etapa:** NENHUMA alteração de comportamento — apenas mapeamento.

---

## 1. VISÃO GERAL

| Camada | Módulos .mqh | Papel declarado |
|---|---|---|
| Raiz | XAU_AI_PRO.mq5 + Utils.mqh | Orquestrador (OnInit/OnTick/OnTimer/OnTradeTransaction) |
| Core | 22 | Config, sinais, validação, execução, posição, risco, símbolos |
| AI | 8 | Engine, connector Python, dataset, pesos adaptativos |
| Indicators | 5 | ADX, RSI, ATR, TrendStrength, VolatilityFilter |
| Filters | 6 | Spread, Session, Trend, MTF, News, MarketRegime |
| Management | 4 | BreakEven, DailyRisk, EquityProtection, PortfolioManager |
| Monitoring | 14 | Dashboard, stats, health, watchdog, checklists |
| Enterprise | 26 | Execução smart, retry, safety, recovery, telemetria, etc. |
| **Total** | **~86 arquivos** | |

**Dependência externa:** `MQL5\Include\KCI\` (KCI_Volatility_Distance, KCI_Directional_Matrix) — usada por DecisionEngine, DataLogger (AI) e via iCustom (tester_indicator implícito).

## 2. GRAFO DE DEPENDÊNCIAS (resumo do fluxo real)

```
XAU_AI_PRO.mq5 (53 includes diretos)
 ├─ Trade.mqh (biblioteca padrão MT5)
 ├─ Core/SystemManager -> CompatibilityManager -> BrokerInfo/BrokerConfig/SymbolManager/Path/Env/TimeFrame
 ├─ Core/Config.mqh (fonte única dos inputs)
 ├─ Indicators/* (ATR, ADX, RSI, TrendStrength, VolatilityFilter)
 ├─ Filters/* (Spread, Session, Trend, MTF, News)
 ├─ AI/* (AIClient, AIConnector, AIEngine->SignalCore+AdaptiveWeights+AILearningMemory, Dataset, DataLogger->KCI)
 ├─ Core/SignalCore -> DecisionEngine(->ValidationEngine+KCI+AIEngine) -> ValidationEngine(->Filters+ADX+AIEngine)
 ├─ Core/RiskEngine(->DailyRisk), ExecutionEngine(->OrderManager+PositionManager+TradeController+SmartExecution+SimulationEngine)
 ├─ Core/MarketScanner(->SignalCore+ValidationEngine+ExecutionEngine+PositionManager+AIEngine)
 ├─ Core/SymbolManager (SymbolSelect/tradeable/pending)
 ├─ Management/* (BreakEven, DailyRisk, EquityProtection, PortfolioManager)
 ├─ Monitoring/* (Dashboard, TradeLogger, PerformanceAnalyzer, Statistics)
 └─ Enterprise/* (SafetyManager, CircuitBreaker, RecoveryManager, SmartExecution(->AntiLoop+VolumeValidator+MarginChecker+OrderRetry+ExecutionQuality+ExecutionStats+PositionSynchronizer+BrokerAnalyzer), TradeMonitor, Scheduler, DatabaseManager, Telemetry)
```

**Observação estrutural:** `Utils.mqh` inclui Config + TrendStrength + VolatilityFilter e contém resolução de símbolos que DUPLICA o papel do SymbolManager (candidatos/sufixos). Ponto de conflito potencial.

## 3. ÓRFÃOS CONFIRMADOS (20 módulos nunca incluídos — código morto hoje)

| # | Arquivo | Camada | KB | Classificação proposta |
|---|---|---|---|---|
| 1 | AdvancedAI.mqh | AI | 2.7 | Avaliar integração (usa AIEngine) ou remover |
| 2 | EquitySurvival.mqh | Core | 1.1 | Avaliar (proteção equity alternativa) |
| 3 | ExecutionTracker.mqh | Core | 1.1 | Remover ou fundir com ExecutionStats |
| 4 | APILayer.mqh | Enterprise | 4.8 | Morto — API externa não usada |
| 5 | AutoCalibration.mqh | Enterprise | 4.8 | Avaliar (calibração automática) |
| 6 | BackupManager.mqh | Enterprise | 13.8 | Ativar OU mover p/ morto (Scheduler podia usá-lo) |
| 7 | BenchmarkEngine.mqh | Enterprise | 5.8 | Relacionado à Etapa 8 (backtesting) |
| 8 | ConfigManager.mqh | Enterprise | 11.6 | Conflita com Config.mqh — decidir fonte única |
| 9 | EventManager.mqh | Enterprise | 3.2 | Morto |
| 10 | NotificationCenter.mqh | Enterprise | 6.6 | Potencial push/alertas — avaliar |
| 11 | PluginSystem.mqh | Enterprise | 4.3 | Morto (arquitetura de plugins nunca ativa) |
| 12 | VersionManager.mqh | Enterprise | 7.5 | **Ativar** (versionamento central — hoje manual) |
| 13 | MarketRegime.mqh | Filters | 4.7 | **Candidato forte à Etapa 3** (regime de mercado) |
| 14 | AuditLog.mqh | Monitoring | 6.2 | Fundir com log de auditoria existente |
| 15 | BacktestAnalyzer.mqh | Monitoring | 6.5 | Etapa 8 |
| 16 | FailSafe.mqh | Monitoring | 10.0 | **Avaliar ativação** (ENUM_ROBOT_MODE) |
| 17 | FullAudit.mqh | Monitoring | 9.5 | Ferramenta de auditoria pontual |
| 18 | ProductionChecklist.mqh | Monitoring | 15.1 | Ferramenta de release (etapa final) |
| 19 | ReplayEngine.mqh | Monitoring | 8.0 | Etapa 8 (replay de trades) |
| 20 | ValidationChecklist.mqh | Monitoring | 8.1 | Ferramenta de validação pontual |

## 4. ANOMALIAS E CONFLITOS DETECTADOS

| # | Anomalia | Risco | Ação proposta |
|---|---|---|---|
| A1 | `Trend Flasher_AK.mq5` (EA de terceiro, 13.8KB) dentro da pasta | Compilação/organização | Mover fora da pasta do projeto |
| A2 | Dois `PerformanceAnalyzer` (Core 3.6KB órfão vs Monitoring 15KB em uso) | Colisão de nomes/confusão | Renomear/remover o órfão |
| A3 | `Utils.mqh` duplica lógica de resolução de símbolo do SymbolManager | Comportamento divergente | Unificar na Etapa 2 |
| A4 | 6 mecanismos de log/observação (DataLogger, Logger, TradeLogger, Telemetry, DatabaseManager, AuditLog) | Observabilidade fragmentada (Etapa 9) | Consolidar contrato único |
| A5 | `Config.mqh` (inputs) vs `ConfigManager.mqh` (órfão, perfis) | Duas fontes de verdade potenciais | Decidir arquitetura de config |
| A6 | Includes `KCI\...` apontam para Include global (fora do projeto) | Build depende de pasta externa | Documentar/versionar dependência |
| A7 | `prediction.json` solto na raiz Experts (além de Data\) | Lixo legado | Remover após confirmar |
| A8 | Stats diários (TradesToday/DailyProfit) em memória — resetam a cada reinit | Limite diário burlado por queda de rede | Upgrade: persistir em GlobalVariable |
| A9 | Versão nos fontes ainda "1.2.0" apesar das correções v1.2.1/v1.2.2 | Rastreabilidade | Bump oficial na release final |
| A10 | OnTick chama RunTradePipeline a cada tick com verbose ligado (~1MB/min de log) | Disco I/O / ruído | Gate por vela + verbose off em produção |

## 5. ESTADO OPERACIONAL NO CONGELAMENTO

- Terminal build 6120, conta demo MetaQuotes 111194406 (hedging), Algo Trading ON.
- 3 instâncias: XAUUSD/EURUSD/AUDUSD H1, inputs carregados com AutoTrade=true.
- Posição aberta: USDCHF SELL 0.01 (ticket 10153586005).
- Correções vigentes compiladas: cap anti-loop SymbolManager + sem pending espúrio (v1.2.1); filtro MagicNumber + dedup de deals + guard inter-instância de envio (v1.2.2).
- Fontes compilam com 0 erros / 0 warnings.

## 7. RESOLUÇÕES APLICADAS (21/08/2026 — Etapa 2 Parte 1)

- A1 ✅ RESOLVIDO: Trend Flasher_AK.mq5 movido para backup.
- A3 ✅ RESOLVIDO: Utils.mqh removido do build (provado morto — 19/20 funções sem uso; compila 0 erros sem ele).
- A7 ✅ RESOLVIDO: prediction.json da raiz movido para backup.
- Órfãos mortos movidos para `MQL5\Files\Backup\XAU_AI_PRO_orfaos_v122\` (reversível): APILayer, PluginSystem, EventManager, ExecutionTracker + Utils + Trend Flasher + prediction.json + mqproj.bak.
- Órfãos mantidos no projeto para etapas futuras: VersionManager (release), MarketRegime (Etapa 3), FailSafe, BackupManager, NotificationCenter, AutoCalibration, AdvancedAI, EquitySurvival, BenchmarkEngine, BacktestAnalyzer, ReplayEngine, FullAudit, ProductionChecklist, ValidationChecklist, AuditLog, ConfigManager (decisão de config na Etapa 2 Parte 2).
- Detalhes completos: `MQL5\Files\AUDITORIA_ETAPA2_P1.md`.

## 8. PRÓXIMOS PASSOS (ETAPA 2 — auditoria código a código)

Ordem por prioridade de risco:
1. Core/Config + SymbolManager + Utils.mqh (fonte de verdade e gate de execução)
2. Core/DecisionEngine + ValidationEngine + Filters (por que entra/não entra)
3. Hierarquia de risco: RiskEngine + DailyRisk + EquityProtection + SafetyManager + CircuitBreaker (base da Etapa 3)
4. Enterprise/SmartExecution + OrderRetry + AntiLoop + PositionSynchronizer (base da Etapa 7)
5. AI/* (Etapa 5) e Monitoring/* (Etapa 9)