// XAU AI PRO Core — Risk Engine (item 7 do roadmap)
// Regras de risco centralizadas e aplicadas antes de qualquer ordem:
//   - Cálculo de lote por risco (% de equity + stop-loss em pontos)
//   - Validação de spread máximo
//   - Control de drawdown máximo
//   - Control de perda diária (reset à meia-noite)
//   - Kill switch (apagado manual ou automático do trading)

use serde::{Deserialize, Serialize};

/// Configuração de risco (espelho em config.json -> "risk").
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct RiskConfig {
    /// Fração da equity a arriscar por lote (0.01 = 1%).
    pub risk_per_trade_pct: f64,
    /// Lote máximo permitido por ordem (capacidade).
    pub max_lot: f64,
    /// Lote mínimo permitido por ordem.
    pub min_lot: f64,
    /// Spread máximo aceito em pontos (rechaza si lo excede).
    pub max_spread_points: u64,
    /// Drawdown máximo sobre equity (0.10 = 10%) antes de kill switch.
    pub max_drawdown_pct: f64,
    /// Perda máxima acumulada en el día (0.05 = 5%) antes de kill switch.
    pub max_daily_loss_pct: f64,
    /// Permite trading (kill switch manual).
    pub trading_enabled: bool,
}

impl Default for RiskConfig {
    fn default() -> Self {
        Self {
            risk_per_trade_pct: 0.01,
            max_lot: 0.5,
            min_lot: 0.01,
            max_spread_points: 30,
            max_drawdown_pct: 0.10,
            max_daily_loss_pct: 0.05,
            // Fail-closed: uma instalação nova nunca pode operar sem
            // habilitação explícita do usuário no painel/configuração.
            trading_enabled: false,
        }
    }
}

/// Decisão do engine de risco para uma ordem proposta.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskDecision {
    /// Permite a ordem?
    pub approved: bool,
    /// Motivo do bloqueio (vazio se aprovado).
    pub reason: String,
    /// Código estável do bloqueio (espelho de error_codes do protocolo).
    pub code: Option<String>,
    /// Lote sugerido após cálculo de risco.
    pub suggested_lot: f64,
}

impl RiskDecision {
    pub fn approve(lot: f64) -> Self {
        Self {
            approved: true,
            reason: String::new(),
            code: None,
            suggested_lot: lot,
        }
    }
    pub fn reject(code: Rejection, reason: String, lot: f64) -> Self {
        Self {
            approved: false,
            reason,
            code: Some(code.as_str().to_string()),
            suggested_lot: lot,
        }
    }
}

/// Códigos de rejeição estáveis (espelham error_codes do protocolo v1).
#[derive(Debug, Clone, Copy)]
pub enum Rejection {
    KillSwitch,
    SpreadTooWide,
    LotTooBig,
    LotTooSmall,
    MaxDrawdown,
    DailyLoss,
}

impl Rejection {
    pub fn as_str(&self) -> &'static str {
        match self {
            Rejection::KillSwitch => "KILL_SWITCH",
            Rejection::SpreadTooWide => "SPREAD_TOO_WIDE",
            Rejection::LotTooBig => "LOT_TOO_BIG",
            Rejection::LotTooSmall => "LOT_TOO_SMALL",
            Rejection::MaxDrawdown => "MAX_DRAWDOWN",
            Rejection::DailyLoss => "DAILY_LOSS_LIMIT",
        }
    }
}

/// Dados de mercado usados pelo cálculo de risco.
#[derive(Debug, Clone)]
pub struct RiskMarketData {
    pub bid: f64,
    pub ask: f64,
    pub spread_points: u64,
    pub equity: f64,
    pub point_value_per_lot: f64,
}

/// Contadores de drawdown/perda diária (persistíveis opcionalmente).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskCounters {
    pub peak_equity: f64,
    pub day_start_equity: f64,
    pub day_realized_loss: f64,
    pub day: chrono::NaiveDate,
    pub kill_switch_active: bool,
}
