# PASSAGEM — recuperação de corrupção e gráfico (06/10/2026)

Documento de trabalho para qualquer agente que pegar este projeto.
Sem data e sem hora de propósito: as regras valem para sempre, os números não.
**Se um número aqui divergir do que o comando medir, o comando vence; corrija o número.**

Estado medido no fim desta sessão: **`pytest` 1264 verdes**, **`vitest` 706
verdes (48 arquivos)**, **`tsc --noEmit` limpo**, **`npm run build` ✓ 1,53s**,
**`preflight --etapa app-rodando` todo `[ok]`**.

**Tudo isto está commitado** — `48754ed`, 157 arquivos, 28.473 linhas. Antes
desta sessão, **178 arquivos estavam pendentes e nada do gráfico estava no git**
— ver §1.

---

## 1. O ACIDENTE, E O QUE FOI PERDIDO

Três arquivos do repositório estavam **zerados** quando esta sessão começou.
Não é símbolo de diff sujo: são bytes `0x00` do começo ao fim.

| arquivo | tamanho | conteúdo real | como foi recuperado |
|---|---|---|---|
| `.git/index` | 105.608 | **100% zero** | `git read-tree HEAD` |
| `.git/refs/stash` | 41 | 41 espaços | **não recuperável** |
| `frontend/src/components/charts/PriceChart.tsx` | 19.157 | **100% zero** | **source map do `dist`** |

### 1.1 Como o `PriceChart.tsx` voltou

O `.tsx` zerado tinha **exatamente o mesmo tamanho** da versão em `HEAD`
(19.157 bytes) — por isso o `git diff` dizia `Bin 19157 -> 19157 bytes`, e o
arquivo parecia "só um arquivo binário modificado".

A versão boa estava em **três** lugares, e todos measured:

| fonte | tamanho | tem `modoOrdem`? | tem os desenhos? |
|---|---|---|---|
| `HEAD` (`540b5b4`) | 19.157 | **não** | não |
| checkpoint cline `47f7554` (14:50) | 54.403 | sim (8) | 2 |
| **`.map` do `dist` de 20:47** | **70.001** | sim (8) | **24** |

O `.map` do build era o mais novo e o mais completo. Restaurado:
**71.968 bytes**, 1.794 linhas, `modoOrdem`, `overlayOrdem`, `desenhos`,
`BarraFerramentas`, `GraficoIndicador`.

### 1.2 O que o `.git/index` zerado significava

`git status`, `git diff` e `git log` falhavam com `bad signature 0x00000000`.
O índice foi reconstruído com `git read-tree HEAD` — isso **descartou o stage**
de 178 arquivos, que já era inútil (o índice não lia).

O `refs/stash` tinha 41 bytes de espaço num arquivo que deveria ter 40 hex +
quebra de linha. O stash **foi perdido**. Backup em
`%TEMP%\opencode\stash_ref_quebrado.bak`.

### 1.3 O QUE FICOU SEM CÓPIA

A `BarraFerramentas.tsx` (21:40) e a `PriceChart.desenhos.test.tsx` (21:40) são
**mais novos** que o build de 20:47 que recuperei. A barra ganhou **10 props**
que a versão restaurada não passa:

`selecionado` · `estiloSelecionado` · `podeDesfazer` · `podeRefazer` ·
`aoDesfazer` · `aoRefazer` · `aoMudarCor` · `aoMudarEspessura` ·
`aoMudarOpacidade` · `aoAlternarTrava`

**Perdi a ligação, não o código.** `desenhos.ts` tinha todas as funções prontas
(`pontasVisiveis`, `pontaMaisProxima`, `moverPonto`, `podeMoverPontos`,
`estiloDe`, `normalizarOpacidade`, `normalizarEspessura`) e a barra tinha
todos os botões. Só o `PriceChart` que os conectava não existia mais. Isso
foi reimplementado nesta sessão e está medido em §2.

**19 testes** descreviam exatamente essa ligação e reprovavam. Eles são a
especificação; foram eles que disseram o que reconstruir.

---

## 2. O GRÁFICO — O QUE FOI FEITO E MEDIDO

### 2.1 Os 19 testes que reprovavam, agora verdes

`PriceChart.desenhos.test.tsx` — 20 testes, **19 falhas → 0**.

| grupo | o que mede |
|---|---|
| linha visível com ferramenta desarmada | a linha não some ao fechar |
| pontas arrastáveis | 2 na tendência, 1 na horizontal; arraste move a linha |
| `PROVA` | o preço da ponta é o do **arraste**, não pixel guardado |
| `PROVA NEGATIVA` | arrastar no vazio não move linha nenhuma |
| estilo | paleta, espessura 4 px, opacidade 40% — **na linha, não no botão** |
| `PROVA NEGATIVA` | a cor de um desenho **não vaza** para o próximo |
| trava | esconde as pontas; arrastar **não** move linha travada |
| desfazer/refazer | desfaz criação **e** arraste; `Ctrl + Z` |

### 2.2 O defeito de fundo que os testes nomeiam

> *"A camada dos desenhos renderizava só com `ferramenta !== 'nenhuma'`, e o
> `aoClicar` desarma a ferramenta ao **fechar** o desenho. Ou seja: a linha que
> o operador acabava de clicar aparecia por um frame e **SUMIA** — enquanto o
> contador continuava dizendo '1 desenho'."*

Isso é o AGENTS.md §5 na forma mais cruel: **o nome e a realidade discordando**.
O contador dizia 1, a tela estava vazia, e o operador culparia o próprio clique.

### 2.3 A armadilha do `modoOrdem`

Removi o `return` antecipado de `!modoOrdem` que existia antes — ele impedia o
gráfico de **escolher** um desenho e de **arrastar** uma ponta fora do modo de
ordem. Mas sem ele o `onArmarOrdem` passou a ser chamado sempre, e o teste
`PROVA NEGATIVA: sem modoOrdem o clique nao arma nada` reprovou.

**A correção está no último passo**, não no começo do efeito: o clique primeiro
escolhe desenho, e só o que sobra disso vira ordem. `PriceChart.tsx:1474`.

### 2.4 O `Ctrl + Z` na raiz, não no canvas

O primeiro teste falhou porque o `keydown` estava no canvas. Mas o operador
**não clica no canvas para desfazer**: ele clica numa linha, e o foco sobe para
o elemento do evento. Ouvir só no canvas faria o atalho depender de onde o
clique caiu. Agora é na raiz (`raizRef`), que é o que `closest('.price-chart')`
acha — e é o que o teste mede.

---

## 3. "O HISTÓRICO DEMORA CARREGAR" — MEDIDO, NÃO ADIVINHADO

O dono pediu duas coisas. As duas foram **medidas antes de corrigir**.

### 3.1 O MT5 não era o gargalo

MEDIDO nesta máquina, conta 391773676 (XM, Hedge), terminal aberto:

| chamada | tempo | retorno |
|---|---|---|
| `history_deals_get` 1 dia | **0,1 ms** | 5 deals |
| `history_deals_get` 30 dias | **0,1 ms** | 10 deals |
| `history_deals_get` 90 dias | **0,1 ms** | 10 deals |
| `history_deals_get` 3650 dias | **0,1 ms** | 10 deals |
| `copy_rates` BTCUSD H1 300 | **4,5 ms** | 300 barras |
| `copy_rates` BTCUSD M15 300 | **16,6 ms** | 300 barras |
| `copy_rates` BTCUSD M5 300 | **79,6 ms** | 300 barras |
| `symbols_get` | **22,4 ms** | 1639 símbolos |

**Dez anos respondem no mesmo tempo que um dia.** Nenhum destes números explica
"demora". A causa estava no cliente.

### 3.2 A demora era a tela mentindo — corrigido

`historico.ts` tinha `if (busyRef.current) return` no começo de `carregar`.
Uma requisição em andamento **cancelava a próxima em silêncio**.

O caminho real: digitar `BTCUSD` são **seis** eventos de teclado. O primeiro
dispara a busca; as cinco seguintes eram **descartadas**. O campo mostrava
`BTCUSD`, a tabela mostrava os deals do filtro **anterior**, e o `status` dizia
carregado. Sem erro, sem pendência.

O operador que vê isso digita de novo, esperando que a segunda vez funcione — e
ela funciona, porque a primeira terminou. Ele conclui que a tela é lenta, e
**fica esperando**.

Substituído por um **token de requisição** (`tokenRef`), que faz duas coisas:

1. **`emVoo`** — espera em vez de descartar;
2. **`meuToken !== tokenRef.current`** — uma resposta atrasada **não
   sobrescreve** a tela com o dado de um filtro que o operador já trocou.

Prova: `historicoCarga.test.ts`, 4 testes. O `fetch` só resolve **quando o teste
manda** — com um `fetch` instantâneo o `busyRef` nunca ficaria ocupado e o
descarte nunca aconteceria, e o teste passaria por um motivo errado.

### 3.3 "Não pode depender do MT5 ligado" — agora DITO

Com o `terminal64` fechado, `history_deals_get` volta vazio — e `deals: []` é
**o mesmo payload** de uma conta sem operação. A tela mostrava "Nenhum
registro no período": uma tela de **sucesso** com zero linhas. O operador ia
procurar erro na conta. Não havia erro: havia um programa não aberto.

Corrigido dos dois lados:

- **Produtor** (`mt5_gateway.py:860`): a rota de `mt5` agora declara
  `connected=bool(_mt5_connected())`.
- **Consumidor** (`historico.ts`): `desconectado` no estado, e o `status` diz
  **o que fazer** — "MT5 sem sessão: abra o MetaTrader 5 e faça login".
- **Tela** (`HistoryTab.tsx:590`): três mensagens distintas para três situações
  que produzem a mesma tabela vazia.

`ok` continua `true` com o terminal fechado, **de propósito**: a leitura foi
feita e o resultado foi vazio. `ok: false` faria a tela mostrar erro de rede
para um terminal fechado — trocar uma mensagem errada por outra.

Trva Python: `tests/test_historico_conectado.py`, 5 testes, incluindo a
**prova negativa** de que "desconectado" e "conta vazia" são respostas
**diferentes** — se fossem iguais, o campo seria decorativo.

---

## 4. A COMPARAÇÃO — XM vs MT5 vs XAU AI PRO

Medido nas 48 capturas de `C:\Users\Micro\Pictures\Screenshots\`
(4 subpastas: `XM GLOBAL`, `MT5`, `XAU AI PRO APP`, `RECORTES`).

### 4.1 A conta

| campo | valor | onde |
|---|---|---|
| conta | XAU AI PRO #391773676 · XMGlobal-MT5 14 · **Hedge** | XM, MT5 |
| Capital | $10,50 | XM `Gerir` |
| **Saldo** | **$4,88** → **$3,43** (medido agora) | XM, MT5 |
| Margem / Livre | $0,00 / $10,50 | XM |
| Crédito | $5,62 | XM |
| **Alavancagem** | **1000:1** | XM |

O saldo caiu de 4,88 para 3,43 entre as capturas de 14:14 e as de 20:28. **Não
sei por quê** — não medi. O `telemetry_history.jsonl` mostra `balance: 3.43`
constantemente desde 22:56.

### 4.2 O risco que a conta impõe

Com `0,01 BTCUSD` a 85.523 o nocional é **$855**. A 1000:1 a margem exigida é
`855 / 1000 = $0,855` — exatamente o *"Requisito de margem $0.85"* que a XM
mostra. Confere.

- Oscilação adversa de **0,57%** consome toda a margem.
- O stop 1:1 a 200 pontos é **0,23%** — menos de metade do caminho.
- Saldo livre **$3,43** é menor que o nocional em **249×**.

### 4.3 Tabela de diferenças

| item | XM | MT5 | XAU AI PRO | estado |
|---|---|---|---|---|
| clique arma ordem | desligado | — | **clique arma** | feito |
| SL/TP em dinheiro | `2,00 USD` | — | idem `nivelDoValor` | feito |
| linha com `×` para apagar | sim | — | sim | feito |
| arraste das 3 linhas | sim | — | sim | feito |
| **pontas arrastáveis** | 2 círculos | — | **feito nesta sessão** | feito |
| **paleta 8×10** | sim | — | **feito nesta sessão** | feito |
| **espessura 1–4 px** | sim | — | **feito nesta sessão** | feito |
| **travar desenho** | 🔒 | — | **feito nesta sessão** | feito |
| **Ctrl+Z desfazer** | sim | — | **feito nesta sessão** | feito |
| **requisito de margem** | `$0.85` | — | **feito nesta sessão** | feito |
| barra de margem | `8,01%` | — | **ausente** (assim decidedo) | falta |
| indicadores com busca | `rsi`→3, `ema`→6 | — | botões fixos EMA/RSI/MACD | parcial |
| pincel, texto, formas | sim | — | **ausente** | falta |
| biblioteca com busca | sim | — | **ausente** | falta |
| histórico | deal + saldo | deal | deal + saldo, separado | feito |
| **"Nenhum registro" vs MT5 fechado** | — | — | **diz qual é** | feito nesta sessão |

### 4.4 O REQUISITO DE MARGEM — a correção de um erro anterior

O `Docs/ORDEM_PELO_GRAFICO_20261006.md` recusou este número, e o **motivo** estava
certo: *"é um número que a corretora calcula e que o app não tem de onde ler —
escrever um valor estimado ali seria o 'número inventado no painel vira limite
real' que o AGENTS.md proíbe."*

A **conclusão** estava errada. **A corretora publica.** MEDIDO nos dois lados:

| onde | o que diz |
|---|---|
| painel `Gerir` da XM | `Alavancagem 1000:1` |
| `account_info().leverage` | `1000` |

E a conta confere, que é o que autoriza a tela a escrever:

```
contract_size BTCUSD = 1,0                    (MEDIDO em symbol_info)
alavancagem          = 1000:1
entrada              = 85.376,63
nocional   = 0,01 × 1,0 × 85.376,63 = 853,7663
requisito = 853,7663 ÷ 1000       = 0,8537663   → a XM escreve "$0.85"
```

Corrigido dos dois lados: `leverage` no payload de `/api/live`
(`mt5_gateway.py:1550`) e o cálculo no painel (`requisitoDeMargem`).

**Por que `contract_size` é obrigatório junto.** MEDIDO: BTCUSD tem contrato
`1`, EURUSD tem `100.000`, GOLD tem `100`. O mesmo `0,01` a 85.376,63 vale
`853,77` no BTCUSD e `85.376.630` no EURUSD. Com um palpite de `1`, o número
estaria **certo por coincidência no BTCUSD** — e o operador, que conferiu ali,
não conferiria no forex.

**A barra de margem (`8,01%`) continua fora, e é decisão.** Ela é
`requisito ÷ margem livre`, e a margem livre muda a cada tique. Um percentual
guardado no painel é um número que muda sozinho sem ninguém ler. Quem tem a
margem livre em tempo real é a Carteira.

Testes: `requisitoMargem.test.ts` (7), `test_alavancagem_no_payload.py` (5),
`AcompanharModelos.ordem.test.tsx` (+4).

### 4.5 O que ainda falta, em ordem

1. **Busca de indicadores** — `rsi` → 3 resultados, como a XM. Hoje são três
   botões fixos: EMA, RSI, MACD.
2. **Pincel, texto, formas geométricas** — a XM tem, com `Ctrl+Z`.
3. **Barra de margem** — só depois de decidir de onde vem a margem livre.

---

## 5. O QUE O PRÓXIMO AGENTE DEVE FAZER

### 5.1 Commitar — FEITO

Commit `48754ed`, 157 arquivos. Era a primeira tarefa: **178 arquivos estavam
fora do git**, e foi exatamente por isso que o `.tsx` zerado levou o trabalho
junto. `PriceChart.tsx`, `BarraFerramentas.tsx`, `desenhos.ts`,
`ordemGrafico.ts`, `AcompanharModelos.tsx` e mais 100 arquivos estavam **não
rastreados**.

Também: 28 arquivos de raspagem na raiz (`.py` e `.bat` de uma tarefa só, sem
consumidor) foram **ignorados** no `.gitignore`, com o motivo escrito lá. **Não
foram apagados** — apagar é decisão do dono.

### 5.2 O que fazer agora

1. `pytest -q tests` e `npx vitest run` — baseline **1264** e **706**.
2. **Instalar e testar no app de verdade.** O código está verde; o binário
   instalado ainda é o anterior.
3. Busca de indicadores — `rsi` → 3 resultados, como a XM.

### 5.3 O QUE NÃO DEIXAR PARA O PRÓXIMO

- **Não ligar execução real** sem forward test + endurance test. O AGENTS.md §4
  exige, nesta ordem. Com 1000:1 e $3,43 de saldo livre, o stop padrão está a
  0,23% e a margem é chamada a 0,57%.
- **`REAL_EMERGENCY_STOP` não existe** e o `.env` **não tem nenhuma flag
  `XAU_ENABLE_*`**. O default de `XAU_ENABLE_TRADE_COMMANDS` é `"1"`
  (`mt5_gateway.py:2175`), então **execução está liberada sem flag nenhuma**.
- **O `.ex5` do KCI é de 15/08 e o commit dos `.mqh` é de 25/08.** Falta
  confirmar que o binário bate com o fonte.
- **A divergência de edge na linha H4** (`16,6%` na tela vs `0.1552` em três
  cópias do `.meta.json`) **não foi reproduzida** e **não afirmo que a tela
  esteja certa**. Precisa de conferência dentro do app.

---

## 6. COMO MEDIR

```powershell
cd <repo>
.\.venv\Scripts\python.exe -m pytest -q tests -p no:cacheprovider   # 1264
cd frontend
npx tsc --noEmit                                                    # limpo
npx vitest run                                                      # 706, 48 arquivos
npm run build                                                       # ✓ 1,53s
cd ..; cmd /c "scripts\build_app.bat"
```

**NÃO** usar `scripts\limpeza_segura.ps1 -BuildArtifacts` antes de instalar:
apaga `Temp\cargo-target`, onde está o instalador recém-gerado.

Instalar: fechar o app, rodar
`Temp\cargo-target\release\bundle\nsis\XAU AI PRO_1.2.4_x64-setup.exe /S`.

**Não mexer no `terminal64`** — é onde o EA protege posição, e ele roda fora
deste app.

---

## 7. ARMADILHA QUE QUASE PASSOU

**Um arquivo zerado com o MESMO tamanho do original.**

`git diff` dizia `Bin 19157 -> 19157 bytes`, que parece um `.tsx` tratado como
binário — não um arquivo destruído. Se eu tivesse lido aquilo como "arquivo
binário modificado" e seguido, teria restaurado a versão de `HEAD` e **perdido
as 24 horas de trabalho** de uma vez, porque `HEAD` não tem `modoOrdem`.

**Como se descobre:** ler os bytes. `$b[0..($b.Length-1)] | Where-Object {$_ -eq 0}`.
Zero no primeiro bloco é arquivo destruído, não arquivo especial.

**A mesma armadilha do git:** `bad signature 0x00000000` não é "repositório
estragado", é o índice zerado. `git read-tree HEAD` resolve. O `refs/stash`
com 41 espaços é **outro** arquivo zerado, e esse não tem reconstrução.

---

## 8. REGRAS QUE NÃO SE DESCARTAM

- **Nenhum saque, transferência, resgate ou movimentação para fora da
  corretora.** `withdrawals_enabled` e `transfers` permanecem `False` fixos.
  Trava: `tests/test_movimentacoes.py::TestNadaDeDinheiroForaDaCorretora`.
- **Toda escrita exige `confirm=true` e `request_id` idempotente.** O clique
  arma; só o botão envia.
- **Nenhum símbolo nem corretora pode ser presumido.** A classe vem da
  hierarquia que a corretora publica (`asset_class`), nunca de palavra no nome.
- **Medir antes de dizer que está consertado.** "O histórico está consertado"
  era verdade no código e falso no app instalado — o binário era de um build
  anterior. O mesmo vale para o edge H4.
- **Nunca `xfail` onde existe compilador e código.** Onde há erro, tem de
  reprovar.
- **Um controle que nada lê é pior que a ausência dele.** Ao remover um
  controle, meça o uso e registre no código o que foi removido e por quê.