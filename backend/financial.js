// ETAPA 22 - Endpoint de Reconciliação Financeira no backend
// Sem tocar no EA. Consome dados do broker/audit via modulo financeiro.
// Dados reais de posições fechadas (ETAPA 21 - broker MT5, magic XAU_AI_PRO)
// Em uma integração completa, isso viria do MT5 via MT5 API/bridge.
const POSITIONS = [
  { symbol: "USDCHF", type: "sell", profit: 0.54, swaps: -0.01, close_reason: "Stop loss", open_time: "2026.08.21 22:00", close_time: "2026.08.24 03:05", position_id: 10153586005 },
  { symbol: "NZDUSD", type: "buy", profit: 0.00, swaps: 0, close_reason: "Stop loss", open_time: "2026.08.24 02:38", close_time: "2026.08.24 06:10", position_id: 10155400097 },
  { symbol: "NZDUSD", type: "buy", profit: 0.09, swaps: 0, close_reason: "Stop loss", open_time: "2026.08.24 02:38", close_time: "2026.08.24 07:09", position_id: 10155400102 },
  { symbol: "GBPUSD", type: "buy", profit: -1.50, swaps: 0, close_reason: "Expert", open_time: "2026.08.24 03:10", close_time: "2026.08.24 09:47", position_id: 10155828638 },
  { symbol: "AUDUSD", type: "buy", profit: -1.50, swaps: 0, close_reason: "Expert", open_time: "2026.08.24 09:55", close_time: "2026.08.24 17:50", position_id: 10161822226 },
  { symbol: "USDJPY", type: "buy", profit: 0.40, swaps: 0, close_reason: "Stop loss", open_time: "2026.08.24 10:06", close_time: "2026.08.24 10:32", position_id: 10162007833 },
  { symbol: "USDJPY", type: "buy", profit: 0.35, swaps: 0, close_reason: "Stop loss", open_time: "2026.08.24 10:32", close_time: "2026.08.24 11:07", position_id: 10162465656 },
];

function financialSummary() {
  const wins = POSITIONS.filter(p => p.profit > 0);
  const losses = POSITIONS.filter(p => p.profit < 0);
  const even = POSITIONS.filter(p => p.profit === 0);
  const grossProfit = wins.reduce((a, p) => a + p.profit, 0);
  const grossLoss = Math.abs(losses.reduce((a, p) => a + p.profit, 0));
  const total = POSITIONS.reduce((a, p) => a + p.profit, 0);
  return {
    total_trades: POSITIONS.length,
    vitorias: wins.length,
    derrotas: losses.length,
    empates: even.length,
    win_rate_pct: POSITIONS.length ? +(wins.length / POSITIONS.length * 100).toFixed(2) : 0,
    profit_factor: grossLoss > 0 ? +(grossProfit / grossLoss).toFixed(2) : (grossProfit > 0 ? 999 : 0),
    expectativa_trade: POSITIONS.length ? +(total / POSITIONS.length).toFixed(4) : 0,
    pnl_total: +total.toFixed(2),
    gross_profit: +grossProfit.toFixed(2),
    gross_loss: +grossLoss.toFixed(2),
    trades: POSITIONS,
  };
}

module.exports = { financialSummary };
