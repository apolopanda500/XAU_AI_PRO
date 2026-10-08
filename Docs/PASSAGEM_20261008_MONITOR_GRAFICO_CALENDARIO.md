# PASSAGEM — 08/10/2026, o monitor morreu, o grafico nao tinha dado, e o calendario tinha dois fundos

> **Documento de trabalho. Sem data e sem hora de proposito: as regras valem para
> sempre, os numeros nao. Se um numero divergir do que o comando medir, o
> comando vence; corrija o numero.**

Leitura de entrada. Companion de
[`CONVERSA_20261008_CICLO_BUILD_EA_ABRINDO.md`](./CONVERSA_20261008_CICLO_BUILD_EA_ABRINDO.md),
que tem a **ordem** das perguntas; este tem os **numeros** e as **provas**.

Os tres defeitos deste ciclo tem a mesma forma: **um lado do dado dizia uma
coisa e a tela dizia outra**, e o sintoma caia em quem nao produziu a mensagem.

---

## 0. ESTADO MEDIDO NO FIM DESTE CICLO

```
disco ................. 17,81 GB livres  (era 11,76)
git ................... d19286d, arvore limpa no inicio, 8 arquivos no fim
pytest ................ 1283 passed, 1 skipped, 0 failed   (era 1279)
vitest ................ 773 passed, 55 arquivos           (era 731 / 51)
tsc --noEmit .......... exit 0
test_mql5_compila ..... 2 passed
preflight ............. 13 [ok], 1 aviso, 0 falhas

conta 391773676 · XMGlobal-MT5 14 · 1:1000
balance 15,30   equity 20,19   margem_livre +0,19   1 POSICAO
#246645615  USDCNH  SELL 0,01  entrada 6,7009  SL 0,7x o spread  -0,52
magic 2026001 · comment XAU_AI_PRO
```

### 0.1 O APP ESTA NO AR **SEM BACKEND**

| | medido as 17:17 UTC | medido as 17:50 UTC |
|---|---|---|
| `XAU AI PRO` PID 2936 | vivo | **vivo** |
| `xau-ai-pro-core` PID 3164 (9002, 9003) | vivo | **vivo** |
| **`mt5-gateway` / porta 9001** | **PID 3628** | **NINGUEM** |

**O gateway morreu com o app vivo.** Sem WER e sem crash dump — a mesma
assinatura da morte anterior do app descrita em
`PASSAGEM_20261007_02_BUILD_EA_DESCONECTADO.md` §2: *"nao foi crash, foi
fechamento"*.

**CONSEQUENCIA DIRETA:** sem gateway nao ha `/api/universal/assets`, nao ha
`/api/universal/candles`, nao ha journal. **E por isso que o grafico aparece
com `0 candles`** — antes de qualquer defeito de codigo do grafico. Tambem e
por isso que as ferramentas MCP respondem `401`/`10061`.

---

## 1. O GRAFICO — A RAIZ, E POR QUE O DOCUMENTO ANTERIOR APONTAVA PARA O LADO ERRADO

### 1.1 O sintoma

```
Grafico indisponivel: Identidade de mercado invalida.
BTCUSD sem candles reais para M1.
0 candles          rodape: BTCUSD · — ·
```

### 1.2 O que cada lado devolvia, MEDIDO

```
backend  _universal_assets("mt5", "")     -> status=unavailable  count=0
                                             error="catalogo de ativos ausente no upstream"
         ... e o MESMO para forex, metals, indices e other
         ... e nas CINCO chamadas seguidas

mt5      mt5.symbols_get()                 -> 1640 simbolos
backend  _universal_candles(...)           -> 500 candles, status=ok  (BTCUSD/GOLD/EURUSD, M1 e H1)
```

**O terminal estava bom e o backend tinha 500 candles.** O catalogo saia zero.

### 1.3 A CAUSA — dois leitores do mesmo terminal, uma versao com a guarda e outra sem

`backend/mt5_gateway.py`:

| rota | linhas | guarda de sessao |
|---|---|---|
| `_mt5_candles` (candles) | 2036 e 2087 | `if callable(inicializar) and not _mt5_connected(): _ensure_mt5()` |
| **`_symbols` (catalogo)** | **1733** | **NAO TINHA** |

```python
def _symbols() -> dict:          # ANTES
    mt5 = _mt5()
    rows = discover_assets(mt5, include_hidden=True)
```

`discover_assets` (`backend/asset_registry.py:177`) le `mt5.symbols_get()`. Sem
sessao aberta no processo, o MT5 devolve **`None`, sem lancar**. Dai:
`[]` → `count=0` → `status=unavailable` → `error="catalogo de ativos ausente no
upstream"`.

**E por isso que o catalogo DEPENDIA DA ORDEM:** se a rota de candles rodasse
antes, ela abria a sessao e o catalogo funcionava; se o catalogo fosse o
primeiro a pedir, devolvia zero. O operador via o seletor "aparecer sozinho" as
vezes e `Identidade de mercado invalida` as outras.

### 1.4 A PROVA

```
terminal SEM sessao:  symbols_get() -> None   -> count=0      unavailable
terminal COM sessao:  symbols_get() -> 1640   -> count=1640   ok
```

**Mesma rota, mesmos argumentos.** A diferenca e a guarda, e nada mais.

### 1.5 A CORRECAO

A mesma guarda das linhas 2036/2087, com `getattr` pelo mesmo motivo delas: os
dubles de teste injetam um modulo MT5 minimo, sem `initialize`.

### 1.6 POR QUE 1639 NO DOCUMENTO E LEVA A CULPAR O FRONTEND

`PASSAGEM_20261007_02_BUILD_EA_DESCONECTADO.md` §7.1 mediu **1639 ativos** e
concluiu *"o frontend nao tinha nenhuma reserva"*. Era **verdade naquele
instante** — e o numero **e o que uma sessao funcionando devolve**. O que ele
nao registra e que o catalogo **depende da ordem**, entao o mesmo codigo dava
1639 num minuto e 0 no seguinte.

**O conserto do frontend de 07/10 22:44 (`75309ad`) estava certo** e continua
certo: ele removeu um defeito real. O que ele nao podia resolver, sozinho, era o
produtor devolvendo vazio.

### 1.7 TRAVA E PROVA NEGATIVA

`tests/test_catalogo_exige_sessao_mt5.py`, 5 casos, com um terminal que so
responde depois de `initialize()` — como o MT5 real.

* O duble tem `symbols_get() -> None` **sem** `initialize`, e `initialize` que
  **recusa** (o caso que tem de reprovar: a rota tem de devolver `unavailable`
  e `count=0`, nunca um ativo inventado).
* **Medido: revertendo a guarda, 4 de 5 reprovam.**

O teste fixa o mapa de alias (`{"mt5": {"XAUUSD": "GOLD"}}`). Sem isso ele
dependia de estado deixado por outro teste: **sozinho passava, na suite inteira
reprovava** — e o `AGENTS.md` §11 pede para provar interferencia rodando o
arquivo alheio isolado, que foi o caminho.

---

## 2. O MINI TERMINAL — VERMELHO NO SAUDAVEL, BRANCO NO QUE TRAVAVA

### 2.1 O sintoma, nas capturas de 08/10 14:20

```
14:20:25  INFO   QQ ... XAU_AI_PRO (BTCUSD,M5) [RECOVERY]
14:20:25  ERROR  GD ... XAU_AI_PRO (BTCUSD,M5) AI: OK | Failures: 0 | Error:
14:20:25  ERROR  CI ... XAU_AI_PRO (BTCUSD,M5) Indicators: OK | Failures: 0 | Error:
14:20:25  ERROR  NR ... XAU_AI_PRO (BTCUSD,M5) Broker: OK | Failures: 0 | Error:
14:20:25  ERROR  GK ... XAU_AI_PRO (BTCUSD,M5) Dataset: OK | Failures: 0 | Error:
```

**Sete checks 100% OK marcados ERROR.**

### 2.2 A CAUSA — o classificador lia o NOME DO CAMPO

O formato vem do produtor, `MQL5/Experts/XAU_AI_PRO/Enterprise/RecoveryManager.mqh:621`:

```mql5
"  %s: %s | Failures: %d | Error: %s\n"
```

**`Failures` e `Error:` sao NOME DE CAMPO, impressos em toda linha, com saude
ou nao.** O classificador antigo (`UniversalLiveTerminal.tsx:146`) cascateava
regex sobre a PALAVRA:

```ts
: /error|fail/i.test(message) ? 'ERROR' : ...
```

`/fail/i` acha `Failures`. Uma linha 100% saudavel vira ERROR.

### 2.3 E no sentido inverso — medido em 200.185 linhas do EA

| tag | ocorrencias | o que e | o painel dizia |
|---|---|---|---|
| `[SAFETY]` | **63.837** | trava de margem/seguranca | INFO |
| `[CIRCUIT]` | **29.574** | disjuntor de spread | INFO |
| `[BACKUP]` | 1.865 | `FAIL \| copiados=9 \| falhas=98` | INFO |
| `[RECOVERY]` | 1.811 | relatorio de recuperacao | INFO |
| `[OPTIONAL]` | 100 | `Performance: PASS` | INFO |
| `[CRITICAL]` | 70 | `Execution: PASS - Bid/Ask disponiveis` | **TRADES** |
| `[VALIDATION]` | 30 | `1 BLOCKED - verificar antes de operar` | INFO |

`[CRITICAL]` era **TRADES** porque a cascata testava `/execut/i` e a linha tem a
palavra `Execution`. Um check que **passou** marcado como operacao de mercado.

**O operador via vermelho no saudavel e branco no que travava.** E o painel
mostra `slice(0, 14)` — **14 linhas de 200.185**.

### 2.4 A CORRECAO

`frontend/src/lib/journalKind.ts` — modulo proprio, nao dentro do componente que
o consome (o mesmo motivo de `useCatalogoAtivos.ts`).

1. **A linha de saude le o VALOR**: `Failures: N` com `N > 0` e ERROR;
   `Error:` com texto e ERROR; `Failures: 0 | Error:` vazio e **INFO**. O ramo
   devolve sempre, para a palavra do rotulo nao vazar para o passo 3.
2. **A etiqueta do produtor** decide pelo mapa de severidade — o vocabulario
   real, contado no `MQL5/Logs/20261008.log`, nao uma lista de palavras em
   ingles. E o veredito da propria linha vence a severidade nominal da
   etiqueta: `[CRITICAL] Execution: PASS` e INFO, porque o check passou.
3. **Veredito explicito** com fronteira de palavra, e so entao a acao de
   mercado.

### 2.5 UM DEFEXTO NOVO, DO PRIMEIRO MINUTO

`erroDeclarado` devolvia `''` quando o rotulo nao existia — e `'' !== null` e
verdade. **Toda linha sem o campo de saude entrava no ramo da saude e voltava
INFO.** O classificador devolvia INFO para TUDO. Achado pelos testes, antes de
medir no terminal.

### 2.6 PROVAS

* `frontend/src/lib/journalKind.test.ts` — **19 casos**, as mensagens sao
  **copias literais** do `MQL5/Logs/20261008.log`, nao inventadas para passar.
* `frontend/src/components/UniversalLiveTerminal.journal.test.tsx` — **4 casos**,
  o caminho inteiro ate a coluna `Tipo` pintada na tela.
* **PROVA NEGATIVA: o classificador ANTIGO, nas mesmas linhas, discorda em 5 de
  6.**

---

## 3. O CALENDARIO — O MESMO COMPONENTE COM DOUS FUNDOS

### 3.1 O sintoma, nas capturas de 08/10 14:14

A tabela do dia **de hoje** aparecia com o papel de parede atravessando as
linhas. A do dia **seguinte**, opaca. Mesmo componente, mesmo dia de dado.

### 3.2 A CAUSA — DUAS FOLHAS, UMA PROPRIEDADE, NINGUEM CONECTOU AS DUAS

`frontend/src/theme/global.css:1112`:

```css
.calendar-tab button { background: var(--panel2) !important; }
```

**A linha do evento e um `<button>`** (`EconomicCalendarTab.tsx:722`), entao essa
regra pinta a superficie da linha com `!important`, sobrepondo o
`background: transparent` do `calendar.css`.

E o esmaecimento de evento ja divulgado era:

```css
.cal-row.passado { opacity: 0.55; }
```

`opacity` no elemento **inteiro** desvanece a superficie junto com o texto. Com o
fundo opaco vindo de outro arquivo, a linha do dia de hoje saia 55%
transparente e o papel de parede aparecia por tras. No dia seguinte **nenhum**
evento e `passado`, nenhuma linha desvanece, e a mesma tabela saia opaca.

### 3.3 A CORRECAO

Esmaecer o **conteudo**, nunca a superficie:

```css
.cal-row.passado { color: var(--muted); }
.cal-row.passado .cal-row-time,
.cal-row.passado .cal-row-title, /* ... */ { opacity: 0.6; }
```

### 3.4 DECLARACAO DUPLICADA — CODIGO MORTO QUE MENTE

`calendar.css` declarava **duas vezes** `.cal-row.passado`, `.cal-row.alto`,
`.cal-row.medio` e `.cal-row:hover`. A segunda vencia. Quem so lesse a ultima
acreditaria num `opacity: 0.55` que nao e o que a tela aplica — e refaria o
defeito. As tres primeiras foram removidas; a quarta permaneceu, por ser a
unica que nao conflictava.

### 3.5 PROVA

`frontend/src/theme/calendar_linha.test.ts` — **9 casos**:

* `.cal-row.passado` **nao pode** ter `opacity` na linha (o defeito literal);
* o esmaecimento tem de existir no conteudo;
* **nenhuma classe da linha pode ser declarada duas vezes** — lista explicita;
* `global.css` tem de continuar pintando `.calendar-tab button` com
  `!important` — e por isso que a superficie existe. Se um dia isso mudar, o
  teste avisa em vez de deixar o defeito voltar em silencio.

**PROVA NEGATIVA: reposicao do `opacity` na linha reprova.**

---

## 4. O MONITOR — ESTAVA MORTO DESDE AS 08:56:56 UTC

### 4.1 O que o relatório anterior afirmava e o que mediava

> *"O monitor está no ar — Temp\monitor_conta.py, a cada 20 s, so leitura"*

**Estava morto ha ~8 h.** `Temp\monitor_err.log`:

```
File "Temp\monitor_conta.py", line 41, in agora_utc
    return datetime.fromtimestamp(mt5.symbol_info_tick("EURUSD").time,
AttributeError: 'NoneType' object has no attribute 'time'
```

### 4.2 QUATRO DEFEITOS, e um deles e o mais caro

| | defeito | por que doia |
|---|---|---|
| 1 | `agora_utc()` **presumia `EURUSD`** | `AGENTS.md` §3: nenhum simbolo pode ser presumido. Um simbolo ausente matava a vigia |
| 2 | `ref = t.ask ...` **fora** da protecao de `t is None` | o mesmo simbolo ausente derrubava o monitor na posicao, e nao no relogio |
| 3 | **`abs(margem_livre) < 0`** | **sempre falso.** O alerta de "margem livre NEGATIVA" era **codigo inalcancavel** — e o documento afirmava que o monitor detectava margem negativa. Ele nao detectava |
| 4 | uma leitura com excecao **matava o laco** | um monitor que morre no primeiro simbolo ausente nao vigia nada |

### 4.3 O FUSO — o carimbo `instante_utc` estava 3 h ADIANTADO

`mt5.symbol_info_tick().time` e hora de **servidor**, e nao UTC. O servidor
XMGlobal-MT5 14 roda GMT+3. O campo se chamava `instante_utc` e gravava `Z`.

```
as 17:02:40 UTC o monitor imprimiu  20:02:42Z
o evento "FECHOU 06:42:10Z" aconteceu as 03:42:10 UTC
```

O bloco de comentario antigo afirmava *"TimeCurrent() do MT5 .. UTC"*. **Medido:
falso.** Agora os dois instantes sao gravados em campos separados
(`instante_utc` do relogio da maquina, `instante_servidor` + `desvio_servidor_h`
de um tick que a corretora devolveu) e nenhum dos dois presume simbolo.

### 4.4 A CORRECAO E A PROVA

`Temp/prova_monitor.py` — **12 verificacoes**, com um duble de MT5 cujo
`symbol_info_tick` pode devolver `None`.

**A prova negativa reproduz o codigo ANTIGO ao pe**, nao um stub: e a copia
literal de `agora_utc`, e ela reproduz o traceback exato de 08/10 08:56:56Z
(`'NoneType' object has no attribute 'time'`). Um stub que apenas "nao existe"
provaria que a funcao sumiu, nao que ela matava o monitor.

O bloco 5 varre o **codigo** com `tokenize` — sem comentario nem docstring — e
reprova se aparecer nome de ativo em string. `EURUSD` sobrevive **so** no
docstring, que registra o defeito. E o `AGENTS.md` §6.4: a trava casa a REGRA,
nao a palavra.

### 4.5 O MONITOR RELIGADO, E ELE ESTA AVISANDO

```
PID 7652, a cada 20 s, so leitura
[17:24:59Z] ALERTA USDCNH: SL a 0.7 x o spread (32.0 pts) - stop dentro do ruido
[17:49:39Z] ALERTA USDCNH: SL a 0.7 x o spread (27.0 pts) - stop dentro do ruido
```

Tambem passou a gravar **`SL/TP ALTERADO`** quando o mesmo ticket muda de stop —
que e exatamente o que aconteceu com a USDCNH e que ninguem tinha registrado.

---

## 5. O QUE O RELATORIO ANTERIOR AFIRMAVA E O QUE MEDI

Tres das "tres coisas que precisam da sua atencao" **nao eram verdade**.

| | `CONVERSA_20261008` afirmava | **medido neste ciclo** |
|---|---|---|
| conta | margem livre **−0,40** | **+0,19**. Em 1.035 leituras com posicao: min **−0,70**, max **+0,56** |
| conta | **2** posicoes (EURUSD e USDCNH) | **1**. EURUSD **fechou as 03:42:10 UTC** |
| margem | "o EA deveria estar recusando por FREE_MARGIN **e nao esta**" | **ESTA recusando.** Journal vivo: `[SAFETY] Free margin low: 0.23/20.00` em GOLD, EURUSD, GBPUSD, USDJPY, USDCHF, USDSEK |
| spread | "SL menor que 1,5x o spread" | **0,7x**, e caindo: **6,57 → 2,20 → 0,62 → 0,70** |
| monitor | "esta no ar" | **morto ha ~8 h** |

`MinFreeMargin = 20` contra margem livre maxima de **$0,56** — fora por **36x**.
Nao e oscilacao de borda.

### 5.1 O SL E O TP DA USDCNH, medidos

```
06:42:10Z  stop 6,7309  alvo 6,6409   sl_sobre_spread 6,57
11:56:35Z  stop 6,7132  alvo 6,6724   sl_sobre_spread 2,20
20:02:42Z  stop 6,7086  alvo 6,6942   sl_sobre_spread 0,62
17:13:58Z  stop ...     alvo ...      sl_sobre_spread 0,70
```

**Mesmo ticket, mesma entrada `6.7009`** — foi **modificado no lugar**, nao
reaberto. **NAO MEDI se foi o EA ou a mao do dono no MT5.** O dono mandou nao
tocar.

---

## 6. O QUE JA EXISTE E QUE NAO FOI REFEITO

O dono pediu "implantar o grafico operavel e arrastavel estilo XM Global" e
"mini terminal ao vivo estilo MT5". **Medido antes de prometer:**

| capacidade | medido em `PriceChart.tsx` (2.182 linhas) |
|---|---|
| desenhos | **140** referencias |
| arrastar | **50** |
| crosshair | 16 |
| zoom | 14 |
| pan | 7 |
| `moverPonto` / `podeMoverPontos` | 6 / 3 |
| `BarraFerramentas` | importada na 35, **renderizada na 1878** |
| timeframes | `M1 M5 M15 M30 H1 H4 D1` |
| indicadores | EMA, RSI de Wilder, MACD |
| desfazer / refazer | sim, com `aria-label` |
| ordem no clique do preco | sim — *"O clique arma: o envio e o botao do painel"* |
| linhas de SL e alvo | sim, com botao `Apagar stop` / `Apagar alvo` |

**Os botoes `+ − ✋ ⊞ ▤` que aparecem na captura de 14:16 SAO a barra de
ferramentas funcionando.** O grafico nunca aparecia porque nao havia dado
chegando. **Refazer o que existe seria o trabalho errado.**

O mini terminal tambem existe: conta, posicoes, "Fechar todas", journal com
`useJournal` a cada 10 s. O defeito era a coluna de tipo, e esta corrigido.

---

## 7. LIMPEZA — 11,76 GB → 18,94 GB

| | antes | depois |
|---|---|---|
| disco livre | **11,76 GB** | **18,94 GB** (**+7,18**) |

**Os instaladores foram salvos ANTES.** `release/` estava vazio, e o script
`limpeza_segura.ps1` com `-BuildArtifacts` inclui `Temp/cargo-target` — onde os
instaladores **unicamente** existiam. Sem copiar antes, o build de 08/10 00:10
era perdido. SHA-256 conferido entre origem e copia:

```
NSIS  E1552C2F36EA62A8 == E1552C2F36EA62A8   219,6 MB
MSI   694EB8A14A036E67 == 694EB8A14A036E67   339,6 MB
```

| o que | tamanho |
|---|---|
| `Temp\cargo-target` (cache Rust + instaladores) | 3,86 GB |
| Logs do MT5 de 06 e 07/10 (dias fechados) | 916 MB |
| `%TEMP%` do usuario, mais velho que 12 h | 1,62 GB |

O log de 06/10 foi medido antes: **zero** ocorrencias de `order`/`deal` nas
primeiras 4.000 linhas. E rotina (`AntiLoop`), nao dado de mercado.
`20261008.log` — o **ativo** — foi preservado.

**`frontend/dist` foi apagado.** Estava na allowlist e regenera com `npm run
build`, mas e o caminho de recuperacao do `AGENTS.md` §14 e a evidencia do CSS
empacotado. Os instaladores estao seguros; essa perda esta registrada aqui.

---

## 8. VALIDACAO

| | resultado | antes |
|---|---|---|
| `pytest -q tests` | **1283 passed, 1 skipped, 0 failed** | 1279 |
| `vitest run` | **773 passed, 55 arquivos** | 731 / 51 |
| `tsc --noEmit` | **exit 0** | limpo |
| `test_mql5_compila` | **2 passed** | 2 passed |
| `preflight --etapa app-rodando` | 13 `[ok]`, 1 aviso, **0 falhas** | — |

O aviso do preflight e "8 arquivos pendentes no git" — os deste ciclo.

### 8.1 As quatro provas negativas, todas medidas

| correcao | como se prova |
|---|---|
| `Temp/monitor_conta.py` | o codigo **antigo**, copiado ao pe, reproduz o traceback exato |
| `lib/journalKind.ts` | o classificador **antigo** discorda em **5 de 6** linhas reais |
| `_symbols()` | revertendo a guarda, **4 de 5** testes reprovam |
| `calendar.css` | reposto o `opacity` na linha, reprova |

---

## 9. O QUE ESTA ABERTO

1. **O gateway morre em silencio com o app vivo.** PID 3628 as 17:17 UTC,
    **ninguem** as 17:50. Sem WER, sem crash dump. Sem ele nao ha catalogo, nem
    candle, nem journal — e o grafico fica vazio.
2. **`[CIRCUIT] SPREAD EXPLOSION | USDSEK | Spread=1498.00 | Limit=500.00`** —
    o limite de spread em **pontos crus**. "500 pontos" vale $5,00 no BTCUSD e
    $0,005 no EURUSD. O USDSEK esta permanentemente bloqueado por causa da
    unidade, nao do spread.
3. **`MinFreeMargin = 20`** contra margem livre maxima de **$0,56**.
4. **`[BACKUP] FAIL | copiados=9 | falhas=98`** — 98 falhas de backup. Nao ha
    alarme para isso em lugar nenhum.
5. **SL e TP desiguais entre simbolos:** EURUSD abriu com razao ~1:17 e USDCNH
    com 1:2, do mesmo `StopLossPoints`.
6. **`[SAFETY] Free margin low` dispara a cada 2-3 s** em 6 simbolos — 63.837
    linhas. O log enche de repeticao que esconde o resto.
7. `/api/trade/pending`: tem `risk_gate`, mas nao grava `audit_log` nem
   `intent_log`.
8. `BacktestReport.csv` corrompido (14,9%) e acumulado entre 12 instancias.
9. Indicadores com busca — `rsi` -> 3 resultados.
10. **`EA: RUNNING · sem sinal ha 128.110s`** na faixa superior = **35,6 horas**
    sem sinal, com 2 posicoes abertas pelo EA nesse intervalo. Nao medi o que
    essa leitura conta.

---

## 10. ARQUIVOS DESTE CICLO

Trabalhei sozinho, mas o `AGENTS.md` §11 pede registro. **8 arquivos:**

```
MODIFICADOS
  backend/mt5_gateway.py                              +30   guarda de sessao em _symbols()
  frontend/src/components/UniversalLiveTerminal.tsx   ~18   usa classificarJournal
  frontend/src/theme/calendar.css                      ~70   esmaece conteudo, remove 3 duplicatas

NOVOS
  frontend/src/lib/journalKind.ts                            o classificador, com o vocabulario real
  frontend/src/lib/journalKind.test.ts                       19 casos, linhas literais do log
  frontend/src/components/UniversalLiveTerminal.journal.test.tsx   4 casos, caminho inteiro ate a tela
  frontend/src/theme/calendar_linha.test.ts                   9 casos, superficie x conteudo
  tests/test_catalogo_exige_sessao_mt5.py                    5 casos, com prova negativa

FORA DO REPOSITORIO (Temp/, ignorado)
  Temp/monitor_conta.py        corrigido: 4 defeitos, dois instantes, laco a prova de falha
  Temp/prova_monitor.py        12 verificacoes, com o codigo antigo reproduzido ao pe
  Temp/prova_catalogo.py       a prova 0 -> 1640
  Temp/cadeia_grafico.py, Temp/catalogo_frio_quente.py, Temp/produtor_catalogo.py   as medicoes
```

---

## 11. REGRAS QUE NAO SE DESCARTAM

- **Nenhum saque, transferencia ou movimentacao para fora da corretora.**
- **Toda escrita exige `confirm=true` e `request_id` idempotente.**
- **Nenhum simbolo nem corretora pode ser presumido** — e o monitor presumiu
  `EURUSD`, agora nao presume nenhum.
- **Onde dois lados do mesmo dado discordam do nome, o sintoma e recusa com o
  motivo errado.** Aconteceu **quatro vezes neste ciclo**, e as quatro tinham a
  mesma forma: `Failures`/`Error` (rotulo por valor), `cal-row`/`cal-row button`
  (superficie por conteudo), `symbols_get` com e sem sessao (mesma rota, duas
  versoes), `instante_utc` com hora de servidor (rotulo por fuso).
- **Toda correcao precisa de prova negativa.** Quatro, todas medidas.
- **Nao declarar "pronto" sem os numeros.** Nenhum numero deste documento veio
  de documento anterior: todos foram medidos neste ciclo.