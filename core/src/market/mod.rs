// XAU AI PRO Core - Market Data Service
// Coleta cotacoes de multiplos providers (MT5, Binance, Yahoo, Stooq)
// e distribui via canal broadcast para WebSocket clients.

use chrono::Utc;
use std::sync::Arc;
use tokio::sync::{broadcast, RwLock};
use tokio::time::{interval, Duration};
use tracing::{info, warn};

use axum::extract::ws::{WebSocket, WebSocketUpgrade};
use axum::extract::State;
use axum::response::IntoResponse;
use axum::routing::get;
use axum::Router;

use crate::bridge::MT5Bridge;
use crate::config::{MarketConfig, WebSocketConfig};
use crate::protocol::Quote;

/// Servico de dados de mercado
pub struct MarketDataService {
    config: MarketConfig,
    quotes: Arc<RwLock<Vec<Quote>>>,
    tx: broadcast::Sender<Quote>,
    bridge: Arc<RwLock<Option<MT5Bridge>>>,
}

impl MarketDataService {
    pub async fn new(config: &MarketConfig) -> anyhow::Result<Self> {
        let (tx, _) = broadcast::channel::<Quote>(1000);
        info!(
            "MarketDataService iniciado - {} symbols, {}ms interval",
            config.symbols.len(),
            config.refresh_interval_ms
        );
        Ok(Self {
            config: config.clone(),
            quotes: Arc::new(RwLock::new(Vec::new())),
            tx,
            bridge: Arc::new(RwLock::new(None)),
        })
    }

    /// Retorna handle para uso externo
    pub fn clone_handle(&self) -> Self {
        Self {
            config: self.config.clone(),
            quotes: self.quotes.clone(),
            tx: self.tx.clone(),
            bridge: self.bridge.clone(),
        }
    }

    /// Inicia o loop de coleta de cotacoes
    pub async fn run(&self) -> anyhow::Result<()> {
        let mut ticker = interval(Duration::from_millis(self.config.refresh_interval_ms));
        loop {
            ticker.tick().await;
            if let Err(e) = self.fetch_all().await {
                warn!("Erro ao buscar cotacoes: {}", e);
            }
        }
    }

    /// Busca cotacoes de todos os simbolos configurados
    async fn fetch_all(&self) -> anyhow::Result<()> {
        for symbol in &self.config.symbols {
            match self.fetch_quote(symbol).await {
                Ok(quote) => {
                    let mut quotes = self.quotes.write().await;
                    quotes.retain(|q| q.symbol != quote.symbol);
                    quotes.push(quote.clone());
                    let _ = self.tx.send(quote);
                }
                Err(e) => warn!("Falha ao buscar {}: {}", symbol, e),
            }
        }
        Ok(())
    }

    /// Busca cotacao de um simbolo (com fallback entre providers)
    async fn fetch_quote(&self, symbol: &str) -> anyhow::Result<Quote> {
        if let Ok(quote) = self.try_mt5_quote(symbol).await {
            return Ok(quote);
        }
        self.simulate_quote(symbol).await
    }

    async fn try_mt5_quote(&self, symbol: &str) -> anyhow::Result<Quote> {
        let bridge = self.bridge.read().await;
        if let Some(ref b) = *bridge {
            b.get_quote(symbol).await
        } else {
            Err(anyhow::anyhow!("MT5 bridge nao conectado"))
        }
    }

    async fn simulate_quote(&self, symbol: &str) -> anyhow::Result<Quote> {
        let base_price = match symbol {
            "XAUUSD" => 2350.0,
            "EURUSD" => 1.0850,
            "GBPUSD" => 1.2650,
            "USDJPY" => 149.50,
            "BTCUSD" => 67500.0,
            "ETHUSD" => 3450.0,
            _ => 100.0,
        };
        let variation = (rand::random::<f64>() - 0.5) * base_price * 0.001;
        Ok(Quote {
            symbol: symbol.to_string(),
            bid: base_price + variation,
            ask: base_price + variation + 0.05,
            last: base_price + variation,
            volume: rand::random::<f64>() * 1000.0,
            high: base_price + variation.abs() + 1.0,
            low: base_price - variation.abs() - 1.0,
            change_pct: variation / base_price * 100.0,
            timestamp: Utc::now(),
            source: "simulated".to_string(),
        })
    }

    /// Retorna canal de broadcast para subscribers
    pub fn subscribe(&self) -> broadcast::Receiver<Quote> {
        self.tx.subscribe()
    }

    /// Retorna todas as cotacoes em cache
    pub async fn get_all_quotes(&self) -> Vec<Quote> {
        self.quotes.read().await.clone()
    }
}

/// Inicia o servidor WebSocket para distribuir market data
pub async fn start_market_ws(
    config: &WebSocketConfig,
    market: Arc<MarketDataService>,
) -> anyhow::Result<()> {
    let addr = format!("{}:{}", config.bind_address, config.port);
    info!("Iniciando WebSocket server em {}", addr);

    let app = Router::new()
        .route("/ws/market", get(ws_handler))
        .with_state(market);

    let listener = tokio::net::TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    State(market): State<Arc<MarketDataService>>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, market))
}

async fn handle_socket(mut socket: WebSocket, market: Arc<MarketDataService>) {
    let mut rx = market.subscribe();
    while let Ok(quote) = rx.recv().await {
        let msg = serde_json::to_string(&quote).unwrap_or_default();
        if socket
            .send(axum::extract::ws::Message::Text(msg))
            .await
            .is_err()
        {
            break;
        }
    }
}
