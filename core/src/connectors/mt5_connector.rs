// XAU AI PRO Core — Conector MT5 (item 9 do roadmap).
// Implementação do BrokerConnector para MetaTrader 5, reaproveitando
// o Mt5SessionManager e MT5Bridge existentes. Inclui sandbox, reconciliação
// de posições e rate limit.

use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, warn};

use super::{
    BrokerConnector, BrokerError, BrokerStatus, BrokerConfig,
    BrokerSymbolMapping, SymbolMapping,
};
use super::rate_limiter::RateLimiter;
use crate::bridge::MT5Bridge;
use crate::config::MT5Config as Mt5BackendConfig;
use crate::mt5session::Mt5SessionManager;
use crate::protocol::{AccountInfo, OrderRequest, Position};
use crate::risk::RiskMarketData;

pub struct Mt5Connector {
    exchange: String,
    config: BrokerConfig,
    session_manager: Arc<Mt5SessionManager>,
    bridge: Arc<RwLock<Option<MT5Bridge>>>,
    rate_limiter: Arc<RateLimiter>,
    positions_cache: Arc<RwLock<Vec<Position>>>,
    accounts_cache: Arc<RwLock<Vec<AccountInfo>>>,
    connected_at: Arc<RwLock<Option<chrono::DateTime<chrono::Utc>>>>,
}

impl Mt5Connector {
    pub fn new(
        session_manager: Arc<Mt5SessionManager>,
        rate_limiter: Arc<RateLimiter>,
    ) -> Self {
        Self {
            exchange: "mt5".into(),
            config: BrokerConfig::default(),
            session_manager,
            bridge: Arc::new(RwLock::new(None)),
            rate_limiter,
            positions_cache: Arc::new(RwLock::new(Vec::new())),
            accounts_cache: Arc::new(RwLock::new(Vec::new())),
            connected_at: Arc::new(RwLock::new(None)),
        }
    }

    pub fn reconfigure(&self, config: BrokerConfig) {
        self.config = config;
    }

    pub async fn connect_bridge(&self, mt5_config: &Mt5BackendConfig) -> Result<(), BrokerError> {
        if !mt5_config.enabled {
            return Err(BrokerError::NotInitialized("MT5 desabilitado na configuração".into()));
        }
        match MT5Bridge::new(mt5_config).await {
            Ok(bridge) => {
                let mut b = self.bridge.write().await;
                *b = Some(bridge);
                *self.connected_at.write().await = Some(chrono::Utc::now());
                info!("Mt5Connector conectado ao bridge");
                Ok(())
            }
            Err(e) => {
                warn!("Mt5Connector: falha ao conectar bridge: {}", e);
                Err(BrokerError::Offline(format!("{:?}", e)))
            }
        }
    }

    async fn require_bridge(&self) -> Result<Arc<MT5Bridge>, BrokerError> {
        let b = self.bridge.read().await;
        match b.as_ref() {
            Some(bridge) => Ok(Arc::clone(bridge)),
            None => Err(BrokerError::NotInitialized("MT5 Bridge não conectado".into())),
        }
    }

    async fn reconcile_from_bridge(&self) -> Result<(), BrokerError> {
        let bridge = self.require_bridge().await?;
        let positions = bridge.get_positions().await.map_err(|e| {
            BrokerError::Offline(format!("reconciliação de posições: {}", e))
        })?;
        let mut cache = self.positions_cache.write().await;
        *cache = positions;
        drop(cache);

        let account = bridge.get_account_info().await.map_err(|e| {
            BrokerError::Offline(format!("reconciliação de conta: {}", e))
        })?;
        let mut accounts = self.accounts_cache.write().await;
        accounts.clear();
        accounts.push(account);
        Ok(())
    }

    async fn symbol_mapping_for(&self, local_symbol: &str) -> Option<SymbolMapping> {
        self.config
            .symbols
            .iter()
            .find(|m| m.local_symbol == local_symbol)
            .map(|m| SymbolMapping {
                local_symbol: m.local_symbol.clone(),
                broker_symbol: m.broker_symbol.clone(),
                point: m.point,
                point_value_per_lot: m.point_value_per_lot,
            })
    }
}

impl BrokerConnector for Mt5Connector {