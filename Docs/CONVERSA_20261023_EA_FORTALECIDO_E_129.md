# 23/10/2026 — EA reforcado, versao 1.2.9 e build para reanexar

> Ciclo pedido pelo dono: "corrigir para a melhor versao otimizada e segura,
> sincronizar com o app, criar baterias de teste e simular na demo ate virar
> uso real". Este arquivo registra o que foi **medido**, o que mudou de
> comportamento e o que ainda depende dele.

## 1. Defeitos corrigidos (cada um com a medicao que o justifica)

| # | Defeito | Medido antes | Correcao |
|---|---|---|---|
| 1 | Distancia do stop por `contrato x point` | USDJPY 0,01 lote / US$ 2,00 de risco dava **2 pontos** (0,2 pip), dentro do spread. Erro ~151x (100,00 / 0,66 de `tick_value`) | `Config.mqh::DistanciaPontosParaRiscoUSD` passa a ler `TICK_VALUE/TICK_SIZE` (moeda da conta) e so cai em `contract_size` quando a ficha do simbolo nao responde |
| 2 | Risco por operacao sem comparacao com o orcamento do dia | `RiskPerTradeUsd = 2,00` contra orcamento de 5% de US$ 11,63 (**US$ 0,58**); uma entrada = 3,4x o limite diario | `RiscoCabeNoOrcamento()` + `MaxTradeRiskPctOfBudget` bloqueiam a entrada com motivo; `ExecutionEngine` le o risco real da ordem (`RiscoEmDinheiroDaOrdem`) |
| 3 | Fallback silencioso quando a distancia em dinheiro nao pode ser calculada | `slUSD <= 0` caia calado para os pontos do input, trocando o risco configurado | Bloqueio explicito (`RISK_DISTANCE_UNKNOWN`) |
| 4 | Win rate salvo pela metade | `StatisticsRegisterTrade(0.0)` na **entrada** (`:1152`) e na **saida** (`:1388`); a funcao incrementa o total sempre (`Statistics.mqh:204-216`), entao cada posicao contava 2x | Chamada de entrada removida; o contador diario do `SafetyManager` ja tinha fonte propria (`RegisterDailyTrade`) |
| 5 | Fechamento por ordem contraria nao era registrado | `OnTradeTransaction` tratava `DEAL_ENTRY_OUT` e ignorava `DEAL_ENTRY_OUT_BY` | Ambos tratados |
| 6 | Resultado quantitativo zerado | `InsertTrade(..., type = 0, ...)`, `QuantRecordResult(profit, 0.0)`, `RecordTrade(st, profit, 0.0, 0.0)` | `type` vem do deal; `RiscoDaPosicao()` le o SL do deal de entrada e o R real vai para o quant e para o log; breakeven deixa de ser LOSS (`WIN/LOSS/BE`) |
| 7 | "IA" com confianca falsa | Sem gateway, `GetAIConfidence` subia a **85** (50 base + 15 tendencia + 10 RSI + 10 ADX); multiplicador de lote 1,00 e piso de veto 50 passavam sem IA | `AllowTradeWithoutAI=false` (padrao): IA indisponivel **bloqueia novas entradas**; o fallback e capado em `AIUnavailableConfidenceCap` (40). `true` existe para o Strategy Tester |
| 8 | Lote inventado e truncado | `CalculateLotByRisk("")` devolvia **0,01**; retorno era `NormalizeDouble(lot, 2)`, que zera volume em step 0,001 | Simbolo vazio -> `0.0`; `NormalizarVolume()` deriva as casas do `SYMBOL_VOLUME_STEP` |
| 9 | Score de outro ativo no log | `MarketScore` global; com 11 simbolos o forward log gravava a nota do **ultimo** avaliado | `SetMarketScore/GetMarketScoreFor` (nota por simbolo) |
| 10 | Log flood e comentarios destruidos | `FinalAIAllow` imprimia a cada tick por simbolo; bloco `ETAPA 11` de `DecisionEngine.mqh` e a linha 39 do `.mq5` estavam em mojibake | Throttle de 60 s; textos restaurados |

## 2. Mudanca de comportamento que o dono precisa saber

Com `AIUseGateway=true` e o gateway fora do ar, o EA **deixa de abrir novas
posicoes** (gerencia as existentes normalmente). Antes ele abria com uma
"confianca" que vinha dos indicadores. Para operar sem IA, ligue
`AllowTradeWithoutAI=true` — e leia o numero como indicador, nao como IA.

## 3. Medido depois das correcoes

| Medida | Resultado |
|---|---|
| `MetaEditor64 /compile` | **0 errors, 0 warnings** (20.143 ms) |
| `pytest -q tests` | **1535 passed, 9 skipped** (411 s) |
| `npx tsc --noEmit` | exit **0** |
| `npx vitest run` | **950 passed** (77 arquivos) |
| `.ex5` gerado | 23/10/2026, recompilado depois do fonte |

## 4. Nao feito, e por que

1. **Bateria no Strategy Tester**: o tester roda dentro do terminal logado; a
   automacao headless nao foi executada neste ciclo. O EA compila e a logica de
   risco foi corrigida, mas **nenhum resultado de tester foi medido** aqui.
2. **Operacao repetida na DEMO**: o gateway responde `401` sem o token que o
   Tauri injeta por sessao (registrado tambem em `Temp/gateway_token.txt`
   ausente). Sem token eu nao envio ordem — e isso e o comportamento correto.
3. **Modelos novos treinados**: os ciclos anteriores mediram **0 de 40**
   combinacoes com edge na direcao e **0 de 28** no alvo liquido. Retreinar sem
   mudar o dado/rotulo produz o mesmo resultado; nao ha modelo novo para
   "completar a IA" enquanto a pesquisa nao achar edge. Nao vou apresentar
   modelo sem edge como IA pronta.

## 5. Acoes do dono (nesta ordem)

1. **Reanexar o EA** no grafico (compilar nao reanexa). O `.ex5` ja e o novo.
2. Conferir no journal: `[ADV AI]` com throttle, ausencia de `RISK DISTANCE
   UNKNOWN` e de `RISCO BLOQUEADO` em conta pequena — se aparecer, o
   `RiskPerTradeUsd` precisa caber no saldo.
3. Rodar o forward test em **DEMO** com o app no ar (token de sessao presente).
4. So depois de demo + endurance: autorizar `XAU_ENABLE_REAL_ORDERS=1`.
