# CONVERSA — 08/10/2026, o monitor, o gráfico e o calendário, na ordem

> **Documento de trabalho. Sem data e sem hora de proposito: as regras valem para
> sempre, os numeros nao. Se um numero divergir do que o comando medir, o
> comando vence; corrija o numero.**

Este e o registro da conversa, pergunta por pergunta, com a decisao do dono e o
que cada resposta mudou. Companion de
[`PASSAGEM_20261008_MONITOR_GRAFICO_CALENDARIO.md`](./PASSAGEM_20261008_MONITOR_GRAFICO_CALENDARIO.md),
que tem os numeros e as provas; este tem a **ordem** e as **decisoes**.

---

## 0. DE ONDE A CONVERSA COMECOU

O dono entregou o resumo do ciclo anterior
(`CONVERSA_20261008_CICLO_BUILD_EA_ABRINDO.md`, commit `d19286d`) e fechou com
tres coisas que "precisam da sua atencao":

1. o build feito e nao instalado;
2. o EA abriu em EURUSD e USDCNH, simbolos que nunca operaram, com o app
   desligado;
3. margem livre negativa, e o EA com `MinFreeMargin = 20` contra `$13,52` que
   "deveria estar recusando por FREE_MARGIN e nao esta".

E a pergunta: *"Quer que eu instale o build e suba o app agora, ou prefere
observar as posicoes primeiro com o monitor rodando?"*

**Antes de responder, medi.** E tres das premessas do resumo nao batiam.

---

## 1. AS MEDICOES QUE CONTRADIZIRAM O RESUMO

### 1.1 "O monitor esta no ar"

```
Temp\monitor_err.log, escrito as 05:56:56 local (08:56:56 UTC):
  File "Temp\monitor_conta.py", line 41, in agora_utc
    return datetime.fromtimestamp(mt5.symbol_info_tick("EURUSD").time,
  AttributeError: 'NoneType' object has no attribute 'time'
```

**Morto ha ~8 horas.** A ultima leitura do `jsonl` era de 08:56:35 UTC.

### 1.2 O carimbo `instante_utc` estava 3 h adiantado

```
as 17:02:40 UTC o monitor imprimiu  20:02:42Z
```

`mt5.symbol_info_tick().time` e hora de **servidor** XM (GMT+3), e o campo se
chamava `instante_utc` com `Z`. **O bloco de comentario do arquivo afirmava
`TimeCurrent() do MT5 .. UTC` — medido: falso.** O evento `FECHOU 06:42:10Z`
aconteceu as **03:42:10 UTC**.

### 1.3 Margem livre e posicoes

| | resumo afirmava | `--once` as 17:02:40 UTC |
|---|---|---|
| margem livre | **−0,40** | **+0,19** |
| posicoes | **2** | **1** |
| balance / equity | 15,16 / 20,7 | **15,30 / 20,13** |

Em 1.035 leituras com posicao, margem livre variou de **−0,70 a +0,56**.
EURUSD **fechou as 03:42:10 UTC**.

### 1.4 O SL estava sendo apertado, e ninguem via

```
06:42:10Z  stop 6,7309  alvo 6,6409   sl_sobre_spread 6,57
11:56:35Z  stop 6,7132  alvo 6,6724   sl_sobre_spread 2,20
20:02:42Z  stop 6,7086  alvo 6,6942   sl_sobre_spread 0,62
```

Mesmo ticket, mesma entrada `6.7009`: **modificado no lugar**, nao reaberto.
O limiar do proprio monitor era 1,5x — e o monitor, que existia para avisar
desse limiar, morreu justo nessa janela.

### 1.5 O que a medicao NAO me deixou concluir

**Nao medi se quem moveu o SL foi o EA ou a mao do dono no MT5.** Fica escrito
como duvida, nao como achado.

---

## 2. AS PERGUNTAS AO DONO E O QUE CADA RESPOSTA MUDOU

### 2.1 "O monitor morreu e e a unica coisa olhando a conta. Conserto e religo?"

**"Consertar e religo (Recomendado)"**

Abri `Temp/monitor_conta.py` para corrigir e **encontrei mais tres defeitos
antes de mexer**:

- `ref = t.ask ...` estava **fora** da protecao de `t is None` — o mesmo simbolo
  ausente derrubava o monitor na posicao, e nao no relogio;
- **`abs(margem_livre) < 0` e sempre falso** — o alerta de margem negativa era
  **codigo inalcancivel**, e o documento afirmava que o monitor detectava
  margem negativa. Ele nao detectava;
- uma leitura com excecao **matava o laco**.

Corrigi os quatro, gravei `instante_utc` e `instante_servidor` em campos
separados com `desvio_servidor_h`, e acrescentei o evento **`SL/TP ALTERADO`** —
que e exatamente o que aconteceu com a USDCNH e que ninguem tinha registrado.

`Temp/prova_monitor.py`: 12 verificacoes. **A prova negativa reproduz o codigo
antigo ao pe** — a copia literal de `agora_utc`, que reproduz o traceback exato
de 08/10 08:56:56Z. Um stub que so "nao existe" provaria que a funcao sumiu, nao
que ela matava o monitor.

Religado: **PID 7652, a cada 20 s**, e avisando
`ALERTA USDCNH: SL a 0.7 x o spread`.

### 2.2 "USDCNH #246645615 esta com SL a 0,62x o spread. O que faco?"

**"Nao toca, so me avisa (Recomendado)"**

Nao mexi na posicao. **O monitor passou a ser o aviso.** E a mao na ordem continua
sua — decisao dele, e o que a plataforma permite: as tres vias do
`AGENTS.md` §1.

### 2.3 "E o build de 08/10 00:10, ainda nao instalado?"

**"validar tudo antes da build, e olhar imagens C:\Users\Micro\Pictures\Screenshots"**

---

## 3. AS IMAGENS — O QUE ELAS MOSTRARAM QUE O CODIGO NAO CONTAVA

### 3.1 As capturas de 14:14-14:16 do app instalado

O app **estava no ar** nesse momento — eu o tinha medido **parado** as 14:02. O
dono o subiu entre uma medicao e outra. **Por isso toda medicao de "o app esta
ligado" tem hora.**

Duas coisas nas capturas:

**O mini terminal mostrava `TIPO = ERROR` em sete checks cujo texto era `OK`:**

```
14:20:25  ERROR  GD ... AI: OK | Failures: 0 | Error:
14:20:25  ERROR  CI ... Indicators: OK | Failures: 0 | Error:
```

**E o grafico:**

```
Graficos indisponivel: Identidade de mercado invalida.
BTCUSD sem candles reais para M1.
0 candles
```

### 3.2 As pastas de imagens

O dono mandou ver **todas** as pastas. Sao quatro, alem da raiz:

```
Screenshots\               65 arquivos  (a raiz, inclui as de hoje)
Screenshots\MT5             5
Screenshots\RECORTES        2
Screenshots\XAU AI PRO APP 24
Screenshots\XM GLOBAL      25
```

A `XM GLOBAL` e a referencia do estilo pedido; a `MT5`, do mini terminal.

### 3.3 O que elas responderam: o grafico operavel JA EXISTE

**Medi antes de prometer construir.** `PriceChart.tsx`, 2.182 linhas:

```
desenhos .......... 140 referencias
arrastar .......... 50
crosshair ........ 16
zoom ............. 14
pan .............. 7
moverPonto ....... 6      podeMoverPontos ... 3
BarraFerramentas . importada na 35, RENDERIZADA na 1878
timeframes ....... M1 M5 M15 M30 H1 H4 D1
indicadores ...... EMA, RSI de Wilder, MACD
desfazer/refazer . sim, com aria-label
ordem no clique .. "O clique arma: o envio e o botao do painel"
SL e alvo ........ linhas com botao "Apagar stop" / "Apagar alvo"
```

**Os botoes `+ − ✋ ⊞ ▤` que aparecem na captura de 14:16 SAO a barra de
ferramentas funcionando.** O grafico nunca aparecia porque nao havia dado
chegando.

O mesmo vale para o mini terminal: existe, com conta, posicoes, "Fechar todas" e
journal a cada 10 s.

**Isso muda o trabalho.** Refazer o que existe seria refazer. O caminho e fazer
o dado chegar.

---

## 4. "Usar motores de forca total para implantar o grafico operavel e arrastavel estilo XM Global e mini terminal ao vivo estilo MT5"

Foi aqui que a raiz do grafico apareceu — e ela **nao** era do grafico.

### 4.1 O que o backend devolvia

```
_universal_assets("mt5", "")  -> status=unavailable  count=0
                                 error="catalogo de ativos ausente no upstream"
  ... nas CINCO chamadas seguidas, e em forex, metals, indices e other

mt5.symbols_get()             -> 1640
_universal_candles(...)       -> 500 candles, status=ok
```

**O terminal estava bom, e havia 500 candles.** O catalogo saia zero.

### 4.2 A causa

| rota | linhas | guarda de sessao |
|---|---|---|
| `_mt5_candles` | 2036 e 2087 | **tem** |
| **`_symbols`** (catalogo) | **1733** | **nao tinha** |

`_symbols` lia `symbols_get()` sem garantir a sessao. Sem sessao o MT5 devolve
`None`, sem lancar. **E o catalogo dependia da ORDEM das chamadas** — por isso o
seletor "aparecia sozinho" as vezes.

**Prova:** mesma rota, mesmos argumentos, **0** sem sessao e **1640** com.

Corrigi com a mesma guarda das linhas 2036/2087.
**Prova negativa: revertendo a guarda, 4 de 5 testes reprovam.**

### 4.3 E o que isso diz sobre o documento anterior

`PASSAGEM_20261007_02_BUILD_EA_DESCONECTADO.md` §7.1 mediu **1639 ativos** e
concluiu que o frontend nao tinha reserva. O numero **e** o que uma sessao
funcionando devolve. O que faltou registrar e que o catalogo **depende da
ordem** — o mesmo codigo dava 1639 num minuto e 0 no seguinte.

**O conserto do frontend de 07/10 22:44 (`75309ad`) estava certo** e continua
certo: ele removeu um defeito real. So nao podia resolver, sozinho, um produtor
que devolvia vazio.

### 4.4 O calendario

*"Calendario tem erro na luminacao do fundo, esta diferente do dia seguinte e o
dia atual."*

```
global.css:1112
  .calendar-tab button { background: var(--panel2) !important; }

calendar.css
  .cal-row.passado { opacity: 0.55; }
```

**A linha do evento e um `<button>`** (`EconomicCalendarTab.tsx:722`). A primeira
regra pinta a superficie com `!important`; a segunda desvanece o elemento
**inteiro**. No dia de hoje quase todo evento e passado → translucido, o papel
de parede atravessa. No dia seguinte nenhum e → opaco. **Mesma tabela, duas
iluminações, sem mudanca de dado.**

Corrigi esmaecendo o **conteudo**. E removi tres declaracoes duplicadas mortas
(`.cal-row.passado`, `.cal-row.alto`, `.cal-row.medio`): a segunda vencia, e quem
so lesse a ultima refazia o defeito.

**Prova negativa: reposito o `opacity` na linha, reprova.**

### 4.5 O mini terminal

Causa: o classificador casava a **PALAVRA**, e `Failures`/`Error:` sao **NOME
DE CAMPO** impressos em toda linha de saude — formato em
`RecoveryManager.mqh:621`.

E no sentido inverso, medido em **200.185 linhas**:

| tag | ocorrencias | o painel dizia |
|---|---|---|
| `[SAFETY]` | **63.837** | INFO |
| `[CIRCUIT]` | **29.574** | INFO |
| `[BACKUP]` `FAIL \| falhas=98` | 1.865 | INFO |
| `[CRITICAL] Execution: PASS` | 70 | **TRADES** |

**O operador via vermelho no saudavel e branco no que travava.** E o painel
mostra `slice(0, 14)` — **14 de 200.185**.

`frontend/src/lib/journalKind.ts`, com o vocabulario **real**, contado no log.
O veredito da linha vence a severidade nominal da etiqueta: `[CRITICAL]
Execution: PASS` e INFO, porque o check passou.

**No caminho, um defeito meu:** `erroDeclarado` devolvia `''` e `'' !== null` e
verdade — **toda linha voltava INFO**. Achado pelos testes antes de medir no
terminal.

**Prova negativa: o classificador antigo discorda em 5 de 6 linhas reais.**

---

## 5. "Veja as duas ultimas imagens do app atual instalado"

Duas capturas de 14:20. A segunda mostrou o **Terminal ao vivo** com a conta:

```
CONTA 391773676 · XMGlobal-MT5 14 · SALDO 15,30 · PATRIMONIO 20,25
FLUTUANTE -0,67 · MARGEM 20,00 · LIVRE 0,00 · NIVEL 101% · 1 POSICAO
#246645615 USDCNH SELL 0,01 6,70 -> 6,71  SL 6,71  TP 6,69  -0,67
```

E o journal, com `TIPO = ERROR` nas linhas `OK` que viraram o §4.5.

**Nivel de margem 101% e margem livre 0,00** com posicao aberta. `AUTO`
desligado, `Motor desligado`, `EA off` — e mesmo assim a posicao existe, com
`magic 2026001`. **Terceira confirmacao de que o EA opera fora do app.**

---

## 6. "Limpar Windows, arquivos temporarios e outros seguros regeneraveis, log etc."

### 6.1 O perigo que quase nao vi

`release/` estava **vazio**. O script `limpeza_segura.ps1` com `-BuildArtifacts`
inclui `Temp/cargo-target` na allowlist — e os instaladores **unicamente**
existiam ali. **Sem copiar antes, o build de 08/10 00:10 era perdido.**

Copiei para `release/1.2.4/` e conferi SHA-256 entre origem e copia: **iguais**.

### 6.2 O que foi removido

| | tamanho |
|---|---|
| `Temp\cargo-target` (cache Rust + instaladores) | 3,86 GB |
| Logs do MT5 de 06 e 07/10 (dias fechados) | 916 MB |
| `%TEMP%` do usuario, mais velho que 12 h | 1,62 GB |

**11,76 GB → 18,94 GB (+7,18).**

O log de 06/10 foi **medido antes**: zero ocorrencias de `order`/`deal` nas
primeiras 4.000 linhas. E rotina (`AntiLoop`), nao dado de mercado.
`20261008.log`, o **ativo**, foi preservado.

**`frontend/dist` foi apagado** — estava na allowlist e regenera, mas e o
caminho de recuperacao do `AGENTS.md` §14. Registrado como perda, nao escondido.

---

## 7. AS CORRECOES AO RESUMO QUE O DONO ENTREGOU

| | `CONVERSA_20261008` afirmava | **medido** |
|---|---|---|
| margem livre | **−0,40** | **+0,19** (min −0,70 · max +0,56) |
| posicoes | **2** | **1**; EURUSD fechou as 03:42:10 UTC |
| FREE_MARGIN | "deveria estar recusando **e nao esta**" | **esta recusando**: `[SAFETY] Free margin low: 0.23/20.00` em 6 simbolos |
| SL vs spread | "menor que 1,5x" | **0,7x**, caindo de 6,57 |
| monitor | "esta no ar" | **morto ha ~8 h** |

---

## 8. O QUE ACHEI E O DONO AINDA NAO SABE

**O app esta no ar SEM BACKEND.**

| | 17:17 UTC | 17:50 UTC |
|---|---|---|
| `XAU AI PRO` PID 2936 | vivo | **vivo** |
| `xau-ai-pro-core` PID 3164 | vivo | **vivo** |
| **porta 9001 / `mt5-gateway`** | **PID 3628** | **NINGUEM** |

Sem WER e sem crash dump — a mesma assinatura da morte anterior do app.
**Sem gateway nao ha catalogo, nem candle, nem journal.** E por isso que a tela
esta vazia, e por isso que as ferramentas MCP respondem `401`.

**E AGORA O DONO SABE, porque foi medido e escrito aqui.**

---

## 9. O QUE O DONO AUTORIZOU, E O QUE SAIU

| pergunta | resposta |
|---|---|
| monitor: consertar e religar? | **sim** |
| USDCNH com SL a 0,62x: o que faco? | **nao toca, so me avisa** |
| build: instala e sobe? | **validar tudo antes da build, e olhar as imagens** |
| grafico e mini terminal: "motores de forca total" | **o grafico ja existe; o caminho e fazer o dado chegar** |
| limpeza de disco | **sim** |
| salvar documentos e conversas | **sim** |
| iniciar build completa | **sim** |

**Nao commitei nada antes da decisao do dono.** Os 8 arquivos ficaram na arvore
ate ele dizer "proximo".

---

## 10. REGRAS QUE NAO SE DESCARTAM

- **Nenhum saque, transferencia ou movimentacao para fora da corretora.**
- **Toda escrita exige `confirm=true` e `request_id` idempotente.**
- **Nenhum simbolo nem corretora pode ser presumido.** O monitor presumiu
  `EURUSD` e morreu por isso.
- **Onde dois lados do mesmo dado discordam do nome, o sintoma e recusa com o
  motivo errado.** Aconteceu **quatro vezes neste ciclo**, todas com a mesma
  forma: `Failures`/`Error` (rotulo por valor), `cal-row`/`cal-row button`
  (superficie por conteudo), `symbols_get` com e sem sessao (mesma rota, duas
  versoes), `instante_utc` com hora de servidor (rotulo por fuso).
- **Toda correcao precisa de prova negativa.** Quatro, todas medidas.
- **Nao declarar "pronto" sem os numeros.** Todo numero aqui foi medido neste
  ciclo; nenhum veio de documento anterior.