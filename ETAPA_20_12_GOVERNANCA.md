# ETAPA 20.12 — Governança do Repositório

> **Data:** 2026-08-28
> **Escopo:** política de branch protection, regra de release, baseline oficial e regras de versionamento.
> **Decisão:** documentar a governança **sem tocar no EA** (nenhuma alteração de código MQL5 nesta etapa).

---

## 20.12.1 — Branch Protection

### Status real (auditado em 28/08/2026 via API)

| Item | Repo `apolopanda500/XAU_AI_PRO` | Repo `apolopanda500/mql5` |
|---|---|---|
| Visibilidade | **privado** | **privado** |
| Plano | Free (User) | Free (User) |
| Branch default | `main` | `main` |
| API branch protection | **HTTP 403** — recurso indisponível no plano Free | — |

**Conclusão documentada:** branch protection (proteção de branch via API/UI) **exige GitHub Pro** (u$ 4/user/mês) **ou** tornar o repositório público. Em plano Free + repo privado, a proteção **não pode ser habilitada pelo GitHub** — qualquer tentativa via API retorna `403: Upgrade to GitHub Pro or make this repository public to enable this feature`.

### Política desejada (a ativar quando o plano permitir)

Quando o plano for atualizado (ou o repo for tornado público — **não recomendado** por conter dados proprietários), aplicar **exatamente**:

1. **`main` protegida** — ninguém pode commitar direto (inclusive admin, salvo override explícito e raro);
2. **Pull Request obrigatório** — toda alteração entra via PR;
3. **CI obrigatório antes do merge** — o check `CI MQL5 - Validacao Estatica` (repo mql5) e o `CI/CD - XAU AI PRO` (repo XAU_AI_PRO) devem passar antes do merge;
4. **Impedir force-push** — `force-push: false` na branch `main`;
5. **Impedir deleção da branch** — `allow_deletions: false` na branch `main`.

**Mitigação imediata (sem GitHub Pro):** um workflow de verificação pode atuar como "quase-proteção" — ex.: job que falha se o PR não rodou o CI. **Porém não substitui a proteção real**; a política formal fica registrada aqui como requisito pendente.

---

## 20.12.2 — Regra de Release

Fluxo hierárquico oficial (cada degrau **bloqueia** o seguinte):

```
main (código-fonte)
  │
  ▼
CI 0/0 + validações          ← CI estático 181 arquivos → 0 problemas + build
  │
  ▼
Release candidate            ← empacotado e hasheado (v1.2.0, re-package 28/08)
  │
  ▼
Forward / Demo               ← operação demo/simulada monitorada
  │
  ▼
Production Gate              ← PF ≥ 1,0 + métricas estáveis (NÃO liberar sem gate)
  │
  ▼
Release                      ← somente após aprovação formal
```

**Princípio inegociável:** *"mesmo com a plataforma tecnicamente completa, não liberar capital real apenas porque o código/CI está saudável."* A decisão de capital é **financeira**, não técnica.

---

## 20.12.3 — Baseline (referências oficiais)

Registrado em **28/08/2026 20:28 -03:**

| Referência | Valor | Repo |
|---|---|---|
| **MQL5 commit** | `1704fb3` | `apolopanda500/mql5` |
| **Backend commit** | `3c347dd` (vercel.json + security headers) | `apolopanda500/XAU_AI_PRO` |
| **EA validation** | **181 arquivos → 0 problemas** (validate_mql5.py) | mql5 |
| **Vercel Deploy** | **Run #64 → SUCCESS** (healthcheck OK + headers) | XAU_AI_PRO |

- Slack action: **v4.0.0** (node24) com `webhook-type: incoming-webhook` — notificações início/sucesso/falha validadas (Run #64).
- Vercel CLI: `59.9.1`; `upload-artifact@v7.0.1` — pipeline livre de warnings de ações.
- Deploy produção: `https://xau-ai-pro-api-apolopanda500.vercel.app` (`/api/health` → `{"ok":true}`).

---

## 20.12.4 — Não Versionar (regra definitiva)

Manter **definitivamente fora** do Git (`.gitignore` já cobre):

```
*.pkl                      → modelos/dados serializados
Files/Common/              → dados gerados em runtime
Files/Data/*.json          → predições/snapshots gerados
*.ex5 / *.ex4 / *.dll      → binários compilados
*.log / logs/              → logs
dados temporários          → *.tmp, *.cache, Files/Temp/, Files/Backup/
outputs de tester          → Profiles/Tester/*.ini|*.set gerados, Profiles/deleted/
```

> Removidos do tracking em 20.12 (commit `1704fb3`): `Files/Data/model.pkl`, `Files/Data/prediction.json`, `Files/XAU_AI_PRO_stats.csv`.

---

## Sequência técnica (próximos degraus)

| Etapa | Descrição | Status |
|---|---|---|
| **20.12 Governança** | branch protection + regra de release + baseline + não-versionar | ✅ **esta etapa** |
| **20.13 CI/CD final** | validar pipeline completo (github + vercel + sentry + slack) | ⏭ próxima |
| **20.14 Observação 30 dias** | forward/demo monitorado (janela limpa 28/08 21:05 UTC, 11 símbolos) | ⏭ |
| **20.15 Gate financeiro** | **PF ≥ 1,0** + métricas estáveis | ⏭ bloqueia 20.16 |
| **20.16 Production** | somente após aprovação formal do gate | ⏭ |

---

## ⚠️ Bloqueio financeiro (não técnico)

- **PF observado:** 0,46 (referência anterior) / 0,12 (janela contaminada 20.5) — **abaixo do gate de 1,0**.
- Janela limpa 20.6 em medição desde 28/08 21:05 UTC.
- **Decisão:** capital real **NÃO será liberado** até o gate 20.15 (PF ≥ 1,0 + métricas estáveis em janela limpa). A saúde de CI/plataforma **não substitui** o gate financeiro.