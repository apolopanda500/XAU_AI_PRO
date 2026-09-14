// XAU AI PRO Core - Market Data Service
// Coleta cotacoes de multiplos providers (MT5, Binance, Yahoo, Stooq)
// e distribui via canal broadcast para WebSocket clients.

use chrono::Utc;
use std::sync::Arc;
use tokio::sync::{broadcast, RwLock};
use tokio::time::{interval, Duration};
use tracing::{info, warn};

use crate::bridge::MT5Bridge;
use crate::config::MarketConfig;
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

    pub async fn set_bridge(&self, bridge: MT5Bridge) {
        let mut slot = self.bridge.write().await;
        *slot = Some(bridge);
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

        if self.config.providers.iter().any(|p| p == "binance") {
            if let Ok(quote) = self.try_binance_quote(symbol).await {
                return Ok(quote);
            }
        }

        if self.config.allow_simulated_data
            && self.config.providers.iter().any(|p| p == "simulated")
        {
            return self.simulate_quote(symbol).await;
        }

        Err(anyhow::anyhow!(
            "nenhuma fonte real disponivel para {} e dados simulados estao desabilitados",
            symbol
        ))
    }

    async fn try_mt5_quote(&self, symbol: &str) -> anyhow::Result<Quote> {
        let bridge = self.bridge.read().await;
        if let Some(ref b) = *bridge {
            b.get_quote(symbol).await
        } else {
            Err(anyhow::anyhow!("MT5 bridge nao conectado"))
        }
    }

    async fn try_binance_quote(&self, symbol: &str) -> anyhow::Result<Quote> {
        let pair = match symbol {
            "BTCUSD" => "BTCUSDT",
            "ETHUSD" => "ETHUSDT",
            "BNBUSD" => "BNBUSDT",
            "XRPUSD" => "XRPUSDT",
            "DOGEUSD" => "DOGEUSDT",
            "LINKUSD" => "LINKUSDT",
            "AVAXUSD" => "AVAXUSDT",
            "SOLUSDT" => "SOLUSDT",
            "ADAUSDT" => "ADAUSDT",
            _ => anyhow::bail!("símbolo não suportado pela Binance: {}", symbol),
        };
        let data: serde_json::Value = reqwest::Client::new()
            .get("https://api.binance.com/api/v3/ticker/24hr")
            .query(&[("symbol", pair)])
            .send()
            .await?
            .error_for_status()?
            .json()
            .await?;
        let number = |key: &str| -> anyhow::Result<f64> {
            data[key]
                .as_str()
                .ok_or_else(|| anyhow::anyhow!("campo ausente: {}", key))?
                .parse::<f64>()
                .map_err(Into::into)
        };
        Ok(Quote {
            symbol: symbol.to_string(),
            bid: number("bidPrice")?,
            ask: number("askPrice")?,
            last: number("lastPrice")?,
            volume: number("volume")?,
            high: number("highPrice")?,
            low: number("lowPrice")?,
            change_pct: number("priceChangePercent")?,
            timestamp: Utc::now(),
            source: "binance_public".to_string(),
        })
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
