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
   - Causa: `vercel.json` legado com BOM e configuração inválida de `microfrontends`
     (removido no commit `4b852c2`).
   - O alias de produção ficou órfão de um deployment deletado, fazendo o check
     `deployment-alias` falhar e os deployments ficarem **STAGED**.
   - Solução: promoção manual (`vercel promote`) — recria o alias limpo.

2. **SSO Protection ativo** — desabilitado via API nos dois projetos
   (`PATCH /v9/projects/{id}` com `ssoProtection: null`), pois bloqueava qualquer
   acesso público à API.

3. **Bug no `/api/_diag`** — import dinâmico com caminho errado
   (`'./workflows/index.mjs'` → `'../workflows/index.mjs'`) corrigido no commit `e2f8ac0`.

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
