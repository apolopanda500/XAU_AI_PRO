# PRODUCTION READINESS - XAU_AI_PRO v1.2.0-RC1 -> PRODUCTION CANDIDATE
## ETAPA 15.10 - Consolidacao Operacional

**Data:** 24/08/2026

---

## Status consolidado da ETAPA 15

| Fase | Entrega | Status |
|------|---------|--------|
| 15.1 | Baseline congelado v1.2.0-RC1 | DONE |
| 15.2 | Contratos EA<->Python<->App + teste integrado 13/13 | DONE |
| 15.3 | IA profissional (staleness, UNAVAILABLE, fallback) + modelos 25 features | DONE |
| 15.4 | Execution auditada + politica lote minimo unificada | DONE |
| 15.5 | RiskCenter (fachada unica) + fonte unica de drawdown | DONE |
| 15.6 | Observabilidade (system_status.json) | DONE |
| 15.7 | Failover: matriz 9 cenarios validada por codigo | DONE* |
| 15.8 | Seguranca: varredura limpa + checklist | DONE |
| 15.9 | Endurance: framework pronto + coletor testado | FRAMEWORK OK / EXECUCAO PENDENTE |
| 15.10 | Production Candidate declarado | DECLARADO |

## Pendencias HONESTAS antes de v1.2.0-PRODUCTION

### Bloqueantes (obrigatorios)
1. [ ] Endurance 24h/72h/7d/14d/30d EXECUTADO com criterios PASS
       (requer dias de relogio; coletor ja operante)
2. [ ] Reload do EA no terminal para ativar SystemStatus/RiskCenter/
       staleness (build novo ja compilado 0/0)
3. [ ] Forward test demo >= 30 dias com metricas coletadas

### Nao-bloqueantes (melhorias)
4. [ ] CheckRiskPerSymbol/Session implementados (SafetyManager stubs)
5. [ ] Exposicao nocional real no PortfolioManager (hoje = P/L flutuante)
6. [ ] Latencias da Telemetry incluidas no system_status.json
7. [ ] Leitor do system_status.json no app (dashboard tab)
8. [ ] Alerta dedicado p/ falha de WebRequest (news)

## Caminho de promocao

```
v1.2.0-RC1  [ATUAL - PRODUCTION CANDIDATE]
   |
   +--> Endurance 30d PASS (coletor rodando sobre forward demo)
   |
   +--> Operational Acceptance (revisao humana dos relatorios JSONL)
   |
   +--> v1.2.0-PRODUCTION  (conta real, risco minimo, 1 simbolo)
```

## Regras de producao (conta real)
- Iniciar SOMENTE XAUUSD, lote fixo pequeno ou risco 0.5%
- RequireAIJSON=true (modo estrito) nas primeiras semanas
- AllowMinLotOverride=false (estrito)
- Telegram token configurado via input na instalacao
- Rollback: restaurar models_backup_*.pkl + build anterior (.ex5)

---
*Documento oficial - ETAPA 15.10*
