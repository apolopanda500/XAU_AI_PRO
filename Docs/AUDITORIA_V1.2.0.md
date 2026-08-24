# AUDITORIA XAU AI PRO — v1.2.0 (18/08/2026)

**Auditor completo:** MetaTrader Assistant
**Data:** 18/08/2026 17:39 (GMT-3)
**Escopo:** EA MQL5 (Experts\XAU_AI_PRO) + Aplicativo desktop (C:\Users\Micro\Downloads\XAU_AI_PRO)
**Resultado geral:** CONSISTENTE — todos os módulos unificados na versão **v1.2.0**

---

## 1. DIAGNÓSTICO: por que o robô parou de abrir operações

| # | Causa | Evidência | Status |
|---|-------|-----------|--------|
| 1 | **AutoTrading do terminal DESLIGADO** (`experts_trade_allowed=false`) | Terminal API + Journal 18/08 | ⚠️ Requer ação do usuário (Ctrl+E) |
| 2 | **Input AutoTrade=0 nos 3 gráficos** (XAUUSD, EURUSD, AUDUSD) | Chart inputs (list_open_charts) | ⚠️ Requer ação do usuário (F7) |
| 3 | **Bug MQL5: input AutoTrade ignorado no OnTick** | `CheckTradingConditions()` nunca era chamada | ✅ Corrigido no código v1.2.0 |
| 4 | CircuitBreaker em SAFE MODE por conta do item 1 | `CheckBrokerError()` → `ACCOUNT_TRADE_ALLOWED=false` | ✅ Bloqueio correto (proteção); libera com item 1 |

**Conclusão:** o robô não abria operações porque o **AutoTrading do terminal estava OFF** e os inputs estavam com **AutoTrade=0**. Além disso, o input `AutoTrade` era ignorado pelo código (bug corrigido na v1.2.0).

---

## 2. AUDITORIA DE VERSÃO — EA MQL5 (Experts\XAU_AI_PRO)

### 2.1 Arquivo principal
| Arquivo | Antes | Depois |
|---------|-------|--------|
| XAU_AI_PRO.mq5 | v1.20 | **v1.2.0** (#property version "1.2.0") |

### 2.2 Módulos com versão corrigida (39 arquivos)
Cabeçalhos atualizados de v1.0/v1.1/v1.10/v1.20/v2.0 → **v1.2.0**:

- Core: Config, SignalCore, ValidationEngine, MarketScanner, ExecutionEngine, SymbolManager, CompatibilityManager
- AI: AIConnector, DataLogger
- Filters: MultiTimeframeFilter
- Enterprise: AntiLoop, APILayer, AutoCalibration, BackupManager, BenchmarkEngine, BrokerAnalyzer, CircuitBreaker, ConfigManager, DatabaseManager, EventManager, ExecutionQuality, MarginChecker, NotificationCenter, OrderRetry, PluginSystem, PositionSynchronizer, RecoveryManager, SafetyManager, Scheduler, SimulationEngine, SmartExecution, Telemetry, VersionManager, VolumeValidator
- Management: BreakEven
- Monitoring: FullAudit (#property 1.10→1.2.0), ProductionChecklist (#property 1.10→1.2.0), Statistics

### 2.3 Módulos com cabeçalho v1.2.0 adicionado (50 arquivos)
Utils.mqh, AI (AdaptiveWeights, AdvancedAI, AIClient, AIEngine, AILearningMemory, Dataset),
Core (BrokerConfig, BrokerInfo, DecisionEngine, EnvironmentManager, EquitySurvival, ExecutionTracker,
OrderManager, PathManager, PerformanceAnalyzer, PositionManager, RiskEngine, SymbolValidator,
SystemManager, TimeFrameManager, TradeController, TradePipeline), Enterprise (ExecutionStats, TradeMonitor),
Filters (MarketRegime, NewsFilter, SessionFilter, SpreadFilter, TrendFilter),
Indicators (ADX, ATR, RSI, TrendStrength, VolatilityFilter),
Management (DailyRisk, EquityProtection, PortfolioManager),
Monitoring (AuditLog, BacktestAnalyzer, Dashboard, Diagnostics, FailSafe, HealthMonitor, Logger,
PerformanceAnalyzer, ReplayEngine, TradeLogger, ValidationChecklist, WatchDog)

### 2.4 VersionManager.mqh
- Cabeçalho: v1.0 → **v1.2.0**
- `m_current.version`: "1.0.0" → **"1.2.0"**
- `changes`: "V1.2.0 - Production Ready"

### 2.5 Compilação
- Resultado: **0 erros, 1 warning** (warning 68: formato de versão "1.2.0" p/ MQL5 Market — inofensivo para uso local)
- .ex5 gerado: MQL5\Experts\XAU_AI_PRO\XAU_AI_PRO.ex5 (18/08 18:02)

---

## 3. AUDITORIA DE VERSÃO — APLICATIVO (C:\Users\Micro\Downloads\XAU_AI_PRO)

| Arquivo | Antes | Depois |
|---------|-------|--------|
| app/core.py (título janela) | v2.0 | **v1.2.0** |
| app/config_manager.py (app_version) | "2.0.0" | **"1.2.0"** |
| app/data/config.json (app_version) | "2.0.0" | **"1.2.0"** |
| app/main.py (docstring) | v2.0 | **v1.2.0** |
| app/components/sidebar.py | Trading Desk v2.0 | **Trading Desk v1.2.0** |
| Python/pipeline.py (APP_VERSION) | "2.0.0" | **"1.2.0"** |
| Python/backend/api.py (FastAPI version) | "2.0.0" | **"1.2.0"** |
| build_app.spec | v2.0 / name XAU_AI_PRO_v2 | **v1.2.0 / name XAU_AI_PRO** |
| XAU_AI_PRO_v2.spec | name XAU_AI_PRO_v2 | **name XAU_AI_PRO** |
| README.md | "Crypto Trader Pro" | **"XAU AI PRO v1.2.0"** |
| frontend/package.json | crypto-trader-pro | **xau-ai-pro / XAU AI PRO** |
| CHANGELOG.md | última 1.13 | **entrada [1.2.0] adicionada** |

### Itens NÃO alterados (mantidos de propósito)
- Docs\ROADMAP_V1.0.md / STATUS_ATUAL.md: menções a "V2.0" são marcos futuros de roadmap (planejamento), não versão do produto.
- Ultimate/ (app desktop antigo): sem string de versão de produto; config.json sem app_version.
- dist\XAU_AI_PRO_v2.exe: binário antigo — **requer rebuild** com o spec atualizado para gerar XAU_AI_PRO.exe v1.2.0.

---

## 4. CORREÇÃO DE CÓDIGO APLICADA (v1.2.0)

### XAU_AI_PRO.mq5 — OnTick agora respeita o input AutoTrade
```mql5
// AutoTrade (input) - v1.2.0
if(!AutoTrade)
{
   Print("[TRADE BLOCK] AUTOTRADE OFF | Ative AutoTrade=true no EA");
   return;
}
```
Antes, `AutoTrade` só era checado em `CheckTradingConditions()`, que nunca era chamada — o input não tinha efeito.

---

## 5. BACKUPS
- MQL5: `MQL5\Files\Backup\XAU_AI_PRO_backup_v120\` (cópia integral do projeto antes das alterações)
- App: `C:\Users\Micro\Downloads\XAU_AI_PRO\Backup_v120\` (arquivos alterados, versão original)

---

## 6. PENDÊNCIAS / PRÓXIMOS PASSOS
1. **Ligar AutoTrading no terminal** (Ctrl+E) e **AutoTrade=true** no EA (F7) — necessário para operar.
2. **Rebuild do executável** do app desktop:
   `pyinstaller build_app.spec` (gera dist\XAU_AI_PRO.exe v1.2.0).
3. Forward-test em DEMO (MetaQuotes-Demo 111194406, US$ 200).
4. KCI com dados zerados no dataset (colunas KCI_* = 0).
5. Reduzir verbosidade de logs (ValidationEngine imprime por tick).
