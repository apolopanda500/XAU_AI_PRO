// XAU AI PRO Core - Entry point
// Motor de execucao critica, market data streaming, e bridge MT5.

use std::sync::Arc;
use tracing::{info, warn};

use xau_ai_pro_core::{Config, MT5Bridge, MarketDataService};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt().with_env_filter("info").init();

    let config = Arc::new(Config::load()?);
    info!("XAU AI PRO Core v0.1.0 - modo: {}", config.app.mode);
    info!("MT5 habilitado: {}", config.mt5.enabled);

    // Inicializa serviço de market data
    let market_service = MarketDataService::new(&config.market).await?;
    let market = Arc::new(market_service);

    // Inicia WebSocket server para frontend (se habilitado)
    if config.websocket.enabled {
        let ws_config = config.websocket.clone();
        let ws_market = market.clone();
        tokio::spawn(async move {
            if let Err(e) = xau_ai_pro_core::market::start_market_ws(&ws_config, ws_market).await {
                warn!("Erro no servidor WebSocket: {}", e);
            }
        });
    }

    // Inicia market data loop
    let market_loop = market.clone();
    tokio::spawn(async move {
        if let Err(e) = market_loop.run().await {
            warn!("Market data loop error: {}", e);
        }
    });

    // Inicializa bridge MT5
    let _bridge = if config.mt5.enabled {
        match MT5Bridge::new(&config.mt5).await {
            Ok(b) => {
                info!("MT5 Bridge conectado");
                Some(b)
            }
            Err(e) => {
                warn!("MT5 Bridge: {}", e);
                None
            }
        }
    } else {
        None
    };

    info!("XAU AI PRO Core pronto. Pressione Ctrl+C para sair.");
    tokio::signal::ctrl_c().await?;
    info!("Encerrando...");
    Ok(())
}
