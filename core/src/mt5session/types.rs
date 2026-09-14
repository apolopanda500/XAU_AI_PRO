// XAU AI PRO Core — Sessão MT5 (item 6 do roadmap).
// Estado de conexão do EA MT5: handshake, heartbeat e reconciliação.
// Parte 1: tipos (payloads HTTP do EA + sessão).

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Estado da conexão do EA MT5.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Mt5LinkState {
    /// Nenhum EA conectado ainda.
    Offline,
    /// Handshake OK, heartbeat dentro do prazo.
    Online,
    /// Heartbeat atrasado além do limite (reconciliação pendente).
    Stale,
}

/// Snapshot de posição reportado pelo EA (reconciliação).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EaPosition {
    pub ticket: u64,
    pub symbol: String,
    pub side: String,
    pub volume: f64,
    pub open_price: f64,
    pub current_price: f64,
    pub profit: f64,
    pub magic: u32,
}

/// Payload do handshake do EA (POST /api/ea/hello).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EaHello {
    /// Versão do protocolo (major precisa ser "1").
    pub version: String,
    /// Número da conta MT5 (login).
    pub login: String,
    /// Servidor da corretora (ex.: "MetaQuotes-Demo").
    pub server: String,
    /// Símbolos que o EA publica.
    #[serde(default)]
    pub symbols: Vec<String>,
    /// Magic number do EA.
    #[serde(default)]
    pub magic: u32,
}

/// Payload do heartbeat do EA (POST /api/ea/heartbeat).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EaHeartbeat {
    pub login: String,
    /// Posições abertas no terminal (para reconciliação).
    #[serde(default)]
    pub positions: Vec<EaPosition>,
    /// Cotação de referência (símbolo principal do EA).
    #[serde(default)]
    pub quote: Option<crate::protocol::Quote>,
}

/// Resposta do Core ao EA.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EaAck {
    pub ok: bool,
    pub core_version: String,
    pub protocol_version: String,
    /// Comandos pendentes para o EA executar (ordens do React).
    #[serde(default)]
    pub pending_commands: Vec<EaCommand>,
    pub message: String,
}

/// Comando do Core para o EA executar (polling).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EaCommand {
    /// Correlação com o comando WS original do React.
    pub request_id: String,
    pub kind: EaCommandKind,
}

/// Tipo de comando para o EA.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum EaCommandKind {
    PlaceOrder(crate::protocol::OrderRequest),
    ClosePosition { ticket: u64 },
    CancelOrder { ticket: u64 },
}

/// Sessão ativa do EA MT5 no Core.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Mt5Session {
    pub login: String,
    pub server: String,
    pub state: Mt5LinkState,
    pub symbols: Vec<String>,
    pub magic: u32,
    pub connected_at: DateTime<Utc>,
    pub last_heartbeat: DateTime<Utc>,
    /// Posições segundo o último heartbeat (lado EA).
    #[serde(default)]
    pub ea_positions: Vec<EaPosition>,
    /// Comandos enfileirados aguardando coleta do EA.
    #[serde(default)]
    pub pending: Vec<EaCommand>,
    /// Contador de heartbeats recebidos (diagnóstico).
    #[serde(default)]
    pub heartbeat_count: u64,
}

/// Limite de staleness do heartbeat em segundos.
pub const MT5_HEARTBEAT_TIMEOUT_SEC: i64 = 30;
