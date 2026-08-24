/**
 * XAU AI PRO - Backend Observabilidade (ETAPA 16.4)
 * Consome o Event Stream real do EA (forward_test_events.csv).
 * API unica: health, events, trading, positions, ai, risk, execution,
 * telemetry, alerts + WebSocket. SEM alteracao no EA.
 */
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

const TERMINAL_DATA = path.join(
  process.env.APPDATA || '',
  'MetaQuotes','Terminal',
  'D0E8209F77C8CF37AD8BF550E51FF075','MQL5','Files','Data','forward_test_events.csv'
);
const LOCAL_DATA = path.join(__dirname, '..', 'MQL5','Files','Data','forward_test_events.csv');

function eventsFile() {
  try { if (fs.existsSync(TERMINAL_DATA)) return TERMINAL_DATA; } catch(e){}
  return LOCAL_DATA;
}

// ---------- Event Ingestion (CSV UTF-16, tolerante ','/'\t') ----------
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
      const p = ln.split(delim).map(x => x.trim());
      const o = {};
      cols.forEach((c, i) => o[c] = p[i] !== undefined ? p[i] : '');
      return o;
    }).filter(e => e.Event); // ignora linhas corrompidas
    return { source: f, events: events.slice(-limit) };
  } catch (e) {
    return { source: f, events: [], error: String(e) };
  }
}

// ---------- Derivacao de estado (15.6.5) ----------
function deriveState(events) {
  const counts = {};
  events.forEach(e => { const t = e.Event || ''; if(t) counts[t] = (counts[t]||0)+1; });
  let estado = 'HEALTHY';
  if (counts['HEALTH_FAILURE']) estado = 'FAILURE';
  else if (counts['CIRCUIT_BREAKER'] || counts['SAFE_MODE']) estado = 'SAFE';
  else if (counts['SYSTEM_ERROR']||counts['BROKER_ERROR']||counts['PYTHON_ERROR']||counts['DATABASE_ERROR']) estado = 'ERROR';
  else if (counts['RECOVERY']) estado = 'RECOVERY';
  else if (counts['HEALTH_WARNING']||counts['RISK_BLOCK']||counts['NEWS_BLOCK']||counts['AI_BLOCK']) estado = 'WARNING';
  else if (counts['TRADE_OPEN']) estado = 'TRADING';
  return { estado, counts };
}

// ---------- Sub-agregacoes por dominio ----------
function byType(events, types) {
  return events.filter(e => types.includes(e.Event));
}
function lastOf(events, type) {
  for (let i = events.length-1; i >= 0; i--) if (events[i].Event === type) return events[i];
  return null;
}

function buildDomains(events) {
  const counts = {};
  events.forEach(e => { const t = e.Event||''; counts[t] = (counts[t]||0)+1; });
  const trades = byType(events, ['TRADE_OPEN','TRADE_CLOSE','TRADE_APPROVED','TRADE_REJECTED']);
  const lastOpen = lastOf(events, 'TRADE_OPEN');
  const lastClose = lastOf(events, 'TRADE_CLOSE');
  const ai = byType(events, ['AI_PREDICTION','AI_BLOCK','AI_ERROR']);
  const risk = byType(events, ['RISK_BLOCK','SAFE_MODE','RECOVERY','CIRCUIT_BREAKER','NEWS_BLOCK']);
  const exec = byType(events, ['TRADE_APPROVED','TRADE_REJECTED']);
  const alerts = events.filter(e => ['WARN','ERROR','CRITICAL'].includes(e.Severity));
  return {
    counts,
    trading: {
      trades_abertos: counts['TRADE_OPEN']||0,
      trades_fechados: counts['TRADE_CLOSE']||0,
      aprovados: counts['TRADE_APPROVED']||0,
      rejeitados: counts['TRADE_REJECTED']||0,
      ultimo_open: lastOpen,
      ultimo_close: lastClose,
      trades
    },
    positions: {
      abertas: (counts['TRADE_OPEN']||0) - (counts['TRADE_CLOSE']||0),
      abertas_bruto: Math.max(0, (counts['TRADE_OPEN']||0) - (counts['TRADE_CLOSE']||0)),
      ultima: lastOpen
    },
    ai: {
      predictions: counts['AI_PREDICTION']||0,
      blocks: counts['AI_BLOCK']||0,
      errors: counts['AI_ERROR']||0,
      ultima_prediction: lastOf(events, 'AI_PREDICTION'),
      ultimo_block: lastOf(events, 'AI_BLOCK'),
      eventos: ai
    },
    risk: {
      risk_blocks: counts['RISK_BLOCK']||0,
      news_blocks: counts['NEWS_BLOCK']||0,
      safe_mode: counts['SAFE_MODE']||0,
      recoveries: counts['RECOVERY']||0,
      circuit_breaker: counts['CIRCUIT_BREAKER']||0,
      eventos: risk
    },
    execution: {
      aprovados: counts['TRADE_APPROVED']||0,
      rejeitados: counts['TRADE_REJECTED']||0,
      taxa_aprovacao: ((counts['TRADE_APPROVED']||0) + (counts['TRADE_REJECTED']||0)) > 0
        ? Math.round((counts['TRADE_APPROVED']||0) * 100 / ((counts['TRADE_APPROVED']||0)+(counts['TRADE_REJECTED']||0))) : null,
      eventos: exec
    },
    telemetry: {
      total_eventos: events.length,
      por_tipo: counts,
      fontes: [...new Set(events.map(e=>e.Module).filter(Boolean))],
      heartbeat_estimado: (counts['SYSTEM_START']||0) + (counts['FORWARD_TEST_START']||0)
    },
    alerts: { total: alerts.length, eventos: alerts.slice(-20) }
  };
}

app.use(cors());
app.use(express.json());

app.get('/', (req, res) => { res.json({ app: 'XAU_AI_PRO Backend', status: 'online', version: '1.2.0-RC1', etapa: '16.4' }); });

// ---------- Contrato JSON 16.4 ----------
app.get('/api/health', (req, res) => {
  const { source } = readEvents(1);
  res.json({ ok: true, uptime_sec: Math.round(process.uptime()), stream_ok: fs.existsSync(source), source, ts: new Date().toISOString() });
});

app.get('/api/events', (req, res) => {
  const limit = parseInt(req.query.limit) || 100;
  res.json(readEvents(limit));
});

app.get('/api/events/latest', (req, res) => {
  const { source, events } = readEvents(1);
  res.json({ source, evento: events[events.length-1] || null, ts: new Date().toISOString() });
});

app.get('/api/system', (req, res) => {
  const { source, events } = readEvents(200);
  const st = deriveState(events);
  res.json({ source, estado: st.estado, contagem: st.counts, total_eventos: events.length, ts: new Date().toISOString() });
});

app.get('/api/trading', (req, res) => res.json(buildDomains(readEvents(500).events).trading));
app.get('/api/positions', (req, res) => res.json(buildDomains(readEvents(500).events).positions));
app.get('/api/ai', (req, res) => res.json(buildDomains(readEvents(500).events).ai));
app.get('/api/risk', (req, res) => res.json(buildDomains(readEvents(500).events).risk));
app.get('/api/execution', (req, res) => res.json(buildDomains(readEvents(500).events).execution));
app.get('/api/telemetry', (req, res) => res.json(buildDomains(readEvents(500).events).telemetry));
app.get('/api/alerts', (req, res) => res.json(buildDomains(readEvents(500).events).alerts));

// ---------- WebSocket (polling 5s - fs.watch no Windows e nao uniforme) ----------
io.on('connection', (socket) => {
  console.log('Dashboard conectado:', socket.id);
  const push = () => {
    const { events } = readEvents(100);
    const st = deriveState(events);
    const dom = buildDomains(events);
    socket.emit('system_state', { ts: new Date().toISOString(), estado: st.estado, contagem: st.counts, ultimo: events[events.length-1] || null, dominios: { trading: dom.trading, ai: dom.ai, risk: dom.risk, execution: dom.execution } });
  };
  push();
  const iv = setInterval(push, 5000);
  socket.on('disconnect', () => clearInterval(iv));
});

server.listen(PORT, () => {
  console.log(`XAU_AI_PRO Backend ETAPA 16.4 rodando na porta ${PORT}`);
  console.log(`Event stream: ${eventsFile()}`);
});