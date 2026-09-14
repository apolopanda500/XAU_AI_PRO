// XAU AI PRO Core — Risk Engine (item 7 do roadmap)
// Regras de risco centrais: lote por risco, spread, drawdown,
// perda diária e kill switch. Aplicadas antes de qualquer ordem.

mod config;
mod engine;

pub use config::{Rejection, RiskConfig, RiskCounters, RiskDecision, RiskMarketData};
pub use engine::RiskEngine;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::protocol::OrderRequest;

    fn market(equity: f64) -> RiskMarketData {
        RiskMarketData {
            bid: 2350.0,
            ask: 2350.3,
            spread_points: 30,
            equity,
            point_value_per_lot: 10.0, // 1 ponto = 10 USD/lote (XAU padrão)
        }
    }

    #[tokio::test]
    async fn aprova_ordem_com_risco_ok() {
        let config = RiskConfig {
            trading_enabled: true,
            ..Default::default()
        };
        let engine = RiskEngine::new(config);
        let req = OrderRequest {
            symbol: "XAUUSD".into(),
            side: "buy".into(),
            volume: 0.1,
            sl: Some(2300.0),
            tp: Some(2400.0),
            magic: Some(2026001),
        };
        let decision = engine.evaluate(&req, Some(&market(10_000.0))).await;
        assert!(decision.approved, "deveria aprovar: {}", decision.reason);
    }

    #[tokio::test]
    async fn default_fail_closed_bloqueia_ordem_ate_habilitacao_manual() {
        let engine = RiskEngine::new(RiskConfig::default());
        let req = OrderRequest {
            symbol: "XAUUSD".into(),
            side: "buy".into(),
            volume: 0.1,
            sl: Some(2300.0),
            tp: Some(2400.0),
            magic: None,
        };
        let decision = engine.evaluate(&req, Some(&market(10_000.0))).await;
        assert!(!decision.approved);
        assert_eq!(decision.code.as_deref(), Some("KILL_SWITCH"));
    }

    #[tokio::test]
    async fn bloqueia_ordem_com_lote_acima_do_max() {
        let config = RiskConfig {
            trading_enabled: true,
            ..Default::default()
        };
        let engine = RiskEngine::new(config);
        let req = OrderRequest {
            symbol: "XAUUSD".into(),
            side: "buy".into(),
            volume: 9.0,
            sl: Some(2300.0),
            tp: Some(2400.0),
            magic: Some(2026001),
        };
        let decision = engine.evaluate(&req, Some(&market(10_000.0))).await;
        assert!(!decision.approved);
        assert_eq!(decision.code.as_deref(), Some("LOT_TOO_BIG"));
    }

    #[tokio::test]
    async fn kill_switch_bloqueia_tudo() {
        let engine = RiskEngine::new(RiskConfig::default());
        engine.set_trading_enabled(false).await;
        let req = OrderRequest {
            symbol: "XAUUSD".into(),
            side: "buy".into(),
            volume: 0.1,
            sl: None,
            tp: None,
            magic: None,
        };
        let decision = engine.evaluate(&req, Some(&market(10_000.0))).await;
        assert!(!decision.approved);
        assert_eq!(decision.code.as_deref(), Some("KILL_SWITCH"));
    }

    #[tokio::test]
    async fn bloqueia_spread_acima_do_max() {
        let config = RiskConfig {
            trading_enabled: true,
            ..Default::default()
        };
        let engine = RiskEngine::new(config);
        let mut m = market(10_000.0);
        m.spread_points = 5000;
        let req = OrderRequest {
            symbol: "XAUUSD".into(),
            side: "buy".into(),
            volume: 0.1,
            sl: None,
            tp: None,
            magic: None,
        };
        let decision = engine.evaluate(&req, Some(&m)).await;
        assert!(!decision.approved);
        assert_eq!(decision.code.as_deref(), Some("SPREAD_TOO_WIDE"));
    }

    #[tokio::test]
    async fn sugestao_de_lote_respeita_risco() {
        let engine = RiskEngine::new(RiskConfig::default());
        // 1% de 10k = 100 USD de risco.
        // stop 500 pontos * 10 USD/lote = 5000 USD/lote.
        // lote = 100/5000 = 0.02
        let lot = engine.suggested_lot(500.0, &market(10_000.0)).await;
        assert!((lot - 0.02).abs() < 1e-6, "lote sugerido {}", lot);
    }
}
