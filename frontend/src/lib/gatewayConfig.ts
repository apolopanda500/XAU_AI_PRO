/**
 * Configuracao do gateway em runtime (Android e diagnostico no desktop).
 *
 * Sem esta tela o app Android nao tinha como apontar para um gateway remoto: a
 * chave `xau-api-base` era lida por `apiBase()` mas nenhuma tela a escrevia, e o
 * comentario do modulo prometia "ajustar em runtime pela tela de conexao" que
 * nao existia. Era esse o motivo real do APK "nao operacional", alem do TLS.
 */

export const CHAVE_API_BASE = 'xau-api-base';
export const CHAVE_WS_URL = 'xau-ws-url';

/** 10.0.2.2 e o alias que o emulador Android usa para alcancar o host. */
export const HOST_EMULADOR = 'http://10.0.2.2:9001';

export interface Resultado {
  ok: boolean;
  origem: string;
  /** Preenchido quando `ok` e true. */
  status?: number;
  latencia_ms?: number;
  detalhe?: string;
  /** Preenchido quando `ok` e false. */
  erro?: string;
  dica?: string;
}

function ler(chave: string): string {
  try {
    return typeof window === 'undefined' ? '' : window.localStorage.getItem(chave) ?? '';
  } catch {
    return '';
  }
}

function gravar(chave: string, valor: string): boolean {
  try {
    window.localStorage.setItem(chave, valor);
    return true;
  } catch {
    return false;
  }
}

/** Normaliza a origem: sem barra final, sem caminho, protocolo obrigatorio. */
export function normalizeOrigin(valor: string): string {
  const bruto = String(valor || '').trim();
  if (!bruto) return '';
  const semBarra = bruto.replace(/\/+$/, '');
  if (!/^https?:\/\//i.test(semBarra)) return '';
  try {
    const url = new URL(semBarra);
    if (!url.hostname) return '';
    return url.origin;
  } catch {
    return '';
  }
}

export function normalizeWsUrl(valor: string, origem: string): string {
  const bruto = String(valor || '').trim().replace(/\/+$/, '');
  if (!bruto) {
    // Sem WS explicito, deriva da origem: https -> wss, http -> ws.
    if (!origem) return '';
    return `${origem.replace(/^http/i, 'ws')}/ws/market`;
  }
  if (!/^wss?:\/\//i.test(bruto)) return '';
  try {
    const url = new URL(bruto);
    if (!url.hostname) return '';
    return bruto;
  } catch {
    return '';
  }
}

export function gatewayConfigurado(): { apiBase: string; wsUrl: string } {
  return { apiBase: ler(CHAVE_API_BASE), wsUrl: ler(CHAVE_WS_URL) };
}

/** Grava a configuracao. Retorna o motivo da recusa quando invalido. */
export function salvarGateway(apiBase: string, wsUrl: string): { ok: boolean; erro?: string; apiBase: string; wsUrl: string } {
  const origem = normalizeOrigin(apiBase);
  if (!origem) {
    return { ok: false, erro: 'Informe uma URL completa, por exemplo https://gateway.exemplo.com', apiBase: '', wsUrl: '' };
  }
  const ws = normalizeWsUrl(wsUrl, origem);
  if (!ws) {
    return { ok: false, erro: 'URL de WebSocket invalida; use wss:// em producao', apiBase: '', wsUrl: '' };
  }
  if (!gravar(CHAVE_API_BASE, origem) || !gravar(CHAVE_WS_URL, ws)) {
    return { ok: false, erro: 'Nao foi possivel salvar a configuracao neste dispositivo', apiBase: '', wsUrl: '' };
  }
  return { ok: true, apiBase: origem, wsUrl: ws };
}

export function limparGateway(): void {
  try {
    window.localStorage.removeItem(CHAVE_API_BASE);
    window.localStorage.removeItem(CHAVE_WS_URL);
  } catch {
    /* armazenamento indisponivel */
  }
}

/** Uma origem http:// em runtime mobile e recusa com explicacao. */
export function alertaSeguranca(origem: string, mobile: boolean): string | null {
  if (!mobile) return null;
  if (/^http:\/\//i.test(origem) && !/^http:\/\/10\.0\.2\.2(:\d+)?$/i.test(origem) && !/^http:\/\/127\.0\.0\.1(:\d+)?$/i.test(origem)) {
    return 'Conexao sem TLS. Use https:// (o trafego com credencial nao deve viajar em texto claro).';
  }
  return null;
}

/** Testa o gateway chamando /api/health, que responde 401 sem token. */
export async function testarGateway(origem: string, timeoutMs = 6000): Promise<Resultado> {
  const base = normalizeOrigin(origem);
  if (!base) {
    return { ok: false, origem: String(origem || ''), erro: 'URL invalida', dica: 'Use o formato https://host:porta' };
  }
  const inicio = Date.now();
  try {
    const resposta = await fetch(`${base}/api/health`, { signal: AbortSignal.timeout(timeoutMs) });
    const latencia = Date.now() - inicio;
    // 401 e a resposta esperada sem token: prova que o gateway existe e exige
    // autenticacao. Qualquer 2xx tambem e sinal de gateway vivo.
    if (resposta.status === 401 || resposta.ok) {
      return {
        ok: true,
        origem: base,
        status: resposta.status,
        latencia_ms: latencia,
        detalhe: resposta.status === 401 ? 'gateway no ar, exige token (401)' : `gateway no ar (${resposta.status})`,
      };
    }
    return {
      ok: false,
      origem: base,
      erro: `HTTP ${resposta.status}`,
      dica: resposta.status === 404 ? 'essa origem nao expoe /api/health;-check a porta do gateway' : 'o host respondeu, mas nao como gateway',
    };
  } catch (erro) {
    const mensagem = String(erro);
    const dica = /abort|timeout/i.test(mensagem)
      ? 'tempo limite excedido; o host esta acessivel do aparelho?'
      : /failed to fetch|networkerror|refused/i.test(mensagem)
        ? 'conexao recusada; no emulador use http://10.0.2.2:9001 para alcancar o PC'
        : 'falha de rede';
    return { ok: false, origem: base, erro: mensagem, dica };
  }
}
