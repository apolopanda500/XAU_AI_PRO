# CONVERSA — 07 e 08/10/2026, o ciclo inteiro, na ordem

> **Documento de trabalho. Sem data e sem hora de proposito: as regras valem para
> sempre, os numeros nao. Se um numero divergir do que o comando medir, o
> comando vence; corrija o numero.**

Este e o registro da conversa, pergunta por pergunta, com o que foi medido em
cada resposta. Companion de `PASSAGEM_20261007_02_BUILD_EA_DESCONECTADO.md`, que
tem os numeros; este tem a **ordem** e as **decisoes**.

---

## 0. ESTADO NO MOMENTO EM QUE ESTE DOCUMENTO FOI ESCRITO

```
conta 391773676 · XMGlobal-MT5 14 · 1:1000
balance 15,16   equity 20,7   margem_livre -0,40   2 POSICOES ABERTAS
```

| posicao | simbolo | lado | vol | entrada | SL | alvo | P&L | magic |
|---|---|---|---|---|---|---|---|---|
| `#246627332` | **EURUSD** | SELL | 0,01 | 1.12070 | 1.12056 | 1.11825 | +0,46 | **2026001** `XAU_AI_PRO` |
| `#246645615` | **USDCNH** | SELL | 0,01 | 6.70090 | 6.73090 | 6.64090 | -0,66 | **2026001** `XAU_AI_PRO` |

**A MUDANCA QUE DISPARA TUDO:** antes as **93 ordens de 30 dias tinham todas
`magic = 0`** e **zero** com `MagicNumber 2026001`. Agora as posicoes tm
`magic = 2026001` e comment `XAU_AI_PRO`. **O dono reanexou o `.ex5` novo**, e o
EA passou a operar — com o **app desligado**.

### Fusos (medido, e a razao de um relatorio que mentiu)

```
hora do Windows ......... UTC-3   (Get-Date -Format K -> -03:00)
TimeCurrent() do MT5 .... UTC
position.time_msc ...... epoch em UTC
```

O primeiro relatório dizia que a posicao tinha aberto "no futuro" (01:57 e
03:00 contra uma relogio em 00:10). Nao era o MT5: **e `fromtimestamp()` sem
fuso, que aqui aplica UTC-3.** Todo instante medido neste ciclo passa por
`TimeCurrent()`/`timezone.utc`.

---

## 1. A PERGUNTA INICIAL — "ler pasta docs"

Leitura da `Docs/` (90 itens). O arquivo de entrada era
`PASSAGEM_20261007_PRIMEIROS_PASSOS.md`. **Tres coisas divergiam do que eu medi:**

- `INDICE.md` manda ler documentos de 03→04/10, mas o estado real era 07/10.
- `ESTADO_E_PENDENCIAS.md` (27/09) fala da conta `111194406 MetaQuotes-Demo
  US$150,87`. A conta real e `391773676`.
- O proprio doc de passagem estava **1 commit atras** (`097567b`; o HEAD era
  `442ee94`).

**Nao me limitei ao que estava escrito.** Fui medir `pytest`, `vitest`, `tsc`,
`preflight`, as portas, os processos, o `.ex5`, a conta — e foi ai que apareceram
as tres descobertas que nenhum dos 90 documentos registrava.

---

## 2. O QUE EU MEDI, E O QUE OS DOCUMENTOS AFIRMAVAM

| | docs diziam | **medido** |
|---|---|---|
| `pytest` | 1271 | **1271** |
| `vitest` | 731 / 51 | **731 / 51** |
| `git status` | "0 pendentes" | **`?? .cursor/`** |
| HEAD | `097567b` | **`442ee94`** |
| conta: saldo livre | **$3,94** | **$13,52** |
| conta: posicoes | **8** | **0** (as 20:33) |
| resultado da conta | +0,62 em 8 | **+2,28** em 3 dias |
| `.ex5` do repo | 07/10 01:08 | **436.534 B de 07/10 20:13** |

**O app morreu durante a sessao.** No inicio medi `XAU AI PRO` PID 6684 e
9001/9002/9003 em `Listen`; no fim, nada. O `preflight` respondeu `porta 9001:
livre` — **e nao mentiu**: o app tinha morrido de verdade. Sem WER, sem
CrashDumps: nao foi crash, foi fechamento.

---

## 3. PERGUNTAS AO DONO E O QUE CADA RESPOSTA MUDOU

### 3.1 "Autorizo o build e a reinstalacao?"
**"Sim, build e reinstalar."** → Build 7/7, NSIS 219,6 MB, instalado, portas
9001/9002/9003 no ar. **Prova de que a correcao entrou:** o CSS novo tem
`minmax(280px` e **nao** tem `minmax(0, 1.35fr)`, que era o defeito.

### 3.2 "O EA esta travado por margem. Como trato?"
**"Medir por que o spread esta explodindo."**

Fui medir e o spread **nao** estava explodindo — **a comparacao e que esta em
unidades diferentes**:

| simbolo | point | spread | **spread em %** | pontos | disparou? |
|---|---|---|---|---|---|
| GOLD | 0,01 | 0,56 | **0,013%** | 56 | nao |
| EURUSD | 0,00001 | 0,00019 | **0,018%** | 19 | nao |
| **BTCUSD** | 0,01 | 40,00 | **0,048%** | 4000 | **10.451x** |
| **USDSEK** | 0,00001 | 0,01662 | **0,166%** | 1662 | **46.796x** |

**BTCUSD tem o MENOR spread relativo da conta e era o mais bloqueado.** Duas
causas: (A) `MaxSpreadBySymbol = "GOLD#:350,BTCUSD#:600,ETHUSD#:600"` usa `#`, e
os graficos usam os nomes **sem `#`**, com `StringCompare` exato — **o mapa nao
acerta para nenhum dos tres que ele nomeia**; (B) por isso o limite e
`50 × 10 = 500`, e "500 pontos" vale **$5,00 no BTCUSD e $0,005 no EURUSD**.

### 3.3 "Mudou o default dos gates?"
**"So o `/api/trade/pending`."** → Nao mexi em nenhum default. Documentei que
`XAU_ENABLE_TRADE_COMMANDS` tem default `"1"` e que `XAU_ENABLE_REAL_ORDERS`
nao existe no codigo.

### 3.4 "O `.ex5` foi recompilado hoje. Mudo a decisao de nao rodar backtest?"
**"Nao rodar."** → Nenhum backtest foi disparado por mim.

### 3.5 "O EA do terminal nao e o do repo. Como faco?"
**"Sincronizar e recompilar."** → Autorizado. **Ainda NAO executado** — exige
recompilar na pasta do terminal e **o dono reanexar**, que e passo dele (§7).

### 3.6 "Como trato o log de 4,80 GB?"
**"Analisar resultado para possivel treino nos modelos depois apagar."**

Analisei primeiro, apaguei depois: **disco 9,21 GB → 14,01 GB**. E registrei que
`xau_ai_pro_summary.csv` e **sobrescrito a cada ciclo** — as 22:29 um ciclo novo
com 0 trades apagou o resultado. **A prova esta no documento, nao no arquivo.**

### 3.7 "Quem disparou o backtest?"
**"Fui eu / foi proposital."** → Registrado. O backtest rodou `BTCUSD,M5`,
medindo `estadoA_8445b74\...ex5` de **23/09 com fonte de 11/09**.

### 3.8 "Quero que voce remova SL/TP obrigatorios antes de abrir posicao."
**"Remover sl tp obrigatorios... deixar o risco para o usuario e IA, com botao
pre configurados ao vivo real, com opcao mais sem sl tp obrigatorio."**

Feito nos 5 lugares. Detalhes na §4.

### 3.9 "Proximo"
**"Proximo"** → Fui atras do SL de 14.850 pontos. **A premessa estava errada.**

---

## 4. SL E TP — O QUE MUDOU, E O QUE NAO

**MEDIDO que motivou:** o painel escrevia *"Preencha SL e TP para ligar o AUTO"* e
recusava sem os dois campos, enquanto as colunas **S/L e T/P do historico saiam
VAZIAS** nas 10 operacoes. **O acoplamento nao existia:** a obrigatoriedade era
do painel, e o que saia era ordem a mercado sem os dois.

| lugar | antes | agora |
|---|---|---|
| `mt5_gateway._trade_order` | `sl <= 0 or tp <= 0` recusa | so `sl < 0 or tp < 0` recusa |
| `mt5_gateway._trade_pending_order` | idem | idem |
| `auto_engine.LimitesAuto.valido()` | exige lote + sl + tp | **exige so o lote** |
| `AcompanharModelos.tsx` | recusa e desabilita | **avisa e deixa clicar** |
| `OperacaoAutomatica.tsx` | recusa em `ligar()` | nao inclui os campos |

**NAO MUDOU:** `symbol`, `side`, `volume` obrigatorios; valor informado tem de
ser `> 0`; `confirm=true`, `request_id`, `risk_gate`, `intent_log`, `audit_log`.

**`sl: 0` nao vai no corpo** — zero e numero, e nao ausencia. **Botao
`Enviar sem SL/TP`** com `aria-pressed`, e aviso escrito antes de mandar.

### 4.1 Um furo que nao era do relaxamento

`LimitesAuto.valido()` **nunca checou `sl_preco`/`tp_preco`/`sl_valor`/`tp_valor`
negativos** — a lista so tinha `sl_atr`/`tp_atr`. **`sl_preco=-1` era aceito, e
ja passava antes**, pela porta do modo simples. Corrigido.

### 4.2 Quatro testes, e um deles mentindo

Tres travavam a regra revogada: **foram reescritos com prova negativa do que
continua recusado** (volume, `confirm`, sl negativo).

O quarto — `test_demo_exige_sl_e_tp` — **passava pelo motivo errado**: usava
`_pedido()`, que monta `quantity`, enquanto `_trade_order` le `volume`. O volume
chegava **0** e a ordem morria por volume, **antes de a regra de sl/tp ser
alcancada**. Verde sem verificar nada. Corrigido com `_pedido_mt5()`.

---

## 5. O ERRO MAIOR — EU ACEITEI UMA PREMESSA ERRADA

Fui atras do SL de 14.850 pontos (contra 80 declarados). E **nao ha bug**: as
ordens **nao eram do EA**.

| | medido |
|---|---|
| `AntiLoop: Aberturas 0/5` em 06/10 | **79.914 ocorrencias, todas `0/5`** |
| `magic` das 93 ordens de 30 dias | **0 em todas** |
| ordens com `MagicNumber 2026001` | **ZERO** |
| `EXECUTION SUMMARY` nos 12 graficos | `Orders=0 \| Exec=0` sempre |
| comment das saidas | `[sl 85615.69]` — **formato de ordem manual do MT5** |

**O EA nunca abriu nada.** As posicoes e o resultado medido eram **do dono, no
MT5 manual** — o caminho **MESA** do `AGENTS.md` §1.

Corrigi `PASSAGEM_20261007_PRIMEIROS_PASSOS` §6.1 e `FIM_DE_CONEXAO` §2.5, que
afirmam *"E o EA do MT5"*, e o commit `c578f10`, *"o motor que perdeu 2,94 na
conta"*. **Eu mesmo escrevi "o EA opera as cegas" no documento, e corrigi.**

E o que muda agora, com o dono reanexando o `.ex5`: **o EA passou a operar, com
o app desligado, e com as mesmas 91 defasagens.**

---

## 6. O BACKTEST, E A RESPOSTA SOBRE TREINAR

```
902 deals · 52,88% · Lucro -374,17 · PF 0,4415 · Sharpe -10,43 · MaxDD 66.921%
ganho medio +0,6200 · perda media -1,5401 · razao 2,484
break-even exige 71,30% de acerto — tinha 52,30%
```

**Treinar nao fecha a conta.** O melhor modelo (`MULTI_METALS`) acerta **58,31%**
em 3 classes — 13 pontos abaixo do necessario. E o baseline e 33,33% = 1/3.

**Os 8 modelos M5 tem `edge_estavel: false`, e `XAUUSD_M5` tem edge NEGATIVO
(-0,45%)** — pior que nao ter modelo. O backtest rodou em **BTCUSD,M5**, o
segundo pior dos 39.

Com razao **1:1** e 52,30% o resultado e positivo. Com 1:2 exige **71,30%**.

E a razao 2,484 vem de ordens **manuais** (§5): **mede um gesto humano, nao um
modelo.**

---

## 7. O MONITOR

`Temp\monitor_conta.py` — **so le, nao envia nada.** Rodando a cada 20 s, gravando
em `Temp\monitor_conta.jsonl`.

```
.\.venv\Scripts\python.exe Temp\monitor_conta.py --once
.\.venv\Scripts\python.exe Temp\monitor_conta.py            # Ctrl+C para
```

Grava por leitura: instante **UTC**, login, servidor, balance, equity, margem
livre, alavancagem, e por posicao: ticket, simbolo, lado, volume, entrada, stop,
alvo, P&L, magic, comentario, spread, SL e TP em pontos, e **`sl_sobre_spread`**.

Detecta e registra como evento: **abriu**, **fechou**, **margem livre negativa**,
e **SL a menos de 1,5x o spread**.

---

## 8. OS NUMEROS, MEDIDOS NO FIM DESTE CICLO

| | medido | antes do ciclo |
|---|---|---|
| `pytest` | **1279 verdes** | 1271 |
| `vitest` | **741 verdes, 52 arquivos** | 731 / 51 |
| `tsc --noEmit` | **exit 0** | limpo |
| `test_mql5_compila` | **2 passed**, 0 erros | — |
| `preflight` | 13 `[ok]`, **1 aviso**, 0 falhas | — |
| build | **7/7**, core Rust 5m 04s | — |
| NSIS / MSI | **219,6 MB / 339,6 MB** | — |
| disco livre | **14,01 GB** | 9,06 GB |
| git | **0 pendentes** | — |

### 8.1 O BUILD ESTA FEITO E **NAO ESTA INSTALADO**

| | |
|---|---|
| `XAU AI PRO_1.2.4_x64-setup.exe` | **08/10 00:10:10** |
| `XAU AI PRO_1.2.4_x64_en-US.msi` | 07/10 23:58:52 |
| CSS do `dist` | `index-JYVc-1jS.css` · tem `.sem-protecao` **e** `minmax(280px` |
| **instalado** | **ainda o de 07/10 21:42** |
| **app rodando** | **NAO** (o build parou os processos) |

**O app precisa ser reinstalado e subir** para voce conferir na tela o grafico
corrigido, o SL/TP opcional e o botao `Enviar sem SL/TP`.

---

## 9. O QUE ESTA ABERTO

1. **O app precisa ser reinstalado** do build de 08/10 00:10 e subir. **E o
   unico caminho para voce conferir na tela.**
2. **O EA esta operando agora**, com o app desligado, em **EURUSD e USDCNH** —
   simbolos que antes **nunca** operaram. Margem livre **negativa**.
3. **`MinFreeMargin = 20`** contra `$13,52` no momento medido. Se a margem livre
   esta negativa, o proprio EA deveria estar recusando por `FREE_MARGIN`.
4. **Sincronizar e recompilar o EA do terminal** — autorizado, nao executado.
5. **SL e TP desiguais entre simbolos:** EURUSD abriu com razao ~1:17 e USDCNH
   com 1:2. Nao medi de onde sai cada um; e o mesmo `StopLossPoints`.
6. **Limite de spread em pontos crus** (§3.2) — precisa ser relativo ao preco.
7. **`/api/trade/pending`**: tem `risk_gate`, mas nao grava `audit_log` nem
   `intent_log`.
8. **`BacktestReport.csv` corrompido** (14,9%) e acumulado entre 12 instancias.
9. **Indicadores com busca** — `rsi` -> 3 resultados.

---

## 10. REGRAS QUE NAO SE DESCARTAM

- **Nenhum saque, transferencia ou movimentacao para fora da corretora.**
- **Toda escrita exige `confirm=true` e `request_id` idempotente** — retirar a
  obrigatoriedade de SL/TP **nao** abre essa porta.
- **Nenhum simbolo nem corretora pode ser presumido.**
- **Medir antes de dizer que esta consertado.** Aconteceu **três vezes** neste
  ciclo: o grafico (corrigido no codigo, falhava no app novo as 22:01), o SL
  (media de uma premissa errada dos docs) e o teste que passava pelo motivo
  errado.
- **Toda correcao precisa de prova negativa.** Feita: reverter a correcao do
  catalogo reprova 4 de 5; o `sl: 0` e o `sl: 0.01` estao ambos travados em
  sentidos opostos.
- **Nao declarar "pronto" sem os numeros.**