# XAU_AI_PRO — Registro de Progresso

> Plataforma XAUUSD: modular, auditável, testável e preparada para operação.
> Última atualização: 2026-09-07 (v1.2.0)

---

## Ciclo 2026-09-07 — testes ADX (SHORT/LONG) + C5 + health

### TEST_ADX (filtro ADX MinimumADX=18, fail-open SKIP + sentinela)

| Métrica | SHORT (02–03/09) | LONG (01/08–05/09) |
|---|---|---|
| Barras | 264 | 6.600 |
| Ticks | 447.571 | 10.839.724 |
| Deals / Trades | 40 / 20 | 1.611 / 1.165 |
| Long / Short | 4 / 16 | 814 / 351 |
| P/L | −155,10 | −454,56 |
| Profit Factor | 0,49 | 0,80 |
| DD balance | 2,98% | 9,56% |
| Expected payoff | — | −0,39 |
| Sharpe | — | −3,51 |
| ADX unavailable / valid / block | 1 / 17.134 / 4.531 | 1 / 5.930.462 / 498.965 |

**Reading:** `GetADX()<0 → fail-open`, `ADX<18 → BLOCK` funcional (block crece con la ventana; PASS real en USDJPY 34,08 / USDBRL 37,61). La estrategia base NO es rentable en ventana larga (PF 0,80, E=−0,39, DD 9,9%). **No producción.**

### Reconciliação C5 (window ≥ 2026.09.02 00:33:40 servidor)
- missing_audit_entry=0 · dup_exec=0 · unknown_event_tickets=[] (el falso positivo 10090527226 = caché API, confirmado)
- missing_event_entry=2: tickets 10067813690, 10068219749 (build antiguo 04/09, pre-fix ADX)
- Broker: 201 deals, net +9,96, 1 posición EURUSD abierta
- **C5 = 3/4 limpias; cerrado para el build actual** (2 pendientes son de build anterior). No se implementa Opción A (re-emisión al arranque) → evita rebuild+reload = nuevo T0.

### HEALTH ERROR en producción — causa raíz (falso positivo)
- Heartbeats ATR/ADX/RSI/AI = inicio de OnTick; CSV/JSON/PYTHON = final (tras `UpdateDataset` = tras todos los early-return).
- Trades: 20/20 (SAFETY MAX_TRADES_PER_DAY) → OnTick retorna en `CSafetyManager::CheckAll()` ANTES del heartbeat dataset/python → 3 módulos sin batir → 3× warning + HEALTH FAILURE por check.
- Backoff exponencial confirmado (60→120→…→1920 s; techo 32 min).
- **No es fallo de engine/dataset/python/AI.** Auto-recupera al resetear el contador diario. Fix cosmético recomendado (beat pre-bloqueo).

### Endurance técnico del build nuevo
- `XAU_AI_PRO.ex5` (07/09 03:27Z, fix ADX): run LONG = 10,84 M ticks / 6.600 barras SIN crash → evidencia de estabilidad (C2/C3 técnico con build nuevo).
- Disco: 10,79 GB libres tras rotación de logs.

### Fix definitivo — LIVENESS vs PROGRESS (auditado + refeito, 07/09)
- `HealthMonitor.mqh`: novo canal `g_wdLastProgress[]`/`g_wdProgressFails[]` + funcoes `HealthMonitorProgress()` e `HealthIsPipeline()`.
- `HealthMonitorCheckHeartbeatModule()`: modulos pipeline (PYTHON/CSV/JSON) usan `g_wdLastProgress` (so avanza con `UpdateDataset` real -> detecta parada real); indicadores/AI usan `g_wdLastTime` (liveness por tick).
- `XAU_AI_PRO.mq5`: **removidos** os 3 heartbeats do topo do OnTick (mascaravam parada); o bloco pos-UpdateDataset agora chama `HealthMonitorProgress("CSV"/"JSON"/"PYTHON")`. OnInit mantiene heartbeats iniciais (liveness base).
- Build validado: **0 erros, 0 warnings** (07/09 17:33). `.ex5` regenarado (410.498 B). Aplicacion exige reload dos 7 charts = novo T0.
- **Nota de proceso:** durante a edicion um helper corrompiu temporalmente o `.mq5` (delete en offset errado); restaurado via `git checkout -- XAU_AI_PRO.mq5` e re-aplicado o fix cirurxicamente. Estado final: LF consistente, 0/0.

## Resumo de status (Etapas do roadmap)

| Etapa | Status | Observação |
|---|---|---|
| 1 — SignalCore (entrada + A/B) | ✅ | Baseline aprovado; estratégia B (EMA+ADX+Breakout) experimental |
| 2 — DecisionEngine | ✅ | Auditado; TF da EMA do score alinhado à estratégia; anti-repaint (vela fechada) |
| 3 — ValidationEngine | ✅ | Auditado (9 filtros); código de rejeição estruturado adicionado |
| 4 — RiskEngine | ✅ | Cadeia equity→%→SL→tick→lote completa; drawdown via RiskHub |
| 5 — ExecutionEngine | ✅ | Auditado; não-grava sinais; inclui simulação e blindagem a duplicidade |
| 6 — PositionManager | ✅ | BE, trailing ATR, parcial, controle de posições; padrões registrados |
| 7 — IA/ML (infra) | ✅ | Veto/direção/score/lote/feedback + **AIMetrics** (accuracy/precision/recall) |
| 8 — Backtest protocol | 🔄 | A/B rodados; E (OOS) inconclusivo; F (recente) rodando |
| 9 — Robustez | ⏳ | — |
| 10 — Broker/Environment | ✅ | Detecção automática (símbolo/digits/point/spread/volume/stops/freeze); `ProbeSymbolProfile()` |
| 11 — Data + Telemetry | ✅ (parcial) | código de rejeição integrado; "porquê não entrou" disponível |
| 12 — Dashboard | ✅ | Ampliado: Trend, Regime, IA Dir/Conf, DD RiskHub e mais (build OK) |
| 13 — PLATFORM/BACKEND | ✅ | DatabaseManager (SQLite): analytics reais — `GetTotalProfit/Trades/WinRate/ProfitFactor` implementados |
| 14 — Segurança operacional | ✅ | CircuitBreaker robusto: kill-switch, DD, spread(10x), IA fallback, broker, mercado anormal, persistência, auto-recovery, FailSafe API |
| 15 — Forward test | ⏳ | — |

---

## Resultado A/B (Etapa 1/8) — XAUUSD M5 (14–24/08, ticks reais)

| Métrica | A (baseline RSI) | B (EMA+ADX+Breakout) |
|---|---|---|
| Lucro | **-14,45** | -66,17 |
| Profit Factor | **0,8855** | 0,2033 |
| Trades | 49 | 15 |
| Win rate | 59% | 40% |

**Decisão:** baseline A aprovado como entrada corrente. B mantido experimental (não segue para produção até atingir consistência).

**Requisito de engenharia:** cada backtest every-tick XAU M5 leva ~1h50–2h real. Perfil `TESTE_F_OTIMIZADO.ini` (logs off, Model=2) acelera janelas longas.

## IA — snapshot vs. walk-forward
`prediction_XAUUSD.json` é um snapshot único e estático. Rodar o Teste C/D com ele num período longo é inválido (mesma predição "BUY 87.86" em todas as barras). Só é válido após predição intraperioodal / walk-forward (pipeline Python externo).

## Mudanças v1.3.1 (recentes)
- `ValidationEngine.mqh`: `enum ValidationRejectCode` + `GetLastReject()` + `RejectCodeToString()` — observabilidade sem mudar decisão.
- `DecisionEngine.mqh`: EMA do `MarketScore` alinhada ao TF da estratégia; usa vela fechada `[1]`.
- `SignalCore.mqh`: seletor `XAU_UseNewStrategy` permite A/B em runtime; interfaces `GetSignal()/GetSignal(symbol)` preservadas.
- `SymbolValidator.mqh`: `ProbeSymbolProfile()` consolida detecção broker (digits/point/tick/volume/stops/freeze/spread).
- `Dashboard.mqh`: ampliado com Trend, Regime, IA Dir/Conf, DD (RiskHub).
- Perfis de teste otimizados (`.ini` com logs off) p/ janelas longas.
- Build validado: 0 erros, 0 warnings em todo o projeto.

## Notas de risco
- `RiskPercent`, `MaxDailyLossPercent`, `MaxDrawdownPercent` não alterados (capital real).