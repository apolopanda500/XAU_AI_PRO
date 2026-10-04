/**
 * Formatadores e regra de vencimento compartilhados entre a leitura de
 * mercado.
 *
 * POR QUE SAIRAM DO MARKETTAB
 * ===========================
 * `formatNumber`, `formatTime`, `receivedTimestamp` e `isMarketStale` estavam
 * privados em `MarketTab.tsx`. Com a aba Mercado fundida na Robo, a faixa de
 * mercado (`RobotMarketBar`) precisa exatamente da mesma formatacao e do mesmo
 * limite de 15s — duas copias divergiriam, e uma cotacao poderia ser considerada
 * vencida num painel e valida no outro.
 */

export const STALE_AFTER_MS = 15_000;

export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  return value.toLocaleString('pt-BR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatSigned(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  return `${value > 0 ? '+' : ''}${formatNumber(value, digits)}`;
}

export function formatTime(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString('pt-BR');
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('pt-BR');
}

export function receivedTimestamp(value: string | null | undefined): number | null {
  if (!value) return null;
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

export function isMarketStale(receivedAt: number | null, now = Date.now()): boolean {
  return receivedAt !== null && now - receivedAt > STALE_AFTER_MS;
}
