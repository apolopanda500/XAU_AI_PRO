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

## 2. A RECONCILIAÇÃO DO SALDO — ABERTA, E EU NÃO SEI

**Esta é a questão mais importante em aberto. Não tenho resposta, e não vou
inventar uma.**

MEDIDO em `history_deals_get` e `account_info()`, conta 391773676:

| | valor |
|---|---|
| `balance` | **3,94** (era 2,78 às 00:30, 3,43 às 22:56, 4,88 na XM às 14:14) |
| `credit` | 5,62 (bônus NewClients) |
| `equity` | 8,40 |
| deals em 30 dias | 13 |
| **soma dos 13 deals** | **+9,05** |
| **diferença** | **−5,11** |

### 2.1 O saldo mexeu com o app DESLIGADO

| quando | ticket | lucro |
|---|---|---|
| 07/10 00:36 | 261109609 | entrada, 0,00 |
| 07/10 01:12 | 261118356 | **−1,45** `[sl 85393.55]` |

O saldo subiu 2,78 → 3,94 **apesar** de −1,45. **Entrou dinheiro** — não foi
operação.

E o negócio maior: **o MT5 estava em EPI** (tester de estratégia) na captura de
00:42, e o app em `AUTO NÃO` / `Motor desligado` / `EA off`. **Operação acontece
com o app desligado** — é o EA do MT5, que roda fora do app (AGENTS.md §7).

### 2.2 O rodapé do MT5 diz `Retirada: 0,00`

```
Lucro: -2,84  Crédito: 5,62  Recarregar: 5,62  Retirada: 0,00  Saldo: 8,40
```

**Atenção:** isso é o rodapé do MT5. O MT5 pode não ver o que a XM fez.

### 2.3 Hipóteses, nenhuma confirmada

1. A XM reteve margem/depósito em aberto que não aparece como deal.
2. `history_deals_get` da sessão devolve menos que a conta real.
3. Saldo e histórico vêm de sessões diferentes.

Testei a hipótese óbvia — "o bônus é crédito, não saldo": `9,05 − 5,62 = 3,43`,
e o saldo é 3,94. **Não bate.** Faltam 5,11 sem deal que os explique.

### 2.4 A PERGUNTA QUE DECIDE

**No painel da XM, o saldo está em $3,94 ou em outro número?**

- XM = 3,94 → o MT5 está certo, o histórico está incompleto, é bug de leitura.
- XM = 9,05 → o MT5 erra o saldo e o app mostra ao operador número que a
  corretora não confirma.
- outro → reconcilio com o número.

**Correção de uma afirmação minha:** eu disse antes que "não houve saque" com
base no rodapé do MT5. Esse rodapé não é a corretora. Não posso afirmar isso.

---

## 3. O QUE FALTA, NESTA ORDEM

1. **Responder §2.4.** Tudo o resto da conta depende disso.
2. **GOLD / XAUUSD.** Os modelos existem — 36 `.meta.json`, incluindo
   `XAUUSD_H1/H4/M15/M5` e `MULTI_METALS`. **Falta confirmar que o catálogo da
   XM publica `XAUUSD`** e não só `GOLD`: se publicar só `GOLD`, a ficha não
   vem, `mercadoDoAtivo` devolve `null`, e o gráfico fica vazio **pela regra que
   acabei de escrever**.
3. **Build novo** com §1.6 e §1.7.
4. **Conferir na tela**: gráfico com candles, SL e TP lado a lado, requisito de
   margem, pontas arrastáveis, paleta, `Ctrl + Z`.
5. **Indicadores com busca** — `rsi` → 3 resultados, como a XM. Hoje são três
   botões fixos.

### 3.1 O RISCO QUE NÃO É MEU

**A conta opera com o app desligado.** Perdeu 1,45 às 01:12 sem ninguém tocar
em nada. Com 1000:1 e stop de 200 pontos (0,23%), três stops com a mesma
configuração comem 15% do saldo. Isso é exatamente o que o AGENTS.md §4 exige
antes de conta real: forward test (rodou, 4 operações, Lucro −0,74) e endurance
test. **A amostra foi pequena demais e a conta estava real.**

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