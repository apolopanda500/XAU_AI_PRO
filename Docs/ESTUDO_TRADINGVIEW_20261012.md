# Estudo TradingView (12/10/2026) — decisao do dono: ESTUDAR antes de trocar

> Pesquisa, sem codigo. O grafico atual e de outro agente — nada aqui autoriza
> a troca; e o mapa para decidir.

## O que o dono pediu

"Motor mais simples tipo TradingView ou XM, mais otimizado, menos erros —
mas podendo operar no grafico junto com modelos." E: grafico sempre vivo com
valores reais, com ou sem conta; menu direito configura ordens ao vivo.

## As duas TradingViews (nao sao a mesma coisa)

| | Widget avancado (iframe, gratis) | Charting Library (self-hosted) |
|---|---|---|
| Custo/licenca | gratis, embed por script | gratis, repo GitHub (acesso liberado) |
| Nossos candles (MT5/GOLD, modelo) | NAO — so simbolos da TV | SIM — datafeed nosso (`/api/universal/candles`) |
| BUY/SELL dos modelos no grafico | NAO | SIM (`createMultipointShape`/marks) |
| Linhas de SL/TP arrastaveis | NAO | SIM (`createOrderLine`, arrasto com callback) |
| Desenhos/indicadores/timeframes | nativos, zero manutencao | nativos, zero manutencao |
| Funciona sem internet | NAO (iframe remoto) | grafico SIM; dado MT5 SIM; exchange/publico NAO |
| Enviar ordem pelo grafico | NAO (só com programa de corretoras) | via NOSSO painel (o que ja existe) |

Nota: `lightweight-charts` (o de hoje) ja e DA TradingView — o "motor tipo
TradingView" parcial ja existe. O que falta nele (desenhos, indicadores,
linhas arrastaveis nativas) e exatamente o que foi recortado a mao — e cada
recorte virou um defeito medido (clip, pontas, toolbar, undo).

## Veredito tecnico

- Widget iframe: **reprovado** para este produto. Mata os dois requisitos que
  o dono marcou ("operar no grafico" + "junto com modelos") e morre sem
  internet — o oposto de "sempre vivo".
- Charting Library + datafeed no gateway: **viavel**. Cobre tudo que o
  grafico atual faz (linhas de ordem arrastaveis, marcadores de modelo,
  tabela propria) com motor mantido pela TV, e o dado continua universal
  (MT5 aberto, exchange com chave, publico sem conta).
- Custo da troca: reescrever `PriceChart` (~2000 linhas) + integracao em
  `AcompanharModelos` contra outra API; ~80 testes de grafico reescritos;
  manter os DOIS motores lado a lado durante a troca (duplicacao temporaria,
  com data de morte escrita). Estimativa honesta: dias, nao horas.

## Pre-requisito ja medido (12/10/2026)

`tests/test_candles_publicos_sem_conta.py`: candles de exchange saem SEM
credencial (klines publico, cofre intocado). O dado livre que alimentaria o
grafico sempre-vivo ja existe no gateway — falta o outro agente ligar a
ponta da tela (lane dele).

## Recomendacao

Nao trocar agora: o grafico atual esta sem defeito aberto conhecido apos os
cortes (toolbar/desenhos fora) e a troca e dias de trabalho com dois motores
vivos no meio. Reavaliar se voltarem defeitos de MOTOR de desenho (clip,
escala, crosshair) — nunca por cosmetica.
