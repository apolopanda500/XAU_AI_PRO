const express = require('express');
const rateLimit = require('express-rate-limit');
const cors = require('cors');
const http = require('http');
const socketIo = require('socket.io');
const fs = require('fs');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '.env') });
require('dotenv').config({ path: path.join(__dirname, '.env.local') });
// Tambem carrega .env da RAIZ do projeto (onde ficam SENTRY_DSN, SLACK, GITHUB)
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });
require('dotenv').config({ path: path.join(__dirname, '..', '.env.local') });
require('dotenv').config({ path: path.join(__dirname, '..', '.env.integrations') });
const integrations = require('./integrations');
const { resolveDataDir } = require('./paths.cjs');

const app = express();
const server = http.createServer(app);
const HOST = process.env.HOST || '127.0.0.1';
const ALLOWED_ORIGINS = (process.env.XAU_AI_PRO_ALLOWED_ORIGINS || 'http://127.0.0.1,http://localhost')
  .split(',').map(value => value.trim()).filter(Boolean);
const corsOptions = { origin: ALLOWED_ORIGINS, methods: ['GET', 'POST', 'DELETE'] };
const io = socketIo(server, { cors: corsOptions });
const mt5Room = io.of('/ws/mt5');
const eaRoom = io.of('/ws/ea');
const mobileRoom = io.of('/ws/mobile');
const mobileDevices = new Map();
const mobileSessions = new Map();
const GATEWAY_URL = process.env.XAU_GATEWAY_URL || 'http://127.0.0.1:9001';
async function relayGateway(pathname) {
  const response = await fetch(`${GATEWAY_URL}${pathname}`, { signal: AbortSignal.timeout(4000) });
  if (!response.ok) throw new Error(`Gateway HTTP ${response.status}`);
  return response.json();
}
mt5Room.on('connection', socket => { socket.emit('stream:ready', { channel: 'mt5', source: 'mt5_gateway' }); });
eaRoom.on('connection', socket => { socket.emit('stream:ready', { channel: 'ea', source: 'mt5_gateway' }); });
mobileRoom.on('connection', socket => { socket.emit('stream:ready', { channel: 'mobile', source: 'desktop_relay' }); });
setInterval(async () => { try { const data = await relayGateway('/api/status'); mt5Room.emit('status', data); eaRoom.emit('heartbeat', data.ea_heartbeat ?? null); } catch (error) { const event = { online: false, error: error.message, ts: new Date().toISOString() }; mt5Room.emit('stream:error', event); eaRoom.emit('stream:error', event); } }, 5000);
const PORT = process.env.PORT || 3001;
// 17.4+: Sentry ativo se DSN configurado e SDK instalado (nunca quebra o boot)
const sentryClient = integrations.initSentry();
if (sentryClient) console.log('[integrations] Sentry ativo com DSN');

const DATA_DIR = resolveDataDir();

function eventsFile() {
  const p = path.join(DATA_DIR, 'forward_test_events.csv');
  return fs.existsSync(p) ? p : path.join(__dirname, '..', 'MQL5', 'Files', 'Data', 'forward_test_events.csv');
}

function readEvents(limit = 200) {
  const f = eventsFile();
  if (!fs.existsSync(f)) return { source: f, events: [] };
  try {
    const raw = fs.readFileSync(f, 'utf16le').replace(/^\uFEFF/, '');
    const lines = raw.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    if (!lines.length) return { source: f, events: [] };
    const header = lines[0];
    const delim = header.includes('\t') && !header.includes(',') ? '\t' : ',';
    const cols = header.split(delim).map(h => h.trim());
    const events = lines.slice(1).map(ln => {
      const p2 = ln.split(delim).map(x => x.trim());
      const o = {};
      cols.forEach((c, i) => o[c] = p2[i] !== undefined ? p2[i] : '');
      return o;
    }).filter(e => e.Event);
    return { source: f, events: events.slice(-limit) };
  } catch { return { source: f, events: [] }; }
}

// ---------- 17.1: Estado IA a partir do prediction JSON (staleness) ----------
function aiState() {
  const base = path.join(DATA_DIR, 'prediction_XAUUSD.json');
  const local = path.join(__dirname, '..', 'MQL5', 'Files', 'Data', 'prediction_XAUUSD.json');
  const f = fs.existsSync(base) ? base : local;
  if (!fs.existsSync(f)) return { estado: 'UNAVAILABLE', motivo: 'sem prediction', file: f };
  try {
    const j = JSON.parse(fs.readFileSync(f, 'utf8'));
    const ts = j.timestamp || j.timestamp_utc || '';
    let ageMs = Infinity;
    const ageSec = j.age_sec;
    if (ts) {
      const t = new Date(ts).getTime();
      if (!isNaN(t)) ageMs = Date.now() - t;
    }
    const ageSecNum = Number.isFinite(ageMs) ? Math.round(ageMs / 1000) : (ageSec || 1e9);
    let estado = 'READY';
    if (j.signal === 'UNAVAILABLE') estado = 'UNAVAILABLE';
    else if (ageSecNum > 300) estado = 'STALE';          // >5min obsoleto
    else if (j.signal === 'ERROR') estado = 'ERROR';
    else if (!j.timestamp && !j.timestamp_utc) estado = 'STALE';
    return { estado, signal: j.signal || null, confidence: j.confidence ?? null, age_sec: ageSecNum, timestamp: ts, file: f };
  } catch { return { estado: 'ERROR', motivo: 'json invalido', file: f }; }
}

// ---------- 17.3: ESTADO UNIFICADO (7 estados) ----------
// HEALTHY / WARNING / DEGRADED / SAFE / RECOVERY / ERROR / OFFLINE
function unifiedState(events, ai) {
  // Janela de recencia: considera apenas eventos dos ultimos 10 min
  // para nao propagar falhas historicas como estado atual (correcao 17.5)
  const WINDOW_MS = 600000;
  const eventsWithTime = [];
  let newest = 0;
  events.forEach(e => {
    const m = /^(\d{4})\.(\d{2})\.(\d{2}) (\d{2}):(\d{2}):(\d{2})/.exec(e.Time || '');
    if (m) {
      const t = new Date(+m[1], +m[2]-1, +m[3], +m[4], +m[5], +m[6]).getTime();
      eventsWithTime.push({ t, e });
      if (t > newest) newest = t;
    }
  });
  const recentMs = Math.max(0, Date.now() - newest);
  if (!eventsWithTime.length || recentMs > 300000) {
    return { estado: 'OFFLINE', source: 'sem eventos recentes', recent_sec: Math.round(recentMs/1000) };
  }
  const windowEvents = eventsWithTime.filter(x => newest - x.t <= WINDOW_MS).map(x => x.e);
  const counts = {};
  windowEvents.forEach(e => { const t = e.Event; if (t) counts[t] = (counts[t] || 0) + 1; });

  if (counts['HEALTH_FAILURE'] || counts['SYSTEM_ERROR'] || counts['BROKER_ERROR'] || counts['DATABASE_ERROR'])
    return { estado: 'ERROR', reasons: ['health_failure/system/broker/db'] };
  if (counts['CIRCUIT_BREAKER'] || counts['SAFE_MODE'])
    return { estado: 'SAFE', reasons: ['circuit_breaker/safe_mode'] };
  if (ai.estado === 'UNAVAILABLE' && (counts['PYTHON_ERROR'] || counts['AI_ERROR']))
    return { estado: 'DEGRADED', reasons: ['ia_unavailable'] };
  if (counts['RECOVERY']) return { estado: 'RECOVERY', reasons: ['recovery'] };
  if (ai.estado === 'STALE' || ai.estado === 'UNAVAILABLE')
    return { estado: 'DEGRADED', reasons: ['ia_stale/unavailable'] };
  if (counts['HEALTH_WARNING'] || counts['RISK_BLOCK'] || counts['NEWS_BLOCK'] || counts['AI_BLOCK'])
    return { estado: 'WARNING', reasons: ['warning/block'] };
  return { estado: 'HEALTHY', reasons: ['ok'] };
}

function buildDomains(events) {
  const counts = {};
  events.forEach(e => { const t = e.Event||''; if(t) counts[t]=(counts[t]||0)+1; });
  return {
    counts,
    ai_raw: aiState(),
    trading: { opens: counts['TRADE_OPEN']||0, closes: counts['TRADE_CLOSE']||0,
      aprovados: counts['TRADE_APPROVED']||0, rejeitados: counts['TRADE_REJECTED']||0 },
    positions: { abertas: Math.max(0,(counts['TRADE_OPEN']||0)-(counts['TRADE_CLOSE']||0)) },
    risk: { blocks: counts['RISK_BLOCK']||0, news: counts['NEWS_BLOCK']||0,
      safe: counts['SAFE_MODE']||0, recovery: counts['RECOVERY']||0 },
    execution: { aprovados: counts['TRADE_APPROVED']||0, rejeitados: counts['TRADE_REJECTED']||0 },
    telemetry: { total: events.length, por_tipo: counts },
    alerts: events.filter(e => ['WARN','ERROR','CRITICAL'].includes(e.Severity)).slice(-20)
  };
}

app.use(cors(corsOptions));
app.use(express.json());

app.post('/api/mobile/pair', (req, res) => {
  const deviceId = String(req.body?.device_id || '').trim();
  const name = String(req.body?.name || 'dispositivo').trim().slice(0, 80);
  if (!deviceId) return res.status(400).json({ ok: false, error: 'device_id obrigatorio' });
  const pairToken = require('crypto').randomBytes(24).toString('hex');
  const device = { device_id: deviceId, name, paired_at: new Date().toISOString(), last_seen: new Date().toISOString(), status: 'paired' };
  mobileDevices.set(deviceId, { ...device, pair_token: pairToken });
  return res.status(201).json({ ok: true, device, pair_token: pairToken, source: 'desktop_relay' });
});
app.post('/api/mobile/unpair', (req, res) => {
  const deviceId = String(req.body?.device_id || '').trim();
  const removed = mobileDevices.delete(deviceId);
  for (const [id, session] of mobileSessions) if (session.device_id === deviceId) mobileSessions.delete(id);
  res.json({ ok: removed, device_id: deviceId, status: removed ? 'unpaired' : 'not_found' });
});
app.get('/api/mobile/devices', (req, res) => res.json({ ok: true, devices: [...mobileDevices.values()].map(({ pair_token: _pairToken, ...device }) => device), count: mobileDevices.size, source: 'desktop_relay' }));
app.post('/api/mobile/session', (req, res) => {
  const deviceId = String(req.body?.device_id || '').trim();
  const token = String(req.body?.pair_token || '').trim();
  const device = mobileDevices.get(deviceId);
  if (!device || token !== device.pair_token) return res.status(403).json({ ok: false, error: 'pareamento invalido' });
  const sessionId = require('crypto').randomUUID();
  mobileSessions.set(sessionId, { session_id: sessionId, device_id: deviceId, created_at: new Date().toISOString(), expires_at: new Date(Date.now() + 86400000).toISOString() });
  device.last_seen = new Date().toISOString();
  res.status(201).json({ ok: true, session: mobileSessions.get(sessionId), channel: '/ws/mobile' });
});
app.delete('/api/mobile/session', (req, res) => { const id = String(req.body?.session_id || req.headers['x-session-id'] || '').trim(); res.json({ ok: mobileSessions.delete(id), session_id: id }); });

// Rate limiting anti-DoS (CodeQL js/missing-rate-limiting): 100 req / 15 min por IP
const apiLimiter = rateLimit({ windowMs: 15 * 60 * 1000, max: 100 });
app.use('/api', apiLimiter);

app.get('/', (req, res) => res.json({ app: 'XAU_AI_PRO Backend', status: 'online', version: '1.2.0-RC1', etapa: '17.3' }));

app.get('/api/health', (req, res) => {
  const { source } = readEvents(1);
  res.json({ ok: true, uptime_sec: Math.round(process.uptime()), stream_ok: fs.existsSync(source), source, ts: new Date().toISOString() });
});
app.get('/api/sync/status', async (req, res) => {
  try { const response = await fetch(`${GATEWAY_URL}/api/sync/status`); res.status(response.status).json(await response.json()); }
  catch (e) { res.status(503).json({ ok: false, error: e.message, gateway: 'offline' }); }
});
app.get('/api/stream/status', (req, res) => res.json({ ok: true, relay: 'online', gateway: GATEWAY_URL, channels: ['/ws/mt5', '/ws/ea'], transport: 'socket.io', fallback: 'http' }));

async function forwardJson(pathname, method, body) {
  const response = await fetch(`${GATEWAY_URL}${pathname}`, { method, headers: { 'content-type': 'application/json' }, body: method === 'GET' ? undefined : JSON.stringify(body || {}) });
  return { status: response.status, data: await response.json() };
}
const gatewayReadRoutes = ['/api/demo/positions', '/api/demo/orders', '/api/demo/execution-status', '/api/demo/last-command', '/api/ea/status', '/api/config', '/api/config/themes', '/api/config/languages', '/api/update/check', '/api/audit', '/api/audit/commands', '/api/execution/history', '/api/errors', '/api/sync/status', '/api/positions', '/api/orders', '/api/account', '/api/history'];
gatewayReadRoutes.forEach(pathname => app.get(pathname, async (req, res) => { try { const out = await forwardJson(pathname, 'GET'); res.status(out.status).json(out.data); } catch (e) { res.status(503).json({ ok: false, error: e.message, gateway: 'offline' }); } }));
const gatewayCommandRoutes = ['/api/demo/close-all', '/api/demo/modify-position', '/api/demo/breakeven', '/api/demo/trailing', '/api/demo/partial-close', '/api/demo/set-protection', '/api/demo/remove-protection', '/api/demo/close-symbol', '/api/demo/cancel-order', '/api/demo/cancel-all-orders', '/api/demo/order', '/api/demo/close', '/api/ea/start', '/api/ea/stop', '/api/ea/pause', '/api/ea/resume', '/api/ea/set-symbol', '/api/ea/set-mode', '/api/ea/set-timeframe', '/api/ea/set-autotrading'];
gatewayCommandRoutes.forEach(pathname => app.post(pathname, async (req, res) => { try { const out = await forwardJson(pathname, 'POST', req.body); res.status(out.status).json(out.data); } catch (e) { res.status(503).json({ ok: false, error: e.message, gateway: 'offline' }); } }));

// 17.4+: status REAL das integracoes (valida GitHub via API, verifica SDK Sentry)
app.get('/api/integrations', async (req, res) => {
  try {
    const st = await integrations.getIntegrationsStatus();
    res.json(st);
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

// 17.5: envia um teste real no canal do Slack (retorna ok/erro do webhook)
app.post('/api/integrations/slack/test', async (req, res) => {
  const result = await integrations.sendSlackTest();
  res.json(result);
});
// 17.6: teste do inbound webhook do Kilo (retorna ok/status do servico de captura)
app.post('/api/integrations/kilo/test', async (req, res) => {
  const result = await integrations.sendKiloTest();
  res.json(result);
});
app.get('/api/events', (req, res) => res.json(readEvents(parseInt(req.query.limit) || 100)));
app.get('/api/events/latest', (req, res) => { const { source, events } = readEvents(1); res.json({ source, evento: events[events.length-1] || null, ts: new Date().toISOString() }); });

// 17.3: endpoint de estado unificado
app.get('/api/system', (req, res) => {
  const { source, events } = readEvents(200);
  const ai = aiState();
  const st = unifiedState(events, ai);
  res.json({ source, estado: st.estado, razones: st.reasons || [], recent_sec: st.recent_sec, ai, contagem: buildDomains(events).counts, total_eventos: events.length, ts: new Date().toISOString() });
});

// 17.1: estado IA dedicado
app.get('/api/ai', (req, res) => { const { events } = readEvents(200); res.json({ ...aiState(), eventos: events.filter(e=>['AI_PREDICTION','AI_BLOCK','AI_ERROR'].includes(e.Event)).slice(-20) }); });

app.get('/api/trading', (req, res) => res.json(buildDomains(readEvents(500).events).trading));
app.get('/api/positions', (req, res) => res.json(buildDomains(readEvents(500).events).positions));
app.get('/api/risk', (req, res) => res.json(buildDomains(readEvents(500).events).risk));
app.get('/api/execution', (req, res) => res.json(buildDomains(readEvents(500).events).execution));
app.get('/api/telemetry', (req, res) => res.json(buildDomains(readEvents(500).events).telemetry));
app.get('/api/alerts', (req, res) => res.json(buildDomains(readEvents(500).events).alerts));

// Conector suportado atualmente: MT5 local. Nenhuma corretora ficticia e nenhum REAL.
app.get('/api/brokers', async (req, res) => {
  try { const health = await relayGateway('/api/health'); res.json({ ok: true, brokers: [{ id: 'mt5', label: 'MetaTrader 5 local', connected: !!health.ok, modes: ['DEMO'], real_enabled: false }] }); }
  catch (e) { res.json({ ok: true, brokers: [{ id: 'mt5', label: 'MetaTrader 5 local', connected: false, modes: ['DEMO'], real_enabled: false }], error: e.message }); }
});
app.post('/api/brokers/connect', async (req, res) => { try { res.json({ ok: true, broker: 'mt5', connected: !!(await relayGateway('/api/health')).ok, mode: 'DEMO' }); } catch (e) { res.status(503).json({ ok: false, error: e.message }); } });
app.post('/api/brokers/disconnect', (req, res) => res.json({ ok: false, broker: 'mt5', error: 'MT5 e gerenciado pela sessao do terminal; feche-o no proprio MT5 para desconectar.' }));
app.get('/api/brokers/accounts', async (req, res) => { try { const data = await relayGateway('/api/account'); res.json({ ok: true, broker: 'mt5', accounts: [data.account || data], real_enabled: false }); } catch (e) { res.status(503).json({ ok: false, error: e.message }); } });
app.get('/api/brokers/:broker/positions', async (req, res) => { if (req.params.broker !== 'mt5') return res.status(404).json({ ok: false, error: 'broker nao suportado' }); try { res.json(await relayGateway('/api/demo/positions')); } catch (e) { res.status(503).json({ ok: false, error: e.message }); } });
app.post('/api/brokers/:broker/order', async (req, res) => { if (req.params.broker !== 'mt5') return res.status(404).json({ ok: false, error: 'broker nao suportado' }); if (req.body?.mode !== 'DEMO' || req.body?.confirm_demo !== true) return res.status(403).json({ ok: false, error: 'somente ordem DEMO com confirm_demo=true' }); try { const response = await fetch(`${GATEWAY_URL}/api/demo/order`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(req.body) }); res.status(response.status).json(await response.json()); } catch (e) { res.status(503).json({ ok: false, error: e.message }); } });
app.post('/api/brokers/:broker/close', async (req, res) => { if (req.params.broker !== 'mt5') return res.status(404).json({ ok: false, error: 'broker nao suportado' }); if (req.body?.confirm_demo !== true) return res.status(403).json({ ok: false, error: 'confirm_demo=true obrigatorio' }); try { const response = await fetch(`${GATEWAY_URL}/api/demo/close`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(req.body) }); res.status(response.status).json(await response.json()); } catch (e) { res.status(503).json({ ok: false, error: e.message }); } });

io.on('connection', (socket) => {
  const push = () => {
    const { events } = readEvents(100);
    const ai = aiState();
    const st = unifiedState(events, ai);
    socket.emit('system_state', { ts: new Date().toISOString(), estado: st.estado, razoes: st.reasons||[], ai, dominios: buildDomains(events) });
    // 17.5: alerta Slack na transicao para estado critico (uma vez por estado)
    try {
      const critical = ['ERROR', 'OFFLINE', 'SAFE', 'DEGRADED'];
      if (critical.includes(st.estado) && global.__lastAlertedState !== st.estado && integrations.slackConfigured()) {
        global.__lastAlertedState = st.estado;
        const razoes = (st.reasons || []).join(', ') || 'sem detalhe';
        integrations.sendSlack(
          `:warning: XAU AI PRO entrou em estado *${st.estado}* (${razoes}) - ${new Date().toISOString()}`
        ).then(r => {
          if (!r.ok) console.error('[slack] falha ao notificar estado critico:', r.error || r.status);
        });
      } else if (!critical.includes(st.estado)) {
        global.__lastAlertedState = st.estado;
      }
    } catch (e) {
      console.error('[slack] erro no alerta automatico:', e.message);
    }
  };
  push();
  // Estado operacional nao precisa de polling agressivo; reduzimos CPU/aquecimento
  // sem alterar leituras sob demanda, ordens ou dados reais do MT5.
  const iv = setInterval(push, 10000);
  socket.on('disconnect', () => clearInterval(iv));
});

server.listen(PORT, HOST, () => {
  console.log(`XAU_AI_PRO Backend ETAPA 17.3 rodando em ${HOST}:${PORT}`);
  console.log(`Event stream: ${eventsFile()}`);
});
app.get('/api/reconcile', (req, res) => { const { reconcile } = require('./reconcile'); res.json(reconcile()); });

const { financialSummary } = require('./financial');
app.get('/api/financial', (req,res)=>res.json(financialSummary()));

