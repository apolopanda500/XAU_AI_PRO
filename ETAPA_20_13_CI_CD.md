# ETAPA 20.13 — CI/CD Final (Auditoria Formal)

> **Data:** 2026-08-28
> **Escopo:** auditoria end-to-end do pipeline (GitHub → Vercel → Sentry → Slack), testes de gate e limpeza de artefatos.
> **Resultado:** pipeline saudável com gate real de validação comprovado por teste negativo.

---

## 1. Pipeline completo (cadeia validada)

```
push (main)
  → validate-and-package (Python compileall + bundle + artefato)
  → build-frontend (auxiliar, if: always() - fonte de source maps Sentry)
  → deploy-vercel (needs validate; só main/tags)
  → health check final (needs deploy; success())
  → notificações Slack (início / sucesso / falha / conclusão)
```

| Job | Gate | Comportamento em falha |
|---|---|---|
| `validate-and-package` | **gate principal** | falha → `deploy-vercel` **skipped** |
| `build-frontend` | auxiliar (Sentry) | roda com `always()` — não é deploy |
| `deploy-vercel` | `needs validate` + `if: main/tags` | **não roda** se validate falhar |
| `preview-deploy` | só PR | skip em push |
| `healthcheck` | `needs deploy` + `success()` | **não roda** se deploy falhar |

**Confirmado:** uma falha de validação **impede o deploy** (job skipped), não vira warning.

---

## 2. Runs recentes (auditoria 28/08)

| Run | Evento | Commit | Resultado | Observação |
|---|---|---|---|---|
| #61 | dispatch | `373d891` | ✅ success | Slack v4 + texto (baseline antigo) |
| #62 | push | `8cc7a9c` | ✅ success | remoção workflow inválido + Slack v4 |
| #63 | push | `17808e3` | ✅ success | upload-artifact v7, zero warnings |
| #64 | push | `3c347dd` | ✅ success | vercel.json + headers |
| #65 | push | `d1af7c7` | ⏸ cancelled | **cancelado por concurrency** (política: deploy mais novo vence) — esperado, não é falha |
| #66 | push | `ff09bce` | ❌ failure | **expôs erro real mascarado** (`dashboard.py` backtick-n) — gate funcionou: deploy skipped |
| #67 | push | `66e44a0` | ✅ success | correção dashboard + deploy + health OK |
| #68 | dispatch (branch teste) | `aea282e` | ❌ failure | **teste negativo intencional** — CI detectou e bloqueou |

**Falhas intermitentes:** nenhuma. O #66 foi uma falha genuína (código-fonte quebrado escondido pelo `|| true`) — corrigida e confirmada no #67. O #65 foi cancelamento por política de concurrency (comportamento esperado).

---

## 3. Gates obrigatórios — teste negativo (prova formal)

### Descoberta crítica
O passo `Validar sintaxe Python` usava `|| true` → **qualquer falha de sintaxe era mascarada** como sucesso. Removido no commit `ff09bce` (gate real).

### Prova do gate (Run #66, na main)
- `Validar sintaxe Python` → **failure** (erro real: `app/tabs/dashboard.py` linha 17 com backtick-n literal `` `n `` colando 2 imports)
- `Deploy Vercel` → **skipped** (bloqueado pela validação)

### Correção do erro encontrado (Run #67, commit `66e44a0`)
- `app/tabs/dashboard.py` L17: `` `n `` literal → quebra de linha real (2 imports separados)
- verificação: varredura do repo — `backend/src/index.mjs` tem backticks mas são **legítimos** (`` `npx ...` `` em strings/comentários; `node --check` OK); `.output/` são build artifacts; `Dashboard.md` são docs com `` `n `` em exemplos de shell (intencional)

### Teste negativo formal (branch temporária)
- Branch `teste-negativo-20-13` criada com `app/tabs/teste_negativo_invalido.py` (sintaxe deliberadamente quebrada)
- Run #68 (workflow_dispatch na branch): `Validar sintaxe Python` → **failure**, `Empacotar bundle` → **skipped**, `Deploy Vercel` → **skipped**
- **Branch descartada** (remota + local deletadas) — `main` intacta

✅ **Conclusão: CI detecta alteração inválida e bloqueia o deploy.**

---

## 4. Artefatos — fora do versionamento (verificado)

| Repo | Artefato encontrado | Ação |
|---|---|---|
| **XAU_AI_PRO** | `Python/ai/model.pkl` (modelo IA binário) | `git rm --cached` + gitignore já cobre → commit `02722a4` |
| **mql5** | 135 `Profiles/Tester/*.ini` (outputs de tester, muitos de EAs de terceiros) | `git rm --cached` + gitignore `Profiles/Tester/*.ini` → commit `dc80487` |

Regras definitivas (20.12.4) confirmadas ativas: `*.pkl`, `Files/Common/`, `Files/Data/*.json`, `*.ex5`, `*.log`, temporários, `Profiles/Tester/*.ini`, `Profiles/deleted/`.

---

## 5. Baseline oficial (atualizado)

| Referência | Valor |
|---|---|
| **Governança** | commit `d1af7c7` (ETAPA 20.12) — push confirmado, run #65 cancelado por concurrency (normal), pipeline revalidado |
| **CI/CD baseline funcional** | commit `66e44a0` → **Run #67 → SUCCESS** (validação + deploy + health + Slack) |
| **MQL5** | commit `1704fb3` (validação estática 181 arquivos → 0 problemas) |
| **Backend/App** | commit `02722a4` (model.pkl untracked) |
| **Gitignore mql5** | commit `dc80487` (tester outputs untracked) |
| **Gate real** | removido `\|\| true` do compileall (`ff09bce`); **comprovado por teste negativo #68** |

---

## 6. Decisões e pendências

- ✅ **Gate validado**: falha de validação bloqueia deploy (não vira warning)
- ✅ **Pipeline limpo**: Slack v4, Vercel CLI 59.9.1, upload-artifact v7 — zero warnings de ações
- ✅ **Artefatos**: nenhum dado gerado/tester output versionado
- ⚠️ **Branch protection**: continua indisponível (repo privado, GitHub Free) — política registrada na 20.12, exige Pro/Team/Enterprise
- ⚠️ **Bloco financeiro inalterado**: PF < gate 1,0 → **sem capital real** (CI saudável ≠ rentabilidade)

---

## Sequência

| Etapa | Status |
|---|---|
| 20.12 Governança | ✅ |
| **20.13 CI/CD final** | ✅ **esta auditoria** |
| 20.14 Endurance (24h → 72h → 7d → 30d) | ⏳ janela limpa 28/08 21:05 UTC em medição |
| 20.15 Gate financeiro (PF ≥ 1,0) | 🔴 bloqueante |
| 20.16 Release final | ⏳ |
| 20.17 Pós-release | ⏳ |