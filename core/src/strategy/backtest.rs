// XAU AI PRO Core — Backtest walk-forward (item 8 do roadmap).
// Métrica auditável: para cada janela fora-da-amostra, aplica `evaluate`
// nos candles de treino e mede o resultado simulado na janela de teste.

use serde::{Deserialize, Serialize};

use super::evaluate;
use super::StrategyConfig;

/// Resultado agregado do walk-forward.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BacktestReport {
    pub windows: Vec<WindowResult>,
    pub total_trades: u32,
    pub wins: u32,
    pub losses: u32,
    /// PnL somado em pontos.
    pub pnl_points: f64,
    /// win rate = wins / (wins+losses); None se sem trades.
    pub win_rate: Option<f64>,
}

/// Resultado de uma janela fora-da-amostra.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WindowResult {
    /// Índice inicial da janela de teste no vetor de candles.
    pub start_idx: usize,
    pub trades: u32,
    pub wins: u32,
    pub losses: u32,
    pub pnl_points: f64,
}

impl Default for BacktestReport {
    fn default() -> Self {
        Self {
            windows: Vec::new(),
            total_trades: 0,
            wins: 0,
            losses: 0,
            pnl_points: 0.0,
            win_rate: None,
        }
    }
}

/// Executa walk-forward: divide os candles em janelas deslizantes; treina
/// (avalia sinal) no fim da janela de treino e simula na janela de teste.
///
/// Simulação de trade: ao detectar sinal, entra no preço de fechamento com
/// stop `sl` e alvo `tp` (pontos). O trade fecha no primeiro candle cuja
/// faixa toque stop ou alvo (alvo tem prioridade em empate pessimista:
/// stop primeiro — conservador).
pub fn run_walk_forward(closes: &[f64], cfg: &StrategyConfig) -> BacktestReport {
    let mut report = BacktestReport::default();
    let windows = cfg.backtest_windows.max(1);
    let min_history = cfg.ema_slow + 2;
    // Janela de teste = 20% do total (mínimo 30 candles); treino = resto anterior.
    let test_len = ((closes.len() / 5).max(30)).min(closes.len() / 2);
    if closes.len() < min_history + test_len + 2 {
        return report;
    }
    let Some(mut start) = (closes.len()).checked_sub(windows * test_len) else {
        return report;
    };
    while start + test_len <= closes.len() {
        let test = start..(start + test_len);
        let mut w = WindowResult {
            start_idx: start,
            trades: 0,
            wins: 0,
            losses: 0,
            pnl_points: 0.0,
        };
        // Estado do trade aberto na janela.
        let mut open_dir: i8 = 0; // 1 compra, -1 venda, 0 flat
        let mut entry: f64 = 0.0;
        for i in test {
            let price = closes[i];
            // Fecha trade aberto com base no movimento do candle atual.
            if open_dir != 0 {
                let move_pts = (price - entry) * open_dir as f64;
                // Conservador: stop tem prioridade sobre o alvo em empate.
                if move_pts <= -cfg.stop_loss_points {
                    w.trades += 1;
                    w.losses += 1;
                    w.pnl_points -= cfg.stop_loss_points;
                    open_dir = 0;
                } else if move_pts >= cfg.take_profit_points {
                    w.trades += 1;
                    w.wins += 1;
                    w.pnl_points += cfg.take_profit_points;
                    open_dir = 0;
                } else if i + 1 == start + test_len {
                    // Fim da janela com trade aberto: não conta (neutro).
                    open_dir = 0;
                }
            }
            // Sinal avaliado apenas com histórico até o candle atual
            // (sem vazamento de dados futuros — ponto no tempo i).
            if open_dir == 0 && i + 1 >= min_history {
                let history = &closes[..=i];
                match evaluate(history, cfg) {
                    super::Signal::Buy => {
                        open_dir = 1;
                        entry = price;
                    }
                    super::Signal::Sell => {
                        open_dir = -1;
                        entry = price;
                    }
                    super::Signal::Flat => {}
                }
            }
        }
        report.total_trades += w.trades;
        report.wins += w.wins;
        report.losses += w.losses;
        report.pnl_points += w.pnl_points;
        report.windows.push(w);
        start += test_len;
    }
    if report.wins + report.losses > 0 {
        report.win_rate = Some(report.wins as f64 / (report.wins + report.losses) as f64);
    }
    report
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn report_vazio_com_poucos_dados() {
        let cfg = StrategyConfig::default();
        let r = run_walk_forward(&[1.0; 50], &cfg);
        assert!(r.windows.is_empty());
    }

    #[test]
    fn walk_forward_gera_metricas_consistentes() {
        let cfg = StrategyConfig::default();
        // Série alternada ampla para gerar cruzamentos e trades.
        let closes: Vec<f64> = (0..600)
            .map(|i| 100.0 + 30.0 * ((i as f64) / 10.0).sin())
            .collect();
        let r = run_walk_forward(&closes, &cfg);
        assert_eq!(r.windows.len(), 3);
        assert_eq!(r.total_trades, r.wins + r.losses);
        if let Some(wr) = r.win_rate {
            assert!((0.0..=1.0).contains(&wr));
        }
    }
}
