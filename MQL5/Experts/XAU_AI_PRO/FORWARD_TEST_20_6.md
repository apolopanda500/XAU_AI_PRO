# XAU_AI_PRO — ETAPA 20.6: ENDURANCE 24h → 7d → 30d (KICKOFF)

Data início janela limpa: **2026-08-28 21:05 UTC** | Baseline v1.2.0 | Conta MetaQuotes-Demo 111194406 (demo)

---

## 1. Estado validado na reanexação (20.5 — COMPLETO)

- ✅ **11 EAs XAU_AI_PRO v1.2.0 carregados** (SYSTEM_START + FORWARD_TEST_START registrados no EventStream para cada um: XAUUSD, EURUSD, USDBRL, NZDUSD, USDCHF, AUDUSD, USDSEK, GBPUSD, USDCAD, USDJPY, USDCNH — M5).
- ✅ Log do terminal: `expert XAU_AI_PRO (...) loaded successfully` — sem "Falha ao copiar RSI", sem erro de OnInit.
- ✅ EventStream `forward_test_events.csv` ativo e crescendo (em uso pelos EAs).
- ✅ Telemetria `system_status.json` atualizando (HEALTHY, algo ON).
- ✅ EA operando: **3 posições abertas** (21:05 UTC): GBPUSD SELL 0.01, USDCHF BUY 0.01, USDCAD BUY 0.01 (SL/TP 300/600 corretos).
- ⚠️ Inputs aplicados = **padrão do EA** (validação pura): UseRiskManagement=0, EnableNewsFilter=0, EnableAIFilter=0, filtros OFF, AutoTrade input=0 (não bloqueia; gate real = botão Algoritmos ON). Coerente com o roteiro 20.5. **Não alterar durante a janela.**

## 2. Janela de medição (LIMPA)

- **Início:** 2026-08-28 21:05 UTC (primeiras posições da sessão pós-reanexação).
- **Símbolos (11):** XAUUSD, EURUSD, USDBRL, NZDUSD, USDCHF, AUDUSD, USDSEK, GBPUSD, USDCAD, USDJPY, USDCNH.
- **Fim 24h:** 2026-08-29 21:05 UTC | **Fim 7d:** 2026-09-04 21:05 UTC | **Fim 30d:** 2026-09-27 21:05 UTC.
- **Excluídos (contaminação):** XAGUSD, US30, US500, USTEC, USDCLP, USDCOP, USDCZK (SL 300 fixo não normalizado).

## 3. Referência negativa congelada (janela contaminada 21–28/08)

| Métrica | Valor |
|---|---|
| Trades fechados | 40 (35 sem XAG) |
| PnL | **−83,43** (sem swap) |
| PF | **0,12** (0,58 sem XAG) |
| Saldo inicial/final | 198,37 → 116,81 |

> Narrativa registrada para auditoria: piora atribuída à contaminação (14 charts, XAG −75,00). Janela nova é a referência válida para o gate.

## 4. Objetivo do gate financeiro (20.11)

**PF DA JANELA LIMPA ≥ 1,0** (medido, jamais forçado) + endurance completa + recovery + reconciliação 0 divergências. Só então Production Gate.

## 5. Checklist de monitoramento diário (20.6)

- [ ] PF diário por símbolo e total (deals magic 2026001, janela ≥ 28/08 21:05 UTC)
- [ ] Win rate, expectancy, drawdown pico→vale
- [ ] Rejeições/erros/retry; latência heartbeat; IA READY/STALE/UNAVAILABLE
- [ ] SAFE/RECOVERY e divergências de audit
- [ ] NÃO abrir charts extras nem tocar inputs (regra de baseline)

## 6. Métricas do kickoff

| Item | Valor |
|---|---|
| Saldo | 116,81 |
| Equity | 116,36 |
| Posições abertas | 3 (GBPUSD, USDCHF, USDCAD — 0,01 cada) |
| P/L flutuante | −0,67 |
| Trades hoje | 3 |
| Free margin | 82,83 |
| Drawdown (RiskHub) | 0,39% |

---

*Artefato oficial ETAPA 20.6 — kickoff. Baseline v1.2.0 intacto; janela limpa em andamento.*