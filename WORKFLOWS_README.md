# 🚀 XAU_AI_PRO — Integração Vercel (100% configurada)

## Estado atual (verificado em produção)

- ✅ **Vercel CLI instalada** no Windows (global): `vercel --version` → 59.6.2
- ✅ **Login autenticado**: conta `apolopanda500` (CLI user rickjax123-6204)
- ✅ **Projeto dedicado criado e em produção**: `xau-ai-pro-api`
  - URL fixa: https://xau-ai-pro-api.vercel.app
  - Último deploy: Ready in ~1m, preset Nitro → Build Output API da Vercel
- ✅ **Workflows duráveis reais rodando** (Workflow SDK v4.8.5 + workflow/nitro):
  - POST /api/workflows/market-data → runId wrun_... (exemplo real gravado)
  - POST /api/workflows/reconcile → runId wrun_... (exemplo real gravado)
- ✅ **GitHub integrado**: `vercel git connect` OK em github.com/apolopanda500/XAU_AI_PRO (main)
- ✅ **Variáveis de ambiente Production** configuradas:
  ENVIRONMENT, LOG_LEVEL, ASSET=XAUUSD, TIMEFRAME=M5, SENTRY_DSN(3 ambientes)
- ✅ **Sentry já estava ligado à Vercel** (SENTRY_AUTH_TOKEN/DSN/ORG/PROJECT/OTLP/LOG_DRAIN)
- ✅ Projeto web original `xau-ai-pro` permaneceu INTACTO (protection+microfrontends próprios)

## Testes executados (produção)

| Rota | Resultado |
|---|---|
| GET / | JSON app online, etapa 17.3 |
| GET /api/health | ok:true |
| GET /api/_diag | diagnóstico SDK (manter p/ ops) |
| POST /api/workflows/reconcile | 200 runId REAL |
| POST /api/workflows/market-data | 200 runId REAL |

## Estrutura criada/ajustada em backend/

- src/index.mjs → app Express export default (serverless)
- workflows/index.mjs → marketDataWorkflow, reconcileWorkflow + steps/hook-ready
- nitro.config.mjs → modules:[workflow/nitro], preset vercel, entryFormat node
- reconcile.js → BUG corrigido (const→let streamF, ILLEGAL_REASSIGNMENT)
- server-desktop.cjs → legado local renomeado (era server.js)
- api.mjs movido p/ src/index.mjs; scripts: dev/build/vercel-build/start

## Painéis úteis

- Deployments/API: https://vercel.com/apolopanda500/xau-ai-pro-api/deployments
- Workflows runs: https://vercel.com/apolopanda500/xau-ai-pro (Observability→Workflows do projeto API)
- App web atual: https://vercel.com/apolopanda500/xau-ai-pro
- CLI inspeção local: cd backend; npx workflow inspect runs | npx workflow web

## CI/CD

1. **Auto-deploy Git (ativo)**: Ajuste único no dashboard → Project xau-ai-pro-api → Settings → General → Root Directory = `backend` → Save. Aí cada push main redeploya.
2. **Alternativa GitHub Actions**: usar .github/workflows/deploy.yml já preparado; criar secrets VERCEL_TOKEN (+org/project IDs: prj_RApeFNVlnOGYxtYcRDqaSUTIJD1G / team_m6XXhz0AuVtzK0zxtv96h03a).

## Dev local

cd backend
npm install
npm run dev   # server-desktop.cjs porta 3001 (Socket.IO etc.)
npm run build # nitro build (.vercel/output)

## Próximos passos sugeridos

- Consumir hooks/durable events + Vercel Cron chamando endpoints
- Migrar telemetria MT5 p/ blob/API (serverless sem FS local)
- Conectar Sentry releases nos builds Nitro
