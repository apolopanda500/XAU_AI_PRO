# ORDEM PELO GRÁFICO — desenho medido nas capturas da XM (06/10/2026)

Sem data e sem hora de propósito: as regras valem para sempre, os números não.
**Se um número aqui divergir do que o comando medir, o comando vence.**

## A REFERÊNCIA

Duas capturas da XM (`my.xm.com/pt/symbol-info/BTCUSD`), conta Real 11,47.
Elas respondem o que era decisão e não eu medi.

### O que o clique faz

`Ordem com 1 clique` **desligado** na captura. O clique **ARMA** a ordem; não
envia. O envio é o botão `Colocar ordem a 85.510.25`, à direita.

Então: clique arma → painel mostra tudo → operador confirma → envia.

### As TRÊS linhas

Medido nas duas capturas. São três, e não uma:

| linha | captura | preço | rótulo | cor |
|---|---|---|---|---|
| stop | 141239 | 85.694,50 | `0,01 \| −2,00 USD \| ×` | laranja |
| entrada/posição | 141239 | 85.513,85 | `−0,01 \| −0,37 USD \| ×` | vermelha |
| alvo | 141239 | 85.305,49 | `0,01 \| +2,00 USD \| ×` | azul |
| stop | 141407 | 85.663,29 | `0,01 \| −1,50 USD \| ×` | laranja |
| posição | 141407 | 85.513,85 | `−0,01 \| −0,37 USD \| ×` | vermelha |
| alvo | 141407 | 85.361,80 | `0,01 \| +1,52 USD \| ×` | verde |

Cada linha tem **`×` para apagar** e **arrastar**. O volume aparece na própria
linha (`0,01`, `−0,01` na posição).

### Stop e alvo em DINHEIRO

`−2,00 USD` e `+2,00 USD` na primeira captura; `−1,50 USD` e `+1,52 USD` na
segunda. O operador escreve **quanto aceita perder**, não um preço — e o preço
da linha é derivado. É o modo `Quantidade` do `OperacaoAutomatica`, com a linha
arrastável para ajuste fino.

O sinal NEGATIVO do stop e do alvo da posição aberta é o da posição, não do
papel: uma posição vendida mostra `−0,01`.

### O que o painel mostra

`Quantidade 0.01 lotes` · `Requisito de margem $0.85` · barra de margem em 8,01%
· `Vender quando preço atingir` · `TP/SL` · `Colocar ordem a 85.510.25`.

### A barra de cima

`15m · Indicadores · layout · ⊞ · ↶ · ↷` — o item 5 já está feito, e o botão
de tipo de gráfico é o `↶ ↷` de desfazer/refazer mais o quadrado de layout.

## O QUE ENTRA NO APP, E EM QUAL ORDEM

1. **`PriceChart` em modo de ordem.** `modoOrdem` liga a leitura do clique
   (`coordinateToPrice`, que o componente já usa para arrastar SL/TP) e desenha
   as três linhas com rótulo de dinheiro e `×`.
2. **Arrastar e apagar** as três linhas. O `onMoveLine` já existe para as
   linhas de posição; falta o mesmo para stop e alvo da ordem armada.
3. **Painel de confirmação** com preço clicado, quantidade, stop e alvo em
   dinheiro, e o botão `Colocar ordem a <preço>`.
4. **`/api/trade/order`** com `confirm: true` e `request_id` — sem mudá-la. A
   rota já existe e já é usada; o que mudou foi que ela passou a ser chamada a
   partir do clique, e não de um botão de 1-clique (que saiu a pedido do dono).

## OS 4 PASSOS: FEITOS E MEDIDOS

| passo | onde | teste | estado |
|---|---|---|---|
| 1. `PriceChart` em modo de ordem | `charts/PriceChart.tsx` — `modoOrdem`, `ordem`, `onArmarOrdem` | `PriceChart.ordem.test.tsx` 21 | feito |
| 2. Arrastar e apagar as três linhas | mesmo arquivo — efeito das linhas, `overlayOrdemRef` | mesmo arquivo, 21 | feito |
| 3. Painel de confirmação | `AcompanharModelos.tsx` — `robo-ordem-painel` | `AcompanharModelos.ordem.test.tsx` 18 | feito |
| 4. `/api/trade/order` com `confirm` | mesmo arquivo — `enviarOrdem` | mesmo arquivo, 18 | feito |

Medido: `npx tsc --noEmit` sem erro; `npx vitest run` **626 passaram, 44 arquivos**
(587 antes, +39 novos); `pytest -q tests` **1213 passaram, 1 skipped** (o skip é o
bundle ainda não construído, pré-existente); `npm run build` **✓ built in 1.42s**.

### O QUE A LEITURA DO CODIGO MUDOU NESTE CICLO

Duas coisas medidas na leitura que o doc não previa, e que mudam o desenho:

**O `x` NÃO EXISTE no lightweight-charts.** O `title` da `createPriceLine` é
texto desenhado no canvas e não recebe clique — `IPriceLine` só tem
`applyOptions`, `options` e `remove` (tyings 4.2.3). Um `×` desenhado como
`title` seria o botão que parece funcionar e não funciona. Ele é um `<button>`
de verdade, numa camada sobre o canvas, posicionado por
`series.priceToCoordinate(preco)`.

**O GATEWAY EXIGE `sl > 0` E `tp > 0`.** Medido em `mt5_gateway.py:2190`:
`symbol`, `side`, `0 < volume <= 0.10`, `sl > 0`, `tp > 0`. Então o `×` não é
só visual: sem stop ou sem alvo **a ordem não vai**, e o motivo do gateway é
`"symbol, side, volume <= 0.10, sl e tp validos sao obrigatorios"` — que não diz
qual dos cinco faltou. Por isso o painel recusa **antes**, nomeando o campo.

### A ARMADILHA QUE QUASE PASSOU

`getAssets` devolve `MarketAsset`, que **não tem** `contract_size`
(`marketApi.ts:37`). `parseAssetCatalog` lê o campo do payload **cru**
(`brokerCatalog.ts:128`). Passar a resposta normalizada ao parser dava
`contractSize: null` **sem erro nenhum**: a tela dizia "depende do contrato"
para um ativo que a corretora já tinha publicado, e o painel ficava travado sem
o operador ter feito nada de errado.

Corrigido usando `useCatalogoAtivos` — o mesmo hook que `OperacaoAutomatica` e
`SeletorModelo` leem. É a regra do AGENTS.md 5 pelo outro lado: o sintoma
cairia em quem **escreveu** a tela, e a culpa seria da corretora.

### O QUE FICOU FORA, E POR QUE

- **"Requisito de margem $0,85" e a barra de margem em 8,01%.** São números que
  a corretora calcula (alavancagem, spread, taxa da exchange) e que o app não tem
  de onde ler. Escrever um valor estimado ali é o "número inventado no painel
  vira limite real" que o AGENTS.md proíbe.
- **"Vender quando preço atingir"** (ordem pendente). A rota existe
  (`/api/trade/pending`) com as mesmas travas, mas é um quinto passo e não foi
  pedido agora.

## REGRAS QUE NÃO SE DESCARTAM

- **Toda escrita exige `confirm` e `request_id` idempotente** (AGENTS.md 4). O
  clique arma; só o botão envia.
- **Símbolo vazio é recusa com motivo**, nunca um ativo padrão (AGENTS.md 3).
- **`contract_size` vem da ficha da corretora.** Sem ele o dinheiro não vira
  preço — e o nível sai errado em forex.
- **Stop zero é ausência**, não preço. `null`, e a linha fica vazia.

## O QUE FOI REMOVIDO NESTE CICLO, E POR QUÊ

- **"Comprar 1-clique" e "Vender 1-clique"** (`AcompanharModelos.tsx`). O dono
  pediu, e o motivo não é o preço: era o único caminho que mandava ordem com
  LOTE/SL/TP do motor sem o operador escolher o preço. O clique no gráfico
  substitui, com o preço escolhido no gráfico e o SL/TP em dinheiro.
- **Checkbox "EMA 12/26"**, que duplicava o botão `EMA` do topo do gráfico. Era
  o controle decorativo que o dono reportou como "travado de cima azul".
- **`pronto1Clique`**, que ficou sem consumidor depois da remoção dos botões.
  Um cálculo que nada lê é pior que não existir (AGENTS.md 9).

## O QUE AINDA NÃO ESTÁ NO APP INSTALADO

O build do frontend está feito (`npm run build`, ✓ 1.42s), mas o **app instalado
é um build anterior** e não tem nada disto: nem o clique que arma, nem as três
linhas, nem o `×`, nem o painel. Quem for testar precisa de **build e
reinstalação** — testar o binário antigo mostra defeitos que já estão corrigidos
no código.

## REGRAS QUE NÃO SE DESCARTAM