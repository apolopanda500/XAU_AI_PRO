# 05/10/2026 — A IA CHEGOU AO MT5, E O OURO VOLTOU A FUNCIONAR

Dois bugs medidos nesta sessao, ambos da mesma familia: os dois lados falando
nomes diferentes.

## 1. O HEADER ERRADO NO EA

O gateway so aceita `Authorization: Bearer` (`fastapi_gateway.py:103`:
`auth != f"Bearer {API_TOKEN}"`). Eu enviei `X-Gateway-Token` — que produz
"token invalido" com HTTP 401 **mesmo com o token correto**. Quarta vez que
dois lados discordam do nome do mesmo campo.

## 2. O OURO NAO INFERIA — E A FALHA ERA SEGURA

Pergunta do dono: *"o EA esta operando GOLD porque XAUUSD era conta DEMO hoje e
REAL"*.

Medido na conta 391773676 (XMGlobal-MT5 14, 1639 simbolos):

```
XAUUSD  existe na XM?   NAO
GOLD    existe na XM?   SIM
SILVER  existe na XM?   SIM
```

O modelo foi treinado como `XAUUSD`; a XM chama o ouro de `GOLD`. Sem traduzir,
a rota pedia `XAUUSD` ao MT5 e recebia `no_candles_for_symbol`.

**A FALHA ERA SEGURA:** a rota recusava com motivo e nenhuma ordem de ouro era
enviada. O perigo era o MOTIVO ERRADO — o operador culparia a corretora ou o
modelo, e nenhum dos dois estava quebrado.

O mecanismo ja existia: `symbol_aliases.json` tem `{"mt5": {"XAUUSD": "GOLD"}}`,
e `para_corretora()` traduz. O caminho de ORDEM usava; o de LEITURA nao.

### A DIRECAO — e eu errei a primeira vez

Usei `para_modelo()`, que faz o caminho INVERSO (`GOLD` -> `XAUUSD`), e
continuei pedindo `XAUUSD` ao MT5. `para_modelo` e o que o caminho de ordem
usa quando recebe o nome da corretora de volta — nao o que a leitura de candles
precisa. Depois de corrigir:

```
XAUUSD H4 -> available: true  signal: BUY  confidence: 49.9%
            edge: +0.1261       price: 4145.43   (preco real do GOLD na XM)
```

## 3. SOBRE A CONTA DEMO -> REAL

Nao foi outra conta. `login 391773676` e o mesmo; o SERVIDOR mudou de
`XMGlobal-MT5 16` para `XMGlobal-MT5 14` durante a sessao. As tres conexoes
MT5 do app apontam para o 14 — consistente.

E a operacao que fechou no alvo foi BTCUSD BUY 0,01 aberta no MT5:
entrada 86.384,85, TP 86.584,30, saldo 5,62 -> 7,63. Nada de GOLD foi
aberto.

## O QUE AINDA FALTA PARA O EA USAR A IA

1. Autorizar `http://127.0.0.1:9001` em Ferramentas > Opcoes > Expert
   Advisors > Allow WebRequest. Sem isso o MT5 devolve -401.
2. Colar o token (64 caracteres) no input `AIGatewayToken`.
3. **Reanexar o EA no grafico.** Compilar NAO reanexa: o `.ex5` novo so entra
   em vigor quando o EA e trocado no grafico. Este e o passo que destrava.

## REGRA QUE A SESSAO DEIXOU

Quando dois lados do mesmo dado discordam do nome, o sintoma e `recusa com
motivo errado` — e o operador culpa a coisa errada. Verificar o nome nos DOIS
lados antes de culpar o terceiro (a corretora, o modelo, a rede).

Quarta vez nesta semana: `volume`/`quantity`, `ts`/`timestamp`,
`symbol`/`esperado`, `X-Gateway-Token`/`Authorization: Bearer`.
