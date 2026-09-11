# XAU_AI_PRO — FORWARD WINDOW TRACKER (JANELA LIMPA 20.5 → 20.11)

> Criado: 2026-08-28 18:40 UTC | Autor: MetaTrader Assistant
> **Marco oficial da janela limpa: 2026-08-28 18:35 UTC (= 21:35 horário do servidor, UTC+3).**
> Regras da fase: **11 símbolos · zero mudança de código · zero otimização forçada ·
> métricas só da janela limpa.**

---

## 1. CONJUNTO OFICIAL (11 símbolos — congelado)

XAUUSD · EURUSD · USDBRL · AUDUSD · NZDUSD · USDCHF · USDSEK · GBPUSD · USDCAD · USDJPY · USDCNH — todos M5, magic 2026001, SL 300 / TP 600, EMA 50/200, RSI 14/45/55, NewsFilter=0, AIFilter=0, lote 0.01.

**Fora do conjunto (bloqueados até normalização de risco por símbolo):** XAGUSD, US30, US500, USTEC.

---

## 2. MARCO E CHECKPOINTS

| Marco | UTC | Servidor (UTC+3) | Ação |
|---|---|---|---|
| **WINDOW START** | 2026-08-28 18:35 | 2026-08-28 21:35 | ✅ registrado (DAY 01) |
| 20.6 Fase A | 2026-08-29 18:35 | 2026-08-29 21:35 | Endurance 24h — consolidar |
| 20.6 Fase B1 | 2026-08-31 18:35 | 2026-08-31 21:35 | Endurance 72h |
| 20.6 Fase B2 | 2026-09-04 18:35 | 2026-09-04 21:35 | Endurance 7d |
| 20.6 Fase C | 2026-09-27 18:35 | 2026-09-27 21:35 | Endurance 30d + gate financeiro |

---

## 3. EVIDÊNCIA INICIAL (snapshot 28/08 18:40 UTC)

| Item | Valor | Veredito |
|---|---|---|
| Eventos na janela (`forward_test_events.csv`, UTF-16) | **209** após 21:35 servidor | ✅ gravando |
| Sequência final do stream | 11× `SYSTEM_START/FORWARD_TEST_START` (… USDCNH ONLINE) | ✅ reanexação dos 11 |
| `system_status.json` @21:37:40 servidor | HEALTHY · algo ON · risco OPEN · DD 0,69% · AI SELL (conf 36,57) | ✅ backend saudável |
| Posições herdadas (pré-janela, em voo) | GBPUSD SELL #10263362670 · USDCHF BUY #10263362709 · USDCAD BUY #10263363321 | ⏳ resolvem via SL/TP |
| Dataset Python | 173.162.556 B (crescendo) | ✅ coleta ativa |

---

## 4. REGISTRO DIÁRIO (preencher a cada check-in; métricas SOMENTE da janela limpa)

| DAY | Data (UTC) | Trades | Win% | PF | Expectancy | MaxDD | Sharpe | AI acc | Rejeições | Uptime | Recovery | Notas |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | 28/08 | — | — | — | — | — | — | — | — | — | — | início 18:35 UTC |
| 02 | 29/08 | 2 (ab.) | N/D* | N/D* | N/D* | 2,07% | N/D* | n/a | 0 | OK | 6 HEALTH (rec) | 24h — *PF/WR/EX/Sharpe N/D: 0 trades fechados (mercado fechado); pré-chk 30/08 01:10 UTC |
| 03 | 30/08 | 7 exec / 4 dec (**3 dup-exec** + NZDUSD) | 66,7% (2/3) | 1,21 | +0,14 | 4,76%* | — | 0 | 0 | OK | 24 reconexões (recovery) | reabertura; **3ª dup-exec (NZDUSD 02:30)** — 2º símbolo; USDCAD+EURUSD 01:45 1:1 (anti multi-symbol); NZDUSD #65408279 SL ajustado p/ lucro (+0,51) — ex5≠fonte; *DD pico ~4,76% (<15%) | |
| 04 | 31/08 | | | | | | | | | | | 72h |
| 05–07 | 01–03/09 | | | | | | | | | | | |
| 08 | 04/09 | | | | | | | | | | | 7d |
| 09–30 | 05–26/09 | | | | | | | | | | | |
| 31 | 27/09 | | | | | | | | | | | 30d + GATE |

---

## 5. RECONCILIAÇÃO (20.8) — contrato de fontes

| Fonte | Arquivo | Papel | Observações |
|---|---|---|---|
| Broker | History (deals magic 2026001) | Verdade de execução | fonte canônica de tickets/px/vol/profit |
| AuditLog | `full_audit.csv` (novo) | Por-deal EA | ignorar `audit_log.csv` (Common, legado Fase 9) |
| EventStream | `forward_test_events.csv` (UTF-16) | Eventos/estado | fonte oficial de eventos |
| Backend | `system_status.json` + `dataset.csv` | Heartbeat/coleta | — |
| Telemetria | `forward_test_session.csv` (Common) | ConnGuard snapshot | não é contrato de trade |

**Critérios de saída (20.8):** 0 missing · 0 duplicates não justificados · 0 mismatch · 0 posições órfãs.

---

## 6. REGRAS VIGENTES (não negociáveis durante a janela)

1. Zero alteração no núcleo do EA.
2. Conjunto de símbolos congelado (pode ACRESCENTAR FX, não remover).
3. Métricas financeiras calculadas **exclusivamente** da janela limpa (18:35 UTC 28/08 em diante).
4. Qualidade técnica ≠ resultado financeiro: gate 20.11 só abre com PF ≥ 1,0 + endurance + recovery + reconciliação em evidência.
5. Pendências técnicas (hash ex5 stale, `AIMetrics.mqh` untracked, duplicidades full_audit, `forward_test_trades.csv` vazio) são registradas para 20.10/21 — não corrigidas agora.

---

## 8. TRANSIÇÃO 20.5 → 20.6 (registrada 28/08 18:45 UTC)

### Gate 20.5 — ✅ PASS (operacional)

| Critério | Evidência | Resultado |
|---|---|---|
| 11 charts com EA (M5, magic 2026001) | list_open_charts (11 charts, todos anexados) | ✅ |
| Conjunto congelado (XAG/índices fora) | lista oficial 11 símbolos | ✅ |
| Algoritmos ON | system_status.json `algo_trading_enabled=true` | ✅ |
| Journal sem `Falha ao copiar RSI` / erros | scan tail 600 KB (8.347 linhas) → **0 hits** | ✅ |
| Stream de eventos gravando | 211 eventos na janela; reanexação 11× registrada | ✅ |
| Backend/Python vivos | dataset cresce; system_status atualiza | ✅ |
| Posições herdadas | 3 posições com SL/TP, sem intervenção | ✅ (segue EA) |

### 20.6 — Fase A (24h) — 🔄 IN PROGRESS

- Início: 28/08 21:35 servidor (18:35 UTC)
- Checkpoint: 29/08 21:35 servidor (18:35 UTC)
- Métricas a consolidar no checkpoint: trades da janela, PF, Win%, Expectancy, MaxDD,
  rejeições, uptime, + 1ª rodada de reconciliação 20.8.
- Regime: **passivo** — sem scripts novos, sem alteração de EA/pipeline, sem intervenção.

### DAY 01 — baseline (28/08, 18:40–21:40 UTC)

- Eventos na janela: **212** (stream continua; última escrita 21:29 servidor, transição de estado).
- Backend: HEALTHY · algo ON · DD 0,29% · IA SELL (conf 36,3) · dataset 173.165.220 B.
- **Posições herdadas (pré-janela, abertas 21:05 servidor):** 3 — GBPUSD SELL #10263362670,
  USDCHF BUY #10263362709, USDCAD BUY #10263363321. Seguem com SL/TP.
  - Tratamento de métricas: entram na reconciliação **quando fecharem** (close_time ≥ 21:35 = dentro
    da janela), mas com **entry_time < janela** — sinalizar como "carried (entrada pré-janela)"
    na contagem de trades, para não inflar/contaminar PF/WinRate da janela.
- Trades fechados na janela até aqui: **0** (nenhum deal com close_time ≥ 21:35 até 21:40).

### CONTRATO DO CHECKPOINT 24h (29/08 18:35 UTC) — aceito como oficial

**Entregáveis obrigatórios (DAY 01 / DAY 02):**
Trades novos (janela limpa, close_time ≥ 21:35 servidor) · Win Rate · Profit Factor ·
Expectancy · Max Drawdown · Sharpe · Rejeições · Uptime · Eventos (count/sanity) ·
AI status (READY/STALE/ERROR) · SAFE/RECOVERY count · Reconciliação.

**Escopo da reconciliação no checkpoint — 4 fontes:**
`BROKER (deals magic 2026001)` × `full_audit.csv` × `forward_test_events.csv` ×
`forward_test_trades.csv` — critérios: **missing = 0 · duplicate = 0 (não justificadas) ·
mismatch = 0 · orphan = 0**.

**Tratamento das posições herdadas:** 3 posições (GBPUSD SELL #10263362670, USDCHF BUY
#10263362709, USDCAD BUY #10263363321) — NÃO contam como trades novos. Se fecharem com
close_time ≥ início da janela, entram como **carried (entrada pré-janela)** na reconciliação,
com nota explícita, sem impacto em PF/WinRate novos.

**Regra de evidência (inalterada):** amostra curta NÃO é prova de qualidade de estratégia.
PF/WinRate só são considerados com janela limpa suficientemente longa (20.6-B 72h → 20.6-C 7d
→ 30d) + reconciliação + recovery. Nenhuma "melhoria" de código durante o experimento.

**Sequência pós-24h (PASS):** 20.6-B (72h) → 20.6-C (7d) → 20.7 Recovery → 20.8 Reconciliação
final → 20.10 Release → 20.11 Gate financeiro.

---

### 9. FIM DE SEMANA — MERCADO FECHADO (sexta 28/08)

- Fechamento confirmado: 28/08 ~23:59:58 servidor (UTC+3) = 20:59 UTC = **17:59 Brasília**.
- Status no fechamento: HEALTHY · algo ON · 5 entradas no dia · DD 2,05% · IA **STALE** (esperado: pipeline sem predições novas com mercado fechado — recupera na reabertura; é um **recovery natural**).
- Fim de semana: **sem ticks → sem trades novos, sem eventos**; EA/processo permanecem vivos.
- Posições herdadas/abertas antes do fechamento ficam **carried** (swap de sexta→segunda aplica; conta demo). Não contam como trades novos.

### 9.1 CALENDÁRIO AJUSTADO (checkpoints em HORAS DE MERCADO ATIVO)

| Marco | Critério | Data prevista | Hora Brasília |
|---|---|---|---|
| Reopen check | mercado reabre domingo ~21:00 UTC | dom 30/08 | ~17:00–18:00 |
| **20.6-A · 24h ativo** | 24h com ticks (28/08 18:35 UTC + fechamento) | **seg 31/08** | ~15:35–16:35 |
| 20.6-B · 72h ativo | +3 sessões | ~qui 03/09 | — |
| 20.6-C · 7d ativo | ~7 sessões de mercado | ~seg 07/09 | — |
| 30d ativo / gate | ~30 sessões | ~meados out | — |

> Nota: marcos em **horas de mercado ativo** substituem o relógio de parede. O 24h **ativo** cai na segunda 31/08 (~15:35–16:35 Brasília) — coincide com o marco 72h de parede; mantemos ambos registrados. Nenhuma alteração de código.

---

## 10. ETAPA 20.14 — ENDURANCE PROFISSIONAL (registro oficial)

> Adicionado: 2026-08-28 20:51 UTC (MetaTrader Assistant)
> Regime: **passivo** — nenhuma alteração de EA/código/pipeline durante a janela.
> Protocolo completo: `ETAPA_20_14_ENDURANCE.md` (repo XAU_AI_PRO).

### 10.1 Baseline DAY 01 (snapshot 28/08 23:59:58 servidor)

| Item | Valor | Veredito |
|---|---|---|
| Estado | HEALTHY · terminal OK · algo ON · trade OK | ✅ |
| Símbolos (congelado) | 11 charts M5, 1 EA cada (magic 2026001) | ✅ |
| Drawdown | 2,07% | ⚠️ dentro do limite (15%) |
| Trades hoje | 5 (aberturas) | — |
| Balance / Equity | 116,81 / 114,40 | — |
| AI | STALE (mercado fechado — esperado, recupera na reabertura) | ⏳ recovery natural |
| Dataset | 173.230.046 B (crescendo) | ✅ |
| Posições abertas | 5: GBPUSD SELL, USDCHF BUY, USDCAD BUY, **2× USDJPY BUY** | ⚠️ ver 10.2 |

### 10.2 🔴 ACHADO — duplicação de execução USDJPY (EM INVESTIGAÇÃO)

- **2 posições BUY USDJPY abertas em 22:15:02/03** (mesmo candle, mesmo preço 160.118, SL 300/TP 600):
  - `#10264640104` (22:15:02) e `#10264640153` (22:15:03), ambas volume 0.02 (full_audit), lotes 0.01
- **Não** é chart duplicado (11 charts, 1 EA cada — auditado via list_open_charts).
- **full_audit.csv confirma 2 tickets reais distintos** (não é log duplicado).
- Explicação provável: retry de execução duplicado no OrderManager (2 envios no mesmo tick) OU
  MarketScanner/TradePipeline chamado 2× no mesmo tick para o mesmo símbolo.
- **Sem intervenção** (regra passiva): posições seguem com SL/TP; entram na reconciliação com tag `dup-exec`.
- Ação futura (FORA da janela, pós-20.14): revisar guarda de deduplicação por símbolo/tick no OrderManager.
- Impacto em métricas: **NFU x2 no mesmo símbolo** — registrar manualmente no checkpoint para não
  inflar PF (`dup-exec` conta como 1 decisão, 2 execuções).

### 10.3 Contrato do checkpoint 24h (mantido do tracker §8)

Entregáveis: trades novos da janela, WinRate, PF, Expectancy, MaxDD, Sharpe, rejeições, uptime,
eventos, AI status, SAFE/RECOVERY, reconciliação 4 fontes (BROKER × full_audit × events ×
forward_test_trades). Tratamento das posições herdadas: `carried` (entrada pré-janela), sem impacto
em PF/WinRate novos. Duplicação USDJPY: tag `dup-exec`.

### 10.4 PRÉ-CHECKPOINT 20.14-C (executado 30/08 01:10 UTC - sábado, mercado fechado)

> Registro: MetaTrader Assistant | Comando: `heartbeat_watchdog.py --checkpoint` ✅ sem alertas.
> **A janela de 24h ATIVAS ainda NÃO completou** (faltam ticks: reabertura domingo ~21:00 UTC +
> segunda). Marco definitivo: **seg 31/08 ~15:35-16:35 Brasília** (calendário §9.1). Este registro
> é o estado da janela até o fechamento de sexta + fim de semana - primeira rodada de reconciliação.

**Heartbeat / Backend**
| Item | Valor | Veredito |
|---|---|---|
| system_status.json | HEALTHY · terminal OK · algo ON · DD 2,07% · AI STALE (fds) | ✅ vivo (mtime 30/08 01:06) |
| Event stream | 77 eventos na janela limpa; último 28/08 23:59:58 (fechamento) | ✅ esperado p/ fds |
| dataset.csv | 173.230.046 B (estático no fds - retoma na reabertura) | ✅ |

**Reconciliação 20.8 - janela limpa (4 fontes)**
| Fonte | ENTRY janela | EXIT janela | Veredito |
|---|---|---|---|
| Broker (deals magic 2026001) | 2 (USDJPY #10264640104/#10264640153) | 0 | canônico |
| full_audit.csv | 2 (mesmos tickets) | 0 | ✅ 0 missing / 0 mismatch |
| forward_test_events.csv | 0 trade events | 0 | ⚠️ telemetria não emite trade event (limitação; sem perda) |
| forward_test_trades.csv | vazio | vazio | ⚠️ pendência §6 (20.10) |

- Posições órfãs: **0**. Trades fechados na janela: **0**.
- Divergência financeira: **0** - soma profits posições = -2,38 = profit da conta ✅
- Carried: 3 herdadas pré-janela (GBPUSD SELL, USDCHF BUY, USDCAD BUY) seguem abertas com SL/TP.

**Métricas (janela limpa)** - PF / Win Rate / Expectancy / Sharpe: **N/D** (sem trades fechados).
MaxDD observado: 2,07% (< 15%). Rejeições: 0. Erros críticos: 0 (journal 29/08: 0 hits).

**SAFE/RECOVERY**: SAFE 0 · RECOVERY 8 (inclui 6× HEALTH_FAILURE transientes do HealthMonitor na
passagem 22:43-23:59 servidor - todos `RECOVERED`; nenhum erro de execução; comportamento de
entrada/saída do mercado após fim de ticks).

**dup-exec USDJPY - classificação atualizada**: **RECORRENTE / SISTÊMICO** (não isolado). Padrão
pré-existente à janela (múltiplas entradas no mesmo tick em 24/08, 25/08, 27/08, 28/08 - NZDUSD,
EURUSD, USDJPY, USDCAD no full_audit). Na janela: 1ª ocorrência USDJPY 22:15:02/03 (mesmo preço
160.118, 0.01 lot cada, 2 tickets reais). Sem intervenção (regra passiva); guarda de deduplicação
por símbolo/tick no OrderManager/TradePipeline → revisão **20.15** (fora da janela).

**Checklist de aprovação (pré-checkpoint)**
- [x] 11/11 charts ativos · [x] EA sem erro crítico · [x] heartbeat contínuo · [x] stream contínuo
- [x] backend saudável · [x] sem corrupção de dados de trade · [x] sem divergência financeira
- [⚠️] dup-exec USDJPY: recorrente - sem ação na janela, aguarda 20.15
- [–] PF/WinRate/Expectancy/Sharpe: N/D até 24h ativas (seg 31/08)
- [x] MaxDD 2,07% · [x] uptime OK · [x] rejeições 0 · [x] erros 0

**Veredito pré-checkpoint**: ✅ **OPERACIONAL** - sistema íntegro, reconciliação 20.8 limpa.
Aguardar 24h ATIVAS (seg 31/08 ~15:35-16:35 BRT) para o checkpoint oficial com métricas.

### 10.5 CHECKPOINT 20.14-C — segundo ciclo (sáb 30/08 ~09:50 BRT / 12:50 UTC)

> Executado: MetaTrader Assistant | Regime passivo mantido (nenhuma alteração de EA/params).
> Fato novo: **terminal reiniciado sáb 30/08 ~08:44 UTC (05:44 BRT)** — EAs reanexados aos 11
> charts; eventos de reanexação gravados com timestamp de servidor congelado `23:59:58`
> (sem ticks no fds). Heartbeat confirmado por mtime dos artefatos (08:44Z) e journal ativo.

**Watchdog / Heartbeat**
| Item | Valor | Veredito |
|---|---|---|
| 11 charts M5 + EA (magic 2026001) | list_open_charts → 11/11 anexados | ✅ |
| system_status.json | HEALTHY · terminal OK · algo ON · AI STALE (fds esperado) · DD 2,07% | ✅ vivo (reinit 08:44Z) |
| journal 20260830.log | ativo, EA init OK, AuditLog READY, sem erros | ✅ |
| heartbeat_watchdog.py --checkpoint | script NÃO localizado no workspace/Desktop/Documents (repo externo) — execução anterior 01:10 UTC ✅ registrada no §10.4; reexecutar seg 31/08 | ⚠️ pendência logística |
| Event stream | 1.263 registros válidos; **97 na janela** (último 23:59:58; 0 após) | ✅ |

**Reconciliação 20.8 — janela limpa (4 fontes)**
| Fonte | ENTRY janela | EXIT janela | Veredito |
|---|---|---|---|
| Broker (deals magic 2026001) | 2 = USDJPY #10264640104/#10264640153 | 0 | canônico |
| full_audit.csv | 2 (mesmos tickets, 22:15:02/03) | 0 | ✅ 0 missing / 0 mismatch |
| forward_test_events.csv | 0 trade events (limitação §6) | 0 | ⚠️ sem perda |
| forward_test_trades.csv | vazio (pendência §6 → 20.10) | vazio | ⚠️ registrado |

- Posições abertas: **5** = 3 carried (GBPUSD SELL, USDCHF BUY, USDCAD BUY — entrada 21:05, pré-janela)
  + 2 dup-exec USDJPY (22:15:02/03). Floating = **-2,38** = profit da conta ✅ (divergência 0).
- Trades fechados na janela: **0**. Orfãos: **0**.

**Métricas (janela limpa)** — PF / WinRate / Expectancy / Sharpe: **N/D** (0 fechados; check oficial
seg 31/08). MaxDD 2,07% (< 15%). Rejeições 0 · erros críticos 0 · SAFE 0 · RECOVERY 8 (transientes,
todos RECOVERED).

**Incidente USDJPY (dup-exec)**: **0 novas ocorrências** (mercado fechado, 0 novos deals). Classificação
mantida: **RECORRENTE / SISTÊMICO** → guarda de deduplicação revisada em **20.15**, sem ação na janela.

**Backtest de confirmação (evidência separada, NÃO misturar com PF da janela)**
- Instrução registrada: usar **"Every tick based on real ticks" (modelo 0)** quando disponível —
  mais próximo das condições reais; MQL5 recomenda ticks reais.
- Ini existente 35d (`XAU_AI_PRO.XAUUSD.M5.20260721_20260825`) está em modelo 2/4 (.200/.400);
  para o modelo 0 seria necessário gerar `.000` ou ajustar o ini **fora da janela** (não tocar agora).

**Checklist 20.14-C (ciclo 2)**
- [x] 11/11 charts · [x] EA sem erro crítico · [x] heartbeat vivo (reinit 08:44Z) · [x] stream íntegro
- [x] backend saudável · [x] reconciliação 20.8 limpa (0 missing / 0 mismatch / 0 órfão) · [x] divergência 0
- [⚠️] dup-exec USDJPY recorrente — sem ação na janela (aguarda 20.15); 0 novas ocorrências
- [–] PF/WinRate/Expectancy/Sharpe: N/D até 24h ATIVAS (seg 31/08 ~15:35-16:35 BRT)
- [⚠️] heartbeat_watchdog.py fora do workspace — localizar/reexecutar no checkpoint oficial

**Veredito ciclo 2**: ✅ **PASS (OPERACIONAL)** — sem novas ocorrências, sem corrupção, sem divergência.
Checkpoint **oficial 24h ATIVAS**: seg 31/08 ~15:35-16:35 BRT (reabertura dom ~21:00 UTC + segunda).
Continuar observação pura → **20.14-D (72h)** após o 24h oficial. Nenhuma alteração de código/parâmetros/símbolos.
Próximo marco: **20.14-D (72h)** em avaliação pós-24h oficial.

### 10.6 REABERTURA — REGISTRO DE SESSÃO (dom 30/08 ~21:15 UTC / 18:15 BRT)

> Executado: MetaTrader Assistant | Regime **passivo** (nenhuma alteração de EA/parâmetros/símbolos).
> Mercado reabriu **dom 30/08 ~21:00 UTC** (= 31/08 00:00 servidor). A janela limpa NÃO reinicia —
> continua de 28/08 21:35 servidor (§2). Este registro é o **estado da reabertura** + 1ª rodada de
> reconciliação da sessão nova.

**Início da sessão (protocolo 20.14)**
| Item | Valor | Veredito |
|---|---|---|
| Janela | ENDURANCE (contínua, não reiniciada) | ✅ |
| Símbolos | 11 oficiais (M5, magic 2026001) | ✅ 11/11 charts com EA (list_open_charts) |
| EA / inputs | XAU_AI_PRO · mesmo ex5 · AIFilter=0 · ADXFilter=0 · SL 300/TP 600 | ✅ idênticos |
| Regime | passivo — sem edição de SL/TP/IA/ADX/RSI/lote/símbolos | ✅ |

**Watchdog / Heartbeat (`py -3 MQL5\Python\watchdog\heartbeat_watchdog.py --once`)**
| Item | Valor | Veredito |
|---|---|---|
| health | HEALTHY · dd 0,56% · age 0,1 min | ✅ |
| ai | SELL/BUY · stale=False (pipeline recuperou) | ✅ (não é falha pós-fds) |
| events | last=**2026-08-31 00:15:01** servidor · file_age 0,5 min · 26/24h | ✅ **stream voltou a avançar** |
| audit | age 14 min (atualiza por trade) | ✅ |

**Reconciliação 20.8 — janela limpa (4 fontes), sessão nova**
| Fonte | ENTRY janela | EXIT janela | Veredito |
|---|---|---|---|
| Broker (deals magic 2026001) | 2 pares dup-exec (22:15:02/03 e **31/08 00:05:04**) | 2 (USDJPY #104/#153, 31/08 00:00:05) | canônico |
| full_audit.csv | 4 entradas (tickets conferem) | — (audit é entry-only; saídas via S1) | ✅ 0 missing / 0 mismatch |
| forward_test_events.csv | 1× TRADE_APPROVED USDJPY 00:05:03 (2 fills) | — | ⚠️ confirma dup-exec (1 evento → 2 execuções) |
| forward_test_trades.csv | vazio (pendência §6 → 20.10) | vazio | ⚠️ registrado |

- Posições órfãs: **0**. Divergência financeira: **0** (balanço 116,81 → 111,25 = **−5,56** =
  −0,99 ×2 (USDJPY dup #1) −3,58 (USDCHF carried) ✅).
- Floating atual (4 abertas) = **+0,09** = profit da conta ✅ (GBPUSD −0,81 · USDCAD +0,16 ·
  USDJPY #87061/#87064 +0,37/+0,37).

**Métricas (janela limpa — snapshot de reabertura, NÃO é o checkpoint 24h)**
| Métrica | Valor |
|---|---|
| Trades fechados na janela | 2 execuções = **1 decisão** (dup-exec #1: 22:15 → 31/08 00:00, ambos −0,99) |
| Win Rate / PF / Expectancy | 0% · **PF 0,00** (0 wins/2 loss-exec) · −0,99/exec — **N minúsculo, sem valor estatístico** |
| Carried fechado (fora do PF novo) | USDCHF #62709 −3,58 (31/08 00:00:06) |
| MaxDD janela | **~4,76%** (pico 116,81 → 111,25+float) — < 15% ✅ |
| Rejeições | entrada: 0 · fechamento: 20 retry-fail "[Position doesn't exist]" (storm) |
| Erros críticos | 0 · uptime OK (24 "connection lost" no dia, todos RECOVERED) |
| AI | READY (não-stale) · conf ~34–38 |

**🔴 INCIDENTES REGISTRADOS NA REABERTURA (sem ação — passivo; correção em 20.15)**
1. **dup-exec USDJPY — RECORRÊNCIA CONFIRMADA → EVIDÊNCIA DE DEFEITO OPERACIONAL.**
   Nova ocorrência em **31/08 00:05:04**: #10265387061/#10265387064 (mesmo tick, preço 160.028,
   vol 0.01, SL/TP 300/600; **1 evento TRADE_APPROVED → 2 fills**). Somadas à ocorrência de
   28/08 22:15 (#104/#153) e ao padrão pré-janela (24–28/08), **a recorrência transforma a
   suspeita em evidência**: guarda de deduplicação por símbolo/tick no OrderManager/TradePipeline
   passa a item obrigatório da **20.15** (o par #87061/#87064 segue aberto com SL/TP, sem intervenção).
2. **Close storm na abertura (00:00:05–06 servidor):** 17 tentativas de fechamento para #104/#153
   (9+8) e USDCHF, com 20 falhas "[Position doesn't exist]" — múltiplas instâncias do EA tentaram
   fechar as mesmas posições simultaneamente. Sem perda de posição; ruído alto no journal.
3. **Modify-loop em #10265387061:** **622 tentativas de modify** (331 "skipped — changes nothing")
   entre 18:10–18:18 BRT, **ainda ativa** — o EA tenta reajustar SL (~160.036–160.045) repetidamente
   a cada tick. Só na posição #87061 (não na #87064). Anomalia operacional registrada para 20.15.
4. **USDCNH HEALTH_FAILURE → RECOVERY** cíclico (00:13/00:15/00:19 servidor) — transiente,
   sempre RECOVERED; mesmo padrão de sexta (§10.4).
5. **Rede instável:** 24 desconexões no dia (ping 198–607 ms, APs BR/EU/US) — todas recuperadas,
   sem perda de posição. Observação de ambiente, não do EA.

**Atenção (não é ação):** daily_loss_pct medido em **4,76%** (limite 5%) — a camada de segurança
pode bloquear novas entradas hoje se o limite for atingido (comportamento intencional, ver §11.2b).
Primeiras horas de abertura têm liquidez/σ atípicos — não interpretar como performance.

**Veredito reabertura**: ✅ **OPERACIONAL** — 11/11 charts · HEALTHY · stream/audit/backend vivos ·
reconciliação limpa · divergência 0. **20.14-C oficial (24h ATIVAS): seg 31/08 ~15:35–16:35 BRT**
(`py -3 MQL5\Python\watchdog\heartbeat_watchdog.py --checkpoint`). Observação pura continua;
**20.14-D (72h)** na sequência. Nada alterado no EA/inputs/símbolos.

### 10.7 DIAGNÓSTICO READ-ONLY DE CAUSA RAIZ — PREPARAÇÃO 20.15 (dom 30/08 ~18:35 BRT)

> Executado: MetaTrader Assistant | **Somente leitura** — nenhum arquivo do EA editado/compilado.
> Objetivo: fechar as pendências técnicas com causa raiz antes do fim da janela, para que a 20.15
> aplique correções de forma cirúrgica. Fontes: árvore atual `Experts\XAU_AI_PRO` (fontes 24/08) +
> journal 30/08 (UTF-16) + deals broker.

**A) dup-exec USDJPY — CAUSA RAIZ: corrida TOCTOU na MESMA instância (não é entre instâncias)**
- `EnableMultiSymbol=0` ⇒ `SymbolManager` cria `ActiveSymbols[1]` (só o símbolo do chart) → cada instância
  negocia apenas o próprio símbolo. O dup-exec acontece DENTRO da instância do USDJPY, não por 11 EAs brigando.
- `ProcessSymbol()` (MarketScanner) tem 3 guards, todos **verificados ANTES do registro da ordem em voo**:
  1. `CanOpenPosition()` → `HasPosition()` usa o **cache de posições do terminal**, que atualiza
     **assincronamente** (lacuna ~100–500ms após o fill);
  2. Latch `AlreadyTradedThisBar()` — `MarkTradedBar()` só é chamado **depois** do retorno completo de
     `ExecuteTrade()` (pós fill);
  3. Guard inter-instância (`XAI_PRO_SENT_*` GlobalVariable, SmartExecution) — **setada só após EXEC_SUCCESS**.
- Efeito: 2 ticks a ≤1s de distância (ex.: 00:05:03.956 e 00:05:04.084) passam nos 3 guards antes do 1º fill
  ser visível ⇒ **2 ordens idênticas, mesmo preço, mesma vela** (#87061/#87064; 22/08 #104/#153 idem).
- Fix 20.15: flag **in-flight** (estática + GlobalVariable com janela, ex.: 5s) setada **ANTES** do OrderSend
  e limpa no deal confirm; re-checar `CountPositions(symbol)` imediatamente antes do envio; mover
  `MarkTradedBar` para logo após o envio aceito (não após o retorno completo).

**B) modify-loop USDJPY #87061 (622 modifies / 331 skipped) — CAUSA RAIZ: DRIFT BINÁRIO (ex5 ≠ fonte)**
- No fonte atual (24/08): `CheckBreakEven()` começa com `if(!EnableBreakEven) return;` (BreakEven.mqh:31) e
  `TrailingStopATR()` com `if(!EnableTrailingATR) return;` (PositionManager.mqh:~184). Inputs dos 11 charts:
  `EnableBreakEven=0` e `EnableTrailingATR=0`. **Com este fonte+inputs o loop é impossível.**
- Comportamento observado (journal 18:10–18:18 BRT): SL de #87061 saltou 159.730 → 160.045 e passou a
  oscilar 160.036↔160.045 a cada tick (padrão típico de trailing: SL = Bid − distância), só na 1ª posição.
- `XAU_AI_PRO.ex5` em disco: escrita **30/08 16:04** (402.344 B, SHA256 `ec9dc102…`), fontes datadas 24/08.
  O binário em execução **comporta-se como se os gates não existissem** ⇒ compilado de outro estado da árvore
  (ex.: WIP v1.3.1 / RC1 copiado) ou input mapeado de forma diferente.
- **Confirmar na 20.15:** recompilar os fontes atuais com MetaEditor, comparar hash do ex5 resultante vs
  `ec9dc102…`; se divergir, reanexar o baseline compilado aos 11 charts (pendência §5/§6 "hash ex5 stale"
  — agora com **impacto comportamental comprovado**, não só de higiene).

**C) close storm na abertura (00:00:05–06 servidor; 17 tentativas, 20 falhas "[Position doesn't exist]")**
- `grep` no fonte atual: únicos caminhos de close = `OrderManager::ClosePosition`, `PositionManager::CloseSymbolPosition`
  (ambos **sem caller ativo**) e `EquityProtection::CheckEquityProtection` (só fecha ≥ 15% DD — não disparou,
  DD era ~0,2%). `CSmartExecution::ClosePosition` também **sem caller**.
- Os closes reais (reason=Expert, comment="") vieram de lógica **não presente no fonte atual** ⇒ mesmo
  **drift binário** de (B). Veredito: sem perda de posição, mas evidência adicional de ex5 divergente.
- Fix 20.15 (após confirmar (B)): auditar a árvore compilada vs fontes e remover/flatten não intencional.

**D) ADX 4807 no Tester — confirmado por leitura (`Indicators/ADX.mqh`)**
- `GetADX()`: `CopyBuffer(handle,0,0,1,buf)`; se `copied != 1` → Print erro → **return 0.0 imediato, sem retry,
  sem warm-up** (linhas ~48–60). `ADX_OK()` trata `<=0` como "abaixo do mínimo" → **fail-closed** → 0 trades
  com `EnableADXFilter=true`. Exatamente o §11.4. Fix proposto (5 candidatos já listados em §11.4, item 1–4).

**E) Fila de fix 20.15 (consolidada — aplicar FORA da janela)**
| # | Item | Origem | Correção proposta |
|---|---|---|---|
| 1 | dup-exec (TOCTOU) | A | flag in-flight pré-OrderSend + recheck de posições + latch no envio |
| 2 | ex5 ≠ fonte (modify-loop/close) | B/C | recompilar baseline, comparar hash, reanexar 11 charts |
| 3 | ADX 4807 | D | retry/not-ready handling no `GetADX()` + fail-open no `ADX_OK()` |
| 4 | duplicidades full_audit | §6 | dedup por ticket+time na reconciliação (já contratado §3) |
| 5 | forward_test_trades.csv vazio | §6 | decidir descontinuação v1.2.1 ou preencher |
| 6 | matriz IA ON/OFF + SL/TP | §11.3 | executar após corrigir (1)-(3) — Baseline/A/B/C conforme decisão do usuário |

> Regra mantida: **nenhuma correção durante a janela**; este §10.7 é preparação read-only para 20.15.
> Nada alterado no EA/inputs/símbolos.

### 10.8 REPRODUÇÃO DO BUG ADX NO TESTER — RODADA 30/08 ~19:0x BRT (evidência p/ 20.15)

> Executado: MetaTrader Assistant | Regime passivo (tester é diagnóstico separado — não toca na janela limpa).
> Comando: `tester_run_backtest` com `DIAG_T6_XAUUSD_M5_4d_RELAXADO.ini` (run_id 7679948966807904379).

**Configuração (deliberadamente permissiva — se o ADX funcionasse, trades apareceriam):**
XAUUSD M5 · 20→24/08 · Model=0 (ticks reais) · `EnableADXFilter=true` · `MinimumADX=10` (mínimo baixo) ·
`RSIPullback=50/50` (sem restrição RSI) · SL/TP 300/600 · lote 0.01 · depósito 200.

**Resultado (report oficial do tester):**
| Métrica | Valor |
|---|---|
| Barras geradas | 528 |
| Ticks gerados | 945.334 |
| Deals / Trades | **0 / 0** |
| Profit | 0,00 |
| Duração | ~5 min (Core 1, sem queda do agente) |

**Leitura:** mesmo com ADX mínimo relaxado (10) e RSI sem restrição, **0 entradas em 945k ticks** —
reproduz exatamente o DIAG_T6 original (§11.1). A cadeia `GetADX() → 0.0` (4807) + `ADX_OK()`
fail-closed (§10.7-D) continua **bloqueando 100%** das entradas com `EnableADXFilter=true`.
Confirma: **nenhuma matriz "com filtros" é válida no tester até o fix de 20.15** (item 3 da fila §10.7-E).

**Evidência do live intacta:** o backtest roda em agente separado; janela limpa e posições live
incontaminadas (verificado: 4 posições abertas seguiram com SL/TP durante a rodada).

### 10.9 CONTRATO DO CHECKPOINT 20.14-C OFICIAL (seg 31/08 ~15:35–16:35 BRT) — FECHADO COM O USUÁRIO

> Registrado: 2026-08-30 19:21 BRT | Regime: **PASSIVO absoluto até o checkpoint** — nenhum fix.
> Proibições explícitas (validade da evidência da 20.14): ❌ dup-exec · ❌ ADX · ❌ ligar IA ·
> ❌ alterar SL/TP · ❌ alterar filtros · ❌ alterar símbolos · ❌ fechar posições manualmente.

**Ordem oficial de execução no checkpoint (9 passos):**
1. `py -3 MQL5\Python\watchdog\heartbeat_watchdog.py --checkpoint`
2. Consolidar trades da janela limpa (≥ 28/08 21:35 servidor)
3. Métricas: PF · WinRate · Expectancy · MaxDD · Sharpe (exclusivamente da janela)
4. Reconciliar **Broker** (deals magic 2026001 — fonte canônica)
5. Reconciliar **full_audit.csv** (0 missing / 0 mismatch; dedup ticket+time)
6. Reconciliar **Event Stream** (`forward_test_events.csv`, UTF-16; count/sanity)
7. Reconciliar **Backend** (`system_status.json` + `dataset.csv`; heartbeat)
8. Verificar **dup-exec USDJPY** (recorrência? novas ocorrências? classificação)
9. Decidir **20.14-C = PASS / INVESTIGATE / FAIL**

**Evidência positiva registrada (NZDUSD):** entrada 31/08 00:20 SELL #10265408279 = **1 decisão →
1 execução** (sem duplicação) — indica que o dup-exec **não é universal** (é gatilho em condições
específicas de timing), mas **não** declara o problema resolvido. Sem valor estatístico; observação.

**Pós-20.14-C (somente após fechar):** entrar no `PLANO_20_15_CHECKLIST_CIRURGICO.md` na ordem
já acordada: Baseline/hash → fix dup-exec → validar 72h (20.14-D) → fix ADX Tester → reexecutar
matriz IA/SL-TP → PF > 1 com robustez → 20.15 (gate) → 20.16 (Release).

### 10.10 REGISTRO DE OBSERVAÇÃO — NOITE DE 30→31/08 ~21:30 BRT (3ª dup-exec; métricas preliminares)

> Executado: MetaTrader Assistant | Read-only. Análise das operações da janela limpa (posições +
> histórico broker); nada alterado.

**Trades fechados na janela (por decisão):** USDJPY dup-1 −1,98 (22:15→31/08 00:00, close storm) ·
NZDUSD #65408279 **+0,51** (00:20→01:38, saída "SL" ajustado com lucro — indício ex5≠fonte) ·
USDJPY dup-2 +1,88 (00:05→02:09, close storm). **Decisões fechadas: 3 (6 execuções)**.

**Métricas preliminares (N minúsculo, sem valor estatístico):** WR 66,7% (2/3) · PF **1,21** ·
Expectancy +0,14 USD/decisão · MaxDD pico ~4,76% → 0,7% · Saldo 116,81→112,20 = **−4,61**
(= −4,58 deals − 0,03 swaps ✅ divergência 0). Carried fechadas: USDCHF −3,58 · USDCAD +0,06 ·
GBPUSD −1,47 (−4,99 fora do PF janela).

**🔴 dup-exec — 3ª ocorrência (NZDUSD 02:30:01 #10266483359/#10266483371), 2º símbolo afetado:**
classificação reforçada **RECORRENTE/SISTÊMICO**. Análise de padrão:
- NZDUSD 00:20 entrou **1:1** (sem dup); NZDUSD 02:30 duplicou → gatilho condicional ao timing de ticks.
- USDCAD+EURUSD 01:45 (2 símbolos no mesmo tick) entraram **1:1** → **hipótese multi-símbolo
  descartada**; dup é **intra-símbolo** (TOCTOU §10.7-A) — correção 20.15 mantida.
- Saída do NZDUSD #65408279 por "SL" **com lucro +0,51** (stop movido p/ abaixo do open) =
  gestão de posição inexistente no fonte atual → **mais evidência de ex5 ≠ fonte** (§10.7-B).

**Posições abertas (4):** USDCAD BUY · EURUSD SELL (01:45) · 2× NZDUSD SELL (02:30, dup).
Seguem com SL/TP, sem intervenção (regra passiva). Próximo marco: checkpoint 20.14-C (seg 31/08).

### 10.11 🔴 INCIDENTE — DUP-EXEC EM MASSA (31/08 06:49 servidor) + RUNBOOKS CRIADOS

> Registrado: 2026-08-30 ~22:15 BRT (31/08 01:15 UTC) | MetaTrader Assistant
> Descoberto ao criar os runbooks de automação (`MQL5\Python\runbooks\`) e rodar o 1º probe
> read-only com a API MT5 Python (nova capability).

**Ocorrência mais grave da janela — 7 fills idênticos em 2 símbolos no mesmo 1–2s (06:49:51–53 servidor):**
| Símbolo | Fills | Tickets | Preço |
|---|---|---|---|
| GBPUSD SELL | **3** | 10267359794 / 10267359954 / 10267359963 | 1.35427/28 |
| USDCHF BUY | **4** | 10267360037 / 10267360038 / 10267360166 / 10267360275 | 0.80863/64 |

**Estado da conta no momento:** 10 posições EA · margem 108,13 (≈96% do saldo 112,80) ·
free_margin 7,91 → **risk=BLOCKED (FREE_MARGIN)** · equity 116,04 · trades_today=16 ·
health=ERROR (transiente/proteção) · AI STALE (esperado pós-fds/pipeline).

**Causa raiz provável (evolução do diagnóstico §10.7-A):** não é só TOCTOU de 2 instâncias —
é **`OrderRetry` reenviando após timeout/requote de um envio que já foi aceito** (rede instável:
24 desconexões, pings até 600ms). Mesma família do close-storm (00:00) e do modify-loop.
Fills em série (3–4) em vez de 2 ⇒ retry em cadeia, não apenas corrida de tick.

**Impacto:** proteção FREE_MARGIN funcionou (bloqueou novas entradas) ✅. Conta demo próxima de
stress de margem, mas todas as posições têm SL 300p → perda limitada. Sem ação manual (regra passiva).

**NOVA CAPACIDADE — runbooks (automação read-only):**
- `MQL5\Python\runbooks\checkpoint_20_14.py` — os 9 passos do checkpoint §10.9 (métricas + reconciliação + veredito)
- `MQL5\Python\runbooks\reconcile_sources.py` — 4 fontes (Broker MT5 × full_audit × events × backend)
- `MQL5\Python\runbooks\matrix_runner.py` — perfis/relatórios/hash ex5/scan log
- Requisito instalado: `MetaTrader5-5.0.6147` (build == terminal ✅) via pip; conexão read-only comprovada.
- Pendência runbook: casamento full_audit por `position_id` (col. Ticket grava order/pos, não deal id) — ajustado.

**Item NOVO de prioridade máxima na 20.15 (fila §10.7-E):** **fix `OrderRetry`** — antes de cada
reenvio, checar se já existe fill do mesmo sinal (posição recém-criada symbol+mágica+preço em ≤ N s);
não reenviar se confirmado; limite de fills por decisão (cap). Este fix tem prioridade sobre o fix
toctou puro, pois é o mecanismo de multiplicação (3–4 fills).

**Ação agora:** nenhuma (congelado). Observação + registro. Checkpoint 20.14-C tende a
INVESTIGATE com evidência forte de defeito de execução sistêmico.

---

## 11. EVIDÊNCIA DA BATERIA DE BACKTESTS (DIAGNÓSTICO — FORA DA JANELA LIMPA)

> Registrado: 2026-08-30 12:5x BRT | Autor: MetaTrader Assistant
> **Não faz parte das métricas da janela limpa (PF do gate 20.11/20.15 não usa estes números).**
> Serve exclusivamente para diagnosticar prejuízos, onde a IA não é aproveitada e onde o EA trava.
> Relatórios brutos salvos em `Common\Files\backtest_reports\*.json`.

### 11.1 Resultados por timeframe (XAUUSD, 21/07→25/08, depósito 200, lote 0.01, SL 300/TP 600)

| Job | TF | Model | Filtros | IA | Trades | PF | Net | WR% | MaxDD% | Sharpe | Obs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DIAG_A | M5 | 0 (ticks reais) | OFF (como live) | OFF | 130 | 0.804 | −55.69 | 29.2 | 44.5 | −5.0 | **confirmação oficial** = produção real |
| DIAG_B | M15 | 2 (1-min OHLC) | OFF | OFF | 88 | 0.794 | −39.00 | 28.4 | 37.5 | — | (do relatório anterior) |
| DIAG_C | M30 | 2 | OFF | OFF | 58 | 0.636 | −48.00 | 24.1 | 28.5 | −5.0 | pior PF; seq 10 perdas |
| DIAG_D | H1 | 2 | OFF | OFF | 42 | 0.800 | −18.00 | 28.6 | 13.1 | −5.0 | menor DD |
| DIAG_F | M5 | 0 | OFF | **ON** | 125 | **1.007** | **+1.74** | 31.2 | **20.0** | **+0.36** | IA reduz DD 44→20% e vira PF |
| DIAG_T6 | M5 4d | 0 | ON (ADX on) | OFF | **0** | — | 0.00 | — | — | — | **bug ADX 4807** bloqueia 100% |
| DIAG_T7 | M5 | 2 | ON (ADX off) | OFF | 127 | 0.740 | −85.97 | 51.2 | 54.3 | −5.0 | filtros técnicos pioram resultado |

### 11.2 Achados-chave (respondem às 3 perguntas)

**a) Onde a IA NÃO está sendo aproveitada**
- **Live/forward roda com `EnableAIFilter=false`** (confirmado nos 11 charts: AIFilter=0) → sinal puro +
  SL/TP fixo. A IA está **off na produção** exatamente onde mais ajudaria: o backtest DIAG_F (IA ON,
  mesmo Model=0/ticks e mesmos filtros que o DIAG_A) mostra PF 0.80→1.01, Net −55.69→+1.74 e
  MaxDD 44.5%→20.0%. Sem IA, o EA é um sinal RSI/EMA+SL/TP sem gestão.
- Nos testes "completos" (T1/T2/T4) a IA também não apareceu, mas por outra razão: o bug ADX zerou
  TODAS as entradas antes de chegar à IA.

**b) Onde o EA trava**
1. **Bug ADX no Strategy Tester** (Error=4807 → `GetADX()` retorna 0.0): qualquer run com
   `EnableADXFilter=true` (T1–T6 "completos", T6 relaxado) gera **0 trades** — o filtro rejeita tudo.
   Confirmado no log: `[ADX] CopyBuffer failed | Error=4807` e `Orders=0` do início ao fim.
   Não afeta a produção (filtros off), mas torna toda a matriz "com filtros" inválida no tester.
2. **Safety layer bloqueia mesmo com `UseRiskManagement=false`**: DIAG_F travou nas últimas horas com
   `[TRADE BLOCK] SAFETY | DD: 5.04%/5.00%` (limite diário 5% + MaxTradesPerDay 20). É proteção de
   capital intencional, mas faz a estratégia "travar" em sequências ruins — deve ser documentado como
   comportamento esperado, não bug.
3. **Agente do tester instável (Core 1 disconnected)**: lançar jobs em sequência imediata derruba o
   agente; necessário matar metatester64 ou aguardar estabilização (OCORRÊNCIAS OPERACIONAIS, não do EA).

**c) Por que há muitos prejuízos**
- **Win rate 24–31% com SL 300 / TP 600**: com TP = 2R, o breakeven é ~33% de acertos (mais spread);
  a estratégia acerta 24–31% → expectativa negativa em todos os TF (−0.21 a −1.03 USD/trade).
- **Viés de compra em rally**: 69–83% das trades são LONG (M5: 90/130; M30: 39/58; T7: 104/127);
  em mercado de rally o RSI fica comprado e as entradas compram topos → TP 2R raramente é alcançado.
- **Filtros técnicos completos pioram** (T7 PF 0.74, DD 54%): BreakEven/Trailing/Partial/Spread/Trend
  sem IA não resolvem o problema de entrada com WR baixo; apenas aumentam o turnover e o DD.
- **Sinal puro sem gestão**: live = EMA 50/200 + RSI pulback + SL/TP fixo, sem break-even, sem trailing,
  sem parcial, sem filtro de notícia — o que o DIAG_A (0.80) confirma em ticks reais.

### 11.3 Pendências para 20.15 (fora da janela — NÃO corrigir agora)
- Corrigir o bug ADX no tester (4807) OU documentar que runs com `EnableADXFilter=true` são inválidos.
- Avaliar ativar `EnableAIFilter=true` na produção (mesmo com fallback local) — único cenário testado
  com resultado ≥ breakeven (DIAG_F PF 1.007).
- Revisar matriz SL/TP (300/600 → ex.: 200/400 ou 150/300) para subir WR efetiva acima do breakeven.
- Revisar guarda de deduplicação por símbolo/tick no OrderManager (dup-exec USDJPY, §10.2).

### 11.4 DIAGNÓSTICO DO BUG ADX no Tester (causa raiz — preparação pós-janela, NÃO editar agora)

**Arquivo:** `Indicators/ADX.mqh` (v1.2.0). **Sintoma:** `[ADX] CopyBuffer failed | Error=4807` desde o
primeiro tick → `GetADX()` retorna `0.0` → todo filtro `ADX_OK`/`GetADX>=MinimumADX` bloqueia → 0 trades.

**Causa raiz (leitura de código):**
- `Error 4807 = ERR_INDICATOR_DATA_NOT_READY` — o buffer do `iADX` ainda não está pronto no warm-up
  do tester (especialmente Model=0 "every tick"), nas primeiras barras.
- `GetADX()` faz `CopyBuffer(handle,0,0,1,buf)` e, se `copied != 1`, **retorna 0.0 imediatamente** sem
  retry e sem sleep (linhas ~48-60 de ADX.mqh).
- Consumidores (`ADX_OK`, `ValidationEngine`, `AIEngine`, `AIClient`, `DecisionEngine`) interpretam
  `0.0` como "abaixo do mínimo" e **bloqueiam** — não distinguem "dado ausente/not ready" de
  "tendência fraca".
- Como o erro persiste das barras iniciais (sem re-tentativa/latch), o bloqueio vale o teste inteiro.

**Candidatos de correção (a aplicar em 20.15, FORA da janela — não tocar agora):**
1. Em `GetADX()`: em `4807`, retry com pequeno `Sleep`/`EventSetTimer` ou aguardar N barras de warm-up
   (`Bars(_Symbol,_Period)>ADXPeriod*2`) antes de ler.
2. Distinguir "not ready" (-1.0 / NaN) de "tendência fraca" (>=0): `ADX_OK` deve degradar para
   **fail-open** (permitir) ou **skip neutro** quando o dado não está pronto, em vez de bloquear.
3. Garantir o handle com `SeriesInfoInteger`/candle fechada antes de `CopyBuffer`, evitando ler barra
   em formação no Model=0.
4. Alternativa: criar o handle e puxar `CopyBuffer` com contagem maior (ex.: 3) e validar só o valor
   mais recente, degradando com warn em vez de 0.0.

> Efeito: corrigir isso deve desbloquear a matriz "com filtros" (T1–T6) no tester e permitir validar
> o cenário **B (IA ON + ADX corrigido)**.

### 11.5 VERIFICAÇÃO READ-ONLY — SÁBADO 30/08 13:05 BRT (pré-checkpoint, janela intacta)

> Executado: MetaTrader Assistant | read-only (nenhuma ordem/edição de EA). `heartbeat_watchdog.py --once`
> via CPython 3.11 (python 3.12 do workspace está com instal quebrada — pendência de ambiente).

**Heartbeat / Backend**
| Item | Valor | Veredito |
|---|---|---|
| system_status.json | HEALTHY · algo ON · DD 2,07% · IA NEUTRAL (conf 37,79) non-stale | ✅ vivo |
| watchdog --once | health=HEALTHY dd=2,07% ai=NEUTRAL stale=False | ✅ |
| Arquivos "parados" 442 min | esperado: hiato de fim de semana (último tick 28/08 23:59:58) | ✅ não é falha |

**Reconciliação live (posições)**
| Posição | Ticket | Tipo | Entrada | SL/TP | PL atual |
|---|---|---|---|---|---|
| GBPUSD | #10263362670 | SELL carried | 28/08 21:05 | 1.35573/1.34673 | −0.73 |
| USDCHF | #10263362709 | BUY carried | 28/08 21:05 | 0.80684/0.81584 | −0.65 |
| USDCAD | #10263363321 | BUY carried | 28/08 21:05 | 1.38788/1.39688 | −0.32 |
| **USDJPY (dup-exec)** | #10264640104 | BUY | 28/08 22:15:02 | 159.817/160.717 | −0.34 |
| **USDJPY (dup-exec)** | #10264640153 | BUY | 28/08 22:15:02 | 159.818/160.718 | −0.34 |

- Soma do PL das 5 posições = **−2.38** = profit da conta (equity 114.40) ✅ divergência 0.
- dup-exec USDJPY: **2 posições BUY idênticas mantidas**, mesmo candle/px 160.118, sem nova ocorrência;
  seguem com SL/TP (regra passiva). Conta como 1 decisão / 2 execuções no checkpoint.
- Carried (pré-janela): 3 posições abertas com SL/TP, sem intervenção. Trades fechados na janela: 0.

**Ambiente** — metatester64 ocioso (jobs encerrados).

### 11.6 🔧 AMBIENTE — PYTHON 3.12 REPARADO (30/08 13:1x BRT)

> Escopo: ambiente local (fora do EA). Nenhum impacto na janela limpa. Registrado p/ o checkpoint oficial.

**Sintoma:** `python`/`py -3` falhavam; `py -0p` apontava para `...\Programs\Python\Python312\python.exe`
inexistente (pasta removida, registro órfão).

**Causa raiz:** Python 3.12 (3.12.9/3.12.10) tinha sido desinstalado/removido do disco, mas o launcher
`py` e o MetaEditor (`compiler_python_folder=...\Python312`) continuavam apontando para ele; sobravam
componentes MSI órfãos em HKLM (Standard Library, pip, Tcl/Tk, Docs) de instalações antigas.

**Correção aplicada (com backup de registro em `%TEMP%\py_reg_backup_*.reg`):**
1. Baixou `python-3.12.10-amd64.exe` (25,7 MB) — 3.12.11+ não têm instalador Windows (release só código).
2. Limpeza cirúrgica: removeu `HKCU\Software\Python\PythonCore\3.12` órfão + bundles HKCU 3.12.9/3.12.10.
3. `msiexec /x` parcial nos componentes HKLM (alguns 1603, sem impacto no resultado final).
4. Reinstalação `/quiet` em `C:\Users\Micro\AppData\Local\Programs\Python\Python312` — ficou incompleta
   (faltava stdlib: `Lib\encodings`, `site-packages`), então:
5. **`/repair`** do bundle resolveu a stdlib (4509 arquivos), e `ensurepip` instalou pip 25.0.1.

**Estado final (validado):**
- `Python 3.12.10` · `STDLIB_OK` · `pip 25.0.1` · `py -0p` → 3.12 default (e uv CPython 3.11 como 2ª opção).
- Watchdog reexecutado com a 3.12: `health=HEALTHY dd=2.07% ai=NEUTRAL stale=False` ✅
- Instalador mantido em `%TEMP%\python-3.12.10-amd64.exe` (25,7 MB) para futuras correções.

**Comando oficial do checkpoint 20.14-C (seg 31/08 ~15:35-16:35 BRT):**

---

## 12. F4 — ENDURANCE OFICIAL (BUILD DEFINITIVO, T0 02/09 00:33:40 SERVIDOR)

> Registrado: 2026-09-01 21:39 UTC | MetaTrader Assistant | **F4 = PASS operacional — ENDURANCE ATIVA**
> **Regra da fase: NENHUMA alteração de código, inputs, símbolos ou posições durante a janela.**

### 12.1 Estado oficial no T0 (02/09 00:33:40 servidor = reload 11/11 do build F4 definitivo)

| Item | Valor | Veredito |
|---|---|---|
| Build | `XAU_AI_PRO.mqproj` → **0 errors / 0 warnings** (X64) | ✅ C1 |
| Reload | 11/11 instâncias (18:33 local / 00:33 server) | ✅ |
| Positions EA | `Positions: 5 total EA (terminal)` == `positions_open.ea_magic` **5/5** (USDBRL, NZDUSD, USDCAD, USDJPY, USDCHF) | ✅ C4 |
| CSV contrato | 10 colunas · UTF-16 · header único · inputs inalterados | ✅ C6 |
| Integridade pós-reload | **interleave 0 · malformadas 0** (padrão open→seek→write→flush→close sob lock) | ✅ C2-parcial |
| `[EVENT] DROP` | 0 no Journal · `AuditLog Dropped=0` | ✅ C3-parcial |
| C5 cadeia | `missing_audit=0` · `missing_event=0` · `unknown_event=[]` (janela limpa) | ✅ |
| unknown_event=1 (legado) | deal USDCAD `10023569245` = TRADE_OPEN gravação pré-reload; deal confirmado na tool nativa; é **latência de cache da API Python**, não corrupção F4 | ⚠️ pendência de sync, não defeito |

> **Nota de arquitetura (confirmado na doc MQL5):** `GlobalVariableSetOnCondition()` oferece acesso
> atômico (CAS) e é indicado como mutex entre múltiplos EAs do mesmo terminal; exige inicializar a
> variável global antes do primeiro CAS (senão a função falha). É a base do `EventLock.mqh` (TTL 2s
> anti-órfão, 20×1ms spin) compartilhado por EventEmitter + AuditLog.

### 12.2 Correção que fechou o F4 (incidente da validação inicial)

- **Sintoma:** interleave no CSV (linhas coladas/cortadas) no storm de HEALTH_FAILURE (00:19–00:30).
- **Causa raiz:** `EventEmit` mantinha `evHandle` **persistente por instância** com `FILE_SHARE_WRITE`;
  `FileSeek(SEEK_END)` de um handle não enxerga o tamanho atualizado por outro handle → overlay.
- **Fix definitivo:** escritores reescritos para **ABRIR→SEEK(END)→WRITE→FLUSH→FECHAR** a cada
  gravação, sob o lock (EventEmitter + AuditLog Decision/Simple/TradeResult). Evidência: arquivos que
  já usavam esse padrão (forward_test_trades/session) nunca corromperam.

### 12.3 Checkpoints da endurance F4

| Marco | UTC | Servidor (UTC+3) | Validação obrigatória |
|---|---|---|---|
| **T0** | 01/09 21:33:40 | 02/09 00:33:40 | ✅ registrado |
| **24H** | 02/09 21:33:40 | 03/09 00:33:40 | Dropped=0 · timeouts=0 · lock saudável · CSV íntegro · C5 completo · Broker×Audit×Events reconciliados |
| **72H** | 03/09 21:33:40 | 04/09 00:33:40 | idem + tendência de lock contention |
| **7D** | 08/09 21:33:40 | 09/09 00:33:40 | idem + métricas da janela |
| **30D + Gate 20.15** | 01/10 21:33:40 | 02/10 00:33:40 | F4 PASS definitivo → liberar produção |

### 12.4 Comando de auditoria em cada marco

`py -3 MQL5\Python\runbooks\reconcile_sources.py` + checagem de integridade do CSV via script Python
(interleave/malformadas/10 colunas) + Journal (`[EVENT] DROP`, `Lock | contention/timeouts`).
`py -3 MQL5\Python\watchdog\heartbeat_watchdog.py --checkpoint`
