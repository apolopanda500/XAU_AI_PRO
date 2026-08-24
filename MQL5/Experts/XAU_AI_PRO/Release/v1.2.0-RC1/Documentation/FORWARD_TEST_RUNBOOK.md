# XAU_AI_PRO v1.2.0-RC1 — Forward Test (Demo) — Runbook

Data: 2026-08-23
Conta: 111194406 (MetaQuotes-Demo) | EA: XAU_AI_PRO v1.2.0-RC1

## Estado atual (verificado)
- EA anexado em 6 gráficos demo (M5): XAUUSD, EURUSD, USDBRL, AUDUSD, NZDUSD, USDCHF
- Conta demo ativa, trading permitido, 1 posição aberta
- ForwardTestRunner ativo (EnableForwardLog=true)
  - Heartbeat: `Data\forward_test_session.csv` (FILE_COMMON)
  - Trades: `Data\forward_test_trades.csv` (FILE_COMMON)

## Critérios de aceite do forward (ETAPA 14 item 9)
1. Operação contínua em demo (≥ 2-4 semanas recomendado)
2. Monitoramento diário: ForwardHeartbeat + AuditLog + HealthMonitor
3. NÃO alterar estratégia/config durante o teste
4. Reconciliar ao final: CSV forward vs TradeLogger vs histórico broker
5. Avaliar com a matriz quantitativa (QuantValidator): PF, DD, Sharpe,
   expectancy, estabilidade

## Regras
- `EnableNotifications` pode permanecer **true** em live/demo (push real),
  ao contrário do backtest (onde gera erro 4014).
- Se mercado fechado/desconexão: FailureMode entra SAFE → RECOVERY → RESUME
  automaticamente (sem intervenção).
- Manter o terminal com "Algoritmos" habilitado (botão Algo Trading).

## Fechamento do RC
Após forward concluído e reconciliação OK → promover para produção (ETAPA 15).