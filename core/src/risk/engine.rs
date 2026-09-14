// XAU AI PRO Core — Risk Engine (lógica)
// Fachada: RiskEngine aplica as regras de risco e atualiza os contadores.

use chrono::{Local, Utc};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, warn};

use crate::protocol::OrderRequest;

use super::config::{Rejection, RiskConfig, RiskCounters, RiskDecision, RiskMarketData};

/// Motor de avaliação de risco.
pub struct RiskEngine {
    config: Arc<RwLock<RiskConfig>>,
    counters: Arc<RwLock<RiskCounters>>,
}

impl Default for RiskEngine {
    fn default() -> Self {
        Self::new(RiskConfig::default())
    }
}

impl RiskEngine {
    pub fn new(config: RiskConfig) -> Self {
        let today = Local::now().date_naive();
        let counters = RiskCounters {
            peak_equity: 0.0,
            day_start_equity: 0.0,
            day_realized_loss: 0.0,
            day: today,
            kill_switch_active: !config.trading_enabled,
        };
        Self {
            config: Arc::new(RwLock::new(config)),
            counters: Arc::new(RwLock::new(counters)),
        }
    }

    /// Configura os limites (chamado na inicialização com config.json).
    pub async fn set_config(&self, config: RiskConfig) {
        let mut cfg = self.config.write().await;
        *cfg = config;
    }

    /// Kill switch manual: desliga/religa o trading.
    pub async fn set_trading_enabled(&self, enabled: bool) {
        let mut cfg = self.config.write().await;
        cfg.trading_enabled = enabled;
        let mut c = self.counters.write().await;
        c.kill_switch_active = !enabled;
        if !enabled {
            warn!("KILL SWITCH ativado — trading desligado manualmente");
        } else {
            info!("Trading religado");
        }
    }

    /// Estado do kill switch.
    pub async fn kill_switch_active(&self) -> bool {
        self.counters.read().await.kill_switch_active
    }

    /// Calcula o lote para um dado stop-loss (em pontos), respeitando o
    /// risco por trade como fração da equity.
    fn calculate_lot(
        &self,
        config: &RiskConfig,
        market: &RiskMarketData,
        stop_loss_points: f64,
    ) -> f64 {
        if stop_loss_points <= 0.0 {
            return config.min_lot;
        }
        let risk_money = market.equity * config.risk_per_trade_pct;
        let loss_per_lot = stop_loss_points * market.point_value_per_lot;
        if loss_per_lot <= 0.0 {
            return config.min_lot;
        }
        (risk_money / loss_per_lot).clamp(config.min_lot, config.max_lot)
    }

    /// Reseta o contador diário se mudou o dia.
    fn roll_day(&self, counters: &mut RiskCounters, now_eq: f64) {
        let today = Local::now().date_naive();
        if counters.day != today {
            counters.day = today;
            counters.day_start_equity = now_eq;
            counters.day_realized_loss = 0.0;
            info!("Reset de perda diária de risco para o novo dia");
        }
    }

    /// Atualiza os contadores com a equity atual e lucro/perda realizado.
    pub async fn observe(&self, equity: f64, realized_pnl: f64) {
        let mut c = self.counters.write().await;
        self.roll_day(&mut c, equity);
        if c.peak_equity <= 0.0 || equity > c.peak_equity {
            c.peak_equity = equity;
        }
        if realized_pnl < 0.0 {
            c.day_realized_loss += -realized_pnl;
        }
    }

    /// Avalia uma ordem contra todas as regras de risco.
    pub async fn evaluate(
        &self,
        request: &OrderRequest,
        market: Option<&RiskMarketData>,
    ) -> RiskDecision {
        let cfg = self.config.read().await.clone();
        let counters = self.counters.read().await;

        // 1. Kill switch ativo / trading desligado.
        if counters.kill_switch_active || !cfg.trading_enabled {
            return RiskDecision::reject(
                Rejection::KillSwitch,
                "Kill switch ativado: trading desligado".into(),
                0.0,
            );
        }

        // 2. Spread máximo (se dados de mercado disponíveis).
        if let Some(m) = market {
            if m.spread_points > cfg.max_spread_points {
                return RiskDecision::reject(
                    Rejection::SpreadTooWide,
                    format!(
                        "Spread {} pts excede máximo {} pts",
                        m.spread_points, cfg.max_spread_points
                    ),
                    0.0,
                );
            }
        }

        // 3. Lote máximo/mínimo explícito.
        if request.volume > cfg.max_lot {
            return RiskDecision::reject(
                Rejection::LotTooBig,
                format!("Lote {} excede máximo {}", request.volume, cfg.max_lot),
                cfg.max_lot,
            );
        }
        if request.volume < cfg.min_lot {
            return RiskDecision::reject(
                Rejection::LotTooSmall,
                format!("Lote {} abaixo do mínimo {}", request.volume, cfg.min_lot),
                cfg.min_lot,
            );
        }

        // 4. Drawdown máximo (distância entre pico e equity atual).
        if let Some(m) = market {
            let drawdown = if counters.peak_equity > 0.0 {
                (counters.peak_equity - m.equity) / counters.peak_equity
            } else {
                0.0
            };
            if drawdown >= cfg.max_drawdown_pct {
                return RiskDecision::reject(
                    Rejection::MaxDrawdown,
                    format!(
                        "Drawdown {:.2}% atinge limite {:.2}%",
                        drawdown * 100.0,
                        cfg.max_drawdown_pct * 100.0
                    ),
                    0.0,
                );
            }
        }

        // 5. Perda diária máxima (só com baseline do dia válido).
        if counters.day_start_equity > 0.0
            && counters.day_realized_loss >= counters.day_start_equity * cfg.max_daily_loss_pct
        {
            return RiskDecision::reject(
                Rejection::DailyLoss,
                "Limite de perda diária atingido".into(),
                0.0,
            );
        }

        // 6. Tudo ok — aprovado.
        RiskDecision::approve(request.volume)
    }

    /// Gera o lote sugerido dado um stop-loss em pontos (útil no frontend).
    pub async fn suggested_lot(&self, stop_loss_points: f64, market: &RiskMarketData) -> f64 {
        let cfg = self.config.read().await.clone();
        self.calculate_lot(&cfg, market, stop_loss_points)
    }

    /// Utilitário p/ tests / CLI: cria um engine com config custom.
    pub async fn from_config(config: RiskConfig) -> Self {
        Self::new(config)
    }

    // Presente p/ uso futuro em reconciliação temporal (UTC).
    #[allow(dead_code)]
    fn _now_utc(&self) -> chrono::DateTime<Utc> {
        Utc::now()
    }
}
