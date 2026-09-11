# RELOAD RUNBOOK — XAU_AI_PRO v1.2.0 ENDURANCE CANDIDATE (F4/1.2)

Objetivo: reload controlado 11/11 do build endurance em ambiente DEMO, com o
watchdog de progresso corrigido ATIVO, sem trading real (`AutoTrade=0`).
Método: desanexar/anexar o EA em cada chart, carregando o snapshot de inputs
(`XAU_AI_PRO.ENDURANCE.set`).

## 1. Registro PRE-RELOAD (2026-09-08 04:08 local / UTC-3)

| Campo | Valor |
|---|---|
| ENDURANCE BUILD (sha256 `.ex5`) | `eab9c4fc37c016f44f72100445d86ce47e127318e95835f60d849d1df3f43654` |
| Compilador | MetaEditor MQL5 build 6182 (x64) · 0 erros / 0 warnings |
| Conta | MetaQuotes-Demo · login 111194406 · balance 122.81 USD · hedging |
| AutoTrade | `AutoTrade=0` (observação — SEM trading real) |
| Health | `EnableHealthMonitor=true` (target) |
| Dataset | `EnableDataset=true` (target) |
| Magic | `2026001` |
| Snapshot inputs | `Release/v1.2.0-ENDURANCE/Config/XAU_AI_PRO.ENDURANCE.set` · cópia em `MQL5\Presets\XAU_AI_PRO.ENDURANCE.set` |

### Charts objetivo (11 instâncias do EA)

| # | Chart | Símbolo | TF | chart_id |
|---|---|---|---|---|
| 1 | chart01 | AUDUSD | M5 | 36613947062002 |
| 2 | chart02 | XAUUSD | **M1** | 36613948282976 |
| 3 | chart03 | GBPUSD | M5 | 36613949438280 |
| 4 | chart04 | EURUSD | M5 | 36613950601962 |
| 5 | chart05 | USDJPY | M5 | 36613951918343 |
| 6 | chart06 | NZDUSD | M5 | 36613953282583 |
| 7 | chart07 | USDCAD | M5 | 36613954587398 |
| 8 | chart08 | USDCHF | M5 | 36613955946415 |
| 9 | chart09 | USDBRL | M5 | 36613957421093 |
| 10 | chart10 | USDSEK | M5 | 36613958985194 |
| 11 | chart11 | USDCNH | M5 | 36613960304378 |

> Nota: o chart12 (XAUUSD M5, chart_id 42048355061075) NÃO tem EA anexado — fica
> fora da contagem 11/11 (referência gráfica apenas).
> Nota M1: o chart02 é a instancia XAUUSD **M1** do profile. O watchdog de
> progresso calcula automaticamente o timeout segundo `PERIOD_CURRENT` (M1 → 120s ≥ cadência
> ~60s), portanto não requer configuração extra.

## 2. Procedimento de reload (11/11) — para cada chart

1. Clic direito sobre o chart → **Expert Advisors → Remove** (remove o EA atual).
2. Clic direito → **Expert Advisors → Attach Expert Advisor...**
3. Selecionar **XAU_AI_PRO** (`Experts\XAU_AI_PRO\XAU_AI_PRO.ex5`).
4. No diálogo, aba **Inputs** → botão **Load...** → escolher
   **`XAU_AI_PRO.ENDURANCE_MIN.set`** (em `MQL5\Presets\`) — set MÍNIMO (Opção A):
   somente `AutoTrade=false`, `MagicNumber=2026001`, `EnableHealthMonitor=true`,
   `EnableDataset=true`, `HealthPipelineProgressTimeout=0`. NÃO altera filtros,
   estratégia, risco, telemetria nem multi-symbol (conserva os valores atuais do chart).
   > ⚠️ NÃO cargar `XAU_AI_PRO.ENDURANCE.set` (completo): altera ~25 inputs
   > (filtros ON, AI, telemetria, EnableMultiSymbol=true, verbose debug). Este arquivo
   > fica apenas como snapshot/documentação em `Release/v1.2.0-ENDURANCE/Config/`.
   > Se o diálogo mostrar `AutoTrade=true`, NÃO salvar: cancela e recarga o MIN set.
5. Verificar na lista de inputs cargados:
   - `MagicNumber` = 2026001
   - `AutoTrade` = false
   - `EnableHealthMonitor` = true
   - `EnableDataset` = true
   - `HealthPipelineProgressTimeout` = 0
   - **Sem mudanças de estratégia/risco** vs snapshot: RiskPercent 1.0,
     MaxDailyLossPercent 5.0, MaxDrawdownPercent 15.0, StopLossPoints 300,
     TakeProfitPoints 600, FastEMA 50, SlowEMA 200, RSIPeriod 14,
     RSIPullbackBuy 45.0, RSIPullbackSell 55.0, ADXPeriod 14, MinimumADX 18.0
     (qualquer outro input deve coincidir com o `.set`).
6. **OK** → confirmar mensagem `OnInit` OK no journal do terminal (Experts).

## 3. Verificação post-reload (esperar 2–5 minutos)

- [ ] 11/11 `OnInit` corretos (journal MQL5: "HealthMonitor inicializado" por instancia; sem erros de carga)
- [ ] Heartbeats de liveness ATIVOS (HealthMonitorUpdateTicks por tick; "HEALTH OK" periódico; SEM "timeout de tick")
- [ ] Progress CSV/JSON/PYTHON SÓ com avanço real (ausência de "módulo de pipeline parado")
- [ ] `Dropped` = 0 (journal sem ticks perdidos/dropped)
- [ ] `EventLock` timeout = 0 (journal sem timeouts de EventLock)
- [ ] `list_open_charts`: 11 EAs XAU_AI_PRO com inputs target

## 4. Registro T0 (completar após verificação estável)

| Campo | Valor |
|---|---|
| ENDURANCE BUILD | `eab9c4fc…3654` |
| INSTANCES | 11/11 |
| AUTOTRADE | 0 |
| HEALTH | ON |
| DATASET | ON |
| T0 | `<server time>` ← completar com `get_time_information` ao confirmar |

Janelas desde T0: **24H → 72H → 7D** (watchdog de progresso + telemetria; NÃO
se avalia desempenho financeiro — AutoTrade=0 intencional).

---

## 5. REGISTRO T0 — COMPLETADO (2026-09-11 00:04 server)

| Campo | Valor |
|---|---|
| Build runtime (`.ex5` instalado) | `XAU_AI_PRO.ex5` · 408454 B · build 2026-09-10T20:32:57Z · compiler 6190 |
| Instâncias | 11/11 `loaded successfully` (17:34:29 local) · 0 prepare-to-execution-failed |
| **T0 (server)** | **2026-09-11 00:04:32** (trade_server_last_known_time; local 2026-09-10 18:04) |
| AutoTrade | 0 (observação — 0 ordens; risk OPEN após rollover 00:00 server, trades_today=0) |
| Health | ON — watchdog ativo: `system_status.json` gerado 23:58:02 → 00:01:00 (server); avanço verificado |
| Dataset | ON — "DATA LOGGER MULTI-SYMBOL ONLINE" no init; `dataset.csv` recriado (2 B) — **monitorar crescimento** |
| MultiSymbol | false ("Single-symbol mode mapped" no log de init) |
| Magic | 2026001 |
| Persistência | 11/11 `.chr` MIN; o terminal re-salvou o profile 20:36:18Z e 20:46:00Z — conteúdo verificado MIN em ambas (66/66) |

### Critério "timeout de tick justificado" (regra do runbook post-T0)
Confirmado por delegação do owner — **vetable**: conta como INJUSTIFICADO
SOMENTE o HEALTH FAILURE **persistente** (≥2 checks consecutivos com backoff
nível ≥2). Um stall único (GBPUSD/USDCHF interno recuperado; USDBRL gap de feed
15,9 s) NÃO é injustificado. Limiar de tick base: 15 s.

### Correção de fonte de verdade (CRÍTICA)
`list_open_charts` reporta inputs 0/0 nos 11 charts ENQUANTO o runtime
executa health/dataset ON (evidencia: `system_status.json` avança, init log com
Single-symbol + DataLogger, `dataset.csv` recriado). **NÃO usar `list_open_charts`
como critério T0.** Verificar por: (1) init log do EA, (2) arquivos de atividade
(`system_status.json`, `forward_test_events.csv`, `dataset.csv`), (3) conteúdo
`.chr` (write root MQL5 → `MQL5\Profiles\Charts\F1_SINGLE_11SYM\chartNN.chr`).

### Observações não críticas
- `health.state=ERROR` em `system_status.json` com `algo_trading_enabled=false`
  → botão **Algo Trading OFF** (ambiente demo/observação). Crônico e JUSTIFICADO;
  não é um failure transitório. Se quiser health verde, ativar Algoritmos no
  terminal (sem risco: AutoTrade=0 impede ordens igualmente).
- chart02 (XAUUSD) está em **M5** no profile atual (o runbook antigo dizia
  M1 — esse era o estado do 09-08).
- `database.dataset_bytes=2` (dataset fresco sem linhas ainda); `forward_test_events.csv`
  e `system_status.json` avançam → liveness OK.

### Checkpoints de observação (confirmados pelo owner 2026-09-11 00:22 server)
Base de observação fixada pelo owner ao confirmar "tudo correto" (server time,
verificado com `get_time_information`):

| Marco | Data/hora (server) | Equivalência local UTC-3 |
|---|---|---|
| **T0 (base confirmada)** | 2026-09-11 00:22 | 2026-09-10 18:22 |
| **24H** | 2026-09-12 00:22 | 2026-09-11 18:22 |
| **72H** | 2026-09-13 00:22 | 2026-09-12 18:22 |
| **7D** | 2026-09-18 00:22 | 2026-09-17 18:22 |

> T0 técnico (rollover 00:00 server) 2026-09-11 00:04:32 — conservado como
> referência; a base de contagem efetiva é a confirmada pelo owner (00:22).
> Em cada marco verificar: watchdog vivo (`system_status.json` avança,
> `forward_test_events.csv` cresce), dataset deverá crescer (`dataset.csv` > 2 B),
> 0 HEALTH FAILURE injustificados (critério: persistente ≥2 checks consecutivos
> com backoff ≥2), AutoTrade=0 (0 ordens).