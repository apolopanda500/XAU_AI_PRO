const express = require('express');
const cors = require('cors');
const http = require('http');
const socketIo = require('socket.io');
const fs = require('fs');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, { cors: { origin: "*", methods: ["GET","POST"] } });
const PORT = process.env.PORT || 3001;

const DATA_DIR = 'C:/Users/Micro/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Files/Data';

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
  } catch (e) { return { source: f, events: [] }; }
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
  } catch (e) { return { estado: 'ERROR', motivo: 'json invalido', file: f }; }
}

// ---------- 17.3: ESTADO UNIFICADO (7 estados) ----------
// HEALTHY / WARNING / DEGRADED / SAFE / RECOVERY / ERROR / OFFLINE
function unifiedState(events, ai) {
  const counts = {};
  events.forEach(e => { const t = e.Event; if (t) counts[t] = (counts[t] || 0) + 1; });

  // OFFLINE: sem eventos recentes (< 5min)
  let newest = 0;
  events.forEach(e => {
    const m = /^(\d{4})\.(\d{2})\.(\d{2}) (\d{2}):(\d{2}):(\d{2})/.exec(e.Time || '');
    if (m) {
      const t = new Date(+m[1], +m[2]-1, +m[3], +m[4], +m[5], +m[6]).getTime();
      if (t > newest) newest = t;
    }
  });
  const recentMs = Math.max(0, Date.now() - newest);
  if (!events.length || recentMs > 300000) {
    return { estado: 'OFFLINE', source: 'sem eventos recentes', recent_sec: Math.round(recentMs/1000) };
  }

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

app.use(cors());
app.use(express.json());

app.get('/', (req, res) => res.json({ app: 'XAU_AI_PRO Backend', status: 'online', version: '1.2.0-RC1', etapa: '17.3' }));

app.get('/api/health', (req, res) => {
  const { source } = readEvents(1);
  res.json({ ok: true, uptime_sec: Math.round(process.uptime()), stream_ok: fs.existsSync(source), source, ts: new Date().toISOString() });
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

io.on('connection', (socket) => {
  const push = () => {
    const { events } = readEvents(100);
    const ai = aiState();
    const st = unifiedState(events, ai);
    socket.emit('system_state', { ts: new Date().toISOString(), estado: st.estado, razoes: st.reasons||[], ai, dominios: buildDomains(events) });
  };
  push();
  const iv = setInterval(push, 3000);
  socket.on('disconnect', () => clearInterval(iv));
});

server.listen(PORT, () => {
  console.log(`XAU_AI_PRO Backend ETAPA 17.3 rodando na porta ${PORT}`);
  console.log(`Event stream: ${eventsFile()}`);
});
app.get('/api/reconcile', (req, res) => { const { reconcile } = require('./reconcile'); res.json(reconcile()); });

const { financialSummary } = require('./financial');
app.get('/api/financial', (req,res)=>res.json(financialSummary()));

