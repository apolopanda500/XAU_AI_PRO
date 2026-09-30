import { apiBase } from './api';

const API = `${apiBase()}`;

/**
 * Corretoras que aceitam API key.
 *
 * POR QUE ESTA LISTA EXISTE
 * =========================
 * O backend aceita `binance, mexc, bybit, okx` (backend/connection_service.py:16).
 * A lista aqui era `mt5 | binance | mexc`, entao Bybit e OKX ficavam prontos no
 * backend e inalcancaveis pela tela: o operador nao tinha como cadastra-los.
 * Cada entrada nova precisa ter cliente correspondente em connection_service.py
 * para o `action()` funcionar.
 */
export type Broker = 'mt5' | 'binance' | 'mexc' | 'bybit' | 'okx';

/** Exchange = corretora que usa API key. MT5 usa a sessao do terminal. */
export type Exchange = Exclude<Broker, 'mt5'>;

/** Mercados aceitos por corretora, espelhando o backend. */
const MERCADOS: Record<Broker, readonly string[]> = {
  mt5: ['forex', 'metals', 'indices'],
  binance: ['crypto-spot', 'crypto-futures'],
  mexc: ['crypto-spot', 'crypto-futures'],
  bybit: ['crypto-spot', 'crypto-futures'],
  okx: ['crypto-spot', 'crypto-futures'],
};

/**
 * Corretoras que exigem `api_passphrase` alem de key e secret.
 *
 * POR QUE SO A OKX
 * ================
 * `connection_service.py:21` recusa OKX sem passphrase e aceita as outras sem
 * ela. Sem este mapa, o campo apareceria para todos (pedindo dado que o
 * backend ignora) ou nunca apareceria (quebrando OKX).
 */
const EXIGE_PASSPHRASE: Record<Broker, boolean> = {
  mt5: false, binance: false, mexc: false, bybit: false, okx: true,
};

export const EXCHANGES: readonly Exchange[] = ['binance', 'mexc', 'bybit', 'okx'];

export const ROTULO_BROKER: Record<Broker, string> = {
  mt5: 'MT5', binance: 'Binance', mexc: 'MEXC', bybit: 'Bybit', okx: 'OKX',
};

export type Connection = { id: string; broker: string; market: string; configured?: boolean; active?: boolean };
export type TerminalAccount = { login: number; server: string; name?: string };

export const marketsFor = (broker: Broker): readonly string[] => MERCADOS[broker] ?? [];

export const exigePassphrase = (broker: Broker): boolean => EXIGE_PASSPHRASE[broker] === true;

export function isExchange(broker: Broker): broker is Exchange {
  return broker !== 'mt5';
}


export async function requestConnection(path: string, method = 'GET', payload?: object) {
  const response = await fetch(`${API}${path}`, {
    method, signal: AbortSignal.timeout(20000),
    ...(payload ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) } : {}),
  });
  const data = await response.json();
  if (!response.ok || data.ok !== true) throw new Error(data.error || 'Não foi possível validar a conexão.');
  return data;
}

export async function detectTerminal(): Promise<TerminalAccount> {
  const data = await requestConnection('/api/status');
  if (data.terminal_connected !== true || !data.account?.login || !data.account?.server) {
    throw new Error('Abra o MetaTrader 5 e entre na conta pelo terminal. Depois clique em Sincronizar MT5.');
  }
  return { login: data.account.login, server: data.account.server, name: data.account.name };
}

/**
 * Cadastra uma exchange. Nao envia ordem: so grava e o chamador valida a leitura.
 *
 * A passphrase so vai no payload quando a corretora exige. Mandar vazia nas
 * outras e inofensivo (o store ignora), mas omitir o campo quando a corretora
 * nao usa mantem o payload minimo e evita guardar segredo que nao sera usado.
 */
export async function saveExchange(
  broker: Exchange,
  market: string,
  name: string,
  key: string,
  secret: string,
  passphrase = '',
): Promise<string> {
  if (!isExchange(broker)) throw new Error('MT5 usa a sessão do terminal, não API key.');
  if (!marketsFor(broker).includes(market)) throw new Error('Mercado incompatível com a corretora.');
  if (![name, key, secret].every(value => value.trim())) throw new Error('Informe nome, API key e secret.');
  if (exigePassphrase(broker) && !passphrase.trim()) {
    throw new Error(`${ROTULO_BROKER[broker]} exige a passphrase criada junto com a API key.`);
  }
  const id = `${broker}:${market}:${name.trim()}`;
  await requestConnection('/api/connections', 'POST', {
    id, broker, market, api_key: key.trim(), api_secret: secret.trim(),
    ...(exigePassphrase(broker) ? { api_passphrase: passphrase.trim() } : {}),
  });
  return id;
}

export async function connectionAction(id: string, action: 'test' | 'activate' | 'deactivate') {
  return requestConnection(`/api/connections/${encodeURIComponent(id)}/${action}`, 'POST');
}
