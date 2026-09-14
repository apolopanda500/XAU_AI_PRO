// XAU AI PRO Core — Conectores mock para CI e teste (item 9).
use chrono::Utc;
use std::sync::Arc;
use tokio::sync::RwLock;

use crate::connectors::BrokerConnector;
use crate::connectors::BrokerError;
use crate::protocol::{AccountInfo, OrderRequest, Position};
use crate::risk::RiskMarketData;

pub struct MockConnector {
    exchange: String,
    config: crate::connectors::BrokerConfig,
    positions: Arc<RwLock<Vec<Position>>>,
    accounts: Arc<RwLock<Vec<AccountInfo>>>,
    next_ticket: Arc<RwLock<u64>>,
    rate_limiter: Arc<crate::connectors::RateLimiter>,
    reconcile_fail: bool,
}

impl MockConnector {
    pub fn new(exchange: &str, rate_limiter: Arc<crate::connectors::RateLimiter>) -> Self {
        let mut cfg = crate::connectors::BrokerConfig::default();
        cfg.sandbox = true;
        cfg.enabled = true;
        Self {
            exchange: exchange.into(),
            config: cfg,
            positions: Arc::new(RwLock::new(Vec::new())),
            accounts: Arc::new(RwLock::new(vec![AccountInfo {
                login: "100000".into(),
                balance: 10000.0,
                equity: 10000.0,
                margin: 0.0,
                free_margin: 10000.0,
                leverage: 100,
                server: format!("Mock{}-Server", exchange),
                currency: "USD".into(),
                profit: 0.0,
            }])),
            next_ticket: Arc::new(RwLock::new(1000)),
            rate_limiter,
            reconcile_fail: false,
        }
    }
    pub fn set_config(&self, config: crate::connectors::BrokerConfig) {
        self.config = config;
    }
    pub fn set_reconcile_fail(&self, fail: bool) {
        self.reconcile_fail = fail;
    }
}

impl BrokerConnector for MockConnector {
    fn exchange(&self) -> &str {
        &self.exchange
    }
    fn connect(&self) -> Result<(), BrokerError> {
        Ok(())
    }
    fn is_online(&self) -> bool {
        true
    }
    fn sandbox(&self) -> bool {
        self.config.sandbox
    }
    fn accounts(&self) -> Vec<AccountInfo> {
        self.accounts.read().unwrap().clone()
    }
    fn positions(&self) -> Vec<Position> {
        self.positions.read().unwrap().clone()
    }
    fn risk_market_data(&self, _ls: &str) -> Option<RiskMarketData> {
        Some(RiskMarketData {
            bid: 1000.0,
            ask: 1000.02,
            spread_points: 2,
            equity: 10000.0,
            point_value_per_lot: 10.0,
        })
    }
    fn place_order(
        &self,
        request: &OrderRequest,
        _rd: &RiskMarketData,
    ) -> Result<u64, BrokerError> {
        if !self.is_online() {
            return Err(BrokerError::Offline("Mock offline".into()));
        }
        if !self.config.sandbox {
            return Err(BrokerError::SandboxRequired);
        }
        self.rate_limiter
            .acquire(self.exchange)
            .await
            .map_err(BrokerError::RateLimit)?;
        let ticket = {
            let mut n = self.next_ticket.write().unwrap();
            let t = *n;
            *n += 1;
            t
        };
        let pos = Position {
            ticket,
            symbol: request.symbol.clone(),
            side: request.side.clone(),
            volume: request.volume,
            open_price: if request.side == "buy" {
                1000.02
            } else {
                1000.0
            },
            current_price: 1000.0,
            sl: request.sl,
            tp: request.tp,
            profit: 0.0,
            open_time: Utc::now(),
            magic: 2026001,
        };
        self.positions.write().unwrap().push(pos);
        Ok(ticket)
    }
    fn cancel_order(&self, _t: u64) -> Result<(), BrokerError> {
        Ok(())
    }
    fn close_position(&self, ticket: u64) -> Result<(), BrokerError> {
        self.positions
            .write()
            .unwrap()
            .retain(|p| p.ticket != ticket);
        Ok(())
    }
    fn status(&self) -> crate::connectors::BrokerStatus {
        crate::connectors::BrokerStatus {
            exchange: self.exchange.clone(),
            online: true,
            sandbox: self.config.sandbox,
            accounts: self.accounts(),
            last_heartbeat: Some(Utc::now()),
            symbol_mappings: Vec::new(),
        }
    }
    fn symbol_mapping(&self, _ls: &str) -> Option<&crate::connectors::SymbolMapping> {
        None
    }
    fn reconcile_positions(&self) -> Result<(), BrokerError> {
        if self.reconcile_fail {
            return Err(BrokerError::Offline("reconciliação mock falhou".into()));
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::connectors::BrokerConnector;

    #[tokio::test]
    async fn mock_connector_bloqueia_em_producao_sem_sandbox() {
        let rl = Arc::new(crate::connectors::RateLimiter::new());
        let conn = MockConnector::new("binance", rl);
        conn.set_config(crate::connectors::BrokerConfig {
            sandbox: false,
            ..Default::default()
        });
        let req = OrderRequest {
            symbol: "BTCUSDT".into(),
            side: "buy".into(),
            volume: 0.001,
            sl: None,
            tp: None,
            magic: None,
        };
        let mkt = RiskMarketData {
            bid: 1000.0,
            ask: 1000.02,
            spread_points: 2,
            equity: 10000.0,
            point_value_per_lot: 10.0,
        };
        assert!(matches!(
            conn.place_order(&req, &mkt).await,
            Err(BrokerError::SandboxRequired)
        ));
    }

    #[tokio::test]
    async fn mock_connector_abre_ceposicao_e_reconcilia() {
        let rl = Arc::new(crate::connectors::RateLimiter::new());
        let conn = MockConnector::new("mexc", rl);
        let req = OrderRequest {
            symbol: "ETHUSDT".into(),
            side: "buy".into(),
            volume: 0.01,
            sl: None,
            tp: None,
            magic: None,
        };
        let mkt = RiskMarketData {
            bid: 1000.0,
            ask: 1000.02,
            spread_points: 2,
            equity: 10000.0,
            point_value_per_lot: 10.0,
        };
        let ticket = conn.place_order(&req, &mkt).await.unwrap();
        assert!(conn.positions().iter().any(|p| p.ticket == ticket));
        conn.reconcile_positions().await.unwrap();
        assert!(conn.positions().iter().any(|p| p.ticket == ticket));
    }

    #[tokio::test]
    async fn mock_connector_fecha_ceposicao_e_update_cache() {
        let rl = Arc::new(crate::connectors::RateLimiter::new());
        let conn = MockConnector::new("mt5", rl);
        let req = OrderRequest {
            symbol: "XAUUSD".into(),
            side: "sell".into(),
            volume: 0.1,
            sl: None,
            tp: None,
            magic: None,
        };
        let mkt = RiskMarketData {
            bid: 1000.0,
            ask: 1000.02,
            spread_points: 2,
            equity: 10000.0,
            point_value_per_lot: 10.0,
        };
        let ticket = conn.place_order(&req, &mkt).await.unwrap();
        conn.close_position(ticket).await.unwrap();
        assert!(conn.positions().is_empty());
    }
}
