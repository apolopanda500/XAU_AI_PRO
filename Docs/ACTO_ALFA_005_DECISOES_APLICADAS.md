# Acto ALFA-005 — Decisões finais aplicadas ao EA (23/11/2026)

## Decisões do DONO aplicadas
| # | Decisão | Onde aplicado |
|---|---|---|
| 1 | 20 posições sem stop por símbolo | `Core/RealAccountGuard.mqh:47` → `RealGuardMaxUnarmedPositions=20` |
| 2 | Correlated sincronizado com 20 | `Core/Config.mqh` → `MaxCorrelatedTrades=20` |
| 3 | Risco 0,50% na banca baixa | Código já tinha `RiskPerTradePercent=0.50`; **perfil vivo dos 16 `.chr` corrigido** de `0.0/1.0 USD (20,9%)` para `0.50` + `RiskPerTradeUsd=0.5` + `MaxRiskPerTradePercentCap=10.0` |
| 4 | Medidor de acertividade | `Monitoring/OperatorBrief.mqh`: `OperatorBriefWinRate()` conta deals fechados do EA (`DEAL_ENTRY_OUT`, MagicNumber) e `[RESUMO]` imprime `acerto=%.1f%% (%dW/%dL)` |
| 5 | Site 24/7 local por enquanto | Nenhuma automação/túnel criado; GitHub Pages/Render ficam para depois |

## Estratégia em vigor (v1.2.222/223)
- Banca < $100 → crescimento puro, sem stop a subir, alvos curtos $0,50–$1,00.
- Banca média ≥$100 → stop acima da entrada; banca grande → alvos maiores.
- Até 20 posições simultâneas em vários símbolos.

## Validação
- Compilação MQL5 (`tests/test_mql5_compila.py`): **2 passed** (0 errors).
- `sync_version.py --check`: **todos alinhados**.
- Perfis vivos (16 `.chr`): `risco=0.50 corr=20 unarmed=20` conferido em chart01/02/03.
- Backup dos perfis originais: `Profiles/Charts/Default/_backup_23nov/`.

## Estado do capital
- Motor: **desligado** (`ativo=false`) — aguardando ordem explícita de operação do DONO.
- Gateway 9027: 200, IA respondendo.
- 32+ posições abertas do DONO: **intactas** (nenhuma foi fechada/alterada).
- `.ex5` produção intacto; nenhuma automação nova no Windows.

## Pendência final
- **Forward real em conta real**: exige a ordem final de ligar o motor. O medidor de acertividade agora permite medir a meta >90% em vez de prometê-la.
