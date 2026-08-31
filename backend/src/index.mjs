/**
 * Entry point para Vercel - exporta a app Express (ESM)
 * Configurado para Vercel Functions com Workflow SDK.
 *
 * Obs: Em desenvolvimento local, use `npm run dev` (server.js).
 */
import express from 'express';
import cors from 'cors';
import { start } from 'workflow/api';
import { marketDataWorkflow, reconcileWorkflow } from '../workflows/index.mjs';
import { track } from '@vercel/analytics/server';

const app = express();
app.use(cors());
app.use(express.json());

// ---------- Rotas de saÃºde ----------
app.get('/', async (req, res) => {
  // Track homepage visits with Vercel Analytics
  try {
    await track('api_home_visit', {}, { request: req });
  } catch (e) {
    // Silently fail analytics to not affect API response
    console.error('Analytics tracking error:', e.message);
  }
  
  // Check if client prefers HTML (browser access)
  const acceptsHtml = req.headers.accept?.includes('text/html');
  
  if (acceptsHtml) {
    // Serve HTML status page with Speed Insights
    res.setHeader('Content-Type', 'text/html');
    res.send(`
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>XAU AI PRO Backend - Status</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
    h1 { color: #0070f3; }
    .status { background: #f0f0f0; padding: 20px; border-radius: 8px; margin: 20px 0; }
    .online { color: #0070f0; font-weight: bold; }
    ul { line-height: 1.8; }
  </style>
</head>
<body>
  <h1>XAU AI PRO Backend</h1>
  <div class="status">
    <p><strong>Status:</strong> <span class="online">Online</span></p>
    <p><strong>Version:</strong> 1.2.0-RC1</p>
    <p><strong>Stage:</strong> 17.3</p>
  </div>
  <h2>Available Workflows</h2>
  <ul>
    <li>Market Data Workflow</li>
    <li>Reconcile Workflow</li>
  </ul>
  <h2>API Endpoints</h2>
  <ul>
    <li><code>GET /api/health</code> - Health check</li>
    <li><code>POST /api/workflows/market-data</code> - Start market data workflow</li>
    <li><code>POST /api/workflows/reconcile</code> - Start reconcile workflow</li>
    <li><code>GET /api/workflows/:runId</code> - Check workflow run status</li>
  </ul>
  <script type="module">
    import { injectSpeedInsights } from 'https://esm.sh/@vercel/speed-insights@2.0.0';
    injectSpeedInsights();
  </script>
</body>
</html>
    `);
  } else {
    // Return JSON for API clients
    res.json({
      app: 'XAU_AI_PRO Backend',
      status: 'online',
      version: '1.2.0-RC1',
      etapa: '17.3',
      workflows_available: ['marketDataWorkflow', 'reconcileWorkflow'],
    });
  }
});

app.get('/api/health', async (req, res) => {
  // Track health check requests
  try {
    await track('api_health_check', {}, { request: req });
  } catch (e) {
    console.error('Analytics tracking error:', e.message);
  }
  
  res.json({ ok: true, ts: new Date().toISOString(), source: 'vercel' });
});


// ---------- DIAGNÃ“STICO TEMPORÃRIO DO WORKFLOW SDK ----------
// Retorna o erro real do start() em JSON para debug no deploy serverless.
app.get('/api/_diag', async (req, res) => {
  const info = {
    node: process.version,
    node_env: process.env.NODE_ENV || null,
    region: process.env.VERCEL_REGION || null,
  };
  try {
    const api = await import('workflow/api');
    info.api_keys = Object.keys(api);
    const wf = await import('../workflows/index.mjs');
    info.wf_keys = Object.keys(wf);
    try {
      const run = await api.start(wf.marketDataWorkflow, [], { name: 'diag' });
      info.start_ok = true;
      info.runId = run?.runId ?? String(run);
    } catch (e2) {
      info.start_ok = false;
      info.start_error = e2.message;
      info.start_stack = (e2.stack || '').split('\n').slice(0, 6);
    }
  } catch (e1) {
    info.import_error = e1.message;
    info.import_stack = (e1.stack || '').split('\n').slice(0, 6);
  }
  res.json(info);
});

// ---------- Endpoint para iniciar workflow de dados de mercado ----------
// POST /api/workflows/market-data
// Inicia o marketDataWorkflow (busca dados e gera previsÃµes)
app.post('/api/workflows/market-data', async (req, res) => {
  try {
    // Track workflow initiation
    await track('workflow_market_data_started', {}, { request: req }).catch(e => 
      console.error('Analytics tracking error:', e.message)
    );
    
    const run = await start(marketDataWorkflow, [], {
      name: 'market-data-sync',
    });
    res.json({ runId: run.runId, status: 'started' });
  } catch (e) {
    // Track workflow errors
    await track('workflow_market_data_error', { error: e.message }, { request: req }).catch(() => {});
    res.status(500).json({ error: e.message });
  }
});

// ---------- Endpoint para iniciar workflow de reconciliaÃ§Ã£o ----------
// POST /api/workflows/reconcile
// Body: { "symbol": "XAUUSD" }
app.post('/api/workflows/reconcile', async (req, res) => {
  try {
    const { symbol } = req.body || {};
    
    // Track workflow initiation with symbol info
    await track('workflow_reconcile_started', { symbol: symbol || 'XAUUSD' }, { request: req }).catch(e => 
      console.error('Analytics tracking error:', e.message)
    );
    
    const run = await start(reconcileWorkflow, [symbol || 'XAUUSD'], {
      name: 'reconcile-trade',
    });
    res.json({ runId: run.runId, status: 'started' });
  } catch (e) {
    // Track workflow errors
    await track('workflow_reconcile_error', { error: e.message }, { request: req }).catch(() => {});
    res.status(500).json({ error: e.message });
  }
});

// ---------- Endpoint de inspeÃ§Ã£o de runs ----------
// GET /api/workflows/:runId
app.get('/api/workflows/:runId', async (req, res) => {
  res.json({
    runId: req.params.runId,
    status: 'Use `npx workflow inspect runs` or Vercel dashboard for details.',
    dashboard: 'https://vercel.com/apolopanda500/~/workflows',
  });
});

// Exporta a app para Vercel Functions
export default app;
