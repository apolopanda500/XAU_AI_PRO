# XAU_AI_PRO — FASE FINAL (ETAPAS 20.5 → 20.11) — GOVERNANÇA

> Revisão: 2026-08-28 17:00 UTC | Autor: MetaTrader Assistant
> Base: baseline v1.2.0 congelado (commit fab96b0 / docs 20.1) — imutável durante toda a fase.

---

## 1. BLOQUEADOR FINANCEIRO (CAPITAL GATE)

**PF = 0,46 (7 trades, 24/08) era o registro-base. Atualização com evidência do broker (deals, magic 2026001, 21–28/08):**

| Métrica | 24/08 (baseline) | 28/08 (acumulado) | Excl. XAGUSD |
|---|---|---|---|
| Trades fechados | 7 | 40 | 35 |
| Win rate | 57,1% | 55,0% (22/40) | 58,3% (21/36) |
| Profit Factor | 0,46 | **0,12** | **0,58** |
| Expectancy | −0,23 | −2,09 | −0,10 |
| PnL (profit, sem swap) | −1,62 | **−83,43** | −8,43 |
| Saldo demo | 198,37 | **116,81** | — |

**Veredito: CAPITAL GATE permanece FECHADO.** PF < 1,0 medido em 40 trades reais (demo). Nenhuma aprovação para capital real ocorre enquanto este critério não for superado por evidência válida (PF ≥ 1,0 em janela forward limpa). PF é **medido, jamais forçado**.

**Causa principal da piora:** contaminação do forward por símbolos fora do baseline — o EA estava anexado a **14 gráficos** (o baseline documenta 6): XAGUSD (5 trades × −15,00 = **−75,00** = 79% do gross loss), USDJPY, USDCAD, GBPUSD, USDCNH, USDSEK, USDCLP, USDCOP, USDCZK. SL 300 pontos não é normalizado por símbolo (XAG 0,01 lote → −15,00 vs EURUSD ~−3,00).

---

## 2. ORDEM OFICIAL DA FASE (sequencial, com gates)

```
20.5  Forward Reattach          → 6 charts oficiais, ex5 baseline, inputs idênticos
   ↓   gate: reattach completo, log sem "Falha ao copiar RSI", [PIPELINE] ativo, Algoritmos verde
20.6  Endurance 24h → 7d → 30d  → 3 marcos; PF medido diário; parar se contaminação
   ↓   gate: janela limpa, telemetria/eventstream contínuos, sem retorno de erro de entrada
20.7  Stress + Recovery         → queda de rede/broker/reinício a frio com posição aberta
   ↓   gate: SAFE/RECOVERY acionam e restauram; sem posição órfã; sem divergence
20.8  Reconciliation            → full_audit.csv × eventstream × histórico broker = 0 divergência
   ↓   gate: 0 divergências não-explicadas
20.9  Security ✅                → já aprovada (commit 0a2fd8b, sem credenciais) — reconfirmar no pacote
20.10 Release                   → re-empacotar RC com ex5/hashes FRESCOS (manifest tinha hash stale)
   ↓   gate: hashes do pacote == hashes compilados; docs/checklists presentes
20.11 Production Gate           → PF ≥ 1,0 (janela forward limpa) + endurance + recovery + reconciliação
   ↓   gate: TODOS os anteriores PASS ⇒ aprovação para capital real
FINAL
```

**PROIBIDO avançar de etapa com gate aberto.** Etapas 20.9/20.10 já existem como commits, mas a 20.10 precisa de re-empacotamento (hash stale) — por isso a ordem completa é reexecutada.

---

## 3. REGRA DE BASELINE (vigente em toda a fase)

**Qualquer correção que:**
1. provoque **erros de compilação** (≠ 0/0), OU
2. **altere o comportamento de entrada** (SignalCore/DecisionEngine/ValidationEngine/filtros de gatilho);

...deve **primeiro voltar ao baseline 0/0** antes de qualquer etapa nova.

Protocolo:
1. `git stash push -m "<motivo>"` (não destrutivo; WIP preservado) — ou revert cirúrgico.
2. `git status` → apenas untracked legítimos (testes/dados).
3. Compilar baseline → **0 erros / 0 warnings**.
4. Conferir hashes de fonte: `XAU_AI_PRO.mq5` = `787b5320...`, `Core\SignalCore.mqh` = `67f28a9b...` (manifesto 20.1).
5. Só então reanexar/reiniciar o forward.

Isso evita reincidência do incidente de encoding e impede alterar uma estratégia já sob validação.

---

## 4. ESTADO VERIFICADO — 2026-08-28 (gate 20.5 pré-condição)

| Item | Resultado |
|---|---|
| Compilação baseline | ✅ 0 erros / 0 warnings (MetaEditor 6140 x64, 12,2s) |
| Hash XAU_AI_PRO.mq5 | ✅ `787b53206d546e5e4ba9d5f41b84fde50870a6a825a697fb7e2488c479d39566` (== manifesto) |
| Hash SignalCore.mqh | ✅ `67f28a9bd1708d0a97e04ea2a9f14e311cc6e9ba13a0bd8bf9870f618251069b` (== manifesto) |
| WIP v1.3.1 (A/B, EMA, reject codes...) | 🗃️ preservado em `stash@{0}` — **proibido mesclar no baseline** |
| Árvore de trabalho | ✅ limpa (tracked) — só untracked de testes/dados |
| Conta demo | ✅ conectada, trading habilitado; saldo $116,81; 0 posições; 0 ordens |
| Charts com EA | ⚠️ **14** (baseline: 6) — ver §5 |
| ex5 Release v1.2.0\EA | ⚠️ hash `165e73f6...` ≠ manifesto `9303e383...` → re-empacotar na 20.10 |

---

## 5. DIAGNÓSTICO DE CONTAMINAÇÃO (20.5 deve corrigir)

Charts abertos com XAU_AI_PRO (28/08):
- **Oficiais (6):** XAUUSD M5 ✅, EURUSD M5 ✅, USDBRL M5 ✅, AUDUSD ⚠️ **H4 (deve ser M5)**, NZDUSD M5 ✅, USDCHF M5 ✅
- **Contaminantes (8):** USDJPY, USDCAD, USDCNH, GBPUSD, USDSEK, USDCLP, USDCOP, USDCZK (M5)
- **Duplicado:** 2º chart XAUUSD M5 (chart 15) sem EA

Plano 20.5:
1. Fechar os 8 charts contaminantes + o XAUUSD duplicado.
2. AUDUSD: fechar chart H4 e reabrir M5.
3. Reanexar (manual) o `XAU_AI_PRO.ex5` **baseline recém-compilado** nos 6 charts oficiais.
4. Conferir inputs idênticos (Magic 2026001; EMA 50/200; RSI 14, pullback 45/55; SL 300/TP 600; EnableNewsFilter=0; EnableAIFilter=0; UseRiskManagement=0).
5. Botão **Algoritmos** VERDE + journal sem "Falha ao copiar RSI".
6. Iniciar monitoramento 20.6 (24h → 7d → 30d).

Custo esperado do gate financeiro: PF ≥ 1,0 medido na janela forward limpa antes de qualquer discussão de capital.

---

## 5'. ESTADO DOS CHARTS — 28/08 18:03 UTC (11 charts abertos)

| # | Símbolo | TF | EA anexado | Ação 20.5 |
|---|---|---|---|---|
| 1 | XAUUSD | M5 | antigo (memória) | remover + reanexar baseline |
| 2 | EURUSD | M5 | antigo (memória) | remover + reanexar baseline |
| 3 | USDBRL | M5 | antigo (memória) | remover + reanexar baseline |
| 4 | NZDUSD | M5 | antigo (memória) | remover + reanexar baseline |
| 5 | USDCHF | M5 | antigo (memória) | remover + reanexar baseline |
| 6 | AUDUSD | M5 | — | reanexar baseline |
| 7 | USDSEK | M5 | — | reanexar baseline |
| 8 | GBPUSD | M5 | — | reanexar baseline |
| 9 | USDCAD | M5 | — | reanexar baseline |
| 10 | USDJPY | M5 | — | reanexar baseline |
| 11 | USDCNH | M5 | — | reanexar baseline |

> ⚠️ Charts 1–5 ainda rodam o ex5 ANTIGO em memória (compilado antes do stash). O roteiro 20.5 exige remover e reanexar o `XAU_AI_PRO.ex5` **baseline recém-compilado** (28/08) em TODOS os charts para carregar o executável correto.

## 6. DECISÃO 28/08 — AMPLIAÇÃO DE SÍMBOLOS (usuário)

- Os **18 símbolos já estão no Market Watch** (visíveis). A ampliação foi feita na **lista de operação** do EA via preset novo: `FASE_FINAL_20_5.SYMBOLS_AMPLIADO.set`.
- **Lista ativa (FX, 11):** XAUUSD, EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, NZDUSD, USDCHF, USDBRL, USDCNH, USDSEK.
- **Fora da lista ativa (até normalização de risco por símbolo):** XAGUSD, US30, US500, USTEC, USDCLP, USDCOP, USDCZK — SL 300 pontos fixo não é normalizado (XAG 0,01 lote = −15,00/trade, 79% do gross loss do forward contaminado).
- ⚠️ **Regra de uso:** `EnableMultiSymbol=true` ⇒ o EA opera em TODOS os símbolos da lista. Se a intenção for apenas observar, manter `EnableMultiSymbol=false` nos charts e usar a lista apenas como referência. O release/baseline **não foi alterado** (preset novo é artefato de validação).

---

*Artefato de governança da fase final. Baseline v1.2.0 intacto; WIP v1.3.1 fora da estratégia sob validação.*