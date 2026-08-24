# MATRIZ DE FAILOVER - XAU_AI_PRO v1.2.0-RC1
## ETAPA 15.7 - Validacao dos 9 cenarios

**Data:** 24/08/2026 | **Metodo:** auditoria de codigo integrado no fluxo
(OnTick/OnTimer ativos - linhas verificadas em XAU_AI_PRO.mq5)

---

## Maquina de resiliencia (FailureMode - Revival Machine)

```
ERROR -> DETECT -> CLASSIFY -> SAFE_MODE -> (cooldown 60s) -> RECOVERY
                                  |                          |
                     bloqueia NOVAS entradas          max 5 ciclos ->
                     gestao de posicoes CONTINUA      intervencao humana
```

Componentes ativos verificados:
- ConnectionGuard: Refresh/CanOperate gate (linhas 315, 914-917)
- CircuitBreaker: Init/Run/CanTrade (311, 559, 829, 1425; gates 621, 831)
- RecoveryManager: Init/Run/IsModuleHealthy (313, 561, 1413, 1416-1417)
- FailureMode: Feed/Run/Operational gate (1418-1419, 920)
- Alertas: CNotificationCenter::SendCircuitBreaker (1539-1543)

---

## Matriz dos 9 cenarios

| # | Cenario        | Detecta                    | Registra            | Alerta              | Estado seguro         | Recupera                  | Valida saude                | Retoma |
|---|----------------|----------------------------|---------------------|---------------------|-----------------------|---------------------------|-----------------------------|--------|
| 1 | MT5 cai        | TERMINAL_CONNECTED off     | [TRADE BLOCK] CONNECTION | NotificationCenter | FailureMode SAFE      | ConnectionGuardRefresh    | IsModuleHealthy(Broker)     | AUTO   |
| 2 | Python cai     | staleness AI (ETAPA 15.3)  | AI PREDICTION STALE | SystemStatus ai.stale | RequireAIJSON=true bloqueia; false= fallback local | novo prediction JSON | RecoveryManager CheckAI | AUTO   |
| 3 | Internet cai   | TERMINAL_CONNECTED=0       | ConnectionGuard log | NotificationCenter  | SAFE (novas entradas) | reconexao terminal        | ConnBrokerConnected         | AUTO   |
| 4 | Broker desconecta | ACCOUNT_TRADE_ALLOWED/ConnBrokerConnected | [TRADE BLOCK] | NotificationCenter | CircuitBreaker SAFE   | CheckBrokerError reset    | IsModuleHealthy(Broker)     | AUTO   |
| 5 | Database falha | CheckDataset               | RecoveryManager log | HealthSummary       | degradacao (log)      | revalidacao periodica     | CheckDataset                | AUTO   |
| 6 | JSON invalido  | LoadAIPrediction valida    | health JSON errors counter | HealthMonitor | fallback local IA     | proximo JSON valido       | CheckJSON                   | AUTO   |
| 7 | Dataset indisponivel | CheckDataset         | RecoveryManager log | HealthSummary       | degradacao suave      | DataLogger recria         | CheckDataset                | AUTO   |
| 8 | WebRequest falha | NewsFilter interno       | log NewsFilter      | -                   | news tratado como sem bloqueio | proximo ciclo    | periodicidade               | AUTO   |
| 9 | Terminal reinicia | RiskHub GlobalVariables persistem | -           | -                   | limites diarios PRESERVADOS | init normal         | RiskHubNewDay               | AUTO   |

---

## Gaps documentados

| Gap | Acao futura |
|-----|-------------|
| WebRequest (news) sem alerta dedicado | Fase 15.6 app / NotificationCenter |
| Endurance real pendente (ver ETAPA 15.9) | janelas 24h-30d sobre forward test |

---
*Documento oficial - ETAPA 15.7*
