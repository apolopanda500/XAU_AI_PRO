# 04/11/2026 — Reattach dos 13 graficos na v1.2.135 e o "1.2.9" que nao era drift

> Ciclo 92. Continua o ciclo 91
> (`CONVERSA_20261104_FAIL_CLOSED_30F_E_LIMPEZA.md`), que fechou o P-01b e
> corrigiu o fail-open do gateway.
>
> Este documento responde a tres perguntas com numero: **o EA que esta no
> grafico e o que foi compilado?**, **o `Docs/version.json` esta errado?** e
> **o que ainda falta para "pronto para uso real"?**

---

## 1. O que o dono pediu

> "sim pode fazer commits push deploy anotar e salvar documentos novos e
> atualizados e garantir EA par auso real daqui pra frente"

> "corrigir todas falhas, erros, avisos, etc.. deixar limpo"

> "so com PF > 1.20 e perdas seguidas <= 8 se discute conta real, e mesmo ai
> com EnableRealAccountGuard=true e risco baixo"

Traduzido em trabalho: (a) provar que o binario que corre nos graficos e o
ultimo compilado; (b) varrer o que ainda diz versao antiga; (c) nao inventar
"pronto" — medir; (d) registrar tudo em documento novo e commitar.

---

## 2. O que foi medido

### 2.1 O grafico estava com a instancia ANTIGA do `.ex5`

Antes de qualquer alteracao, a leitura dos 13 graficos mostrou os inputs
vivos com os defaults **antigos**:

| Input | Valor no grafico | O que era |
|---|---|---|
| `AIGatewayUrl` | `http://127.0.0.1:9001/api/ai/predict` | porta 9001 |
| `AIGatewayToken` | `XAU_GATEWAY_TOKEN` | **o nome da variavel**, 17 chars |

O `AIGatewayToken` no grafico era o *nome* da variavel de ambiente, nao o
token. E o gateway real estava na **9011** (P-01d). Ou seja: o EA no grafico
batia na porta errada com um token que nao era token.

Correcao aplicada nos 13 graficos por `chart_add_expert` com o binario de
`2026-11-04 19:15:59`, e a prova esta no journal, nao no `ok:true`:

```
[START] XAU_AI_PRO v1.2.135 | conta=113568614 | MetaQuotes Ltd./MetaQuotes-Demo
[VERSION] v1.2.135 | Build=2026.11.04 | Stable=Yes | AutoUpdate=OFF | Modulos=16
```

nos 13 simbolos: XAUUSD, USDSEK, USDJPY, USDCHF, USDCZK, USDCAD, USDCNH,
AUDUSD, NZDUSD, GBPUSD, USDBRL (M5), USDRUB, USDSGD. E os 16 modulos OK
(ConfigManager, VersionManager, RiskEngine, ExecutionEngine, AIEngine,
ReplayEngine, BackupManager, BacktestAnalyzer, BenchmarkEngine,
NotificationCenter, HealthMonitor, AuditLog, ProductionChecklist,
ValidationChecklist, NewsFilter, MCPServer).

**Por que isto importa mais do que parece:** `AIGatewayTokenEfetivo()` e
`AIGatewayUrlEfetiva()` (`AI/AIConnector.mqh:596-660`) leem token e porta do
`.env` em runtime e **sobrepoem-se** ao input. Logo o input velho nao
quebrava a IA a 100% — mas mascarava o defeito: quem olhasse os inputs veria
"estou na 9001", e quem lesse o journal veria a 9011. Dois lados do mesmo
dado com nomes diferentes (§5 do `AGENTS.md`).

### 2.2 O reattach NAO mudou comportamento — e isso foi provado, nao suposto

O medo era que reanexar trocasse os parametros de risco vivos pelos defaults
do codigo. Comparacao feita antes de chamar o `chart_add_expert`:

| Parametro | Default no codigo | Valor no grafico | Igual? |
|---|---|---|---|
| `RewardRatio` | `Core/Config.mqh:301` = 0.65 | 0.65 | sim |
| `MinRewardRatio` | `Core/ExecutionEngine.mqh:226` = 0.55 | 0.55 | sim |
| `RiskPercent` | `Core/Config.mqh:111` = 1.0 | 1.0 | sim |
| `RiskPerTradeUsd` | `Core/Config.mqh:300` = 2.0 | 2.0 | sim |
| `MaxDailyLossUsd` | `Core/Config.mqh:122` = 60.0 | 60.0 | sim |
| `MaxDrawdownPercent` | `Core/Config.mqh:123` = 15.0 | 15.0 | sim |
| `DailyProfitTargetMaxUsd` | `Core/Config.mqh:1478` = 40.0 | 40.0 | sim |
| `EnableRealAccountGuard` | `Core/RealAccountGuard.mqh:43` = true | true | sim |

Como todos batem, revincular troca o **binario** e nao o **risco**. A conta
e DEMO (login 113568614, `MetaQuotes-Demo`, saldo 12592.02 USD, 0 posicoes,
0 ordens), portanto revincular nem sequer toca capital real.

### 2.3 `Docs/version.json` dizendo `1.2.9` NAO e drift

Este era o item que a lista de pendencias mandava "corrigir para 1.2.135
antes de correr `sync_version.py`". Medido antes de mexer:

```
backend\package.json:3:                          "version": "1.2.9"
backend\package-lock.json:3:                     "version": "1.2.9"
frontend\package.json:3:                         "version": "1.2.9"
frontend\src-tauri\tauri.conf.json:36:           "version": "1.2.9"
frontend\src-tauri\bridge\_internal\Docs\version.json:2:  "version": "1.2.9"
Docs\version.json:2:                             "version": "1.2.9"
```

e em `scripts/sync_version.py`:

```
19: VERSION_FILE = ROOT / "Docs" / "version.json"
174: ("backend/package.json",  ROOT / "backend" / "package.json"),
175: ("frontend/package.json", ROOT / "frontend" / "package.json"),
177: ("frontend/src-tauri/tauri.conf.json", ...),
```

Ou seja: **`Docs/version.json` e a versao do APP (desktop/Tauri), nao do EA.**
O `1.2.9` esta coerente com os cinco arquivos que ele governa. Trocar para
`1.2.135` faria o `sync_version.py` propagar `1.2.135` para o
`package.json`, mudar a versao que o **instalador NSIS compara** e — no
melhor caso — reinstalar tudo; no pior, reproduzir o defeito ja medido em
`AGENTS.md` §7 (bridge defasada que o instalador nao sobrescreve porque a
versao nao muda).

**Decisao: nao mexer.** O item de pendencia estava errado, nao o arquivo. O
que muda e que agora esta escrito, para o proximo ciclo nao repetir a
conclusao errada.

### 2.4 Varredura de drift: 6 ocorrencias `1.2.134`, todas tratadas

`findstr /S /N /C:"1.2.134"` devolvia 6 textos dizendo que o EA era 1.2.134
quando `Enterprise/VersionManager.mqh:14` define `"1.2.135"`. Corrigidos:
`README.md:8`, `PENDENCIAS.md:12`, `PENDENCIAS.md:30`, `PROGRESS.md:4413`,
`PROGRESS.md:4434`, `Tools/HANDOFF.md:336` e a linha 253 do documento do
ciclo 91. As duas ocorrencias que sobraram sao **historicas e
intencionais**:

```
AI/AIConnector.mqh:638   // v1.2.134 (04/11/2026) - P-01d: a porta do gateway ...
Enterprise/VersionManager.mqh:63   "v1.2.134 (04/11/2026) - P-01d: ..."  (changelog)
```

Regra que fica: **procurar a versao errada so prova algo se as ocorrencias
historicas forem contadas e explicadas.** Um `findstr` que devolve zero so
esta provando que ninguem escreveu o numero — nem no changelog.

---

## 3. O que NAO foi feito, e por que

| Item | Estado | Motivo medido |
|---|---|---|
| Re-medir no Strategy Tester | **nao lancado** | `metatester64.exe` 8772 / 12896 / 4476 e `MetaTester64.exe` 11832 / 4212 vivos. Lancar com o slot ocupado ja morreu em 20-50 ms (`Core 1 disconnected`) |
| `Tools\agent-toolkit.ps1 deploy` | **nao re-corrido** | nenhum `.mqh`/`.mq5` mudou neste ciclo (so `.md`). O binario publicado continua o de `2026-11-04 19:15:59`: 108 ficheiros validados, `Result: 0 errors, 0 warnings`, 25739 ms, `X64 Regular` |
| `pytest` | **nao executado** | `pytest` nao esta instalado no `.venv` (o `requirements-dev.txt` pede `pytest>=9.0.3`); instalar exige rede e decisao do dono |
| Conta real | **recusada** | PF 0,6206, 41,4% de acerto, 10-11 perdas consecutivas. A regra do dono e PF > 1,20 e streak <= 8 |
| `chart14` | **intocado** | XAUUSD,H1 (chart_id `91943700848411`, 60349 barras) sem expert. Nao se liga um 14. grafico identico ao chart01 sem o dono decidir — seriam duas instancias no mesmo simbolo com o **mesmo** `MagicNumber=2026001` |
| `Docs/version.json` | **intocado de proposito** | ver §2.3 |

---

## 4. O que ainda separa o EA de "uso real"

Nao e codigo. E medicao. E a medicao esta bloqueada por uma coisa so:

1. **Slot do tester.** Sem backtest novo, os P1.25–P1.36 (reducao de ~51% das
   linhas de journal) e o P-01b (IA 30F) nao tem prova em run — o run
   `7702926785952690594` corre `v1.2.45` e nao prova nada disso.
2. **Geometria incoerente entre producao e tester.** `RewardRatio` 0,65 em
   producao contra 1,30 no `.set` do tester; `MinRewardRatio` 0,55 contra
   1,00. Com TP a 65% do SL, um acerto de 41,4% precisa de **>60%** de
   acerto so para empatar. O A/B do `MinRewardRatio` ainda nao foi corrido.
3. **`Data\prediction_<SYM>.json`.** WebRequest com `Authorization: Bearer`
   **nao funciona dentro do Strategy Tester**. Para o EA consumir IA em
   backtest falta o ficheiro de predicao no disco.

Enquanto os tres nao fecharem, a resposta a "esta pronto para uso real" e
**nao**, com numero: PF 0,6206 e 10-11 perdas seguidas.

---

## 5. Arquivos tocados neste ciclo

| Arquivo | Mudanca |
|---|---|
| `Experts/XAU_AI_PRO/PROGRESS.md` | cabecalho `2026-10-30 (v1.2.25)` -> `2026-11-04 (v1.2.135)` |
| `Experts/XAU_AI_PRO/CONVERSAS.md` | indice (sessao 14) + `Sessao G` |
| `Files/XAU_AI_PRO/Docs/CONVERSA_20261104_REATTACH_13_GRAFICOS.md` | este documento |
| `Files/XAU_AI_PRO/Docs/version.json` | **nao tocado** — §2.3 |

Nenhum `.mq5`/`.mqh`: por isso nao houve recompilacao, e por isso o `.ex5`
em producao continua o mesmo que o journal provou.
