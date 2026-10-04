# EA passa a chamar o BACKEND por WebRequest (05/10/2026)

## O QUE ESTAVA QUEBRADO

O `AIConnector.mqh` lia `Data\prediction_<SIMBOLO>.json`. Medido nesta maquina:
essa pasta **NAO EXISTE**. O backend tem 25 modelos publicados e responde por
HTTP, mas ninguem escreve o arquivo — entao o EA vivia **sem sinal nenhum**, e
sem erro visivel, porque "arquivo ausente" e um caminho previsto do codigo.

Confirmado no heartbeat: `autotrading: true`, `write_count` crescendo, e o EA
operando sem IA. Ligado eemnudo.

## O QUE FOI FEITO

`Core/Config.mqh` — cinco inputs:

```
input bool   AIUseGateway       = true;
input string AIGatewayUrl       = "http://127.0.0.1:9001/api/ai/predict";
input string AIGatewayToken     = "";
input int    AIPollSeconds      = 15;
input int    AIRequestTimeoutMs = 5000;
```

`AI/AIConnector.mqh` — quatro funções:

| Função | Para que |
|---|---|
| `PeriodLabel()` | traduz o enum do MT5 (`16385`) para o nome do modelo (`H1`) |
| `FetchPredictionFromGateway()` | a chamada HTTP, com limite de taxa de 15 s |
| `ParsePredictionJSON()` | UM parser para gateway E arquivo |
| `LoadAIPrediction()` | tenta o gateway; cai para o arquivo |

## AS TRES DECISOES QUE IMPORTAM

### 1. UM parser, duas fontes
O corpo de parsing foi extraido para `ParsePredictionJSON()` e as DUAS fontes o
usam. Se cada uma tivesse o seu, a divergencia apareceria como "o gateway
funciona, o arquivo nao" — sem nenhuma pista do porque. E a terceira vez que o
mesmo nome significa coisas diferentes neste projeto (`volume`/`quantity`,
`ts`/`timestamp`, e agora `symbol`/`esperado`).

### 2. FALHA DO GATEWAY NUNCA VIRA SINAL INVENTADO
`FetchPredictionFromGateway` devolve `false` quando o HTTP falha ou quando o
corpo tem menos de 10 caracteres. Um `WebRequest` que devolvesse 200 com corpo
vazio faria o EA receber `signal=""` e `AIBuyAllowed` devolveria `false` — por
sorte, e nao por desenho.

### 3. LIMITE DE TAXA
`AIBuyAllowed` e chamado a cada tick, e a inferencia real carrega o `.pkl` e
monta 25 features. Sem o cache de 15 s, o gateway receberia centenas de
requisicoes por segundo. Previsao com 15 s e melhor do que perder tick perto
de um nivel — que e quando o tick importa.

## PROVA

`tests/test_mql5_compila.py` reprovou com **6 erros** na primeira compilacao:

```
AIConnector.mqh(261,13) : error 256: undeclared identifier 'symbol'
AIConnector.mqh(277,13) : error 256: undeclared identifier 'symbol'
AIConnector.mqh(292,33) : error 256: undeclared identifier 'symbol'
```

Causa: o corpo do parser veio da `LoadAIPrediction`, onde as variaveis eram
`symbol` (nome do broker) e `normalized` (nome do modelo); extraido para uma
funcao com parametro `esperado`, os dois nomes sumiram. Este e exatamente o
defeito que o teste existe para pegar: um `.mq5` quebrado passa o CI inteiro,
porque a suite Python roda contra o fonte e `mq5` nao e modulo.

Depois da correcao: **MetaEditor64, 0 erros**.

## O QUE FALTA PARA LIGAR (medido)

1. **Autorizar o WebRequest no MT5** — Ferramentas > Opcoes > Expert Advisors >
   "Allow WebRequest for listed URL", com `http://127.0.0.1:9001`. Sem isso o
   MT5 devolve **-401** e o log mostra "AI GATEWAY | URL nao autorizada".

2. **O gateway tem que estar rodando.** Medido agora: porta 9001 **sem
   resposta** e nenhum processo `mt5-gateway`. O app instalado nao existe nesta
   maquina. Sem o gateway, o `WebRequest` cai no fallback de arquivo — que tambem
   nao existe.

3. **Compilar e reanexar o EA no grafico.** Compilar NAO reanexa: o `.ex5` novo
   so entra em vigor quando o EA e trocado no grafico. Este e o passo que
   destrava o proximo.

4. **Colar o token** no input `AIGatewayToken` (64 caracteres do `.env`).
