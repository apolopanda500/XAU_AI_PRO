# ðŸš€ XAU_AI_PRO â€” IntegraÃ§Ã£o Vercel (100% configurada)

## Estado atual (verificado em produÃ§Ã£o)

- âœ… **Vercel CLI instalada** no Windows (global): `vercel --version` â†’ 59.6.2
- âœ… **Login autenticado**: conta `apolopanda500` (CLI user rickjax123-6204)
- âœ… **Projeto dedicado criado e em produÃ§Ã£o**: `xau-ai-pro-api`
  - URL fixa: https://xau-ai-pro-api.vercel.app
  - Ãšltimo deploy: Ready in ~1m, preset Nitro â†’ Build Output API da Vercel
- âœ… **Workflows durÃ¡veis reais rodando** (Workflow SDK v4.8.5 + workflow/nitro):
  - POST /api/workflows/market-data â†’ runId wrun_... (exemplo real gravado)
  - POST /api/workflows/reconcile â†’ runId wrun_... (exemplo real gravado)
- âœ… **GitHub integrado**: `vercel git connect` OK em github.com/apolopanda500/XAU_AI_PRO (main)
- âœ… **VariÃ¡veis de ambiente Production** configuradas:
  ENVIRONMENT, LOG_LEVEL, ASSET=XAUUSD, TIMEFRAME=M5, SENTRY_DSN(3 ambientes)
- âœ… **Sentry jÃ¡ estava ligado Ã  Vercel** (SENTRY_AUTH_TOKEN/DSN/ORG/PROJECT/OTLP/LOG_DRAIN)
- âœ… Projeto web original `xau-ai-pro` permaneceu INTACTO (protection+microfrontends prÃ³prios)

## Testes executados (produÃ§Ã£o)

| Rota | Resultado |
|---|---|
| GET / | JSON app online, etapa 17.3 |
| GET /api/health | ok:true |
| GET /api/_diag | diagnÃ³stico SDK (manter p/ ops) |
| POST /api/workflows/reconcile | 200 runId REAL |
| POST /api/workflows/market-data | 200 runId REAL |

## Estrutura criada/ajustada em backend/

- src/index.mjs â†’ app Express export default (serverless)
- workflows/index.mjs â†’ marketDataWorkflow, reconcileWorkflow + steps/hook-ready
- nitro.config.mjs â†’ modules:[workflow/nitro], preset vercel, entryFormat node
- reconcile.js â†’ BUG corrigido (constâ†’let streamF, ILLEGAL_REASSIGNMENT)
- server-desktop.cjs â†’ legado local renomeado (era server.js)
- api.mjs movido p/ src/index.mjs; scripts: dev/build/vercel-build/start

## PainÃ©is Ãºteis

- Deployments/API: https://vercel.com/apolopanda500/xau-ai-pro-api/deployments
- Workflows runs: https://vercel.com/apolopanda500/xau-ai-pro (Observabilityâ†’Workflows do projeto API)
- App web atual: https://vercel.com/apolopanda500/xau-ai-pro
- CLI inspeÃ§Ã£o local: cd backend; npx workflow inspect runs | npx workflow web

## CI/CD

1. **Auto-deploy Git (ativo)**: Ajuste Ãºnico no dashboard â†’ Project xau-ai-pro-api â†’ Settings â†’ General â†’ Root Directory = `backend` â†’ Save. AÃ­ cada push main redeploya.
2. **Alternativa GitHub Actions**: usar .github/workflows/deploy.yml jÃ¡ preparado; criar secrets VERCEL_TOKEN (+ VERCEL_ORG_ID e VERCEL_PROJECT_ID como Secrets).

## Dev local

cd backend
npm install
npm run dev   # server-desktop.cjs porta 3001 (Socket.IO etc.)
npm run build # nitro build (.vercel/output)

## PrÃ³ximos passos sugeridos

- Consumir hooks/durable events + Vercel Cron chamando endpoints
- Migrar telemetria MT5 p/ blob/API (serverless sem FS local)
- Conectar Sentry releases nos builds Nitro
