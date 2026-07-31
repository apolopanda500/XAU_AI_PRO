# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 31 de julho de 2026

### ✅ Resumo

Primeira versão estável e lucrativa do XAU_AI_PRO. O sistema passa a operar multi-símbolo, com IA efetivamente integrada às decisões de trading, gestão de risco robusta e pipeline Python de machine learning aprimorado.

### ✨ Recursos Adicionados

- **Multi-símbolo no MQL5** — Todos os indicadores, filtros e módulos aceitam um parâmetro `string symbol`, permitindo operação em XAU/USD e outros pares simultaneamente.
- **IA com peso de 50%** — A confiança da IA (RandomForest) agora contribui com 50% do score de decisão (era 30% na V1.0-beta).
- **AI Veto** — A IA pode vetar uma operação se a confiança for insuficiente, mesmo que os sinais técnicos indiquem entrada.
- **AI Lot Multiplier** — O tamanho do lote é ajustado dinamicamente pela confiança da IA.
- **AI Feedback Logging** — Todas as previsões e decisões são registradas para análise offline (`LogAIFeedback`).
- **GetCombinedSignal** — Combina sinal técnico e sinal de IA em um único score ponderado.
- **Equity Protection** — Monitoramento contínuo de equity; fechamento de emergência em caso de drawdown crítico.
- **Daily Loss Limit** — Bloqueio de trading após atingir limite diário de perdas.
- **MinEquityPercent** — Previne trading se o equity cair abaixo de percentual mínimo definido.
- **Break-even dinâmico com ATR** — SL movido para break-even + buffer ATR quando operação está a favor.
- **Trailing Stop robusto com ATR** — Trailing baseado em ATR com distância mínima e normalização por símbolo.
- **CanTradeToday** — Bloqueio de trading em dias de alta volatilidade ou após limite de perdas.
- **RegisterDailyTrade** — Registro de trades diários para controle de limite.
- **Symbol-aware Validation Engine** — Filtros de tendência, ADX e MTF validados por símbolo.
- **Python predict.py multi-símbolo** — Gera `prediction_{SYMBOL}.json` para cada símbolo no dataset.

### 🐛 Correções

- **Problema 1:** Filtro hardcoded de `XAUUSD` no pipeline Python removido — agora suporta todos os símbolos presentes no dataset.
- **Problema 2:** IA não influenciava decisões — aumentado o peso da IA de 30% para 50%, implementado AI Veto e GetCombinedSignal.
- **Problema 3:** Vazamento de memória — todos os handles de indicadores são liberados (`Release()`) em todos os caminhos de código.
- **Problema 4:** Gestão de risco insuficiente — adicionado EquityProtection, BreakEven ATR, Trailing Stop robusto e daily loss limit.
- **Problema 5:** Multi-símbolo no MQL5 — todos indicadores, filtros e validadores agora aceitam parâmetro de símbolo.

### 🔬 Mudanças Técnicas

#### MQL5

| Módulo | Alterações |
|---|---|
| `AI/AIEngine.mqh` | GetConfidenceWithAI, AI Veto, GetAISignal, GetCombinedSignal, LogAIFeedback, GetAILotMultiplier |
| `AI/AIConnector.mqh` | LoadAIPrediction(string symbol) — carrega `prediction_{symbol}.json` |
| `AI/DataLogger.mqh` | SaveMarketData(string symbol) — multi-símbolo, usa SymbolInfoDouble para point |
| `Core/DecisionEngine.mqh` | CalculateMarketScore com peso de IA 50%, símbolo-aware indicators |
| `Core/SignalCore.mqh` | Multi-symbol support, error handling, handle release |
| `Core/RiskEngine.mqh` | Equity check, daily loss limit, MinEquityPercent |
| `Core/ExecutionEngine.mqh` | CanTradeToday(), RegisterDailyTrade(), AI lot multiplier |
| `Core/ValidationEngine.mqh` | TrendBuy, ADX_OK, MTFApproved — todos symbol-aware |
| `Core/PositionManager.mqh` | TrailingStopATR robusto, VolatilityFilter include |
| `Core/Config.mqh` | Adicionado MinEquityPercent |
| `XAU_AI_PRO.mq5` | OnTick salva dados para todos os símbolos, CheckEquityProtection, LogAIFeedback |
| `Filters/TrendFilter.mqh` | GetTrendEMA overload com symbol |
| `Filters/MultiTimeframeFilter.mqh` | MTFApproved overload com symbol |
| `Indicators/ADX.mqh` | GetADX(string symbol), ADX_OK(string symbol) |
| `Indicators/RSI.mqh` | GetRSI(string symbol), RSI_OK_Buy/Sell com symbol |
| `Indicators/VolatilityFilter.mqh` | GetATR(string symbol) |
| `Management/BreakEven.mqh` | Trigger ATR dinâmico, MagicNumber check, SL sem retrocesso |
| `Management/EquityProtection.mqh` | EmergencyCloseAll, CheckEquityProtection |

#### Python

| Arquivo | Alterações |
|---|---|
| `train.py` | 9 novas features (BodySize, RangeSize, shadows, ATR_Pct, RSI_Diff, Close_Diff, Volume_MA, ADX_Change); RandomForest com 300 estimadores, class_weight=balanced; target Future_Return |
| `predict.py` | Predição multi-símbolo — gera `prediction_{SYMBOL}.json` para cada símbolo; imports fixos |
| `data/data_engine_xau.py` | Removido filtro hardcoded de XAUUSD |

### 🎯 Métricas

- Win Rate: target > 50%
- Profit Factor: target > 1.5
- Drawdown: target < 15%

---

## Versionamento

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 31/07/2026 | Versão estável — multi-símbolo, IA 50%, gestão de risco |
| 1.1.0 | Em planejamento | Performance e proteção de capital |
