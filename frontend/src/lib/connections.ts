const API = 'http://127.0.0.1:9001';
export type Broker = 'mt5' | 'binance' | 'mexc';
export type Connection = { id: string; broker: string; market: string; configured?: boolean; active?: boolean };
export type TerminalAccount = { login: number; server: string; name?: string };
export const marketsFor = (broker: Broker) => broker === 'mt5'
  ? ['forex', 'metals', 'indices'] : ['crypto-spot', 'crypto-futures'];

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

export async function saveExchange(broker: Broker, market: string, name: string, key: string, secret: string) {
  if (broker === 'mt5') throw new Error('MT5 usa a sessão do terminal, não API key.');
  if (!marketsFor(broker).includes(market)) throw new Error('Mercado incompatível com a corretora.');
  if (![name, key, secret].every(value => value.trim())) throw new Error('Informe nome, API key e secret.');
  const id = `${broker}:${market}:${name.trim()}`;
  await requestConnection('/api/connections', 'POST', {
    id, broker, market, api_key: key.trim(), api_secret: secret.trim(),
  });
  return id;
}

export async function connectionAction(id: string, action: 'test' | 'activate' | 'deactivate') {
  return requestConnection(`/api/connections/${encodeURIComponent(id)}/${action}`, 'POST');
}
