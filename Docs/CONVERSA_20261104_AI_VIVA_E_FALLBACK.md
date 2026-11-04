# 04/11/2026 — IA viva nos 13 graficos e o fallback do Strategy Tester

Ciclo 93. Pedido do dono: *"sim pode fazer commits push deploy anotar e salvar
documentos novos e atualizados e garantir EA par auso real daqui pra frente"*.

O ciclo 92 tinha deixado tres bloqueios medidos. Este fecha o primeiro deles
(a IA) com prova de journal e fecha o terceiro (o fallback `prediction_*.json`)
com um ficheiro novo. O segundo — re-medir no Strategy Tester — continua
bloqueado e esta escrito no fim.

---

## 1. A IA esta VIVA nos 13 graficos (prova de journal)

Consultado `MQL5\Logs` via `get_expert_journal` em 04/11/2026 18:00–20:00,
filtro `GATEWAY`:

```
2026.11.04 19:07:52.856  XAU_AI_PRO (USDCHF,H1)  [AI] GATEWAY | USDCHF | H1 | 357 bytes
2026.11.04 19:07:52.857  XAU_AI_PRO (USDSEK,H1)  [AI] GATEWAY | USDSEK | H1 | 357 bytes
2026.11.04 19:07:52.867  XAU_AI_PRO (XAUUSD,H1)  [AI] GATEWAY | XAUUSD | H1 | 1123 bytes
2026.11.04 19:07:53.088  XAU_AI_PRO (USDJPY,H1)  [AI] GATEWAY | USDJPY | H1 | 357 bytes
... (mais 9 simbolos, todos 357 bytes)
```

O `XAUUSD` e o unico com **1123 bytes** — o tamanho de uma resposta real. Os
outros doze recebem **357 bytes**, que NAO e falha: e a recusa com motivo.

Prova do que sao os 357, medida em 04/11/2026 22:29:18 UTC contra o gateway
vivo (`GET /api/ai/predict?symbol=USDJPY&timeframe=H1`):

```json
{"ok":true,"available":false,
 "reason":"edge +0.0248 abaixo do minimo +0.0500 (acc 0.3746 vs palpite 0.3499)",
 "symbol":"USDJPY","timeframe":"H1","signal":"NEUTRAL","confidence":0.0}
```

**Regra que fica:** `available=false` com `reason` preenchida e o gate a
trabalhar. O que seria defeito e um `false` sem motivo, ou um `true` com
`confidence=0`. Doze simbolos sem modelo aprovado, um com modelo — e o
contrato, nao o defeito.

Resposta real do XAUUSD no mesmo instante (1122 bytes de corpo):

```json
{"ok":true,"available":true,"signal":"SELL","confidence":63.6,
 "prob_buy":0.3635,"prob_sell":0.6365,"price":4063.84,"atr":17.4394,
 "edge":0.03629,"accuracy":0.5361,"inference_ms":49.28,
 "model":"XAUUSD 1H","feature_hash":"5305081777808310"}
```

O `feature_hash` e o mesmo que o artefacto publicado declarava — logo o
runtime corrigido no P-01b esta a servir o modelo certo, nao outro.

### 1.1 E o que era o 401 das 18:12

```
2026.11.04 18:12:03  (USDJPY,H1)  [AI] GATEWAY | HTTP 401 |
  http://127.0.0.1:9001/api/ai/predict?... | token RECUSADO
  (17 caracteres enviados) | corpo=0B
```

Duas coisas medidas nessa linha, ambas ja corrigidas pelo reattach do ciclo
92: a porta era **9001** (o gateway esta em 9011) e o token tinha **17
caracteres** — o nome da variavel, nao o valor. Depois do reattach, todas as
13 instancias apontam para 9011 e o token e lido do `.env` em runtime. A
diferenca entre as duas linhas de journal e a prova.

### 1.2 Uma anomalia que fica registada, nao resolvida

```
2026.11.04 18:37:54  (USDCZK,H1)  [AI] GATEWAY | HTTP 1001 | ... | backend fora do ar | corpo=0B
```

`1001` nao e um codigo HTTP. O EA imprime o que o `WebRequest` devolveu na
variavel de status e o texto cai no ramo "backend fora do ar". Como a mesma
rota responde 200 para USDCZK depois das 19:07, isto e intermitente e nao
bloqueia. **Fica aberto** com esta descricao exata, para nao ser redescoberto
como "a IA caiu".

---

## 2. O fallback do Strategy Tester: `Data\prediction_XAUUSD.json`

O bloqueio medido do ciclo 92: `WebRequest` com `Authorization: Bearer` nao
funciona dentro do Strategy Tester, logo em backtest o EA so tem a FONTE 2
(`AI\AIConnector.mqh`, `LoadAIPrediction`).

O ficheiro existia, mas **velho**:

| Campo | Antes (03/11 00:44) | Depois (04/11 22:28 UTC) |
|---|---|---|
| `timestamp_utc` | 2026-11-03T03:44:18 | 2026-11-04T22:28:22 |
| `signal` / `confidence` | SELL / 69.02 | SELL / 63.6 |
| `price` | 3879.83 | 4063.84 |
| `feature_hash` | 5305081777808310 | 5305081777808310 (igual) |
| tamanho | 1235 B | 1082 B |

O gateway **nao publica `timestamp_utc`** — o parser le `timestamp_utc` e, se
vazio, cai para `timestamp` (`AIConnector.mqh`, P1.83). Nenhum dos dois vem na
resposta do `/api/ai/predict`. Por isso o ficheiro tem de levar a data: uma
copia crua do corpo do gateway ficaria sem frescura nenhuma e a verja nao
teria como aprovar nem reprovar.

O ficheiro e **dado gerado**, nao fonte: `.gitignore:80` e
`Files/Data/*.json`, confirmado com

```
git check-ignore -v --no-index "Files/Data/prediction_XAUUSD.json"
→ .gitignore:80:Files/Data/*.json
```

Logo nao entra no repositorio e nao polui o CI.

### 2.1 O aviso que tem de ficar escrito

1. **Um retrato nao e um modelo.** O ficheiro guarda a resposta de UM instante
   (SELL, 63.6, preco 4063.84). Em backtest o EA le esse sinal para todos os
   bars do periodo. Isso NAO mede a IA: mede o que acontece quando se repete o
   mesmo sinal durante dois meses. Qualquer resultado desse run diz respeito a
   geometria e a gestao, nao a capacidade preditiva. Para medir a IA em
   backtest e preciso o pipeline a escrever o ficheiro por bar, nao uma copia.
2. **A frescura em tester e tempo historico.** No tester `TimeCurrent()` e o
   tempo do bar simulado, nao o relogio. Um `timestamp_utc` de 04/11 contra um
   backtest que termina em 01/11 e uma data FUTURA; se a verja calcular
   `agora - ts`, o resultado e negativo e passa. Isso e um comportamento, nao
   uma validacao — e fica escrito para nao ser lido como "a frescura foi
   aprovada".
3. **Regenerar e barato e tem de ser feito com o gateway vivo:**

```
GET http://127.0.0.1:9011/api/ai/predict?symbol=XAUUSD&timeframe=H1
Authorization: Bearer <XAU_GATEWAY_TOKEN do .env>
```

   O valor do token nunca vai para documento, log, commit nem resposta.

---

## 3. O que NAO foi feito, e por que

- **Re-medir no Strategy Tester.** Continua bloqueado. `tasklist` em 04/11
  mostra `metatester64.exe` 8772 e 12896 (Services), `MetaTester64.exe` 11832 e
  4212 (Services) e `metatester64.exe` 4476 (Console, 254 MB) — e
  `tester_list_result_windows` devolve `{"windows":[]}`. As duas fontes
  discordam outra vez; a decisao e acreditar no `tasklist` e NAO lancar run,
  porque lancar com o slot ocupado ja morreu em 20–50 ms com
  `Core 1 disconnected`.
- **Compilar e reanexar.** Nenhum `.mq5`/`.mqh` foi tocado neste ciclo, logo o
  binario publicado continua `XAU_AI_PRO.ex5` de 2026-11-04 19:15:59
  (`Result: 0 errors, 0 warnings`). `deploy` nao foi re-corrido porque nao
  havia fonte nova para publicar.
- **Conta real.** Continua recusada com os numeros do ciclo anterior: PF 0,6206,
  41,4% de acerto, 10–11 perdas consecutivas, contra a regra do dono
  PF > 1,20 e perdas seguidas <= 8.
- **Push para `origin` (forge.mql5.io).** Continua a falhar com
  `Credentials are incorrect or have expired` (exit 128). Nao se repete sem
  credenciais novas; o `github` recebe o commit.

---

## 4. O que separa o EA de "uso real", medido hoje

| # | Item | Estado |
|---|---|---|
| 1 | IA responde no EA vivo | **fechado** — 13/13 graficos com `[AI] GATEWAY`, XAUUSD 1123 B |
| 2 | Fallback para backtest | **fechado** — `prediction_XAUUSD.json` refrescado do gateway, com data |
| 3 | Re-medir com o binario v1.2.135 | **bloqueado** — slot do tester ocupado (5 processos) |
| 4 | PF > 1,20 / streak <= 8 | **nao atingido** — PF 0,6206 / 10–11 perdas |
| 5 | Geometria coerente | **aberto** — RewardRatio 0,65 em producao vs 1,30 no `.set`; MinRewardRatio 0,55 vs 1,00 |

Enquanto o item 3 estiver bloqueado e o 4 nao mudar, "uso real" continua sendo
o que o dono decide com estes numeros na mao — nao uma conclusao que este
documento autorize.
