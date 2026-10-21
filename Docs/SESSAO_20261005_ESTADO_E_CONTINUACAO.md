# ESTADO DA SESSAO — 05/10/2026 (referencia para retomar)

Um arquivo so, com o que MEDIR antes de continuar. Onde a leitura antiga
estava errada, esta marcado ERRADO — as tres correcoes de hoje vieram de
medir a pasta errada, e duas delas custaram ciclos.

## 1. DONO: COMO QUER OPERAR

> "tudo novo e limpo, reconstruir modelos certos agora, fechar trabalho para
>  testar o app e comecar teste de verdade no app"

> "salvar conversa, manter trabalho em dia para futuros dias e voltar para
>  fechar trabalho ate chegar no app rodando instalado 10/10, operando conta
>  real MT5 e nas corretoras"

Arquitetura pedida — a IA faz tudo, o DONO ESCOLHE quem executa:

```
MOTOR -> IA -> decide ativo, timeframe e limites -> opera   (backend Python)
EA    -> IA -> decide sinal                              -> opera   (MT5)
MESA  -> voce -> manda ordem                              -> opera   (grafico)
```

Escolha: "modelos treinados", "EA tambem no automatico" ou "pelo grafico
manual". Nao ha botao de confirmacao por ordem.

## 2. CONTA REAL (medido)

```
XMGlobal-MT5 14 · login 391773676 · balance 7,63 · equity 13,25 · 0 posicoes
1639 ativos · 0 sem `path` preenchido
```

O servidor mudou de XMGlobal-MT5 16 para 14 durante a sessao. O MESMO
login. As tres conexoes MT5 do app apontam para o 14.

OPERACAO FECHADA (aberta a mao no MT5, nao pelo app):
BTCUSD BUY 0,01 @ 86.384,85, TP 86.584,30, SEM STOP LOSS. Saldo 5,62 -> 7,63.
O dono escolheu operar sem SL, sabendo: queda de 2% no BTC levava o equity
de 11,63 para -5,65 (STOP OUT). O `RequireStopLoss` novo existe para o
caminho do app.

## 3. MODELOS (medido)

```
39 artefatos em Python/models/
  36 com feature_version 25F-v2 (25 features) -> OPERAM
   3 com 25F-est-v1 (22 features)            -> NAO ALCANCAVEIS
```

Os 3 inacessiveis sao os de MAIOR edge do catalogo:

| modelo | edge | acerto | amostras |
|---|---|---|---|
| MULTI_METALS | +0,2497 | 58,3% | 67.678 |
| MULTI_FIAT | +0,1853 | 51,9% | 149.927 |
| MULTI_CRYPTO | +0,1816 | 51,5% | 149.926 |

**CAUSA:** treinados com 22 features; o codigo produz 25. Nao ha correcao em
codigo — exige RETREINO.

Os 25 que operam, medidos pela ROTA REAL com preco da XM:

```
EURUSD_H4 +0,2092 | USDCAD_H4 +0,1933 | USDJPY_H4 +0,1879
NZDUSD_H4 +0,1667 | EURUSD_H1 +0,1641 | BTCUSD_H4 +0,1552
GBPUSD_H4 +0,1507 | ETHUSD_H1 +0,1420 | USDJPY_H1 +0,1370
AUDUSD_H1 +0,1318 | ETHUSD_H4 +0,1303 | XAUUSD_H4 +0,1261  (XM:GOLD)
BTCUSD_H1 +0,1225 | GBPUSD_H1 +0,1189 | XAUUSD_H1 +0,1087  (XM:GOLD)
NZDUSD_H1 +0,1085 | AUDUSD_H4 +0,1028 | BTCUSD_M15 +0,1008
ETHUSD_M15 +0,0946 | GBPUSD_M15 +0,0868 | EURUSD_M15 +0,0864
USDCAD_H1 +0,0749 | AUDUSD_M15 +0,0688 | USDCAD_M15 +0,0685
NZDUSD_M15 +0,0604
```

2 deles respondem NEUTRAL (o gate recusa, como deve).

## 4. LATENCIA DA INFERENCIA (medido, separado)

```
candles do MT5      16 ms
preparacao           4 ms
1a inferencia     2096 ms   (carrega o .pkl do disco)
2a em diante      144 ms   (o _CACHE segura)
```

Por isso `AIRequestTimeoutMs` = 15000, e nao 5000: cortar o tempo trocaria
sinal atrasado por sinal ausente.

## 5. IA NO MT5 — ESTADO

```
AIConnector.mqh   le Data\prediction_<SIMBOLO>.json
                  essa pasta NAO EXISTE -> o EA vivia sem sinal

AIUseGateway     agora true: chama http://127.0.0.1:9001/api/ai/predict
PeriodLabel()    traduz 16385 -> H1
ParsePredictionJSON()  UM parser para gateway E arquivo
Authorization: Bearer  (o gateway so aceita este; X-Gateway-Token dava 401)
```

Rota medida com a conta real: BTCUSD H1 SELL 45,9% edge +0,1225 preco
86.766,95 | EURUSD H4 BUY 66,7% edge +0,2092 | XAUUSD H4 BUY 49,9%
edge +0,1261 preco 4145,43.

**XAUUSD -> GOLD:** a XM nao tem `XAUUSD`; tem `GOLD`. O
`symbol_aliases.json` traduz, e a rota de inferencia passou a usar
`para_corretora`. Sem isso a rota pedia `XAUUSD` e recebia
`no_candles_for_symbol` — recusa SEGURA, com motivo ERRADO.

## 6. EA — O QUE MUDOU (compilado, 0 erros)

```
AIHasSignalAuthority  false   -> quando true, a IA DECIDE (padrao: IA so veta)
AIAuthorityMinScore   75.0    -> piso para assumir (separado do veto, 50)
RequireStopLoss       true    -> recusa ordem sem SL
RequireAIJSON         false   -> com true, nunca opera sem IA
AutoTrade             RELIGADO (era `if(false)`, input morto)
PartialTriggerInATR   true    -> gatilho do parcial em ATR, nao em pontos
PartialPercent        30.0
EnableDynamicTP       true    -> TP que SO APROXIMA (novo)
TPAproxStepATRMult    1.0
TPAproxMaxFraction    1.0
```

O pipeline de ordem do EA JA EXISTIA e estava vivo:
`OnTick -> RunTradePipeline -> ProcessSymbol -> GetCombinedSignal ->
ExecuteTrade -> CSmartExecution::OpenPosition`. Faltava AUTORIDADE da IA,
nao construcao.

`OrderManager.mqh` e CODIGO MORTO (o pipeline usa `SmartExecution`).

## 7. FALTA PARA OPERAR DE VERDADE

1. **Autorizar WebRequest** no MT5: Ferramentas > Opcoes > Expert Advisors >
   Allow WebRequest, com `http://127.0.0.1:9001`. O dono JA FEZ.
2. **Colar o token** no input `AIGatewayToken`:
   `3c31ec1f9c0dd4599263eecacf8fcdf8f6c90e93e5474fe2328e186f27810efd`
3. **Gateway rodando.** Ele morre com o processo pai. O app instalado sobe
   junto; no repo, sobe separado.
4. **Reanexar o EA no grafico.** Compilar NAO reanexa.
5. **App instalado.** Medido: `C:\Users\Micro\AppData\Local\XAU AI PRO`
   AUSENTE nesta maquina. O atalho aponta para um alvo que nao esta la.
6. **build_app.bat + install_app.bat** + rodar pelo atalho.
7. **Retreinar os 3 MULTI_*** com 25F-v2 (opcao do dono: B = operar com os
   25 que ja funcionam).

## 8. CLASSES DE ATIVO — VEM DA CORRETORA

```
ANTES (palavra solta, sem fronteira)     DEPOIS (raiz do `path`)
crypto  106  (43 acoes erradas)          crypto   63
equity 1344                            equity  1380
metal    10                            metal    11
index    45                            index    51
forex    55                            forex    55
```

`SOL` casava dentro de "Solvar"; `XRP` dentro de "XRPetersen".

## 9. REGRAS DO PROJETO QUE O DONO REPETIU

- nenhum simbolo ou timeframe PRESUMIDO (nada de default)
- nada de nome de ativo fixado em codigo executavel
- IA pode fazer tudo, mas quem OPERA e escolha do dono

## 10. ESTADO DAS SUITES

```
pytest 1030 passed | vitest 205 passed (21/21 arquivos)
tsc limpo | vite build ok | MetaEditor64 0 erros
```

Commits sincronizados em GitHub e GitLab.

## 11. A REGRA QUE A SESSAO DEIXOU

Quando dois lados do mesmo dado discordam do nome, o sintoma e RECUSA COM
MOTIVO ERRADO — e o operador culpa a coisa errada. Quarta vez nesta semana:

```
volume / quantity                 (auto_engine lia payload["volume"])
ts / timestamp                    (o terminal mostrava "--")
symbol / esperado                 (parser do EA, erro de compilacao)
X-Gateway-Token / Authorization   (401 com o token correto)
```

E: **teste verde escondendo defeito** aconteceu TRES vezes no mesmo ciclo —
o duble de `enviar` lia `payload["sl"]`, o teste de traducao repetia o
codigo em vez de importa-lo, e `getAllByRole('spinbutton')` media 117
elementos em vez de 13. Onde dois lados do mesmo dado falam idiomas
diferentes, o teste tem que exercitar o caminho INTEIRO.
