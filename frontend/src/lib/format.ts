// Formatação numérica e monetária centralizada (pt-BR) para todo o app.
export function fmtNum(v: unknown, digits = 2): string {
  const n = Number(v);
  if (!Number.isFinite(n)) return '--';
  return n.toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function fmtMoney(v: unknown, currency?: string): string {
  const n = Number(v);
  if (!Number.isFinite(n)) return '--';
  const base = n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return currency ? `${base} ${currency}` : base;
}

export function fmtSigned(v: unknown, digits = 2): string {
  const n = Number(v);
  if (!Number.isFinite(n)) return '--';
  const sign = n > 0 ? '+' : '';
  return `${sign}${fmtNum(n, digits)}`;
}

export function fmtPct(v: unknown, digits = 2): string {
  const n = Number(v);
  return Number.isFinite(n) ? `${n.toFixed(digits)}%` : '--';
}

// Classe CSS de sinal para PnL (verde positivo / vermelho negativo).
export function clsPnl(v: number): 'pos' | 'neg' | '' {
  if (v > 0) return 'pos';
  if (v < 0) return 'neg';
  return '';
}

// Cor de texto para valores (não apenas PnL)
export function textColor(v: number): 'pos' | 'neg' | 'muted' {
  if (v > 0) return 'pos';
  if (v < 0) return 'neg';
  return 'muted';
}

// Direção da posição a partir do campo type (numérico MT5 ou texto das exchanges).
export function sideOfPosition(p: { type?: number | string }): 'BUY' | 'SELL' {
  const t = p.type;
  return t === 1 || t === 'sell' || t === 'SELL' ? 'SELL' : 'BUY';
}

// Extrai o símbolo (XAUUSD, BTCUSDT...) de uma mensagem de journal/evento.
export function extractSymbol(message: string): string {
  const m = /#?\d*\s*([A-Z]{3,}(?:USD|USDT|BRL)[A-Z]*)\b/.exec(message.toUpperCase());
  return m?.[1] ?? '--';
}

// Identificador de requisição idempotente para comandos do gateway.
export function requestId(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.floor(Math.random() * 1e9)}`;
}