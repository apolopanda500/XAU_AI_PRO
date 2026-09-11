// integrations.js - Integracoes reais do XAU_AI_PRO desktop backend (ETAPA 17.4+)
// Slack (webhook real), GitHub (valida token via API), Sentry (captura de erros),
// Vercel (status do projeto). Nenhuma integracao quebra o backend se nao configurada.
'use strict';

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

// ---------- Util ----------
function env(k) {
  return (process.env[k] || '').trim();
}

function requestJson(url, options = {}, body = null) {
  return new Promise((resolve, reject) => {
    const lib = url.startsWith('https:') ? https : http;
    const req = lib.request(url, { method: options.method || 'GET', headers: options.headers || {}, timeout: options.timeout || 8000 }, (res) => {
      let data = '';
      res.on('data', (c) => { data += c; });
      res.on('end', () => {
        let parsed = null;
        try { parsed = data ? JSON.parse(data) : null; } catch { parsed = null; }
        resolve({ status: res.statusCode, headers: res.headers, body: parsed, raw: data });
      });
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(new Error('timeout')); });
    if (body) req.write(body);
    req.end();
  });
}

// ---------- Slack ----------
function slackWebhook() {
  return env('SLACK_WEBHOOK_URL');
}

function slackConfigured() {
  return !!slackWebhook();
}

// Envia mensagem de texto simples para o webhook do Slack
async function sendSlack(text, extra = {}) {
  const url = slackWebhook();
  if (!url) return { ok: false, error: 'SLACK_WEBHOOK_URL nao configurado' };
  const payload = JSON.stringify({ text, ...extra });
  try {
    const res = await requestJson(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, timeout: 8000 }, payload);
    return { ok: res.status >= 200 && res.status < 300, status: res.status, error: res.status >= 300 ? res.raw.slice(0, 200) : undefined };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

// Envia teste formatado com blocos (usado pelo POST /api/integrations/slack/test)
async function sendSlackTest() {
  if (!slackConfigured()) return { ok: false, error: 'SLACK_WEBHOOK_URL nao configurado' };
  const blocks = [
    { type: 'header', text: { type: 'plain_text', text: ':white_check_mark: XAU AI PRO - Teste de integracao Slack' } },
    { type: 'section', text: { type: 'mrkdwn', text: 'Integracao Slack funcionando corretamente.' } },
    { type: 'context', elements: [{ type: 'mrkdwn', text: `Host: ${require('os').hostname()} | TS: ${new Date().toISOString()}` }] },
  ];
  const payload = JSON.stringify({ text: 'XAU AI PRO - Teste Slack', blocks });
  try {
    const res = await requestJson(slackWebhook(), { method: 'POST', headers: { 'Content-Type': 'application/json' }, timeout: 8000 }, payload);
    return { ok: res.status >= 200 && res.status < 300, status: res.status, error: res.status >= 300 ? res.raw.slice(0, 200) : undefined };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

// ---------- Kilo (inbound webhook de sessoes) ----------
function kiloWebhook() {
  return env('KILO_WEBHOOK_URL');
}

function kiloConfigured() {
  return !!kiloWebhook();
}

// Envia ping de teste ao inbound webhook do Kilo (usado pelo POST /api/integrations/kilo/test).
// O endpoint captura JSON arbitrario e responde 200 com requestId.
async function sendKiloTest() {
  const url = kiloWebhook();
  if (!url) return { ok: false, error: 'KILO_WEBHOOK_URL nao configurado' };
  const payload = JSON.stringify({ source: 'xau_ai_pro', type: 'connection_test', ts: new Date().toISOString() });
  try {
    const res = await requestJson(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, timeout: 8000 }, payload);
    return { ok: res.status >= 200 && res.status < 300, status: res.status, detail: res.raw.slice(0, 200) };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

// ---------- GitHub ----------
function githubToken() {
  return env('GITHUB_TOKEN');
}

// Valida o token contra a API do GitHub (GET /user)
async function checkGithub() {
  const token = githubToken();
  if (!token) return { service: 'github', ok: false, status: false, detail: 'sem GITHUB_TOKEN' };
  try {
    const res = await requestJson('https://api.github.com/user', {
      headers: { Authorization: `Bearer ${token}`, 'User-Agent': 'XAU_AI_PRO', Accept: 'application/vnd.github+json' },
      timeout: 8000,
    });
    if (res.status === 200 && res.body && res.body.login) {
      return { service: 'github', ok: true, status: true, detail: `token valido (${res.body.login})`, escopos: (res.headers['x-oauth-scopes'] || '').split(',').map(s => s.trim()).filter(Boolean) };
    }
    return { service: 'github', ok: false, status: false, detail: `token invalido (HTTP ${res.status})` };
  } catch (e) {
    return { service: 'github', ok: false, status: false, detail: `erro: ${e.message}` };
  }
}

// ---------- Sentry ----------
function sentryDsn() {
  return env('SENTRY_DSN');
}

// Inicializa o Sentry se o SDK estiver disponivel e o DSN configurado.
// Retorna o client se ativo, null caso contrario (nunca quebra o backend).
function initSentry() {
  const dsn = sentryDsn();
  if (!dsn) return null;
  try {
    const Sentry = require('@sentry/node');
    if (!Sentry || !Sentry.init) return null;
    Sentry.init({
      dsn,
      environment: env('ENVIRONMENT') || 'production',
      release: 'xau-ai-pro@1.2.0',
      tracesSampleRate: 0.1,
    });
    process.on('uncaughtException', (err) => {
      Sentry.captureException(err);
      console.error('[sentry] uncaughtException capturado:', err.message);
    });
    process.on('unhandledRejection', (reason) => {
      Sentry.captureException(reason instanceof Error ? reason : new Error(String(reason)));
    });
    return Sentry;
  } catch (e) {
    console.warn('[sentry] SDK nao disponivel (npm i @sentry/node para ativar):', e.message);
    return null;
  }
}

function sentryStatus() {
  const dsn = sentryDsn();
  if (!dsn) return { service: 'sentry', ok: false, status: false, detail: 'sem SENTRY_DSN' };
  let sdk = false;
  try { require.resolve('@sentry/node'); sdk = true; } catch { sdk = false; }
  return { service: 'sentry', ok: sdk, status: sdk, detail: sdk ? `DSN configurado (env=${env('ENVIRONMENT') || 'production'})` : 'DSN configurado, mas @sentry/node nao instalado (npm i @sentry/node)' };
}

// ---------- Vercel ----------
function vercelStatus() {
  const linked = fs.existsSync(path.join(__dirname, '..', '.vercel', 'project.json'));
  const token = env('VERCEL_OIDC_TOKEN');
  return {
    service: 'vercel',
    ok: true,
    status: true,
    detail: linked ? (token ? 'projeto vinculado (OIDC ativo)' : 'projeto vinculado') : 'sem .vercel/project.json',
  };
}

// ---------- Status unificado ----------
async function getIntegrationsStatus() {
  const slack = slackConfigured()
    ? { service: 'slack', ok: true, status: true, detail: 'webhook configurado' }
    : { service: 'slack', ok: false, status: false, detail: 'sem SLACK_WEBHOOK_URL' };
  const github = await checkGithub();
  const sentry = sentryStatus();
  const vercel = vercelStatus();
  return { ok: true, ts: new Date().toISOString(), integrations: { slack, github, sentry, vercel } };
}

module.exports = {
  env,
  slackConfigured,
  sendSlack,
  sendSlackTest,
  kiloConfigured,
  sendKiloTest,
  githubToken,
  checkGithub,
  sentryDsn,
  initSentry,
  sentryStatus,
  vercelStatus,
  getIntegrationsStatus,
};
