// XAU AI PRO Core — Protocolo de Comunicação
// Tipos compartilhados entre backend Rust e frontend (via JSON/WS)

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Cotação de mercado
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Quote {
    pub symbol: String,
    pub bid: f64,
    pub ask: f64,
    pub last: f64,
    pub volume: f64,
    pub high: f64,
    pub low: f64,
    pub change_pct: f64,
    pub timestamp: DateTime<Utc>,
    pub source: String,
}

/// Informação da conta
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountInfo {
    pub login: String,
    pub balance: f64,
    pub equity: f64,
    pub margin: f64,
    pub free_margin: f64,
    pub leverage: u32,
    pub server: String,
    pub currency: String,
    pub profit: f64,
}

/// Posição aberta
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub ticket: u64,
    pub symbol: String,
    pub side: String,
    pub volume: f64,
    pub open_price: f64,
    pub current_price: f64,
    pub sl: Option<f64>,
    pub tp: Option<f64>,
    pub profit: f64,
    pub open_time: DateTime<Utc>,
    pub magic: u32,
}

/// Requisição de ordem
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderRequest {
    pub symbol: String,
    pub side: String,
    pub volume: f64,
    pub sl: Option<f64>,
    pub tp: Option<f64>,
    pub magic: Option<u32>,
}

/// Resposta de ordem
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderResponse {
    pub success: bool,
    pub ticket: u64,
    pub message: String,
}

/// Candle (vela de preço)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Candle {
    pub symbol: String,
    pub timeframe: String,
    pub timestamp: DateTime<Utc>,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: f64,
}

/// Estado do sistema
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemState {
    pub status: String,
    pub reasons: Vec<String>,
    pub ai_status: String,
    pub ai_age_sec: i64,
    pub recent_events: i64,
    pub timestamp: DateTime<Utc>,
}

/// Mensagem WebSocket (Rust → Frontend)
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum WsMessage {
    Quote(Quote),
    Account(AccountInfo),
    PositionUpdate(Position),
    OrderResponse(OrderResponse),
    SystemState(SystemState),
    Error(String),
    Pong,
}

/// Comando WebSocket (Frontend → Rust)
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum WsCommand {
    Subscribe { symbols: Vec<String> },
    Unsubscribe { symbols: Vec<String> },
    PlaceOrder(OrderRequest),
    ClosePosition { ticket: u64 },
    CancelOrder { ticket: u64 },
    GetAccount,
    GetPositions,
    Ping,
}

/// Constantes do protocolo
pub const PROTOCOL_VERSION: &str = "1.0.0";
pub const WS_PING_INTERVAL_MS: u64 = 30000;
pub const DEFAULT_SYMBOLS: &[&str] = &["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"];
