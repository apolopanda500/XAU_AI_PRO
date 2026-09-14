// XAU AI PRO Core — Library exports
// Exposição pública do motor Rust para uso interno e possíveis bindings futuros.

pub mod account;
pub mod bridge;
pub mod config;
pub mod connectors;
pub mod connectors_mock;
pub mod updates;
pub mod execution;
pub mod market;
pub mod mt5session;
pub mod protocol;
pub mod risk;
pub mod strategy;

pub use bridge::MT5Bridge;
pub use config::Config;
pub use execution::ExecutionEngine;
pub use market::MarketDataService;
pub use risk::RiskEngine;

/// Versão do core.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Inicializa e retorna o state do core, pronto para uso.
pub async fn init_core() -> anyhow::Result<CoreRuntime> {
    let config = Config::load()?;
    let market = MarketDataService::new(&config.market).await?;
    let bridge = if config.mt5.enabled {
        MT5Bridge::new(&config.mt5).await.ok()
    } else {
        None
    };
    Ok(CoreRuntime {
        config,
        market,
        bridge,
    })
}

/// Runtime do core, contendo todos os serviços ativos.
pub struct CoreRuntime {
    pub config: Config,
    pub market: MarketDataService,
    pub bridge: Option<MT5Bridge>,
}
