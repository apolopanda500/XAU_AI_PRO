import { invoke } from '@tauri-apps/api/core';

// Numero de iteracoes do PBKDF2 (referencia OWASP: >= 100k para SHA-256)
const ITERACOES_PADRAO = 150_000;

export interface AuthFile {
  salt_b64: string;
  hash_b64: string;
  iterations: number;
  created_at: string;
}

function bytesParaB64(bytes: Uint8Array): string {
  let bin = '';
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}

function b64ParaBytes(b64: string): Uint8Array<ArrayBuffer> {
  const bin = atob(b64);
  const out = new Uint8Array(new ArrayBuffer(bin.length));
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export function validarPin(pin: string): string | null {
  if (!/^\d{4,8}$/.test(pin)) return 'O PIN deve ter de 4 a 8 digitos numericos.';
  return null;
}

async function derivarHash(pin: string, saltB64: string, iteracoes: number): Promise<string> {
  const material = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(pin),
    'PBKDF2',
    false,
    ['deriveBits'],
  );
  const bits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', salt: b64ParaBytes(saltB64), iterations: iteracoes, hash: 'SHA-256' },
    material,
    256,
  );
  return bytesParaB64(new Uint8Array(bits));
}

/** Le o auth.json via shell Tauri. Retorna null se nao ha PIN cadastrado. */
export async function carregarAuth(): Promise<AuthFile | null> {
  const bruto = await invoke<unknown>('load_auth');
  return bruto ? (bruto as AuthFile) : null;
}

/** Gera salt aleatorio, deriva o PIN com PBKDF2 e grava o auth.json. */
export async function definirPin(pin: string): Promise<void> {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const saltB64 = bytesParaB64(salt);
  const hashB64 = await derivarHash(pin, saltB64, ITERACOES_PADRAO);
  const payload: AuthFile = {
    salt_b64: saltB64,
    hash_b64: hashB64,
    iterations: ITERACOES_PADRAO,
    created_at: new Date().toISOString(),
  };
  await invoke('save_auth', { payload });
}

export async function verificarPin(pin: string): Promise<boolean> {
  const auth = await carregarAuth();
  if (!auth) return false;
  const calculado = await derivarHash(pin, auth.salt_b64, auth.iterations);
  if (calculado.length !== auth.hash_b64.length) return false;
  // Comparacao em tempo constante simples
  let diff = 0;
  for (let i = 0; i < calculado.length; i++) {
    diff |= calculado.charCodeAt(i) ^ auth.hash_b64.charCodeAt(i);
  }
  return diff === 0;
}

export async function removerPin(): Promise<void> {
  await invoke('remove_auth');
}
