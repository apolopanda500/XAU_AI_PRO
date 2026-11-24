# Acto ALFA-003 — Validação das estratégias e estado real do forward (23/11/2026)

## Leitura do jornal (`MQL5/Logs/20261123.log`, medido)
| Métrica | Valor | Leitura |
|---|---|---|
| `[TRADE BLOCK]` | 2.006 | maioria das decisões são RECUSA |
| `[REFRESC]` | 917 | 16/16 falhas até 12:51; corrigido pelo ALFA-001 |
| `ABERTA` / `FECHADA` | 91 / 59 | 32 posições ainda abertas |
| `SAFE_MODE` / `RECOVERY` | 131 / 286 | conexão instável |
| saldo / equity (13:21) | 4,78 / 7,28 | equity é maior pelo aberto |
| `[RISCO EM VIGOR]` | ABSOLUTO 1,00 USD = **20,921% do saldo** | ⚠️ acima do teto 10% declarado |
| `[ATR] IDENTIDADE ERRADA` | presente no restart 13:21 | ⚠️ leitura de indicador não confiável |

## Divergência de configuração (AGENTS.md §5)
- `Core/Config.mqh` declara `RiskPerTradePercent = 0.50` (prioritário) e `RiskPerTradeUsd = 2.0`.
- O **perfil vivo dos gráficos** está com `RiskPerTradePercent = 0` e `RiskPerTradeUsd = 1.00` → regra ABSOLUTA de 1 USD, que com saldo 4,78 é 20,9%.
- Produtor (código) e consumidor (perfil vivo) discordam. Isso é o que o jornal mostra.

## Sobre a meta "acertividade acima de 90%"
- **Não há medição de acertividade no jornal**: 0 linhas `[SINAL]`, 0 `[DECIS` com desfecho, 91 abertas / 59 fechadas.
- Afirmar 90% sem medição seria inventar número. O GATE_REAL registra PF 0,66 contra piso 1,20 — ou seja, **a medição existente indica o contrário**.
- O próprio dono escreveu: *"Backtest não é prova de lucro; esta regra precisa de janela real para ser medida."*

## Estratégia do dono (decisão ALFA-002, em vigor no v1.2.222/223)
- Banca < US$ 100 → **CRESCIMENTO PURO, sem stop a subir** (`GrowthStopMinBancaUsd=100.0`, `protecao=NAO`).
- SL da entrada continua (proteção obrigatória da ordem); nada é levantado acima da entrada.
- Banca média/grande → stop acima da entrada e alvos maiores; a regra já está no código.

## O que este acto NÃO faz
- Não liga o motor (`ativo=false`), não envia ordens, não fecha/altera as 32 posições abertas do dono.
- Não altera inputs de risco/lote/alvo/confiança — isso exige ordem explícita do dono (AGENTS.md §7).
- Não afirma 90% de acertividade sem medição.

## Forward real — pré-requisitos medidos para começar "limpo"
1. Alinhar o perfil vivo ao código (`RiskPerTradePercent=0.50` ou reduzir `RiskPerTradeUsd` para caber em 10%).
2. Corrigir/verificar o handle ATR (`IDENTIDADE ERRADA`).
3. Estabilizar conexão (SAFE_MODE/RECOVERY intermitentes).
4. Medir acertividade em janela real antes de afirmar qualquer percentual.
