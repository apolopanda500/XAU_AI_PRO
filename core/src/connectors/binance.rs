use crate::protocol::{OrderResponse, Quote};
use anyhow::Result;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};

const BINANCE_SPOT_BASE: &str = "https://api.binance.com";
const BINANCE_FUTURES_BASE: &str = "https://fapi.binance.com";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BinanceConfig {
    pub api_key: String,
    pub secret_key: String,
    pub testnet: bool,
    pub market: BinanceMarket,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum BinanceMarket {
    Spot,
    Futures,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BinanceAccountInfo {
    pub balances: Vec<BinanceBalance>,
    pub can_trade: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BinanceBalance {
    pub asset: String,
    pub free: String,
    pub locked: String,
}

pub struct BinanceConnector {
    config: BinanceConfig,
    client: Client,
}

impl BinanceConnector {
    pub fn new(config: BinanceConfig) -> Self {
        Self {
            config,
            client: Client::new(),
        }
    }

    pub async fn ping() -> Result<bool> {
        let client = Client::new();
        let resp = client.get(format!("{}/api/v3/ping", BINANCE_SPOT_BASE)).send().await?;
        Ok(resp.status().is_success())
    }

    pub async fn get_price(&self, symbol: &str) -> Result<Quote> {
        let url = format!("{}/api/v3/ticker/24hr?symbol={}", BINANCE_SPOT_BASE, symbol);
        let resp = self.client.get(&url).send().await?;
        let data: serde_json::Value = resp.json().await?;
        Ok(Quote {
            symbol: symbol.to_string(),
            price: data["lastPrice"].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            bid: data["bidPrice"].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            ask: data["askPrice"].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            last: data["lastPrice"].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            volume: data["volume"].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            high: data["highPrice"].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            low: data["lowPrice"].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            change_pct: data["priceChangePercent"].as_str().unwrap_or("0").parse().unwrap_or(0.0),
            spread: data["askPrice"].as_str().unwrap_or("0").parse::<f64>().unwrap_or(0.0)
                - data["bidPrice"].as_str().unwrap_or("0").parse::<f64>().unwrap_or(0.0),
            digits: 2,
            point: 0.01,
            timestamp: SystemTime::now().duration_since(UNIX_EPOCH)?.as_millis().to_string(),
            source: "binance".to_string(),
        })
    }

    pub async fn get_account(&self) -> Result<BinanceAccountInfo> {
        let timestamp = Self::timestamp_ms();
        let query = format!("timestamp={}", timestamp);
        let signature = self.sign(&query);
        let url = format!("{}/api/v3/account?{}&signature={}", BINANCE_SPOT_BASE, query, signature);
        let resp = self.client.get(&url).header("X-MBX-APIKEY", &self.config.api_key).send().await?;
        let data: serde_json::Value = resp.json().await?;
        let balances: Vec<BinanceBalance> = data["balances"].as_array().unwrap_or(&vec![]).iter()
            .filter(|b| b["free"].as_str().unwrap_or("0").parse::<f64>().unwrap_or(0.0) > 0.0
                || b["locked"].as_str().unwrap_or("0").parse::<f64>().unwrap_or(0.0) > 0.0)
            .map(|b| BinanceBalance {
                asset: b["asset"].as_str().unwrap_or("").to_string(),
                free: b["free"].as_str().unwrap_or("0").to_string(),
                locked: b["locked"].as_str().unwrap_or("0").to_string(),
            }).collect();
        Ok(BinanceAccountInfo { balances, can_trade: data["canTrade"].as_bool().unwrap_or(false) })
    }

    pub async fn place_order(&self, symbol: &str, side: &str, order_type: &str, quantity: f64, price: Option<f64>) -> Result<OrderResponse> {
        let timestamp = Self::timestamp_ms();
        let mut params = format!("symbol={}&side={}&type={}&quantity={}&timestamp={}", symbol, side, order_type, quantity, timestamp);
        if let Some(p) = price { params.push_str(&format!("&price={}", p)); }
        let signature = self.sign(&params);
        let url = format!("{}/api/v3/order?{}&signature={}", BINANCE_SPOT_BASE, params, signature);
        let resp = self.client.post(&url).header("X-MBX-APIKEY", &self.config.api_key).send().await?;
        let data: serde_json::Value = resp.json().await?;
        Ok(OrderResponse {
            success: data.get("orderId").is_some(),
            order_id: data["orderId"].as_u64().unwrap_or(0).to_string(),
            message: data["status"].as_str().unwrap_or("ok").to_string(),
        })
    }

    pub async fn cancel_order(&self, symbol: &str, order_id: u64) -> Result<bool> {
        let timestamp = Self::timestamp_ms();
        let query = format!("symbol={}&orderId={}&timestamp={}", symbol, order_id, timestamp);
        let signature = self.sign(&query);
        let url = format!("{}/api/v3/order?{}&signature={}", BINANCE_SPOT_BASE, query, signature);
        let resp = self.client.delete(&url).header("X-MBX-APIKEY", &self.config.api_key).send().await?;
        Ok(resp.status().is_success())
    }

    fn sign(&self, data: &str) -> String {
        use hmac::{Hmac, Mac};
        use sha2::Sha256;
        type HmacSha256 = Hmac<Sha256>;
        let mut mac = HmacSha256::new_from_slice(self.config.secret_key.as_bytes())
            .expect("HMAC can take key of any size");
        mac.update(data.as_bytes());
        hex::encode(mac.finalize().into_bytes())
    }

    fn timestamp_ms() -> u128 {
        SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_millis()
    }
}
