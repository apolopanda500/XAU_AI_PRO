# Correcoes de seguranca que eu introduzi e a suite pegou (04/10/2026)

Este registro existe porque as tres falhas abaixo foram MINHAS, medidas pelo
`pytest` logo apos a correcao, e nao por revisao.

## 1. Eu subi o limite do regex sem necessidade

Subi `_RE_SIMBOLO` de `{1,12}` para `{1,24}` achando que `MULTI_METALS`
(12) + `_H1` (3) = 15 estouraria o limite.

O limite conta o SIMBOLO, nao o nome do arquivo. Medido:

```
MULTI_METALS     12 caracteres
MULTI_CRYPTO     12 caracteres
BTCUSDT_PERP     12 caracteres
MULTI_FIAT       10 caracteres
```

Nenhum precisa de mais. `tests/test_traversal_modelos.py` barrava `A * 13` e
estava CERTO: subir o limite era afrouxar seguranca sem motivo. Voltou para
12, com o `_` a mais e nada menos.

## 2. A porta do timeframe vazio mudou o comportamento do teste

Para achar `MULTI_METALS.pkl` (que nao tem sufixo), abri uma porta:
timeframe vazio devolve o nome geral. Isso fez o teste de allowlist
reprovar.

O comportamento estava CORRETO: `inferir` ja recusa timeframe fora da
allowlist ANTES de chegar no resolvedor de nome. Medido:

```
inferir("XAUUSD", candles, "")  -> disponivel=False, "timeframe nao suportado: "
inferir("XAUUSD", candles, "H1/../../etc") -> False
inferir("XAUUSD", candles, "ZZZ9") -> False
inferir("XAUUSD", candles, "M1")   -> False
```

O teste antigo media a camada errada. Passou a medir `inferir`, que e o
caminho real do pedido.

## 3. Tirar `_` do SEPARADORES quebrou `BTC_USDT`

`tests/test_symbols.py` fixa `BTC_USDT -> BTCUSDT`. Remover o `_` de
`SEPARADORES` quebrou: `BTC_USDT` virava `BTC_USDT` (com underscore), que
nao casa com o artefato `BTCUSDT_*`.

Resolucao: o underscore so some quando separa as METADES de um par. O
prefixo `MULTI_` e marcador de CLASSE de ativo, e o underscore dele faz
parte do nome.

```
BTC_USDT      -> BTCUSDT        (separador de par, some)
BTCUSDT       -> BTCUSDT
MULTI_METALS  -> MULTI_METALS   (marcador de classe, fica)
MULTIMETALS   -> MULTIMETALS
btc/usdt      -> BTCUSDT
XAUUSD.pro    -> XAUUSD
EURUSD.m      -> EURUSD
```

O operador pode digitar as duas grafias e o resultado e o mesmo nome de
arquivo.

## 4. Meu proprio teste de "folga" estava errado

Escrevi um teste que exigia que o limite do regex tivesse FOLGA sobre o maior
nome real. Ao voltar o limite para 12, o teste passou a reprovar — e ele e que
estava errado: exigir folga e exigir seguranca frouxa.

A propriedade correta e o COBRIMENTO (todo nome real passa). A propriedade de
"nao sobra folga" esta no teste de travessia, que barra `A * 13`.

Este e o terceiro defeito do ciclo que o teste verde estava escondendo,
depois do duble de `enviar` que lia `payload["sl"]` e do
`getAllByRole('spinbutton')` que media 117 elementos em vez de 13.

## ESTADO APOS AS CORRECOES

```
pytest  1030 passed  |  vitest 205 passed  |  21/21 arquivos
25 modelos operam com inferencia real
```

## O QUE AINDA NAO ESTA VALIDADO PARA OPERAR COM DINHEIRO REAL

1. **O app instalado nao existe nesta maquina.**
   `C:\Users\Micro\AppData\Local\XAU AI PRO` ausente. O atalho aponta para
   um alvo que nao esta la. Sem build novo, nao ha app para operar.

2. **Nenhuma ordem foi para a XM.** O ciclo medido parou no contrato
   universal. O envio real depende do `UniversalRouter` com a conta ativa e
   o `risk_gate` da corretora — caminho que so roda com o app no ar.

3. **Os candles das medicoes de inferencia sao SINTETICOS.** Provam que o
   pipeline roda. O edge real vem do `.meta.json`, medido em treino com
   purged k-fold.

4. **Os tres `MULTI_*` nao servem** (feature_version `25F-est-v1`, 22
   features, contra 25 do codigo atual). Exigem retreino. Decisao do dono:
   opcao B — operar com os 25 que respondem.

5. **Latencia no rodape esta pela metade.** Componente existe, falta CSS e
   montar no `App.tsx`.
