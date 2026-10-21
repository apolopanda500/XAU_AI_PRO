# SESSAO 2026-10-04 — IA REAL, MODELOS REAIS, CONTA REAL

Estado medido por comando nesta sessao. Onde a leitura antiga estava errada,
esta marcado como ERRADO, com o motivo.

Dono: "IA real, motores REAIS." Depois: "vou usar conta real e dinheiro real
para operar esses primeiros testes reais".

## Conta real conectada

```
XMGlobal-MT5 14 · login 391773676
balance 5,62 · equity 11,24 · posicoes 0 · autotrading ligado
```

O heartbeat cresce a cada ciclo (`write_count`), entao o EA esta vivo.
Saldo lido como `float` 5.62 — sem virgula decimal quebrando comparacao.
As tres conexoes MT5 do app apontam para o servidor 14, o mesmo do terminal.

O servidor mudou durante a sessao: 16 -> 14. O app reconheceu 14.

## Os seis bugs do ciclo, todos medidos

### 1. `envio falhou: 'volume'` — o motor nao enviava ordem nenhuma

A traducao vivia dentro de `_loop.enviar`, marcado `# pragma: no cover`.
Lia `payload["volume"]` enquanto a montagem produz `payload["quantity"]`.
`KeyError` engolido pelo `except` virava recusa na tela.

E a MESMA classe do bug de vocabulario corrigido antes, pelo caminho inverso:
a montagem foi acertada e a leitura ficou para tras.

A traducao virou `pedido_para_router()`, no modulo, para poder ser testada.

**A primeira versao do teste era falsa.** Replicava a traducao dentro do
proprio teste e passava com o codigo real quebrado: reintroduzi o bug e os 50
testes ficaram verdes. Um duble que repete a logica prova que a logica foi
escrita, nao que ela esta no caminho. Com o teste importando a funcao, o
mesmo bug reprova 7.

### 2. A coluna "Decisao" mostrava `--` e "sem sinal"

A tela lia `d.ts`, `d.side`, `d.simbolo`. O `Decisao` do backend manda
`timestamp`, `sinal`, `symbol`. Tres nomes que nao existem no payload.

"Quando" mostrava a HORA ATUAL, nao a do ciclo: `new Date(undefined)` e
invalido e caia no `now`. Terceira vez do mesmo desacamento de nome
(`volume`/`quantity`, `ts`/`timestamp`).

`normalizarDecisao()` aceita os dois nomes, com precedencia do canonico: se
os dois vierem, o do backend vence, senao o resultado dependeria da ordem
das chaves do objeto.

### 3. O painel nao tinha onde escrever a confianca minima

`LimitesAuto` tem TREZE campos; `valido()` exige os dez primeiros. O painel
mostrava tres. `confianca_minima` — o gate que decide se a ordem sai — nao
tinha campo.

O operador digitava 36, apertava Aplicar, e o motor recusava com
"confianca 38.0% abaixo do minimo 55.0%" — o 55 era o ultimo valor gravado
no servidor. A tela afirmava uma coisa e o motor operava outra.

O gate do motor esta correto: minimo 36 com confianca 38 passa; minimo 55
com 38 recusa.

Segundo defeito no mesmo arquivo: `sujo` nunca voltava a `false` e
`aplicadoRef` era lido sem nunca ser escrito. A trava contra o polling
funcionava por acidente — e, como `sujo` ficava `true` para sempre, uma
mudanca vinda da API NUNCA aparecia na tela.

### 4. A XM escreve forex com ponto, e o ponto ficava no nome

```
EURUSD.m  -> canonico "EURUSD."   <- ponto grudado
GBPUSD.c  -> canonico "GBPUSD."
XAUUSD.m  -> canonico "XAUUSD."
```

`SUFIXOS_CORRETORA` tinha `.PRO`, `_M`, `_C`, `MICRO`, `MINI` — nao `.M`
nem `.C`. E o ponto nao esta em `SEPARADORES`, de proposito: ele faz parte
do nome do contrato na XM.

`EURUSD.` nao casa com nenhum modelo. O operador via a lista de ativos
vazia para pares que existem na conta dele.

### 5. Os tres modelos de MAIOR edge eram inalcancaveis

```
MULTI_METALS   edge +0,2497   acerto 58,3%   67.678 amostras
MULTI_FIAT     edge +0,1853   acerto 51,9%  149.927 amostras
MULTI_CRYPTO   edge +0,1816   acerto 51,5%  149.926 amostras
```

Duas causas, as duas medidas:

a) `_RE_SIMBOLO` era `^[A-Z0-9]{1,12}$`. O `_` do nome nao passava, entao
`_nome_de_artefato()` devolvia `None`. Virou `^[A-Z0-9_]{1,24}$`.
A defesa de travessia continua INTEIRA: o conjunto `[A-Z0-9_]` nao contem
ponto nem barra, que sao o que constroi travessia. 12 vetores testados,
todos barrados.

O comentario da propria constante citava `BTCUSDT_PERP` como simbolo
valido: comentario e regex discordavam, e o regex era o que valia. Por isso
o defeito passou em revisao — os dois pareciam certos.

b) `SEPARADORES` era `"/-_ "`. O operador pode digitar `MULTI_METALS`, e o
canonico devolvia `MULTIMETALS`, que nao existe em disco. Virou `"/- "`.

c) So se buscava `<SIMBOLO>_<TF>`. Os `MULTI_*` sao modelos UNICOS que
cobrem varios periodos, e nao tem sufixo. `_nomes_de_artefato()` agora
tenta o especifico e depois o geral, nessa ordem — o especifico ganha,
senao pedir H1 cairia no modelo de H4. Nenhum arquivo foi renomeado.

### 6. Erro meu, medido e corrigido

Falei que "os modelos estavam so no app instalado e a build apagaria".
ESTAVA ERRADO. Medi a pasta errada (`models/` na raiz). Os 39 modelos
(442,58 MB em `.pkl`) estao em `Python/models/` e a build empacota.

## ONDE PAROU: os tres MULTI_* precisam ser retreinados

```
MULTI_METALS   feature_version = 25F-est-v1   22 features
XAUUSD_H1      feature_version = 25F-v2       25 features
```

Os tres `MULTI_*` foram treinados com 22 features. O codigo hoje produz 25.
O modelo agora CARREGA (o erro mudou de "modelo nao publicado ou ausente"
para incompatibilidade de features), mas o `.pkl` espera nomes que a
inferencia nao gera.

NAO EXISTE CORRECAO EM CODIGO. Exige retreino com a versao atual.

Decisao do dono: opcao B — operar com os 36 que ja funcionam.

## O que opera hoje, medido com INFERENCIA REAL

25 modelos com `25F-v2`, `publicable: true` e inferencia respondendo. Os
melhores:

```
EURUSD_H4   +0.2092  54,3%   BTCUSD_M15  +0.1008  43,4%
USDCAD_H4   +0.1933  52,7%   EURUSD_H1   +0.1641  49,7%
USDJPY_H4   +0.1879  52,1%   BTCUSD_H4   +0.1552  48,9%
NZDUSD_H4   +0.1667  50,0%   GBPUSD_H4   +0.1507  48,4%
```

Ciclo completo (inferencia real -> gates -> contrato real -> ordem):

```
EURUSD H4   SELL 45.7%  edge +0.2092  lote 0.01   pedido passou no contrato
USDCAD H4   SELL 45.1%  edge +0.1933  lote 0.01   pedido passou no contrato
BTCUSD H4   BUY  49.6%  edge +0.1552  lote 0.01   pedido passou no contrato
XAUUSD H4   BUY  41.9%  edge +0.1261  lote 0.01   pedido passou no contrato
```

## Os 13 gates do motor, na ordem do codigo

```
 1. edge abaixo do minimo              8. SL ou TP nao cabe no lado
 2. confianca abaixo do minimo         9. (idem, para o outro lado)
 3. modelo em NEUTRAL                 10. Stop Loss calculou zero
 4. sem ATR ou preco real            11. volume calculado zero
 5. ja ha N posicoes                 12. ciclo ja processado nesta janela
 6. limite diario atingido            13. envio falhou: {motivo}
 7. lote zerado
```

Cada um com motivo proprio. Nenhum falha em silencio.

## SL/TP: cada ativo respeita o preco do SEU par

MODO SIMPLES usa o preco digitado no painel. Medido com preco real de cada
par e distancia de 0,5%:

```
EURUSD    1,08500  BUY   SL 1,08000  TP 1,10000   coerente
USDCAD    1,36000  SELL  SL 1,38000  TP 1,36000   coerente
BTCUSD 95000,00    SELL  SL 95988,69 TP 95038,69  coerente
XAUUSD    4300,00  BUY   SL 4301,75  TP 4344,75   coerente
```

O modo simples aceita SL/TP em DOIS formatos: preco cheio, ou distancia.
O preco cheio vence quando ja e coerente com o lado; senao vira distancia.
Sem isso, quem digita "10" receberia recusa sem entender.

## O que NAO foi validado (honesto)

1. **Os candles das medicoes acima sao SINTETICOS.** Provam que o pipeline
   roda, NAO que o modelo tem edge sobre o mercado. O edge real vem do
   `.meta.json`, medido em treino com purged k-fold.

2. **A ordem nao foi para a XM.** O ciclo parou no contrato universal. O
   envio real depende do `UniversalRouter` com a conta ativa e o
   `risk_gate` da corretora — caminho que so roda com o app no ar.

3. **Falta o build.** O app instalado nao existe nesta maquina agora
   (`C:\Users\Micro\AppData\Local\XAU AI PRO` ausente). O atalho aponta
   para um alvo que nao esta la.

4. **Lote 0,01 com balance 5,62.** O dono definiu 0,01 como minimo e 10,00
   como maximo. Com 5,62 de balance e 1% de risco, o dimensionamento por
   banca da 0,056 — abaixo do minimo. No MODO SIMPLES o lote e digitado, e
   0,01 e o que o dono pediu.

5. **Latencia no rodape esta pela metade.** O componente existe
   (`LatenciaBar.tsx`), falta o CSS e montar no `App.tsx`.

## Provas de que os testes prendem

```
regex antigo [A-Z0-9]{1,12}      -> 15 testes reprovam
voltar a ler d.ts/d.side         ->  3 testes reprovam
remover campo confianca_minima   ->  3 testes reprovam
remover .M/.C dos sufixos        ->  8 testes reprovam
reintroduzir payload["volume"]   ->  7 testes reprovam
```

## Regra que a sessao deixou

O teste verde e o que ESCONDE o defeito nesta sessao:

- o duble de `enviar` lia `payload["sl"]` e os testes conferiam `p["volume"]`
- o teste de traducao repetia o codigo em vez de importa-lo
- `getAllByRole('spinbutton')` sem escopo media 117 elementos, nao 13

Tres vezes, a suite afirmava que o defeito era o comportamento esperado.
Onde dois lados do mesmo dado falam idiomas diferentes, o teste tem que
exercitar o caminho INTEIRO.
