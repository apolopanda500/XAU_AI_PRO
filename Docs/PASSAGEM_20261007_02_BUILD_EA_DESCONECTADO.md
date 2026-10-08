# PASSAGEM — 07/10/2026, o build, o EA que nao e o do repo, e o SL/TP

> **Documento de trabalho. Sem data e sem hora de proposito: as regras valem
> para sempre, os numeros nao. Se um numero divergir do que o comando medir,
> o comando vence; corrija o numero.**

Este ciclo mediu quatro coisas que nenhum dos 90 documentos da pasta registrava.
A maior delas muda o que "o EA" significa neste projeto.

---

## 1. ESTADO EM UMA FRASE

O build novo foi feito, instalado e medido. **O EA que opera a conta real
nao e o do repositorio** — e ele nao tem IA, nem trava de stop obrigatorio, e
91 arquivos `.mqh` defasados. O dono revogou a obrigatoriedade de SL e TP.

---

## 2. OS NUMEROS, MEDIDOS NESTA SESSAO

| | medido | antes |
|---|---|---|
| `pytest` | **1279 verdes** | 1271 |
| `vitest` | **741 verdes, 52 arquivos** | 731 / 51 |
| `tsc --noEmit` | **exit 0** | limpo |
| `preflight` | 13 `[ok]`, **1 aviso**, 0 falhas | — |
| `test_mql5_compila` | **2 passed**, MetaEditor de verdade, 0 erros | — |
| HEAD | `442ee94` + as alteracoes deste ciclo | `442ee94` |

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests -p no:cacheprovider   # 1279
.\.venv\Scripts\python.exe -m pytest -q tests/test_mql5_compila.py # 2, compila
cd frontend; npx tsc --noEmit; npx vitest run                        # 0 / 741
```

### Build e instalacao

| passo | medido |
|---|---|
| `scripts\build_app.bat` | **exit 0, 7/7** |
| frontend (`vite build`) | 199 modulos, **760 ms** |
| core Rust (`cargo build --release`) | **4m 37s** |
| `XAU AI PRO.exe` | **13.829.120 B** (era 13.827.072) |
| NSIS | **219,6 MB** (era 230.238.951 B = 219,6 MiB) |
| MSI | **339,6 MB** |
| instalado | registro `XAU AI PRO 1.2.4`, portas 9001/9002/9003 |
| `%APPDATA%\XAU_AI_PRO` | **sobreviveu** a desinstalacao |

**Prova de que a correcao do SL entrou no artefato:** o CSS novo tem
`minmax(280px` e **nao** tem `minmax(0, 1.35fr)`, que era o defeito.

---

## 3. O ACHADO MAIOR: O EA QUE OPERA NAO E O DO REPOSITRIO

Fui verificar, depois de compilar, **qual `.ex5` o terminal carrega**. Nao e o
do repositorio. Nunca foi.

| | fonte | binario |
|---|---|---|
| **Repositorio** | `XAU_AI_PRO.mq5` **04/10** · 55.591 B | 438.312 B (compilei 07/10 20:42) |
| **Terminal (o que opera)** | `XAU_AI_PRO.mq5` **26/09** · 59.802 B | **628.276 B, 04/10 11:10** |

O diff do `.mq5` tem **469 linhas** diferentes (174 so no repo, 295 so no
terminal). **91 `.mqh` defasados** no terminal.

Varridos os 92 `.mqh`/`.mq5` do terminal (sem `Release`):

```
9001 .............. 0 arquivos
api/ai ............ 0 arquivos
WebRequest ........ 1 arquivo   (Telegram, NotificationCenter.mqh)
RequireStopLoss ... 0 arquivos
```

**O EA que opera a conta 391773676 nao chama o gateway Python e nao tem
`RequireStopLoss`.** Esse input foi criado em 05/10 **justamente porque este
EA abria posicao com `sl = 0.0` nesta conta**.

### 3.1 A IA nunca chega ao EA

O `AIConnector.mqh` do terminal le `Data\prediction_<SYM>.json`. Esses
arquivos existem, mas **com `#` no nome**:

```
prediction_BTCUSD#.json   14/08  BUY  price 66310.86  timestamp 2026-07-21
prediction_GOLD#.json     14/08  BUY  price 4077.93
prediction_XAUUSD.json    05/08  BUY  price 4056.83
prediction_BTCUSD.json    <- NAO EXISTE
```

Os 12 graficos estao anexados a `BTCUSD`, `GOLD`, `ETHUSD` — **sem `#`**.
O EA nao acha predicao para nenhum. E o mais novo tem timestamp de **21/07**,
quase tres meses atras; o repo tem `MaxPredictionAgeSec = 900` que recusaria
mesmo se achasse.

**Este e o mesmo defeito de sufixo `#` do `MaxSpreadBySymbol`** (§5.1). O
mesmo erro, em dois lugares, por misunderstandings diferentes.

### 3.2 Consequencia medida

O EA opera **as cegas**, pelo motor de regras local de agosto. As 20 operacoes
de BTCUSD sairam dai, nao da IA. Isso explica na raiz o defeito D5 de
`PLANO_DEFINITIVO` ("AI: Inativo em todas as telas"): nao era a tela.

**Sao tres versoes do EA em jogo** — e o repositorio e a quarta:

| | quando | fonte |
|---|---|---|
| backtest de 23/09 | `estadoA_8445b74\...ex5` de **23/09 22:03** | **11/09** |
| **o que opera** | binario de **04/10 11:10** | **26/09** |
| o que o `PASSAGEM §6.2` mandava recompilar | 07/10 01:08 | 04/10 |
| o que eu compilei | 07/10 20:42 | 04/10 |

Nenhum documento da pasta aponta essa divergencia. Todos falam como se houvesse
um EA so.

---

## 4. O BACKTEST QUE O DONO RODOU

Rodou sozinho, das ~20:12:38 (quando o app morreu) ate **21:42:08**. O dono
confirmou que foi proposital.

```
test Experts\estadoA_8445b74\XAU_AI_PRO\XAU_AI_PRO.ex5 on BTCUSD,M5
BTCUSD,M5: 2896886 ticks, 18948 bars. Test passed in 1:29:30.168
[CIRCUIT] Perfil: Conservative | Lot=0.01 | SL=80 | TP=160 | MaxDD=3.0% | Trades=5
```

Mediu **o binario de 23/09 com fonte de 11/09** — o mesmo invalido que o
`PASSAGEM §6.2` apontou. E em **BTCUSD,M5**, nao em GOLD,M5.

### 4.1 O resultado (`xau_ai_pro_summary.csv`, escrito 21:42:08)

**ATENCAO — ESTES NUMEROS JA NAO ESTAO NO DISCO.** Medido as 22:44:
`xau_ai_pro_summary.csv` foi **SOBRESCRITO** as **22:29:13** por um ciclo novo
que rodou **0 trades** (`ClosedDeals 0 · NetProfit 0.00 · PF 0.0000`), e
`BacktestSummary.txt` ganhou o bloco `===== 2026.10.08 04:29:13 =====`
(22:29 local, hora de servidor).

**O `xau_ai_pro_summary.csv` e SOBRESCRITO a cada ciclo; o `BacktestSummary.txt`
e ACUMULADO.** Quem procurar o resultado do backtest de hoje no arquivo vai ler
`0` e concluir que o teste nao fez nada. **A prova esta aqui, e so aqui.**

```
Symbol BTCUSD   ClosedDeals 902   Wins 477   Losses 425
WinRate 52,88%  NetProfit -374,17  GrossProfit 295,76  GrossLoss 669,93
ProfitFactor 0,4415   MaxDD 374,76 (66921,43%)   Sharpe -10,43   Expect -0,41
MaxWinStreak 12   MaxLossStreak 16   FinalBalance 624,87
```

O mesmo resultado, medido direto do `BacktestReport.csv` (BTCUSD):
`WIN 477` (ganho medio **+0,6200**, max. **+2,61**) e `LOSS 435` (perda media
**-1,5401**, max. -3,21) — razao **2,484**, winrate real **52,30%**.

| | |
|---|---|
| ganho medio | **+0,6200** (max. **+2,61**) |
| perda media | **-1,5401** (max. -3,21) |
| razao perda/ganho | **2,484** |
| **winrate de break-even** | **71,30%** |
| winrate real | **52,30%** → **faltam 19 pontos** |

### 4.2 O SL configurado NAO e o SL medido

Derivado das 4 perdas reais da conta (volume 0,01, `contract_size` 1,0):

| perda | preco | pontos |
|---|---|---|
| -1,41 | $141,00 | **14.100** |
| -1,53 | $153,00 | **15.300** |
| -1,45 | $145,00 | **14.500** |
| -1,55 | $155,00 | **15.500** |
| **media** | **$148,50** | **14.850** |

O perfil Conservative declara **SL = 80 pontos** e `StopLossPoints = 300`.
**O SL real e 186x o Conservative e 49x o `StopLossPoints`.** Nao medi ainda de
onde vem — essa e a proxima peca.

### 4.3 `BacktestReport.csv` esta CORROMPIDO

**7.100 de 47.699 linhas (14,9%)** com campos trocados: `Symbol` contendo
timestamps, `Result` concatenado. E um arquivo **acumulado** (julho a setembro,
18 simbolos) — nao e so o teste de hoje. Sintoma de escrita concorrente: as 12
instancias do EA gravam no mesmo arquivo sem trava.

**E a coluna `AI` e `0.00` em 40.599 de 40.599 linhas validas — 100%.** O
backtest nunca usou IA.

---

## 5. TREINO DE MODELOS: O QUE A MEDIDA RESPONDE

O dono perguntou se vale treinar. A resposta medida e **nao**, e o motivo nao e
o modelo.

### 5.1 As metricas dos 39 modelos

| modelo | acerto | baseline | edge | amostras | estavel |
|---|---|---|---|---|---|
| **MULTI_METALS** | **58,31%** | 33,33% | **24,97%** | 67.678 | sim |
| EURUSD_H4 | 54,26% | 33,33% | 20,92% | 779 | sim |
| MULTI_FIAT | 51,86% | 33,33% | 18,53% | 149.927 | sim |
| MULTI_CRYPTO | 51,50% | 33,33% | 18,16% | 149.926 | sim |
| BTCUSD_H4 | 48,85% | 33,33% | 15,52% | 1.074 | sim |
| BTCUSD_M5 | 35,27% | 33,33% | **1,94%** | 51.878 | **NAO** |
| **XAUUSD_M5** | **32,88%** | 33,33% | **-0,45%** | 35.376 | **NAO** |

O baseline e 33,33% = 1/3 porque sao 3 classes. **Os 8 modelos M5 tem
`edge_estavel: false`, e `XAUUSD_M5` tem edge NEGATIVO — pior que nao ter
modelo.** O backtest rodou em **BTCUSD,M5**: o segundo pior dos 39.

### 5.2 Por que treinar nao fecha a conta

- O melhor modelo acerta **58,31%** em 3 classes. No melhor caso, se todo
  acerto fosse direcional, dariamos 58% — **13 pontos abaixo dos 71,30%** que a
  razao 2,484 exige.
- **E a conta esta errada desde o inicio.** O perfil declara `SL=80 · TP=160`
  (1:2), que daria razao 0,5 e break-even em **33,3%** — abaixo dos 52,30%
  medidos, e o EA seria lucrativo. A razao medida e **2,484**.
- Com 52,30% de acerto e razao **1:1** o EA **lucra**. O que o quebra e a razao.

**Antes de treinar qualquer coisa: achar de onde vem o SL de 14.850 pontos.**

---

## 6. O FILTRO DE SPREAD (so o barulho, por decisao do dono)

MEDIDO: 934.078 linhas / **139,2 MB** de journal em um dia.

```
 57.393  [CIRCUIT] SPREAD EXPLOSION
 57.393  [CIRCUIT] SPREAD ALTO  (o mesmo tique)
 38.331  [SAFETY] Free margin low
 20.067  blocos de "=== RECOVERY STATUS ===" (8 linhas cada = 160.536)
```

12 instancias do EA, 3 delas no mesmo BTCUSD (M1, M5, M15).

### 6.1 O spread NAO esta explodindo — a UNIDADE esta errada

Spread real medido as 20:35:

| simbolo | point | spread | **spread em %** | pontos | disparou? |
|---|---|---|---|---|---|
| GOLD | 0,01 | 0,56 | **0,013%** | 56 | nao |
| EURUSD | 0,00001 | 0,00019 | **0,018%** | 19 | nao |
| **BTCUSD** | 0,01 | 40,00 | **0,048%** | 4000 | **10.451x** |
| **USDSEK** | 0,00001 | 0,01662 | **0,166%** | 1662 | **46.796x** |

**BTCUSD tem o MENOR spread relativo da lista e e o mais bloqueado.**

Duas causas, ambas confirmadas:

- **A. O mapa nunca acerta.** `Config.mqh:87` tem
  `"GOLD#:350,BTCUSD#:600,ETHUSD#:600"` — com `#`. Os graficos usam os nomes
  **sem `#`, e `GetMaxSpread` compara com `StringCompare` exato. O mapa protege
  exatamente nenhum dos tres que ele nomeia, e todos caem no fallback
  `MaxSpread = 50`.
- **B. Por isso o limit e 500.** `CircuitBreaker.mqh:310-311` faz
  `GetMaxSpread(symbol) * 10.0` → **500**, que e o `Limit=500.00` do journal.
  Se o mapa acertasse, BTCUSD teria 6000 e o spread de 4000 passaria.

**"500 pontos" vale $5,00 no BTCUSD e $0,005 no EURUSD — 1000x**, porque
`digits` vai de 2 a 5 entre os graficos. A raiz e o limite ser **pontos crus**:
precisa ser relativo ao preco, ou normalizado por `point`.

### 6.2 O que foi feito (e o que NAO)

O dono pediu **so reduzir o barulho**. Feito: throttle de 60 s por simbolo em
`CircuitBreaker.mqh`, nos dois pontos.

**A CALIBRACAO NAO FOI TOCADA.** `CheckSpreadExplosion` continua devolvendo
`true` nos mesmos tiques, com o mesmo limite, e `RunSymbol` continua delegando
o bloqueio ao `ValidateTrade`. O proprio comentario da linha 879 ja dizia que
esse log "serve apenas de diagnostico".

Declarado em `AUTORIZACOES_MQL5` como **aviso**, nunca `ok`, porque compilar
nao reanexa (`AGENTS.md` §7).

---

## 7. O GRAFICO: DUAS CORRECOES

### 7.1 O app instalado ainda dava "Identidade de mercado invalida"

MEDIDO na captura de **22:01** — **no app novo que acabei de instalar**:

```
Gráfico indisponível: Identidade de mercado inválida.
BTCUSD sem candles reais para M1.
0 candles          rodapé: BTCUSD · — ·
```

**Os dois lados, medidos:**

| | mercado vazio `''` |
|---|---|
| **backend** `_universal_assets('mt5','')` | **1639 ativos**, BTCUSD `class=crypto contract=1.0` |
| **backend** `_universal_candles('mt5','','BTCUSD','M1')` | **20 candles, `status=ok`** |
| **frontend** `useCatalogoAtivos('mt5','')` | **`setAtivos([])` sem consultar** |
| **frontend** `normalizeMarketSource('mt5','')` | **`null`** → throw |

**O backend tem reserva** (`_universal_scope` troca vazio por `"other"` no MT5).
**O frontend nao tinha nenhuma e falhava antes de chegar la.** E AGENTS.md §5: o
operador lia "Identidade de mercado invalida" e culpava o gateway, que estava
respondendo 1639 ativos.

Cadeia: `auto.market=""` → catalogo vazio → `fichaDoAtivo=null` →
`mercadoDoAtivo(undefined)=null` → `market=""` → throw.

**Corrigido** em `useCatalogoAtivos.ts`. Trava em `useCatalogoAtivos.test.ts`
(5 casos). **Prova negativa feita:** revertendo a correcao, **4 de 5 reprovam**.

### 7.2 O ouro, confirmado no codigo empacotado

```
1639 ativos · GOLD   model_symbol=XAUUSD  has_model=True  class=metal  contract=100.0
BTCUSD               model_symbol=None                     class=crypto  contract=1.0
EURUSD               model_symbol=None                     class=forex   contract=100000.0
para_corretora('mt5','XAUUSD') = GOLD   ·  para_modelo('mt5','GOLD') = XAUUSD
1 de 1639 ativos declara ter modelo   (o guarda segura)
```

---

## 8. SL E TP DEIXARAM DE SER OBRIGATORIOS

**Decisao do dono, 07/10/2026.**

### 8.1 O que motivou

MEDIDO nas capturas de 22:01 e no historico: o painel escrevia **"Preencha SL e
TP para ligar o AUTO"** e recusava sem os dois campos — enquanto as colunas
**S/L e T/P do historico saiam VAZIAS** nas 10 operacoes. **O acoplamento nao
existia:** a obrigatoriedade era do painel, e o que saia era uma ordem a
mercado sem os dois.

### 8.2 O que mudou

| lugar | antes | agora |
|---|---|---|
| `mt5_gateway.py` `_trade_order` | `sl <= 0 or tp <= 0` recusa | so `sl < 0 or tp < 0` recusa |
| `mt5_gateway.py` `_trade_pending_order` | idem | idem |
| `auto_engine.py` `LimitesAuto.valido()` | exige lote + sl + tp | **exige so o lote** |
| `AcompanharModelos.tsx` | recusa e desabilita o botao | **avisa e deixa clicar** |
| `OperacaoAutomatica.tsx` | recusa em `ligar()` | nao inclui os campos |

**O QUE NAO MUDOU:** `symbol`, `side`, `volume` continuam obrigatorios; quando
o valor e informado, continua tendo de ser `> 0`; e a ordem continua exigindo
`confirm=true`, `request_id` idempotente, `risk_gate`, `intent_log` e
`audit_log`. **O que mudou e a obrigatoriedade, nao a trilha.**

**`sl: 0` nao vai no corpo.** Zero e um NUMERO, e nao uma ausencia — o gateway
so distingue os dois pelo **nome** do campo. Campo ausente e o que significa
"sem protecao".

### 8.3 O que o dono pediu e ficou

- Botao explicito **`Enviar sem SL/TP`** no painel de ordem, com `aria-pressed`.
- **Aviso visivel** antes de enviar, dizendo o que falta.
- Os presets 1:1 a 1:4 continuam preenchendo.

### 8.4 Um furo encontrado no caminho

`LimitesAuto.valido()` **nunca checou `sl_preco`/`tp_preco`/`sl_valor`/`tp_valor`
negativos** — a lista de negativos so tinha `sl_atr`/`tp_atr`. `sl_preco=-1` era
aceito. **Nao foi efeito do relaxamento: ja passava antes**, pela porta do modo
simples. Corrigido.

### 8.5 Quatro testes reescritos — e um deles estava mentindo

Os 4 que falhavam travavam a regra revogada. Nenhum foi afrouxado ou removido:
**a regra mudou por decisao do dono, e o teste mudou junto** — cada um ganhou
**prova negativa do que continua recusado** (volume, `confirm`, sl negativo).

Um deles **passava sem provar nada**: `test_demo_exige_sl_e_tp` usava `_pedido()`,
que monta `quantity`, enquanto `_trade_order` le `volume`. O volume chegava
**0** e a ordem era recusada por volume — a excecao nunca chegava na regra de
sl/tp. **E AGENTS.md §6: um teste que so passa nao prova que a guarda funciona.**
Corrigido com `_pedido_mt5()`, no nome que o codigo realmente le.

---

## 9. A CONTA REAL, MEDIDA AS 20:33

```
391773676 · XMGlobal-MT5 14 · 1:1000
balance 7,90   equity 13,52   margem_livre 13,52   posicoes: 0
20 deals em 3 dias, TODOS BTCUSD, +2,28
ultima operacao: 10:42
```

O `PASSAGEM §6.1` dizia "8 posicoes, saldo livre $3,94". Hoje: **0 posicoes,
$13,52**. Deu **+3,96** desde a medicao do doc.

**Tres travas ativas simultaneas**, todas a cada tique:

```
[SAFETY] Daily loss limit: 1.45/0.17
[SAFETY] Free margin low: 13.52/20.00
[CIRCUIT] SPREAD EXPLOSION
```

`MinFreeMargin = 20` (`Config.mqh:62`) contra $13,52: **o EA se auto-bloqueia
em todas as entradas.**

---

## 10. ARMADILHAS DESTA SESSAO

**O app morreu e eu nao vi.** No inicio medi `XAU AI PRO` PID 6684 e as tres
portas em `Listen`; no fim, nada. O `preflight` respondeu `porta 9001: livre` —
**e nao mentiu**. Sem WER nem CrashDumps: nao foi crash, foi fechamento. **Um
`ok` do preflight tambem precisa ser lido contra a medicao.**

**Um teste verde que passava pelo motivo errado** (§8.5). `volume: 0` do
payload errado fazia a excecao nascer antes da regra testada.

**Um `return` sem indentacao derruba 12 arquivos de teste de uma vez.** Perdi
4 espacos num `edit` e o sintoma foi `SyntaxError: 'return' outside function` em
`mt5_gateway.py`, com **12 erros de coleta** — nenhum deles no arquivo que eu
tinha editado de fato. Rodar `ast.parse` no arquivo alterado antes da suite
custa um segundo.

**`grid-area` duplicado SOBREPOE, nao empilha.** A area `presets` ja era dos
botoes 1:1; usar a mesma classe dava dois elementos na mesma area.

**Arquivo de 4,8 GB numa unica varredura** trava o pipeline. O log do Strategy
Tester tinha **4,80 GB**; o disco foi de 17,28 GB para **9,06 GB**. O
`DISCO_MINIMO_GB` do preflight e 4,0, e o `AGENTS.md` §8 registra que o
`cargo check` ja falhou duas vezes com `Espaco insuficiente (os error 112)`.

---

## 11. O QUE ESTA ABERTO

1. **O EA do terminal.** 91 `.mqh` defasados, sem IA, sem
   `RequireStopLoss`, com `MaxSpreadBySymbol` que nunca acerta e predicoes de
   agosto. **Sincronizar e recompilar e o proximo passo natural.**
2. **De onde vem o SL de 14.850 pontos**, contra 80 declarados. Sem isso, nem
   modelo nem ajuste de parametro tem efeito.
3. **A razao 2,484.** Com 52,30% de acerto e razao 1:1 o EA lucra.
4. **Limite de spread em pontos crus** — precisa ser relativo ao preco (§6.1B).
5. **`MinFreeMargin = 20`** contra $13,52 trava o EA.
6. **3 instancias do EA no mesmo BTCUSD** (M1, M5, M15) com o mesmo
   `MagicNumber 2026001`.
7. **`/api/trade/pending`**: tem `risk_gate`, mas nao grava `audit_log` nem
   `intent_log` — unica abertura sem rastro das tres camadas. E nao ha
   consumidor no frontend.
8. **`BacktestReport.csv` corrompido** (14,9%) e **acumulado** entre 12
   instancias sem trava.
9. **Indicadores com busca** — `rsi` -> 3 resultados. Hoje sao tres botoes fixos.
10. **O log de 4,80 GB** do Strategy Tester, e o disco em 9,06 GB.

---

## 12. REGRAS QUE NAO SE DESCARTAM

- **Nenhum saque, transferencia, resgate ou movimentacao para fora da
  corretora.** Trava: `tests/test_movimentacoes.py::TestNadaDeDinheiroForaDaCorretora`.
- **Toda escrita exige `confirm=true` e `request_id` idempotente.** Retirar a
  obrigatoriedade de SL/TP **nao** pode abrir uma porta sem confirmacao — e o
  que `test_confirm_continua_obrigatorio` trava.
- **Nenhum simbolo nem corretora pode ser presumido.** A classe vem da
  hierarquia que a corretora publica, nunca de palavra no nome.
- **Medir antes de dizer que esta consertado.** Aconteceu de novo hoje: o
  grafico estava "corrigido" e falhava **no app novo, na tela, as 22:01**.
- **Nunca `xfail` onde existe compilador e codigo.**
- **Toda correcao precisa de prova negativa.** Um teste que so passa nao prova
  que a guarda funciona — o `test_demo_exige_sl_e_tp` e a prova.
- **Um teste que trava uma regra revogada muda junto; um que trava uma regra
  que vale, fica.** Nenhum dos 4 foi afrouxado: cada um ganhou a prova negativa
  do que continua recusado.
- **Nao declarar "pronto" sem os numeros.**