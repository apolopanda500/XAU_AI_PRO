# Integração Vercel — XAU AI PRO

> Documentação da configuração e correção da integração Vercel (28/08/2026).

## URLs de Produção

| Projeto Vercel | URL | Uso |
|---|---|---|
| `xau-ai-pro` | https://xau-ai-pro-apolopanda500.vercel.app | API Backend (Nitro + Workflows) |
| `xau-ai-pro-api` | https://xau-ai-pro-api-apolopanda500.vercel.app | API Backend (deploy CLI da pasta `backend/`) |

## Endpoints disponíveis (serverless)

- `GET /` — status geral do backend
- `GET /api/health` — health check
- `GET /api/_diag` — diagnóstico do Workflow SDK
- `POST /api/workflows/market-data` — inicia o `marketDataWorkflow`
- `POST /api/workflows/reconcile` — inicia o `reconcileWorkflow` (body: `{"symbol": "XAUUSD"}`)
- `GET /api/workflows/:runId` — inspeção de runs

## Arquitetura

- **Backend local** (`backend/server-desktop.cjs`, porta 3001): lê o `forward_test_events.csv`
  do MT5 na máquina local — usado pelo dashboard desktop (`app/`).
- **Backend Vercel** (`backend/src/index.mjs`): Express serverless com Workflow SDK
  (`marketDataWorkflow` e `reconcileWorkflow`).

## Configuração do projeto Vercel `xau-ai-pro`

- Git: `github.com/apolopanda500/XAU_AI_PRO` (branch `main`)
- Root Directory: `backend`
- Build: `nitro build` (script `vercel-build` em `backend/package.json`)
- Deploy Protection (SSO): **desabilitado** (necessário para o EA/app consumirem a API)

## Correções realizadas (28/08/2026)

1. **Erro "Microfrontends Config Present (mfe-config-present)"**
   - Causa raiz FINAL: o projeto tinha o check `mfe-config-present` configurado como
     **job com target `production`** (campo `jobs` do projeto na API) — um resquício
     da tentativa de configurar microfrontends com o `vercel.json` legado (com BOM,
     removido no commit `4b852c2`).
   - Como o projeto não é um MFE default app, o check sempre falhava como
     "inaplicável" e bloqueava a promoção (deployment ficava em STAGED).
   - Solução: zerar os targets do job nos dois projetos:
     ```bash
     PATCH /v9/projects/{id} -d '{"jobs": {"mfe-config-present": {"targets": []}}}'
     ```
     (o PATCH com `{"jobs": {...}}` faz merge — para remover um job, sete `targets: []`).

2. **Deployments STAGED (check `deployment-alias` failed)**
   - Consequência do item 1: com checks falhando, o alias de produção não era atribuído.
   - Contorno no CI/CD: `vercel promote <deployment-url> --yes` após o deploy.

3. **SSO Protection ativo** — desabilitado via API nos dois projetos
   (`PATCH /v9/projects/{id}` com `ssoProtection: null`), pois bloqueava qualquer
   acesso público à API.

4. **Bug no `/api/_diag`** — import dinâmico com caminho errado
   (`'./workflows/index.mjs'` → `'../workflows/index.mjs'`) corrigido no commit `e2f8ac0`.

5. **Workflow GitHub Actions** (commit `686162d`)
   - Deploy agora roda com `working-directory: backend` (build Nitro real — antes
     subia um build estático vazio da raiz do repo).
   - `vercel promote` explícito após o deploy.
   - `API_URL` corrigida para `https://xau-ai-pro-api-apolopanda500.vercel.app`.

6. **Git desconectado do projeto `xau-ai-pro-api`**
   - (`DELETE /v9/projects/xau-ai-pro-api/link`) — o deploy dele é controlado pelo
     Actions; o projeto `xau-ai-pro` mantém o Git conectado (rootDirectory `backend`).

## Troubleshooting

- **Deployment fica STAGED (não promove):** verificar o check `deployment-alias`
  em `GET /v13/deployments/{id}` e promover manualmente:
  ```bash
  vercel promote https://<deployment-url> --yes
  ```
- **404/redirect para login:** conferir se o SSO Protection está desabilitado
  (Dashboard → Project → Settings → Deployment Protection).
- **"Invalid vercel.json":** nunca adicionar `vercel.json` com BOM nem chaves de
  `microfrontends` (não usamos Microfrontends neste projeto).
