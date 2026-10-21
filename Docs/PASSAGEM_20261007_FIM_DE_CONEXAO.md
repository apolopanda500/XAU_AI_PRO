# PASSAGEM — 07/10/2026, da recuperação à reconciliação do saldo

Documento de trabalho para qualquer agente que pegar este projeto.
Sem data e sem hora de propósito: as regras valem para sempre, os números não.
**Se um número aqui divergir do que o comando medir, o comando vence; corrija o número.**

Estado medido no fim desta sessão: **`pytest` 1264 verdes** · **`vitest` 720
verdes (50 arquivos)** · **`tsc --noEmit` limpo**. Commits `48754ed`, `96a684e`,
`c578f10` + o de fechamento desta rodada.

**O instalador instalado é ANTERIOR a duas correções** (gráfico e CSS). Testar
agora mostra o gráfico vazio. Ver §3.

---

## 1. O QUE FOI FEITO E MEDIDO

### 1.1 Recuperação de corrupção

Três arquivos **zerados** (bytes `0x00` do começo ao fim) quando a sessão
começou:

| arquivo | tamanho | como voltou |
|---|---|---|
| `.git/index` | 105.608 | `git read-tree HEAD` |
| `.git/refs/stash` | 41 (espaços) | **não recuperável** |
| `frontend/src/components/charts/PriceChart.tsx` | 19.157 | **source map do `dist`** |

O `.tsx` tinha **o mesmo tamanho** da versão em `HEAD` — por isso o `git diff`
dizia `Bin 19157 -> 19157 bytes`. A versão boa estava no `.map` do build de
20:47 (71.001 bytes). Detalhes em `PASSAGEM_20261006_RECUPERACAO.md` §1 e
`AGENTS.md` §14.

**Perdido:** a ligação entre `BarraFerramentas.tsx` (10 props) e `PriceChart`.
`desenhos.ts` tinha todas as funções; só o `PriceChart` sumiu. Os **19 testes**
que descreviam essa ligação foram a especificação, e estão verdes.

### 1.2 Gráfico — os 19 testes, e a ligação refeita

`PriceChart.desenhos.test.tsx`: **19 falhas → 0**.

Pontas arrastáveis · seleção · paleta por desenho · espessura 1–4 px ·
opacidade · trava (com guarda no `mousedown`, não só no desenho do círculo) ·
desfazer/refazer por **lista** e não delta · `Ctrl + Z` na raiz.

**Armadilha:** removi o `return` antecipado de `!modoOrdem` e o
`onArmarOrdem` passou a chamar sempre — `PROVA NEGATIVA: sem modoOrdem o
clique nao arma nada` reprovou. O guarda ficou no **último passo**
(`PriceChart.tsx:1474`).

### 1.3 Histórico — "demora carregar"

MEDIDO antes de corrigir, porque o sintoma apontava para a rede:

| chamada | tempo |
|---|---|
| `history_deals_get` 1 dia / 30 / 90 / 3650 | **0,1 ms** (os quatro) |
| `copy_rates` BTCUSD H1 300 | 4,5 ms |
| `copy_rates` BTCUSD M5 300 | 79,6 ms |

Dez anos respondem no mesmo tempo que um dia. **O MT5 não era o gargalo.**

A demora era a tela mentindo: `if (busyRef.current) return` **descartava** a
requisição quando o filtro mudava durante um carregamento. Digitar `BTCUSD` são
seis eventos de teclado; cinco buscas foram jogadas fora. O campo mostrava o
símbolo novo, a tabela os deals do filtro **anterior**, e o status dizia
carregado.

Trocado por **token de requisição**: `emVoo` espera em vez de descartar, e
`meuToken !== tokenRef.current` impede que a resposta atrasada sobrescreva a
tela com o dado de um filtro já trocado. Testes: `historicoCarga.test.ts` (4).

### 1.4 Histórico — "não pode depender do MT5 ligado"

Com o `terminal64` fechado, `history_deals_get` volta vazio — e `deals: []` é
**o mesmo payload** de uma conta sem operação. A tela mostrava "Nenhum registro
no período": uma tela de **sucesso** com zero linhas.

- `mt5_gateway.py`: a rota de `mt5` declara `connected=bool(_mt5_connected())`.
- `historico.ts`: `desconectado` no estado; o status diz **o que fazer**.
- `HistoryTab.tsx`: três mensagens distintas para três causas que produzem a
  mesma tabela vazia.

`ok` continua `true` com o terminal fechado: a leitura foi feita e o resultado
foi vazio. `ok: false` mostraria erro de rede para um terminal fechado.

### 1.5 Requisito de margem — a correção de um erro anterior

O ciclo **anterior** recusou este número. O motivo estava certo (não se escreve
estimativa num painel onde o número vira limite) e a conclusão errada: escreveu
que a alavancagem "é um número que o app não tem de onde ler".

**A corretora publica.** MEDIDO nos dois lados:

```
painel `Gerir` da XM      "Alavancagem  1000:1"
account_info().leverage   1000
```

E a conta confere:

```
contract_size BTCUSD = 1,0
nocional   = 0,01 × 1,0 × 85.376,63 = 853,7663
requisito = 853,7663 ÷ 1000 = 0,8537663   →  a XM escreve "$0.85"
```

`contract_size` é obrigatório junto: BTCUSD tem `1`, EURUSD `100.000`, GOLD
`100`. Com palpite de `1`, o número estaria **certo por coincidência no
BTCUSD** — e o operador, que conferiu ali, não conferiria no forex.

**A barra de margem (8,01%) continua fora, por decisão:** é `requisito ÷ margem
livre`, e a margem livre muda a cada tique.

### 1.6 Gráfico vazio — a regressão que o build novo mostrou

MEDIDO no app instalado, 00:33:

```
Gráfico indisponível: Identidade de mercado inválida.
BTCUSD sem candles reais para .
```

O `para .` com ponto final é o **timeframe vazio** chegando no `PriceChart`, e
o rodapé dizia `BTCUSD · — ·`.

**A causa:** `AcompanharModelos` lia **só** `auto.market` e `auto.timeframe`. O
motor começa sem par e só recebe quando alguém liga o automático — então, com
`Motor desligado`, os dois vinham vazios. `getCandles` recebia `market: ''`, e
`normalizeMarketSource` devolvia `null` (o throw de `marketApi.ts:1368`).

**Correção:** mercado derivado da **ficha** (`mercadoDoAtivo`), e período com
reserva na lista do próprio `PriceChart`.

`marketSalvo` **não** entra na cadeia: `escopoAtivo()` devolve `mt5:forex` sem
chave gravada — um **default**, não uma medida. Usá-lo faria o gateway responder
vazio para cripto, e o sintoma seria "a corretora não devolve candles".

Testes: `AcompanharModelos.grafico.test.tsx` (7), incluindo **BTCUSD vs EURUSD
vs XAUUSD** no mesmo teste — os três terminam em `USD` e só a classe separa.

### 1.7 Campo SL espremido — era CSS, e o CSS mentia o motivo

MEDIDO às 00:37 e no recorte de 00:40: `Stop Loss` com ~10px, rótulo empilhado
em **coluna de um caractere**.

**A causa era do grid, não do componente:** a coluna era `minmax(0, 1.35fr)`. O
`min(0)` permite a coluna chegar a **zero**, e o grid serve primeiro as colunas
`auto` — que têm conteúdo intrínseco. A proteção era a única com mínimo zero, e
foi a que colapsou.

E o lado de dentro era `1fr 1fr`: `1fr` num grid tem mínimo automático igual ao
**conteúdo**, e o conteúdo do `<span>` não quebra.

Corrigido para `minmax(280px, 1.35fr)` na coluna e `minmax(0, 1fr)` nos lados.

**`jsdom` não calcula largura.** Um teste que medisse `offsetWidth` mediria `0`
— verde com o defeito na tela. O teste trava a **regra**, com a prova negativa
que mostra a regra antiga reprovando: `test_robo_ticket_css.test.ts` (7).

### 1.8 Instalador novo — feito, medido, e depois ficou defasado

| passo | medido |
|---|---|
| `scripts\build_app.bat` | exit 0, 7/7 |
| frontend | ✓ 815ms |
| core Rust | 4m 10s |
| `XAU AI PRO.exe` | 13.827.072 bytes |
| NSIS | 230.238.951 bytes |
| MSI | 356.061.488 bytes |
| desinstalar o antigo | pasta e registro removidos |
| instalar o novo | registro de volta: `XAU AI PRO 1.2.4` |
| rodar pelo atalho | PID 2348, core 6368, gateway `mt5-gateway.exe` PID 9348 |
| portas | 9001 · 9002 · 9003 |
| `preflight` | todo `[ok]`, pendentes 0 |

**O estado do usuário sobreviveu** — o NSIS não toca `%APPDATA%\XAU_AI_PRO`.

**Este instalador NÃO contém §1.6 e §1.7.** Precisa de build novo.

---

## 2. A RECONCILIAÇÃO DO SALDO — FECHADA, E EU TINHA ERRADO

**A conta fecha no centavo.** E a "diferença" que eu reportei às 00:30 era um
erro meu de método, não dinheiro faltando.

MEDIDO no mesmo instante, conta 391773676 (`Henrique Carvalho`, XMGlobal-MT5 14):

```
soma dos 19 deals   = +9,56
balance             =  3,94
credit              =  5,62     (bônus NewClients)
balance + credit    =  9,56     ← BATE
equity              =  9,56     ← e o equity é exatamente a soma
```

**Não faltava dinheiro. Faltavam DEALS** — entre a minha medição das 00:30 e a
de agora, entraram **6 operações novas**, e o saldo andou junto.

### 2.1 O ERRO, e a regra que ele é

Eu comparei **uma soma de deals das 00:30 com um saldo lido às 01:xx**. A conta
está **ativa e operando com o app desligado** — entre as duas leituras entraram
6 operações. Produtor e consumidor em instantes diferentes, e o número "não
bate".

É o **AGENTS.md §5 aplicado a mim mesmo**, e a forma mais humilhante: eu relatei
"faltam $5,11 sem deal que os explique" com três hipóteses — saque, margem
retida, sessão diferente — e **nenhuma era a resposta**. A resposta era a mais
boba: a conta mudou enquanto eu media.

**A reconciliação só fecha lida no mesmo instante.** E, para conta que opera,
isso significa: **`equity` é a conferência**, porque ele atualiza junto com o
saldo.

### 2.2 OS 19 DEALS, INTEIROS

| quando | tipo | posição | lucro | o que é |
|---|---|---|---|---|
| 04/10 18:53 | MOV | — | +5,52 | `CD-AST-PIC 265376085` — depósito |
| 04/10 18:53 | MOV | — | +0,10 | `EXP05-AST-PIC 265376085` — taxa |
| 04/10 18:53 | MOV | — | +5,62 | `Credit-In-100%-$100-NewClients` — bônus |
| 04/10 22:46→23:12 | OP | 245033922 | +2,01 | `[tp 86584.30]` |
| 06/10 16:13→16:34 | OP | 245994269 | **−1,41** | `[sl 85615.69]` |
| 06/10 17:12→17:28 | OP | 246012074 | **−1,53** | `[sl 85664.55]` |
| 06/10 22:53→23:09 | OP | 246056881 | +0,19 | |
| 07/10 00:36→01:12 | OP | 246071435 | **−1,45** | `[sl 85393.55]` |
| 07/10 02:37→03:02 | OP | 246103515 | **−1,55** | `[sl 83987.84]` |
| 07/10 03:10→03:13 | OP | 246111060 | +0,90 | **volume 0,05** |
| 07/10 03:46→04:17 | OP | 246119090 | +1,16 | `[tp 84113.70]` |

Movimentações com valor **negativo**: **nenhuma**. `Retirada: 0,00` no MT5 e
ausência de deal negativo são o **mesmo fato visto por dois lados**.

Resultado de operação: **+0,62** em 8 posições. As 4 perdas somam **−5,94**.

### 2.3 O STRATEGY TESTER NÃO TOCOU NESTA CONTA

MEDIDO: o MT5 rodou `XAU_AI_PRO.ex5` em **GOLD, M5** por **4h26min33s**,
15.020.685 ticks no GOLD (55.768.587 em todos os símbolos), 12.665 barras.

**MetaTester tem base própria.** Um deal de EPI **não** entra em
`history_deals_get` da conta logada. Os 19 deals acima são **todos** da conta
real 391773676.

### 2.4 O BACKTEST, E O QUE ELE DIZ

| | medido |
|---|---|
| operações | **923** (491 wins · 417 losses) |
| WinRate | **53,20%** |
| **Profit** | **−334,01** |
| **Profit Factor** | **0,48** |
| MaxDD | 340,79 (log: 7.623,94 %) |
| **Sharpe** | **−9,31** |
| Perfil | Conservative · Lot 0,01 · **SL=80 · TP=160** |
| Módulos | 15, todos `OK` |

**53,20% de acerto com Profit Factor 0,48 é a assinatura de stop curto com alvo
longo** — exatamente o perfil `SL=80 · TP=160`, que é 1:2. Acerta mais da metade
e ainda perde.

**E o binário medido é de 23/09**, de uma pasta `estadoA_8445b74` **fora do
repositório**:

```
tester: Experts\estadoA_8445b74\XAU_AI_PRO\XAU_AI_PRO.ex5   23/09/2026 22:03
repo:   MQL5\Experts\XAU_AI_PRO\XAU_AI_PRO.ex5              07/10/2026 01:08
```

**Se o objetivo era medir o código de hoje, mediu o de setembro.**

O log também acusa: `[NOTIFY] SendNotification falhou | Erro=4014` e
`Sent=0 | Failed=14394`. **14.394 notificações falhadas** — quem acreditava estar
avisado não estava sendo avisado.

### 2.5 A OPERAÇÃO REAL CONTINUA COM O APP DESLIGADO

As 4 perdas são da **conta real**, com o app em `AUTO NÃO` / `Motor desligado` /
`EA off`. É o EA do MT5, que roda fora do app (AGENTS.md §7).

| | |
|---|---|
| perdas | −1,41 · −1,53 · −1,45 · −1,55 |
| padrão | **todas `[sl ...]`, todas ~$1,50** |
| stop | ~200 pontos = **0,23%** do preço |
| volume 0,05 | uma operação, 5× as outras |

Isto é o AGENTS.md §4: forward test rodou (4 operações, Lucro −0,74) e endurance
rodou (923 operações, PF 0,48) — **e os dois medidos em código antigo**.

---

## 3. O QUE FALTA, NESTA ORDEM

1. **Build novo** com §1.6, §1.7 e §3.1.
2. **Conferir na tela**: gráfico com candles, **o ouro pelo nome `GOLD`**,
   SL e TP lado a lado, requisito de margem, pontas arrastáveis, paleta,
   `Ctrl + Z`.
3. **Indicadores com busca** — `rsi` → 3 resultados, como a XM. Hoje são três
   botões fixos.

### 3.1 O OURO: `GOLD` NA CORRETORA, `XAUUSD` NO MODELO — CORRIGIDO

MEDIDO na conta 391773676, com `discover_assets`:

| | existe | `path` |
|---|---|---|
| **`GOLD`** | **sim** | `Derivatives\Spot Metals\GOLD` · `contract_size = 100` |
| `XAUUSD` | **NÃO** | `symbol_info("XAUUSD")` → `None` |
| `XAUJPY` · `XAUEUR` · `XAUCNH` | sim | `Derivatives\Spot Metals` |
| `BTCUSD` | sim | `Cryptocurrencies\Standard` |

1.639 linhas de catálogo, **zero** `XAUUSD`. E os artefatos do app são
`XAUUSD_H1/H4/M15/M5`.

**O alias já existia** — `%APPDATA%\XAU_AI_PRO\symbol_aliases.json` tem
`{"mt5": {"XAUUSD": "GOLD"}}`, e o módulo `backend/symbol_aliases.py` o aplica
em **candles, cotação, ordem e inferência**. O que não existia era o sentido
**na tela**.

**A costura, e o AGENTS.md 5 de novo:**

```
fichaDoAtivo(catalogo, 'XAUUSD')  →  null     (o catálogo só tem 'GOLD')
mercadoDoAtivo(null)              →  null
configurado                       →  false    →  gráfico não carrega
```

E a ficha ausente leva **três decisões** junto: `assetClass` (mercado),
`contract_size` (dinheiro vira preço) e `volume_min/max/step` (faixa). O painel
dizia *"depende do contrato"* para um ativo que a corretora já publicara.

**Corrigido nos dois lados:**

- **Produtor** (`asset_registry.py`): cada linha ganha `model_symbol` e
  `has_model`, calculados por `para_modelo` — o mapa do operador, nunca um nome
  no código (AGENTS.md §3).
- **Consumidor** (`volumeUnidade.ts`): `fichaDoAtivo` busca por `symbol` e, se
  não achar, por `modelSymbol`. **A ordem importa:** com `modelSymbol` primeiro,
  um ativo receberia a ficha de outro, e em forex isso é 100.000× o preço.

**`null` continua sendo `null`.** Se `modelSymbol` ausente caísse no próprio
`symbol`, os 1.639 pares do catálogo declariam ter modelo — e existem 36
`.meta.json`.

Testes: `test_nome_do_modelo_no_catalogo.py` (7, Python),
`fichaPorNomeDoModelo.test.ts` (10, frontend).

### 3.2 UMA TRAVA QUE PROÍBIA DOCUMENTAR

O teste *"o mapa é config e o código não tem nome"* varria o arquivo inteiro e
**reprovou no texto que documenta a medição**. É o AGENTS.md §4e: trava textual
que proíbe documentar é o defeito, não a proteção.

Corrigido com `_sem_docstrings_e_comentarios`, que usa `tokenize` — um `#`
dentro de string (URL, caminho) não é comentário, e um regex apagaria a linha
inteira junto com o código dela.

**A regra escrita no AGENTS.md §3 foi mantida; o que mudou foi o teste.**

### 3.1 NÃO RODAR BACKTEST AGORA

**Decisão do dono (07/10): não rodar backtest, validar antes do build.**

E o motivo está medido: o último mediu um `.ex5` de **23/09**, de fora do
repositório. Rodar de novo agora mediria o mesmo binário velho, por 4h30 — e o
resultado não diria nada sobre o código de hoje.

Para um backtest que valha alguma coisa, o `.ex5` tem de ser recompilado do
fonte atual no MetaEditor (§7 do AGENTS.md), e **anexado ao gráfico** — e o
`.mq5` atual roda em **GOLD,M5**, não em BTCUSD.

### 3.2 O RISCO QUE NÃO É MEU, E ESTÁ ATIVO

**A conta real opera com o app desligado.** 4 perdas, todas `[sl ...]`, todas
~1,50, com o perfil de stop de 200 pontos (0,23% do preço).

**E os dois testes que o AGENTS.md §4 exige já rodaram, ambos em código de
setembro:** forward (4 operações, Lucro −0,74) e endurance (923 operações,
PF 0,48, Sharpe −9,31). **Nenhum mediu o binário de hoje.**

---

## 4. COMO MEDIR

```powershell
cd <repo>
.\.venv\Scripts\python.exe -m pytest -q tests -p no:cacheprovider   # 1264
cd frontend
npx tsc --noEmit                                                    # limpo
npx vitest run                                                      # 720, 50 arquivos
npm run build
cd ..; cmd /c "scripts\build_app.bat"
```

**NÃO** usar `scripts\limpeza_segura.ps1 -BuildArtifacts` antes de instalar: apaga
`Temp\cargo-target`, onde está o instalador.

**O token do gateway é só de sessão.** De fora, `/api/*` devolve **401** — é
fail-closed correto (AGENTS.md §4), não defeito. Para medir o gateway de fora,
usar `MetaTrader5` direto, que foi como a tabela de latência saiu.

**Não mexer no `terminal64`** — é onde o EA protege posição, e ele roda fora do
app.

---

## 5. ARMADILHAS DESTA RODADA

**Arquivo zerado com o mesmo tamanho do original.** `git diff` chama de
"binário modificado". Leia os bytes antes de decidir.

**Um `minmax(0, …)` num grid é a mesma armadilha do `min-width: 0` num flex** —
mas mais silenciosa: o grid serve primeiro as colunas `auto`, então a coluna
com mínimo zero é a única que colapsa, e ninguém sabe por quê.

**`jsdom` não mede layout.** `offsetWidth` é `0` para tudo. Teste de CSS mede a
**regra**, com a prova negativa da regra antiga.

**Default não é medida.** `escopoAtivo()` devolve `mt5:forex` sem chave
gravada. Usar como mercado de consulta é a presunção que o AGENTS.md §3 proíbe.

**O rodapé do MT5 não é a corretora.** `Retirada: 0,00` prova que o MT5 não
registrou saque — não prova que não houve.

---

## 6. REGRAS QUE NÃO SE DESCARTAM

- **Nenhum saque, transferência, resgate ou movimentação para fora da
  corretora.** Trava: `tests/test_movimentacoes.py::TestNadaDeDinheiroForaDaCorretora`.
- **Toda escrita exige `confirm=true` e `request_id` idempotente.** O clique
  arma; só o botão envia.
- **Nenhum símbolo nem corretora pode ser presumido.** A classe vem da
  hierarquia que a corretora publica (`asset_class`), nunca de palavra no nome.
- **Medir antes de dizer que está consertado.** "O histórico está consertado"
  era verdade no código e falso no app instalado — o binário era de um build
  anterior. ** Aconteceu de novo nesta rodada, com o gráfico.**
- **Nunca `xfail` onde existe compilador e código.**
- **Um controle que nada lê é pior que a ausência dele.**
- **Não declarar "pronto" sem os números.**