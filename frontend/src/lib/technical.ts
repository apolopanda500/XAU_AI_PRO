// Indicadores técnicos calculados sobre candles reais do MT5.
// Fonte: GET /api/mt5/candles (copy_rates do terminal). Sem Math.random.
export type Candle = {
  time: number; open: number; high: number; low: number; close: number;
};

const closes = (candles: Candle[]): number[] => candles.map((c) => c.close);

export function ema(values: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const out: number[] = [];
  let prev = values[0] ?? 0;
  values.forEach((v, i) => {
    prev = i === 0 ? v : v * k + prev * (1 - k);
    out.push(prev);
  });
  return out;
}

export function rsi(candles: Candle[], period = 14): number | null {
  const c = closes(candles);
  if (c.length < period + 1) return null;
  let gain = 0;
  let loss = 0;
  for (let i = c.length - period; i < c.length; i++) {
    const d = c[i] - c[i - 1];
    if (d >= 0) gain += d;
    else loss -= d;
  }
  if (loss === 0) return 100;
  const rs = gain / loss;
  return 100 - 100 / (1 + rs);
}

export function macd(candles: Candle[]): { macd: number; signal: number } | null {
  const c = closes(candles);
  if (c.length < 35) return null;
  const fast = ema(c, 12);
  const slow = ema(c, 26);
  const line = fast.map((v, i) => v - slow[i]);
  const sig = ema(line.slice(-9), 9);
  return { macd: line[line.length - 1], signal: sig[sig.length - 1] };
}

export function atr(candles: Candle[], period = 14): number | null {
  if (candles.length < period + 1) return null;
  const trs: number[] = [];
  for (let i = 1; i < candles.length; i++) {
    const h = candles[i].high;
    const l = candles[i].low;
    const pc = candles[i - 1].close;
    trs.push(Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc)));
  }
  const slice = trs.slice(-period);
  return slice.reduce((s, v) => s + v, 0) / slice.length;
}
