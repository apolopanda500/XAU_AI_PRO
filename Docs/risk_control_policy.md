# POLITICA UNICA DE RISCO - XAU_AI_PRO v1.2.0-RC1
## ETAPA 15.5 - RISK CONTROL CENTER

**Data:** 24/08/2026 | **Status:** ATIVA | **Compilacao: 0 erros / 0 warnings**

---

## 1. PRINCIPIOS

1. `RiskHub.GetDrawdownPercent()` e a UNICA fonte de drawdown do sistema
   (vs peak diario persistente em GlobalVariables).
2. Nenhum modulo recalcula metricas de risco por conta propria.
3. Toda decisao de bloqueio retorna UM motivo rastreavel.
4. Novas entradas passam pelo RiskCenter; gestao de posicoes abertas nao.
5. Falha de leitura de metrica -> fail-closed para novas entradas.
6. Acoes drasticas (EmergencyCloseAll, CircuitBreaker) pertencem a camada
   Enterprise e nunca sao disparadas por calculos locais duplicados.

---

## 2. ORDEM DETERMINISTICA DE AVALIACAO (RiskEvaluate)

| Ordem | Regra | Executor | Motivo |
|-------|-------|----------|--------|
| 1 | Perda diaria (vs STARTBAL) | SafetyManager.CheckDailyLoss | DAILY_LOSS |
| 2 | Drawdown diario (vs peak) | SafetyManager.CheckDailyDrawdown | DAILY_DRAWDOWN |
| 3 | Numero de operacoes/dia | SafetyManager.CheckDailyTrades | MAX_TRADES_PER_DAY |
| 4 | Margem livre minima | SafetyManager.CheckFreeMargin | FREE_MARGIN |
| 5 | Exposicao total | SafetyManager.CheckTotalExposure | TOTAL_EXPOSURE |

Camadas anteriores ao RiskCenter (mantidas):
`DecisionEngine` -> `ValidationEngine` -> **RiskCenter** -> `ExecutionEngine`
(lote/risco financeiro no RiskEngine; simulacao pre-execucao no SimulationEngine)

---

## 3. MATRIZ DE CONFLITOS DO INVENTARIO (ETAPA 15.5)

| # | Conflito | Status |
|---|----------|--------|
| C1 | 3 definicoes de drawdown (RiskHub vs RiskEngine vs EquityProtection) | RESOLVIDO - RiskEngine consome GetDrawdownPercent() |
| C2 | EmergencyCloseAll pode conflitar com CircuitBreaker | DOCUMENTADO - integracao na Fase 15.7 (Failover) |
| C3 | Exposure do PortfolioManager = P/L flutuante, nao nocional | DOCUMENTADO - metrica real pendente |
| C4 | MaxOpenPositions checado 2x (PositionManager + PortfolioManager) | DOCUMENTADO - sem efeito pratico |
| C5 | CheckRiskPerSymbol/Session sao stubs | PENDENTE - implementacao futura |
| C6 | Default hardcoded 15.0 em EquityProtection() | DOCUMENTADO |

---

## 4. API DO RISK CENTER

```mql5
// Gate simples:
string reason;
if(!RiskAllowEntry(symbol, reason))
   Print("RISK BLOCK | ", reason);

// Decisao completa (observabilidade):
RiskDecision d = RiskEvaluate(symbol);
// d.allowed, d.reason, d.drawdown_pct,
// d.trades_today, d.daily_loss_pct, d.free_margin

// Summary para log/app:
Print(RiskCenterSummary());
```

---
*Documento oficial - ETAPA 15.5*
