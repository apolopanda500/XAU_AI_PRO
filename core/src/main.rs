// XAU AI PRO Core - Entry point (item 6: sessão MT5 + HTTP do EA).

use std::sync::Arc;
use tracing::{info, warn};

use xau_ai_pro_core::{Config, MT5Bridge, MarketDataService};

mod eahttp;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt().with_env_filter("info").init();

    let config = Arc::new(Config::load()?);
    info!("XAU AI PRO Core v0.1.0 - modo: {}", config.app.mode);
    info!("MT5 habilitado: {}", config.mt5.enabled);

    let mt5 = Arc::new(xau_ai_pro_core::mt5session::Mt5SessionManager::new());
    let risk = Arc::new(xau_ai_pro_core::risk::RiskEngine::default());
    risk.set_config(config.risk.clone()).await;
    let market_service = MarketDataService::new(&config.market).await?;
    let market = Arc::new(market_service);

    if config.websocket.enabled {
        let ws_config = config.websocket.clone();
        let ws_market = market.clone();
        let ws_mt5 = mt5.clone();
        let ws_risk = risk.clone();
        tokio::spawn(async move {
            let r = xau_ai_pro_core::market::start_market_ws_shared(
                &ws_config, ws_market, ws_mt5, ws_risk,
            )
            .await;
            if let Err(e) = r {
                warn!("Erro no servidor WebSocket: {}", e);
            }
        });
    }

    if config.http.enabled {
        let http_config = config.http.clone();
        let http_mt5 = mt5.clone();
        let http_market = market.clone();
        let http_risk = risk.clone();
        tokio::spawn(async move {
            if let Err(e) = eahttp::serve(&http_config, http_mt5, http_market, http_risk).await {
                warn!("Erro no HTTP do EA: {}", e);
            }
        });
    }

    let market_loop = market.clone();
    tokio::spawn(async move {
        if let Err(e) = market_loop.run().await {
            warn!("Market data loop error: {}", e);
        }
    });

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
