// ETAPA 17.4 - Reconciliação: Event Stream vs AuditLog vs TradeLogger
const fs = require('fs');
const path = require('path');

const { resolveDataDir } = require('./paths.cjs');
const DATA_DIR = resolveDataDir();

function readCsv(file, delim, utf16) {
  if (!fs.existsSync(file)) return [];
  try {
    const raw = utf16 ? fs.readFileSync(file, 'utf16le').replace(/^\uFEFF/, '')
                      : fs.readFileSync(file, 'utf8');
    return raw.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
  } catch { return []; }
}

function reconcile() {
  const out = {
    audit_tickets: [],
    stream_tickets: [],
    duplicatas_audit: [],
    na_audit: [],
    analise: [],
    fontes: {}
  };

  // 1. AuditLog (full_audit.csv, ';', ANSI)
  const auditF = path.join(DATA_DIR, 'full_audit.csv');
  out.fontes.auditlog = auditF;
  const auditRows = readCsv(auditF, ';', false);
  const seen = {};
  auditRows.slice(1).forEach(r => {
    const t = (r.split(';')[1] || '').trim();
    if (t) { out.audit_tickets.push(t); seen[t] = (seen[t]||0)+1; }
  });
  Object.keys(seen).forEach(k => { if (seen[k] > 1) out.duplicatas_audit.push({ ticket: k, vezes: seen[k] }); });

  // 2. Event Stream (forward_test_events.csv, ',', UTF-16)
  let streamF = path.join(DATA_DIR, 'forward_test_events.csv');
  if (!fs.existsSync(streamF)) streamF = path.join(__dirname, '..', 'MQL5','Files','Data','forward_test_events.csv');
  out.fontes.event_stream = streamF;
  readCsv(streamF, ',', true).forEach(l => {
    if (l.includes('TRADE_OPEN') || l.includes('TRADE_CLOSE') || l.includes('TRADE_APPROVED')) {
      const parts = l.split(',');
      const t = (parts[4] || '').trim();
      if (t && t !== '0') out.stream_tickets.push(t);
    }
  });

  // 3. Divergencias
  const auditSet = new Set(out.audit_tickets);
  out.na_audit = out.stream_tickets.filter(t => !auditSet.has(t));
  out.analise = out.stream_tickets.map(t => ({
    ticket: t,
    no_auditlog: auditSet.has(t) ? 'sim' : 'NAO (divergencia/perda potencial)'
  }));
  out.resumo = {
    tickets_audit: out.audit_tickets.length,
    tickets_stream: out.stream_tickets.length,
    duplicatas_audit: out.duplicatas_audit.length,
    divergencias_stream_vs_audit: out.na_audit.length
  };
  return out;
}

module.exports = { reconcile };
