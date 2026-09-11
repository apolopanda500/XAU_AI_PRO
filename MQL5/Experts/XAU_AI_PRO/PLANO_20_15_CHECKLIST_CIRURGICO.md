# XAU_AI_PRO — PLANO CIRÚRGICO 20.15 (checklist de execução)

> Preparado: 2026-08-30 ~19:2x BRT | Autor: MetaTrader Assistant
> **Regra: nada deste plano é aplicado durante a janela limpa (20.14).** É o roteiro de execução
> para quando o checkpoint 20.14-C (24h) e 20.14-D (72h) forem concluídos.
> Evidências de origem: §10.7 (causa raiz), §10.8 (reprodução ADX) do FORWARD_WINDOW_TRACKER.md.

---

## 0. Ordem de execução (sequencial, com gates de aceite)

```
1. Reconciliação binário/fonte  (ex5 ≠ fonte — modify-loop + close storm)
   ↓  aceite: hash ex5 == fonte; 0 modify-loop / 0 close-storm após reanexar
2. **Fix OrderRetry (NOVO — PRIORIDADE MÁXIMA)**  (dup-exec em massa: 3–4 fills/sinal)
   ↓  aceite: backtest + live 72h → 1 fill por decisão sempre
3. Fix dup-exec TOCTOU (guard inter-instância)
   ↓  aceite: 2 ticks no mesmo segundo → 1 ordem; live 72h sem recorrência
4. Fix ADX 4807 (tester)
   ↓  aceite: DIAG_T6 repro → trades > 0; log sem Error=4807
5. Matriz IA ON/OFF + SL/TP (Baseline / A / B / C)
   ↓  aceite preliminar: PF > 1 com N ≥ 100, consistente em ≥ 2 janelas
6. Gate financeiro 20.15
   ↓  PF ≥ 1,0 (janela limpa) + DD aceitável + expectancy + recon + sem incidentes recorrentes
```

---

## 1b. Fix OrderRetry — PRIORIDADE MÁXIMA (dup-exec em massa, §10.11)

**Problema:** com rede instável (pings até 600ms, 24 desconexões), `COrderRetry::ExecuteWithRetry`
reenvia a ordem após retcodes retriable (TIMEOUT/REQUOTE/PRICE_CHANGED) — mas o **1º envio já foi
aceito** pelo broker. Resultado: **3–4 fills idênticos do mesmo sinal** (GBPUSD ×3, USDCHF ×4 em
06:49:51–53 servidor). Agravado porque o `RefreshRequestPrice` atualiza o preço a cada retry,
gerando tickets com preços levemente diferentes mas mesma direção/vol.

**Correção proposta:**
1. **Pré-checagem antes de cada reenvio** em `ExecuteWithRetry`: se `request.action==DEAL` com
   `request.type` BUY/SELL, verificar se já existe posição do mesmo símbolo+mágica criada nos
   últimos N segundos (N≈5–10) — se sim, **não reenviar** (retornar SUCCESS do envio original).
2. **Cap de fills por decisão (1)**: uma decisão só pode produzir 1 fill; reenvios só se a
   posição NÃO existir.
3. **Marcar in-flight antes do 1º envio** (GlobalVariable `XAI_PRO_INFLIGHT_<sym>`) e só liberar
   após confirmar o deal no OnTradeTransaction — unificado com o fix TOCTOU (§2).
4. Reavaliar `RefreshRequestPrice` em retries para TRADE_ACTION_DEAL: usar o preço original se a
   ordem é reenvio de uma já provavelmente aceita (ou abortar após 1º envio "possivelmente aceito").

**Aceite:** backtest e live 72h → sempre 1 fill por decisão; 0 repetições de envio confirmado.

---

## 1. Reconciliação binário/fonte (PRIMEIRO — desbloqueia tudo)

**Problema:** `XAU_AI_PRO.ex5` (30/08 16:04, SHA256 `ec9dc102…`) comporta-se como compilado de
árvore ≠ fontes atuais (24/08): trailing/BE ativos com inputs OFF, closes "Expert" sem caller.

**Procedimento:**
1. Compilar `XAU_AI_PRO.mqproj` no MetaEditor (0 erros / 0 warnings).
2. `certutil -hashfile XAU_AI_PRO.ex5 SHA256` → comparar com `ec9dc102…`.
3. Se divergir: remover o EA dos 11 charts e reanexar o ex5 recém-compilado (baseline 24/08,
   inputs idênticos: SL 300/TP 600, EMA 50/200, RSI 14/45/55, AI=0, ADX=0, BE=0, Trail=0, MS=false).
4. Journal por ≥15 min: **0** linhas `modify #... skipped as it changes nothing`; **0** close retry
   `[Position doesn't exist]` fora de operação explícita; `[BREAK EVEN] Ativado` **ausente**.
5. Atualizar `RELEASE_MANIFEST.md` com hash novo (pendência §5 do tracker).

**Rollback:** recompilar estado atual e reanexar; `git stash` preserva qualquer WIP.

---

## 2. Fix dup-exec (TOCTOU — evidência §10.7-A)

**Causa:** guards `CanOpenPosition` / latch de vela / GV-inter-instância são verificados **antes**
do fill (cache assíncrono ~100–500ms) → 2 ticks a ≤1s abrem 2 ordens idênticas.

**Correção proposta (3 mudanças cooperativas):**
1. **Flag in-flight por símbolo**: lista estática `{symbol, time}` setada **antes** do `OrderSend`
   em `ExecuteTrade()` e rejeitando nova chamada para o mesmo símbolo dentro de ~5 s
   (`if(InFlightActive(symbol)) return false;`). Limpar no `OnTradeTransaction` (DEAL_ENTRY_IN)
   ou por expiração no flag.
2. **Re-check imediato** em `CSmartExecution::OpenPosition()`: contar posições abertas do símbolo
   imediatamente antes do envio (além do guard GV existente).
3. **Latch de vela antecipado**: `MarkTradedBar()` chamado logo após envio aceito (não após o
   retorno completo), evitando re-entrada na mesma vela durante o round-trip.

**Aceite:** teste no Strategy Tester com replay de 2 ticks no mesmo segundo → **1** ordem;
live 72h → 0 recorrências `TRADE_APPROVED → 2 fills`.

---

## 3. Fix ADX 4807 (tester — evidência §10.8)

**Causa:** `GetADX()` retorna `0.0` no warm-up (Error=4807) e `ADX_OK()` fail-closed bloqueia tudo.

**Patch proposto (Indicators/ADX.mqh):**

```mql5
double GetADX()
{
   if(adxHandle == INVALID_HANDLE)
      return -1.0;                       // "sem informação", não "tendência fraca"

   // Warm-up: barras suficientes antes de ler
   if(Bars(_Symbol, PERIOD_CURRENT) < ADXPeriod * 3)
      return -1.0;

   ResetLastError();

   int copied = CopyBuffer(adxHandle, 0, 0, 1, adxBuffer);
   if(copied != 1)
   {
      int err = GetLastError();
      if(err == 4807 || err == 4073)     // not ready / ainda calculando
         return -1.0;                    // retry no próximo tick (sem sleep no tester)
      Print("[ADX] CopyBuffer failed | Error=", err);
      return -1.0;
   }

   double value = adxBuffer[0];
   if(value <= 0.0)
      return -1.0;

   return value;
}

bool ADX_OK()
{
   double adx = GetADX();
   if(adx < 0.0)
      return true;                       // fail-open: sem dado não bloqueia
   return (adx >= MinimumADX);
}
```

Consumidores (`ValidationEngine`, `AIEngine`, `DecisionEngine`): tratar `GetADX() < 0` como **skip
neutro** (não como rejeição). Após o fix, rodar **DIAG_T6 repro** → aceite: trades > 0.

---

## 4. Matriz IA ON/OFF + SL/TP (após 1–3)

| Cenário | IA | ADX fix | SL/TP | Objetivo |
|---|---|---|---|---|
| Baseline | OFF | — | 300/600 | referência (DIAG_A, PF 0,80) |
| A | ON | — | 300/600 | confirmar PF > 1 (DIAG_F, PF 1,007) |
| B | ON | ✅ | 300/600 | validar filtros desbloqueados |
| C | ON | ✅ | 200/400 e 150/300 | robustez / WR efetiva ≥ breakeven |

Model=0 (ticks reais), XAUUSD M5, mesmos filtros do live (AI/ADX fora os testados), 35d + janelas
de validação (2 períodos distintos) para evitar overfit. PF da matriz **não conta** para o gate —
é indicativo; o gate usa a janela limpa.

---

## 5. Gate financeiro 20.15 (critérios, inalterados)

PF ≥ 1,0 (janela limpa 20.14) + DD aceitável + expectancy positiva + reconciliação 20.8 limpa +
sem incidentes críticos recorrentes (dup-exec, close-storm, modify-loop). **PF 1,01 de 1 cenário
não abre gate** — só com robustez + forward.

---

## 6. Rollback padrão (qualquer item)

1. Recompilar baseline 24/08 → 0/0 → reanexar 11 charts.
2. Verificar hashes `XAU_AI_PRO.mq5`/`Core\SignalCore.mqh` vs manifesto 20.1.
3. Journal limpo; janela limpa reiniciável a partir de novo marco (se necessário).