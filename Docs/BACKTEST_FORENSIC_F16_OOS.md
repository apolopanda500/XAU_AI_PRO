# Resultado do backtest XAU_AI_PRO_FORENSIC_F16_OOS (Strategy Tester)

Extraido de `Tester/logs/20261003.log` (14,3 GB, 85 milhoes de linhas) ANTES de
apagar o log. O log foi removido por 14,3 GB; este e o resultado que importa.

## Rodada
| | |
|---|---|
| Simbolo / timeframe | XAUUSD, M5 |
| Periodo | 2022.10.27 -> 2025.08.29 |
| Duracao | 4:36:54 |
| Ticks | 24.271.062 |
| Log gerado | 14,3 GB (85.244.849 linhas) |

## Resultado
| Metrica | Valor |
|---|---|
| Trades | 2.998 |
| Wins / Losses | 2.424 / 549 |
| **WinRate** | **80,85%** |
| **Profit** | **-972,14** |
| **Profit Factor** | **0,72** |
| MaxDD | 1.038,33 |
| **Sharpe** | **-3,01** |
| Melhor estrategia | Technical |

## LEITURA — e o ponto central

**WinRate de 80,85% com Profit Factor de 0,72 e Sharpe de -3,01.**

WinRate alto com lucro negativo e a assinatura classica de ** Payoff menor que1**:
o EA acerta 8 de cada 10, mas o acerto ganha menos do que o erro perde. Com PF
de 0,72, cada unidade de ganho gera 0,72 de perda — para empatar, o payoff
precisaria de 1/0,72 = 1,39.

Nao e problema de margem, nem de `EXEC_NO_MARGIN`, nem de erro do broker: o
relatorio final diz, campo a campo, **`Failures: 0`** em AI, Indicators, Broker,
Dataset, JSON e Memory. A execucao foi limpa. O que falhou foi a **economia da
estrategia**, que e problema de modelo e nao de codigo.

## O que este resultado nao autoriza
Nada aqui justifica ordem REAL. O `AGENTS.md` exige validacao completa em DEMO
+ forward test + endurance, e o unico forward test medido ate agora reprovou
(4.246 `EXEC_NO_MARGIN`).

