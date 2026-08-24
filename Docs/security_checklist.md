# CHECKLIST DE SEGURANCA OPERACIONAL - v1.2.0-RC1
## ETAPA 15.8

**Data:** 24/08/2026 | **Varredura:** 157 arquivos (Temp/security_scan.py)

---

## Resultados da varredura

| Item | Status | Evidencia |
|------|--------|-----------|
| Credenciais fora do codigo | PASS | 0 chaves reais hardcodadas; api_key="anything" = padrao LiteLLM local (localhost:4000), falso positivo |
| Telegram token protegido | PASS | Config.mqh linha 303: NotifyTelegramToken="" (vazio=OFF); configurado via inputs, nao commitado |
| .env com placeholders | PASS | BROKER_API_KEY=your_broker_api_key_here (sem valores reais) |
| Configuracoes protegidas | PASS | configs via inputs MQL5 + config_manager.py local |
| Permissoes minimas | PASS* | EA roda em conta DEMO; trade allowed gate via TerminalInfo |
| Backups | PASS | Enterprise/BackupManager.mqh (29KB); models_backup_20260816* |
| Versionamento | PASS | VersionManager.mqh + APP_VERSION 1.2.0 + schema_version JSONs |
| Identificacao de build | PASS | TradeComment=XAU_AI_PRO; model_version/model_id no prediction.json |
| Rollback | PASS | backups de modelos + RiskCenter fail-open documentado |
| Logs de alteracoes | PASS | AuditLog.mqh (12KB) + learning_history.json |
| Nenhuma atualizacao automatica do EA | PASS | auto-update deliberadamente BLOQUEADO (VersionManager) |

*Permissoes de SO (ACLs de pasta) ficam sob responsabilidade operacional do host.

## Pendencias (pre-conta real)

1. Preencher NotifyTelegramToken somente via input na instalacao (nunca commitar).
2. Restringir pasta Downloads/XAU_AI_PRO ao usuario do servico.
3. Revisar .gitignore para excluir *.pkl grandes e logs.

---
*Documento oficial - ETAPA 15.8*
