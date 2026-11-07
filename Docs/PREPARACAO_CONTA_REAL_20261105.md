# Preparação para conta REAL - estado medido em 05/11/2026 (ciclo 108)

> Documento de **portão**, não de autorização. Nada aqui liga ordens reais.
> A conta real continua **recusada** até os critérios da secção 2 estarem
> cumpridos com número, e até o dono autorizar por escrito.
>
> Todas as linhas foram medidas nesta sessão ou citam a medição de onde vêm.
> Onde não houve medição, está escrito "não medido".

---

## 1. O que está a correr agora (medido)

| Item | Valor medido |
|---|---|
| Conta | **demo** MetaQuotes-Demo, login mascarado `1135****14` (medição de 03/11 em `Tools/HANDOFF.md`) |
| Build em disco | `XAU_AI_PRO.ex5` 879 812 B, `04/11/2026 22:58:26` |
| Versão no fonte | **v1.2.150** (`EA_VERSION_STRING`), `#property version "1.350"` |
| Gráficos no perfil `XAI_P216_LIVE` | **13** `.chr` em disco (o HANDOFF de 03/11 registava 15 instâncias; há desvio, ver P-07) |
| `AutoTrade` | `true` |
| `RiskPercent` / `RiskPerTradePercent` | `1.0` / `0.5` % do saldo |
| `MaxDailyLossPercent` / `MaxDailyLossUsd` | `10.0` % / `60.0` USD |
| `MaxDrawdownPercent` | `15.0` % |
| `MaxTotalRiskPercent` / `MaxTotalRiskOpenUsd` | `10.0` % / `60.0` USD |
| `MaxOpenPositions` / `MaxTradesPerDay` | `50` / `100` |
| `MinAIConfidence` | `60.0` |
| `AllowTradeWithoutAI` | **`false`** (fail-closed) |
| `RequireStopLoss` | `true` |
| `EnableRealAccountGuard` | **`true`** |
| `RealGuardBlockMinLotExceedsCap` | `true` |
| `RealGuardStoplessEmergencyRMultFloor` | `1.5` R |
| `RealGuardMaxUnarmedPositions` | `1` |

Fonte das entradas: `Profiles/Charts/XAI_P216_LIVE/chart01.chr` (XAUUSD H1).
As restantes 12 janelas foram anexadas com as mesmas entradas; a leitura
linha-a-linha das 13 não foi feita nesta sessão.

### 1.1 O guarda de conta real existe e está ligado

`Core/RealAccountGuard.mqh` (v1.2.37) só actua quando `IsRealAccount` é
verdadeiro e **fora** do testador. Aperta três coisas e nada mais:

1. lote mínimo acima do teto por operação passa a **bloquear**;
2. o teto de perda do stopless nunca fica a 0 (sem limite) — piso de 1,5 R;
3. no máximo **1** posição sem stop por símbolo, deste EA (`MagicNumber`).

Não muda direcção, score, alvo, lote para além do teto de risco, e não fecha
posições. Ou seja: **o guarda não é a rede de segurança do resultado — é a
rede de segurança da exposição.** O resultado depende do edge.

---

## 2. O portão duro (e onde estamos)

Critérios definidos pelo dono para ligar conta real:

| # | Critério | Medido | Passa? |
|---|---|---|---|
| 1 | Profit Factor > **1,20** | **0,92** (backtest 641 trades) | **NÃO** |
| 2 | Perdas seguidas <= **8** | 10-11 no mesmo backtest | **NÃO** |
| 3 | Drawdown <= **5 %** | **143,70 %** | **NÃO** |
| 4 | >= **100** trades | 641 | sim |
| 5 | Backtest com o build actual | o build mudou 9 vezes desde o run | **NÃO** |
| 6 | Demo completa + forward test aprovado | não concluído | **NÃO** |
| 7 | Endurance test | não concluído | **NÃO** |
| 8 | Autorização explícita do dono | não dada | **NÃO** |

**Conclusão honesta: 1 de 8.** O backtest que existe mediu um EA **diferente**
do actual — os P1.91, P1.92, P1.96..P1.107 corrigiram ADX, ficheiro de
previsão, calendário, cache de ATR e parser de IA depois desse run. Não serve
nem para autorizar nem para recusar com precisão; serve para recusar por
prudência até haver medição válida.

---

## 3. O que a IA está realmente a publicar (medido agora)

Sonda autenticada a `http://127.0.0.1:9011/api/ai/predict` com o token do
`.env` (64 caracteres; o valor não é impresso nem registado), 15 símbolos, H1:

| Símbolo | `available` | Sinal | Motivo |
|---|---|---|---|
| **XAUUSD** | **true** | SELL | inferência real do modelo publicado |
| USDJPY | false | — | edge +0,0248 < mínimo +0,0500 |
| USDCHF | false | — | edge +0,0253 < 0,0500 |
| USDCAD | false | — | edge +0,0317 < 0,0500 |
| USDCNH | false | — | edge **−0,1256** |
| USDCZK | false | — | edge −0,0072 |
| USDCLP | false | — | edge −0,0281 |
| USDCOP | false | — | edge −0,0584 |
| USDSEK | false | — | edge −0,0403 |
| USDSGD | false | — | edge +0,0193 |
| USDRUB | false | — | edge +0,0166 |
| USDBRL | false | — | edge instável entre folds (−0,120 … +0,009) |
| AUDUSD | false | — | edge −0,0184 |
| NZDUSD | false | — | edge +0,0225 |
| GBPUSD | false | — | edge −0,0207 |

**1 de 15** símbolos tem previsão publicável. Isto é **fail-closed
correcto**, não avaria: `AllowTradeWithoutAI=false` transforma a ausência de
IA em motivo de recusa. Mas o efeito prático tem de ser dito: **um EA
"autónomo" hoje opera no máximo o XAUUSD**; as outras 12-14 janelas ficam
paradas por desenho.

### 3.1 O edge do único símbolo que opera é fino

`XAUUSD_H4.meta.json` e o `prediction_XAUUSD.json` de 04/11 22:28:

| Métrica | Valor |
|---|---|
| `feature_version` / `feature_count` | `XAU-30F-v4` / **30** |
| `feature_hash` | `5305081777808310` |
| `accuracy` | **0,5361** |
| `edge` | **+0,0363** |
| folds positivos | 4/5 |
| `train_date` | 2026-11-03 |

Um edge de 3,6 pontos percentuais sobre o acaso, com 53,6 % de acerto, é
**fino**. Sobrevive a custo de spread de 0,6 % do preço? Não está medido
neste ciclo. Antes de dinheiro real isto tem de ser medido com o custo real da
corretora, não assumido.

### 3.2 Divergência de contrato encontrada (documento desactualizado)

`AUTONOMIA_24_7.md` §5 declara:

```
FEATURE_VERSION = 25F-v2   FEATURES = 25   feature_hash = 27727ee00bc30b7f
PUBLICACAO_MIN_EDGE = 0.05
```

O medido é: **XAUUSD em 30F-v4** (hash `5305081777808310`), os outros 80
modelos em 25F-v2 (hash `27727ee00bc30b7f`), e o gateway a recusar por
`edge < +0,0500`. O documento está certo para 80 dos 87 modelos e **errado
para os 4 modelos XAUUSD**. O `PUBLICACAO_MIN_EDGE` do gateway é 0,05 — a
linha do `prediction_XAUUSD.json` que fala em "mínimo 0,0300" é texto do
snapshot, não a regra actual.

Isto não é um defeito de código; é documentação que mente para quem chega
depois. Corrigir o §5 é trabalho de documentação, não de risco.

---

## 4. Riscos de configuração abertos antes de real

Nenhum destes foi alterado — são decisões de risco e exigem pedido explícito.

| # | Observação | Porque importa |
|---|---|---|
| R-1 | `MaxDrawdownPercent = 15` contra critério do dono de **5 %** | o EA pode perder 15 % do saldo antes de parar, três vezes o limite declarado |
| R-2 | `MaxDailyLossPercent = 10` com `MaxDailyLossUsd = 60` | numa conta de 12,5 k, 60 USD = 0,48 %: o limite em USD manda, mas numa conta maior o de 10 % passa a mandar |
| R-3 | `MaxOpenPositions = 50` e `MaxTradesPerDay = 100` | dimensionados para 15 símbolos em demo; num símbolo só, 100 trades/dia é ruído |
| R-4 | `RiskPercent = 1,0` e `RiskPerTradePercent = 0,5` | aceitável, mas o "1 %" e o "0,5 %" são dois caminhos de cálculo de lote; saber qual manda é pré-requisito |
| R-5 | edge XAUUSD 3,6 pp sem medição de custo | ver 3.1 |

**Pergunta ao dono (não decisão do agente):** para conta real, quer apertar
`MaxDrawdownPercent` para 5 e `MaxDailyLossPercent` para 3 antes de ligar, ou
manter os valores de demo e aceitar que o limite real é maior do que o
critério escrito?

---

## 5. Plano mínimo até "pronto para real"

Por ordem. Cada passo tem um número de saída; sem o número, não avança.

### Passo 1 - Fechar o drift de versão e reanexar
- Compilar `v1.2.150` (ou superior) e confirmar `0 errors, 0 warnings`.
- Reanexar nos 13 gráficos (`profile_apply` ou reattach manual).
- **Saída:** `[START] XAU_AI_PRO v1.2.150` repetido 13 vezes no journal, e
  `.ex5` mais recente que o `.mqh` mais recente.

### Passo 2 - Backtest com o build actual
- `Profiles/Tester/XAI_V12135_PRODGEOM_RT_M15.ini`, XAUUSD H1,
  2026.09.01..2026.11.01.
- **Saída:** PF, perdas seguidas, DD, nº de trades. Se PF <= 1,20 → parar
  aqui e voltar ao laboratório; **não** avançar para demo alargada.

### Passo 3 - Demo completa (endurance)
- 7 dias seguidos com o EA ligado, gateway no ar, sem intervenção.
- **Saída:** 0 crashes, 0 `Error=4022` fora do aquecimento, 0 ordens sem
  stop, `[REAL GUARD]` inerte (é demo por definição), log/hora dentro do
  previsto, reconciliação de ordens aberta vs histórico = 0 diferenças.

### Passo 4 - Forward test em demo
- 14 dias, risco em metade do valor alvo de real.
- **Saída:** PF > 1,20 na amostra de forward, perdas seguidas <= 8, DD <= 5 %.

### Passo 5 - Só então: conta real com micro-lote
- `EnableRealAccountGuard=true`, `RealGuardMaxUnarmedPositions=1`.
- Risco inicial **0,1 %** por operação, não 0,5 %.
- Primeiras 20 ordens com supervisão; `[REAL GUARD] CONTA REAL - endurecimento
  ACTIVO` tem de aparecer no journal no arranque.

---

## 6. Rollback (se algo correr mal em real)

1. `AutoTrade=false` (o EA deixa de abrir; **não** fecha o que está aberto).
2. Fechar posições à mão, ou deixar os stops de corretora actuar.
3. `EnableRealAccountGuard` **não** é o botão de emergência — é endurecimento.
4. Só depois investigar: journal, `audit_log.csv`, `trade_history.csv`.
5. Nada de "voltar à versão anterior" sem medir que a versão anterior era
   melhor: o `.ex5` não é versionado.

---

## 7. O que NÃO foi feito neste ciclo, e porquê

| Não feito | Porquê |
|---|---|
| Ligar conta real | 1 de 8 critérios cumpridos |
| Correr backtest novo | slot do Strategy Tester ocupado; sem ferramentas MCP `tester` nesta sessão |
| Reanexar v1.2.150 | sem ferramentas MCP `metatrader5` nesta sessão |
| Alterar parâmetros de risco | proibido sem pedido explícito (ver R-1..R-5) |
| Medir custo real do spread no edge | exige dados de execução real ou tick data da corretora; não medido |
| Remover `EnableRealAccountGuard` | nunca — é invariante do projecto |

---

## 8. Resumo em uma frase

**A infraestrutura GitHub está 10/10; o EA não está.** O código está mais
seguro do que estava, mas o único número de performance que existe (PF 0,92,
DD 143,70 %) foi medido num build que já não é o actual, e a IA só publica
1 dos 15 símbolos com um edge de 3,6 pp. Ligar conta real agora seria apostar
capital num instrumento que ainda não foi medido.
