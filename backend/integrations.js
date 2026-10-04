// integrations.js - Integracoes do XAU_AI_PRO desktop backend
// GitHub: valida o token contra a API. Nenhuma integracao quebra o backend se
// nao configurada.
'use strict';

const https = require('https');
const http = require('http');

// ---------- Util ----------
function env(k) {
  return (process.env[k] || '').trim();
}

function requestJson(url, options = {}, body = null) {
  return new Promise((resolve, reject) => {
    const lib = url.startsWith('https:') ? https : http;
    const req = lib.request(
      url,
      {
        method: options.method || 'GET',
        headers: options.headers || {},
        timeout: options.timeout || 8000,
      },
      (res) => {
        let data = '';
        res.on('data', (c) => {
          data += c;
        });
        res.on('end', () => {
          let parsed = null;
          try {
            parsed = data ? JSON.parse(data) : null;
          } catch {
            parsed = null;
          }
          resolve({ status: res.statusCode, headers: res.headers, body: parsed, raw: data });
        });
      },
    );
    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy(new Error('timeout'));
    });
    if (body) req.write(body);
    req.end();
  });
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
      headers: {
        Authorization: `Bearer ${token}`,
        'User-Agent': 'XAU_AI_PRO',
        Accept: 'application/vnd.github+json',
      },
      timeout: 8000,
    });
    if (res.status === 200 && res.body && res.body.login) {
      return {
        service: 'github',
        ok: true,
        status: true,
        detail: `token valido (${res.body.login})`,
        escopos: (res.headers['x-oauth-scopes'] || '')
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
      };
    }
    return {
      service: 'github',
      ok: false,
      status: false,
      detail: `token invalido (HTTP ${res.status})`,
    };
  } catch (e) {
    return { service: 'github', ok: false, status: false, detail: `erro: ${e.message}` };
  }
}

// ---------- Status unificado ----------
async function getIntegrationsStatus() {
  const github = await checkGithub();
  return {
    ok: true,
    ts: new Date().toISOString(),
    integrations: { github },
  };
}

module.exports = {
  env,
  githubToken,
  checkGithub,
  getIntegrationsStatus,
};
