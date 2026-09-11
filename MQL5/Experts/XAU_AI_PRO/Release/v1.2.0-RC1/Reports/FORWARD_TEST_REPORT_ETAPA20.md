# XAU_AI_PRO — ETAPA 20.3: FORWARD TEST PROLONGADO (30 dias, conta DEMO)

Data de início: 2026-08-24 | Baseline: v1.2.0 (congelado, imutável) | Sem alteração de lógica.

---

## 1. Objetivo
Acumular **30 dias** de operação real em conta DEMO (MetaQuotes-Demo, login 111194406,
saldo $198.37, trading habilitado, hedging) com registro diário das métricas de produção.
Rodar em paralelo/sequência à otimização de endurance 20.2. **Não alterar o baseline.**

## 2. Eixos de operação
- **6× EA XAU_AI_PRO v1.2.0** em charts M5: XAUUSD, EURUSD, USDBRL, AUDUSD, NZDUSD, USDCHF.
- **EventStream**: `Files/Data/forward_test_events.csv` (UTF-16, 10 colunas) crescendo.
- **Telemetria**: `Files/Data/system_status.json` (health, trading, risk, ai, news, python, database).
- **Reconciliação**: full_audit.csv × forward stream × histórico broker.

## 3. Métricas diárias a registrar (30 dias)
Trades abertas/fechadas · Profit factor (sem forçar >1) · Drawdown (pico→vale da equity) ·
Win rate · Expectancy · Rejeições/erros/retry · Latência heartbeat · Estado IA
(READY/STALE/UNAVAILABLE/ERROR) · Períodos SAFE · Recovery (HEALTH_FAILURE→RECOVERY) ·
Divergências de audit.

## 4. Baseline financeiro (antes do período, 7 trades reais fechados — ETAPA 21)
| Métrica | Valor |
|---|---|
| Win rate | 57.14% |
| Profit factor | 0.46 (a investigar na 20.5) |
| Expectancy | -0.23 |
| PnL total | -1.62 |
| Trades | 7 |

> Este é o ponto de partida a comparar ao fim dos 30 dias. PF=0.46 é **medido**, jamais forçado.

## 5. Situação corrente (kickoff)
- [x] Baseline v1.2.0 congelado (commit 22fdbf4 (baseline congelado v1.2.0), working tree limpo).
- [x] Eixo demo ativo: 6 charts M5 com EA v1.2.0, EventStream fluindo, telemetria atualizando.
- [x] Otimização endurance 20.2 em background (bucket separado).
- [ ] 30 dias de dados a acumular → relatório FORWARD_TEST_REPORT_final.md ao término.

---

*Artefato oficial ETAPA 20.3 — kickoff. Baseline intacto.*