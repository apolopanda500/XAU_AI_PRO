#!/usr/bin/env node
/**
 * Gera um override de CSP para o Tauri, em arquivo SEPARADO.
 *
 * Antes este script reescrevia `src-tauri/tauri.conf.json`, que e versionado.
 * Consequencia: um build de teste (emulador, apontando para 10.0.2.2) deixava a
 * origem no repositorio, e o build seguinte sobrescrevia de volta. O arquivo
 * versionado passou a depender de qual build rodou por ultimo.
 *
 * Agora o `tauri.conf.json` fica estavel (gateway local do desktop) e cada
 * destino tem seu proprio override:
 *   - `tauri.emulador.conf.json`  -> 10.0.2.2 (versionado, para o emulador)
 *   - `tauri.<saida>.conf.json`    -> destino de producao (gerado, gitignored)
 *
 * Uso:
 *   node scripts/apply-csp.mjs --saida tauri.producao.conf.json \
 *        --gateway https://gateway.exemplo.com --ws wss://gateway.exemplo.com
 *
 * Em build de producao o script RECUSA texto claro: nao se publica um bundle
 * que aceita conexao sem TLS.
 */
import { writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const dirConf = resolve(here, '..', 'src-tauri');

function arg(nome, padrao = '') {
  const i = process.argv.indexOf(`--${nome}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : padrao;
}

const gateway = (arg('gateway', 'http://127.0.0.1:9001')).replace(/\/+$/, '');
const ws = (arg('ws', 'ws://127.0.0.1:9002')).replace(/\/+$/, '');
const saida = arg('saida');
const producao = process.argv.includes('--production') || process.env.XAU_BUILD_TARGET === 'production';

function urlDe(valor) {
  try {
    return new URL(valor);
  } catch {
    return null;
  }
}

const gatewayUrl = urlDe(gateway);
const wsUrl = urlDe(ws);
if (!gatewayUrl || !wsUrl) {
  console.error(`[csp] origem invalida: gateway=${gateway} ws=${ws}`);
  process.exit(1);
}

if (producao) {
  const problemas = [];
  if (gatewayUrl.protocol !== 'https:') problemas.push(`gateway em texto claro (${gatewayUrl.protocol})`);
  if (wsUrl.protocol !== 'wss:') problemas.push(`websocket em texto claro (${wsUrl.protocol})`);
  if (problemas.length) {
    console.error(`[csp] build de producao recusado: ${problemas.join('; ')}`);
    process.exit(1);
  }
}

if (!saida) {
  console.error('[csp] informe --saida <arquivo.conf.json>. Nada e escrito sem esse parametro.');
  process.exit(1);
}
if (!saida.endsWith('.json')) {
  console.error(`[csp] saida precisa terminar em .json: ${saida}`);
  process.exit(1);
}

const csp = [
  "default-src 'self'",
  `connect-src 'self' ${gateway} ${ws}`,
  "img-src 'self' data:",
  "style-src 'self' 'unsafe-inline'",
].join('; ');

const destino = resolve(dirConf, saida);
writeFileSync(destino, `${JSON.stringify({
  $schema: 'https://schema.tauri.app/config/2',
  app: { security: { csp } },
}, null, 2)}\n`);

console.log(`[csp] ${saida} -> connect-src ${gateway} | ${ws}`);
console.log(`[csp] use com:  tauri android build --config src-tauri/${saida}`);
