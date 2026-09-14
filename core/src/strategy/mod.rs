// XAU AI PRO Core — Estratégia técnica (item 8 do roadmap).
// EMA fast/slow com filtro RSI: sinal determinístico e auditável.
// Regra do projeto: a estratégia apenas OPERA e ANALISA mercado;
// jamais movimenta ativos para terceiros (não existe comando de
// saque/transferência no protocolo — ver teste em mt5session).

mod backtest;
mod candles;
mod paper;

pub use backtest::{run_walk_forward, BacktestReport, WindowResult};
pub use candles::{Candle, CandleStore};
pub use paper::{PaperSnapshot, PaperTrade, PaperTrader};

use serde::{Deserialize, Serialize};

/// Configuração da estratégia (espelho em config.json -> "strategy").
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct StrategyConfig {
    /// Liga o autopilot (sinais automáticos).
    pub autopilot_enabled: bool,
    /// Executa em paper trading (true) ou delega ordens reais via EA (false).
    pub paper_only: bool,
    /// Símbolo operado pelo autopilot.
    pub symbol: String,
    /// Período da EMA rápida.
    pub ema_fast: usize,
    /// Período da EMA lenta.
    pub ema_slow: usize,
    /// Período do RSI de filtro.
    pub rsi_period: usize,
    /// RSI máximo para compra (evita entrar sobrecomprado).
    pub rsi_buy_max: f64,
    /// RSI mínimo para venda (evita entrar sobrevendido).
    pub rsi_sell_min: f64,
    /// Stop loss em pontos.
    pub stop_loss_points: f64,
    /// Take profit em pontos.
    pub take_profit_points: f64,
    /// Equity usada no paper trading / sugestão de lote sem conta real.
    pub paper_equity: f64,
    /// Janelas fora-da-amostra do walk-forward.
    pub backtest_windows: usize,
}

impl Default for StrategyConfig {
    fn default() -> Self {
        Self {
            autopilot_enabled: false,
            paper_only: true,
            symbol: "XAUUSD".into(),
            ema_fast: 9,
            ema_slow: 21,
            rsi_period: 14,
            rsi_buy_max: 70.0,
            rsi_sell_min: 30.0,
            stop_loss_points: 300.0,
            take_profit_points: 450.0,
            paper_equity: 10_000.0,
            backtest_windows: 3,
        }
    }
}

/// Sinal da estratégia.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Signal {
    Buy,
    Sell,
    Flat,
}

impl Signal {
    /// Representação textual estável para auditoria.
    pub fn as_str(self) -> &'static str {
        match self {
            Signal::Buy => "buy",
            Signal::Sell => "sell",
            Signal::Flat => "flat",
        }
    }
}

/// Avalia a estratégia sobre o fechamento dos candles.
/// Regra: cruzamento de EMA (fast cruza acima => compra, abaixo => venda)
/// filtrado por RSI (não comprar sobrecomprado, não vender sobrevendido).
pub fn evaluate(closes: &[f64], cfg: &StrategyConfig) -> Signal {
    if closes.len() < cfg.ema_slow + 2 {
        return Signal::Flat;
    }
    let fast = ema_series(closes, cfg.ema_fast);
    let slow = ema_series(closes, cfg.ema_slow);
    let n = fast.len();
    let prev_diff = fast[n - 2] - slow[n - 2];
    let curr_diff = fast[n - 1] - slow[n - 1];
    let rsi = rsi(closes, cfg.rsi_period);
    // Cruzamento para cima + RSI não sobrecomprado.
    if prev_diff <= 0.0 && curr_diff > 0.0 && rsi < cfg.rsi_buy_max {
        return Signal::Buy;
    }
    // Cruzamento para baixo + RSI não sobrevendido.
    if prev_diff >= 0.0 && curr_diff < 0.0 && rsi > cfg.rsi_sell_min {
        return Signal::Sell;
    }
    Signal::Flat
}

/// Série EMA alinhada ao início do slice (seed = primeiro valor).
pub fn ema_series(values: &[f64], period: usize) -> Vec<f64> {
    if values.is_empty() {
        return Vec::new();
    }
    let k = 2.0 / (period as f64 + 1.0);
    let mut out = Vec::with_capacity(values.len());
    let mut ema = values[0];
    out.push(ema);
    for v in &values[1..] {
        ema = k * v + (1.0 - k) * ema;
        out.push(ema);
    }
    out
}

/// RSI clássico (média simples dos ganhos/perdas na janela).
pub fn rsi(closes: &[f64], period: usize) -> f64 {
    if closes.len() < period + 1 {
        return 50.0;
    }
    let mut gains = 0.0;
    let mut losses = 0.0;
    for w in closes.windows(2).take(period) {
        let d = w[1] - w[0];
        if d > 0.0 {
            gains += d;
        } else {
            losses -= d;
        }
    }
    let avg_gain = gains / period as f64;
    let avg_loss = losses / period as f64;
    if avg_loss <= 0.0 {
        return 100.0;
    }
    let rs = avg_gain / avg_loss;
    100.0 - (100.0 / (1.0 + rs))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cfg() -> StrategyConfig {
        StrategyConfig::default()
    }

    #[test]
    fn flat_sem_dados_suficientes() {
        assert_eq!(evaluate(&[1.0, 2.0, 3.0], &cfg()), Signal::Flat);
    }

    #[test]
    fn detecta_cruzamento_de_compra_em_tendencia_de_alta() {
        // Queda longa (slow acima) seguida de retomada forte: o único
        // cruzamento da série deve ser de compra.
        let mut closes: Vec<f64> = (0..40).map(|i| 100.0 - i as f64).collect();
        for i in 0..27 {
            closes.push(60.0 + i as f64 * 3.0);
        }
        let sinais: Vec<Signal> = (cfg().ema_slow..=closes.len())
            .map(|n| evaluate(&closes[..n], &cfg()))
            .filter(|s| *s != Signal::Flat)
            .collect();
        assert_eq!(sinais, vec![Signal::Buy]);
    }

    #[test]
    fn detecta_cruzamento_de_venda_em_tendencia_de_baixa() {
        // Alta longa seguida de queda forte: o único cruzamento é de venda.
        let mut closes: Vec<f64> = (0..40).map(|i| 60.0 + i as f64).collect();
        for i in 0..27 {
            closes.push(100.0 - i as f64 * 3.0);
        }
        let sinais: Vec<Signal> = (cfg().ema_slow..=closes.len())
            .map(|n| evaluate(&closes[..n], &cfg()))
            .filter(|s| *s != Signal::Flat)
            .collect();
        assert_eq!(sinais, vec![Signal::Sell]);
    }

    #[test]
    fn rsi_em_alta_pura_e_100() {
        let closes: Vec<f64> = (0..30).map(|i| 100.0 + i as f64).collect();
        assert!((rsi(&closes, 14) - 100.0).abs() < 1e-9);
    }
}
