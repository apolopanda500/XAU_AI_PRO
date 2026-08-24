# XAU_AI_PRO v1.2.0-RC1 — Release Candidate

Data: 2026-08-23
Status: HARDENING (ETAPA 14) — Candidato à produção

---

## 1. Congelamento de arquitetura

- Estrutura modular confirmada (Core, AI, Indicators, Filters, Management, Enterprise, Monitoring).
- Todos os módulos `.mqh` são self-contained (0 `#include` inter-módulo; dependência centralizada no EA).
- Nenhum módulo novo adicionado nesta etapa (apenas correções de hardening).
- Órfãos de v1.2.2 já quaranteneados em `Files/Backup/XAU_AI_PRO_orfaos_v122/`.

## 2. Auditoria de includes

- `XAU_AI_PRO.mqproj` regenerado em formato MQL5 válido (`program_type=expert`, lista `files` completa).
- Build oficial do projeto: **0 erros, 0 warnings**.
- Cadeia de includes completa verificada via compilação (Trade → Object → StdLibErr → módulos do EA → KCI).

## 3. Auditoria de fluxo

Pipeline real verificado no código:

```
Market Data (OnTick/ConnectionGuard)
  ↓
Indicators (SignalCore cache de handles)
  ↓
AI (GetCombinedSignal: técnico + IA)
  ↓
Score/Decision (AllowTrade → ValidateTrade + CalculateMarketScore ≥ 60 + FinalAIAllow)
  ↓
Filters (Spread/Session/Trend/ADX/Volatility/MTF/News — dentro de ValidateTrade)
  ↓
Validation (ValidateTrade)
  ↓
Risk/Safety (CSafetyManager::CheckAll + CanTradeToday + CalculateLotByRisk)
  ↓
Simulation (CSimulationEngine::Evaluate)
  ↓
Smart Execution (CSmartExecution::OpenPosition + retry)
  ↓
Position Management (BreakEven, TrailingStopATR, PartialClose)
  ↓
Monitoring/Audit (AuditLog, TradeLogger, Statistics, ForwardTestRunner, QuantValidator)
```

**Fix aplicado (crítico):** o caminho crítico (`MarketScanner::ProcessSymbol`) não chamava
`AllowTrade()` — apenas `ValidateTrade()`. Isso deixava `MarketScore` sempre 0.0 e o filtro
de score ≥ 60 + veto avançado de IA (`FinalAIAllow`) fora do fluxo real de execução.
Corrigido integrando `AllowTrade()` ao scanner. Build 0/0 após o fix.

## 4. Condições extremas (verificação em backtest de ticks reais)

| Condição | Comportamento observado |
|---|---|
| Spread elevado | ✅ CircuitBreaker bloqueou (`SPREAD EXPLOSION` > 500 pts) |
| Validação | ✅ `[VALIDATION] BLOCK | TREND/SPREAD/...` |
| Falha de execução | ✅ Ordem rejeitada → retry/gestão |
| IA/JSON ausente | ✅ RequireAIJSON=false → sem falha (corrigido no Diagnostics) |
| Notificações | ⚠️ Erro 4014 (push não configurado — esperado) |
| Calendário | ⚠️ Erro 4014 no tester (esperado) |

## 5. Recuperação (SAFE/RECOVERY/HEALTHY)

`FailureMode.mqh` implementa o ciclo completo:
NORMAL → (falha) → SAFE_MODE → (cooldown 60s) → RECOVERY → (revalidate) → RESUME → NORMAL.
- SAFE bloqueia novas entradas, NUNCA interrompe gestão de posições abertas.
- `ConnectionGuard` verifica terminal/conta/algo-trading/símbolo antes de cada entrada.
- `RecoveryManager` monitora AI/Indicators/Broker/Dataset/JSON/Memory.

## 6. Build oficial

```
XAU_AI_PRO.mqproj → Compilation succeeded: 0 errors, 0 warnings
```

## 7. Módulos novos integrados (ETAPA 12/13/14)

- `Enterprise/FailureMode.mqh` — máquina de estados de resiliência
- `Enterprise/ConnectionGuard.mqh` — guarda de conexão
- `Monitoring/QuantValidator.mqh` — matriz quantitativa (11 métricas)
- `Monitoring/ForwardTestRunner.mqh` — coletor de sessão forward test
- `AI/ModelGovernance.mqh` — versionamento de modelo

Todos compilados no build 0/0 e incluídos no cierre de dependências.

## 8. Pendências para ETAPA 15

- Forward test em demo (operação contínua).
- Normalizar mojibake de acentos em comentários (cosmético, não afeta build).
- Investigar queda de `HealthMonitor` durante "Notícias" (erro 4014 é ambiente).
