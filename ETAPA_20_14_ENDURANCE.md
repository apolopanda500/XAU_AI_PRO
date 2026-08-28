# ETAPA 20.14 — ENDURANCE PROFISSIONAL

> **Data:** 2026-08-28
> **Regime:** observação passiva — **nenhuma alteração de EA, código, pipeline ou estratégia** durante a janela.
> **Objetivo:** evidenciar estabilidade, resiliência e consistência operacional da janela limpa (27d).
> **Regra mestre:** a saúde técnica não libera capital real. O gate financeiro (20.15, PF ≥ 1,0) decide.

---

## 20.14.1 — Janela limpa congelada

**Início oficial da janela:** 2026-08-28 18:35 UTC (= 21:35 servidor UTC+3).
**Conjunto oficial — 11 símbolos (congelado, M5, magic 2026001):**

`XAUUSD` · `EURUSD` · `USDBRL` · `NZDUSD` · `USDCHF` · `AUDUSD` · `USDSEK` · `GBPUSD` · `USDCAD` · `USDJPY` · `USDCNH`

**Regra:** **nenhum símbolo entra ou sai** durante a janela. Conjunto auditado em 28/08: 11 charts, 1 EA por símbolo.

---

## 20.14.2 — Checkpoints

| Checkpoint | Objetivo | Data (mercado ativo) |
|---|---|---|
| **24h** | estabilidade inicial | ~seg 31/08 (~15:35–16:35 BRT) |
| **72h** | endurance curto | ~qui 03/09 |
| **7 dias** | estabilidade operacional | ~seg 07/09 |
| **30 dias** | evidência para o gate financeiro | ~meados out |

**Métricas registradas em cada checkpoint:**

```
uptime · heartbeat · ticks · trades · wins · losses
Win Rate · Profit Factor · Expectancy · Max Drawdown · Sharpe
rejeições · erros
AI READY/STALE/ERROR · SAFE/HEALTHY/RECOVERY
broker errors · execution errors
event stream · backend health · reconciliation
```

**Fontes:** Broker (deals magic 2026001) · `full_audit.csv` · `forward_test_events.csv` · `forward_test_trades.csv` · `system_status.json` (backend) · Dashboard.

---

## 20.14.3 — Regra financeira (bloqueante)

**PF < 1,00 = NÃO PASSA o gate.** Mesmo que o EA esteja estável, backend saudável, IA funcione,
CI/CD verde e endurance perfeita — **nenhuma dessas condições libera capital real**.

- É a **saúde financeira da estratégia** (PF ≥ 1,0 + métricas estáveis) que decide a 20.15.
- Amostra curta **não** é prova de qualidade; janela completa de 27d + reconciliação + recovery.

---

## 20.14.4 — Reconciliação (em cada checkpoint)

Cadeia de verificação de fontes:

```
BROKER (deals magic 2026001)
   ↓
full_audit.csv
   ↓
forward_test_events.csv
   ↓
Backend (system_status.json)
   ↓
Dashboard
```

Procurar e zerar (0) em cada checkpoint:
`duplicações` · `operações ausentes` · `tickets divergentes` · `profit divergente` · `volume divergente` · `timestamp divergente` · `estado divergente`.

---

## 20.14.5 — Critérios de parada (janela → investigação)

Se ocorrer **qualquer** um:

- EA parado
- stream parado
- corrupção de dados
- erro crítico recorrente
- ordem sem SL/TP
- estado operacional inconsistente
- falha de recuperação
- divergência financeira não explicada

→ a janela entra em **investigação**; o relógio da evidência **pode ser reiniciado**.

**Status (28/08):** achado de **duplicação de execução USDJPY** (`#10264640104`/`#10264640153`, 22:15:02/03) registrado **em investigação** — sem intervenção (segue passivo), monitorado no próximo checkpoint. Não é fato consumado de parada; avaliar se recorrente ou pontual.

---

## 20.14.6 — O que NÃO fazer (durante a endurance)

```
❌ não otimizar estratégia
❌ não alterar SL/TP
❌ não trocar indicadores
❌ não alterar IA
❌ não adicionar símbolos
❌ não mexer no Execution
❌ não alterar Risk
❌ não "melhorar" código
❌ não apagar trades ruins
```

Qualquer alteração **contamina a evidência** da janela. Manter regime passivo.

---

## Baseline registrado (DAY 01, 28/08 23:59 servidor)

| Item | Valor |
|---|---|
| Estado | HEALTHY · algo ON · DD 2,07% (limite 15%) |
| Trades hoje | 5 (aberturas) |
| Balance / Equity | 116,81 / 114,40 |
| AI | STALE (fim de semana — recovery natural na reabertura) |
| Dataset | 173.230.046 B |
| Posições | 5 (GBPUSD, USDCHF, USDCAD, **2× USDJPY**) |

---

## Seqüência

| Etapa | Status |
|---|---|
| 20.12 Governança | ✅ |
| 20.13 CI/CD | ✅ |
| **20.14 Endurance** | 🔄 **ativa (janela desde 28/08 18:35 UTC)** |
| → 24h | ⏳ ~seg 31/08 |
| → 72h | ⏳ ~qui 03/09 |
| → 7d | ⏳ ~seg 07/09 |
| → 30d | ⏳ ~meados out |
| 20.15 Gate financeiro (PF ≥ 1,0) | 🔴 bloqueante |
| 20.16 Release | ⏳ |