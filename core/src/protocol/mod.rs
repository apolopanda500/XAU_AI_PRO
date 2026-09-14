// XAU AI PRO Core — Protocolo de Comunicação v1
// Contrato versionado entre Rust Core, frontend React e EA MT5.
// Regras de compatibilidade:
// - Campos novos sempre opcionais (`#[serde(default)]`) — clientes antigos ignoram.
// - Campos existentes nunca mudam de tipo nem de nome dentro da v1.
// - Quebra intencional de compatibilidade exige bump para v2 + handshake recusa v1.
// Envelope: `{ "protocol": "xau-ai-pro/1", "type": "<Variante>", ...campos }`

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

/// Origem da conexão no handshake.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ClientKind {
    React,
    EaMt5,
    Cli,
    Unknown,
}

impl Default for ClientKind {
    fn default() -> Self {
        Self::Unknown
    }
}

/// Primeira mensagem enviada pelo Core a cada conexão (resposta ao Hello).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelloMessage {
    /// Versão do protocolo aceita (ex.: "1.0.0").
    pub version: String,
    /// Versão do Core (Cargo pkg version).
    pub core_version: String,
    /// Símbolos padrão assináveis.
    #[serde(default)]
    pub symbols: Vec<String>,
    /// Intervalo de heartbeat recomendado em ms.
    #[serde(default = "default_ping_interval")]
    pub ping_interval_ms: u64,
}

fn default_ping_interval() -> u64 {
    WS_PING_INTERVAL_MS
}

/// Resposta ao heartbeat com eco do timestamp do cliente.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PongMessage {
    pub request_id: String,
    /// Timestamp enviado pelo cliente (ms desde epoch).
    pub ts_ms: i64,
    /// Timestamp do servidor ao responder (ms desde epoch).
    pub server_ts_ms: i64,
}

/// Erro tipado com código estável (contrato para UI e EA).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProtocolError {
    /// Código estável (ex.: "BAD_REQUEST", "VERSION_MISMATCH", "MT5_OFFLINE").
    pub code: String,
    /// Mensagem legível em PT-BR.
    pub message: String,
    /// Correlação com o comando que originou o erro (quando houver).
    #[serde(default)]
    pub request_id: Option<String>,
}

/// Ordem enviada por comando WS — carrega `request_id` para correlação.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderCommand {
    #[serde(flatten)]
    pub order: OrderRequest,
    /// Identificador único do comando (UUID v4 no frontend).
    pub request_id: String,
}

/// Requisição de ordem
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderRequest {
    pub symbol: String,
    pub side: String,
    pub volume: f64,
    #[serde(default)]
    pub sl: Option<f64>,
    #[serde(default)]
    pub tp: Option<f64>,
    #[serde(default)]
    pub magic: Option<u32>,
}

/// Resposta de ordem (correlacionada via `request_id`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderResponse {
    pub success: bool,
    pub ticket: u64,
    pub message: String,
    /// Eco do `request_id` do comando que originou a resposta.
    #[serde(default)]
    pub request_id: Option<String>,
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

/// Mensagem WebSocket (Rust → Frontend / EA MT5)
/// Envelope na rede: `{ "protocol": "xau-ai-pro/1", "type": "<Variante>", ... }`
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum WsMessage {
    /// Resposta ao handshake — primeira mensagem de cada conexão.
    Hello(HelloMessage),
    /// Cotação atualizada.
    Quote(Quote),
    /// Atualização da conta.
    Account(AccountInfo),
    /// Atualização de posição.
    PositionUpdate(Position),
    /// Resposta de ordem (correlacionada via `request_id`).
    OrderResponse(OrderResponse),
    /// Snapshot de estado do sistema.
    SystemState(SystemState),
    /// Resposta a ping (heartbeat).
    Pong(PongMessage),
    /// Erro tipado com código estável.
    Error(ProtocolError),
}

/// Comando WebSocket (Frontend / EA MT5 → Rust)
/// Envelope na rede: `{ "protocol": "xau-ai-pro/1", "type": "<Variante>", ... }`
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum WsCommand {
    /// Handshake — deve ser o primeiro comando de cada conexão.
    Hello {
        client: ClientKind,
        version: String,
    },
    Subscribe {
        symbols: Vec<String>,
    },
    Unsubscribe {
        symbols: Vec<String>,
    },
    PlaceOrder(OrderCommand),
    ClosePosition {
        ticket: u64,
        request_id: String,
    },
    CancelOrder {
        ticket: u64,
        request_id: String,
    },
    GetAccount {
        request_id: String,
    },
    GetPositions {
        request_id: String,
    },
    /// Heartbeat com eco do timestamp para medir latência.
    Ping {
        request_id: String,
        ts_ms: i64,
    },
}

/// Códigos de erro estáveis do protocolo v1.
pub mod error_codes {
    /// Comando malformado ou campo obrigatório ausente.
    pub const BAD_REQUEST: &str = "BAD_REQUEST";
    /// Versão do protocolo do cliente incompatível com o Core.
    pub const VERSION_MISMATCH: &str = "VERSION_MISMATCH";
    /// MT5 indisponível (bridge offline ou EA sem resposta).
    pub const MT5_OFFLINE: &str = "MT5_OFFLINE";
    /// Ordem rejeitada pela validação de risco do Core.
    pub const ORDER_REJECTED: &str = "ORDER_REJECTED";
    /// Recurso não encontrado (posição, ordem, símbolo).
    pub const NOT_FOUND: &str = "NOT_FOUND";
    /// Erro interno do Core.
    pub const INTERNAL: &str = "INTERNAL";
}

/// Nome do envelope na rede (constante, nunca muda dentro da v1).
pub const PROTOCOL_ENVELOPE: &str = "xau-ai-pro/1";

/// Constantes do protocolo
pub const PROTOCOL_VERSION: &str = "1.0.0";
pub const WS_PING_INTERVAL_MS: u64 = 30000;
pub const DEFAULT_SYMBOLS: &[&str] = &["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"];

#[cfg(test)]
mod tests {
    use super::*;

    /// Cliente antigo (sem campos novos) continua parseando na v1.
    #[test]
    fn ordem_antiga_sem_request_id_parseia() {
        let json = r#"{"symbol":"XAUUSD","side":"buy","volume":0.1}"#;
        let req: OrderRequest = serde_json::from_str(json).expect("parse ordem antiga");
        assert_eq!(req.symbol, "XAUUSD");
        assert!(req.sl.is_none());
    }

    /// Resposta antiga (sem request_id) continua parseando na v1.
    #[test]
    fn resposta_antiga_sem_request_id_parseia() {
        let json = r#"{"success":true,"ticket":123,"message":"ok"}"#;
        let resp: OrderResponse = serde_json::from_str(json).expect("parse resposta antiga");
        assert!(resp.request_id.is_none());
    }

    /// Erro novo serializa com envelope taggeado.
    #[test]
    fn erro_tipado_serializa_com_type() {
        let msg = WsMessage::Error(ProtocolError {
            code: error_codes::MT5_OFFLINE.into(),
            message: "MT5 indisponível".into(),
            request_id: None,
        });
        let json = serde_json::to_string(&msg).expect("serializa erro");
        assert!(json.contains(r#""type":"Error""#));
        assert!(json.contains("MT5_OFFLINE"));
    }

    /// Handshake hello parseia a origem do cliente.
    #[test]
    fn hello_parseia_origem() {
        let json = r#"{"type":"Hello","client":"react","version":"1.0.0"}"#;
        let cmd: WsCommand = serde_json::from_str(json).expect("parse hello");
        assert!(matches!(
            cmd,
            WsCommand::Hello {
                client: ClientKind::React,
                ..
            }
        ));
    }
}
