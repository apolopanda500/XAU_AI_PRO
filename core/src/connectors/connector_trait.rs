// XAU AI PRO Core — Trait unificado de conector de broker.
// Garante que qualquer exchange (MT5, Binance, MEXC, futuro) seja
// operado com as mesmas garantias de sandbox e auditoria.

use crate::protocol::OrderRequest;
use crate::protocol::{AccountInfo, Position};
use crate::risk::RiskMarketData;
use chrono::DateTime;
use std::sync::Arc;
use thiserror::Error;

/// Erros de conector de corretora.
#[derive(Debug, Error)]
pub enum BrokerError {
    #[error("conector não inicializado: {0}")]
    NotInitialized(String),
    #[error("sandbox desativado: operação bloqueada em produção sem autorização")]
    SandboxRequired,
    #[error("exchange offline / indisponível: {0}")]
    Offline(String),
    #[error("posição não encontrada (ticket={ticket})")]
    PositionNotFound { ticket: u64 },
    #[error("rate limit: {0}")]
    RateLimit(String),
    #[error("operação rejeitada pela corretora: {0}")]
    Rejected(String),
}

/// Conexão e status de uma corretora.
pub struct BrokerStatus {
    pub exchange: String,
    pub online: bool,
    pub sandbox: bool,
    pub accounts: Vec<AccountInfo>,
    pub last_heartbeat: Option<DateTime<chrono::Utc>>,
    pub symbol_mappings: Vec<SymbolMapping>,
}

/// Mapeamento de símbolo local ⇄ símbolo da corretora.
pub struct SymbolMapping {
    pub local_symbol: String,
    /// Símbolo na corretora (ex.: XAUUSD, BTCUSDT).
    pub broker_symbol: String,
    /// Configuração de ponto (convenção de preços).
    pub point: f64,
    /// Valor do ponto por lote em USD (para cálculos de risco consistentes).
    pub point_value_per_lot: f64,
}

/// Interface que todo conector de corretora deve implementar.
pub trait BrokerConnector: Send + Sync {
    /// Nome da exchange (ex.: "mt5", "binance", "mexc").
    fn exchange(&self) -> &str;

    /// Tenta conectar/testar a corretora. Se sandbox=true, opera em modo
    /// de teste sem risco real de capital.
    fn connect(&self) -> Result<(), BrokerError>;

    /// Verifica se a corretora está online e reusável.
    fn is_online(&self) -> bool;

    /// Indica se o conector opera em sandbox (apenas simulação / demo).
    fn sandbox(&self) -> bool;

    /// Retorna as contas disponíveis do conector.
    fn accounts(&self) -> Vec<AccountInfo>;

    /// Posições abertas conforme o último heartbeat/reconciliação.
    fn positions(&self) -> Vec<Position>;

    /// Dados de mercado necessários ao cálculo de risco para o símbolo.
    fn risk_market_data(&self, local_symbol: &str) -> Option<RiskMarketData>;

    /// Envia uma ordem ao broker (respeitando rate limit externo + interno).
    fn place_order(
        &self,
        request: &OrderRequest,
        risk_data: &RiskMarketData,
    ) -> Result<u64, BrokerError>;

    /// Cancela ordem pelo ticket.
    fn cancel_order(&self, ticket: u64) -> Result<(), BrokerError>;

    /// Fecha posição pelo ticket.
    fn close_position(&self, ticket: u64) -> Result<(), BrokerError>;

    /// Último status do conector (para endpoint de saúde e auditoria).
    fn status(&self) -> BrokerStatus;

    /// Mapeia símbolo local para o símbolo da corretora.
    fn symbol_mapping(&self, local_symbol: &str) -> Option<&SymbolMapping>;

    /// Reconcilia posições locais com o estado real da corretora.
    fn reconcile_positions(&self) -> Result<(), BrokerError>;
}

/// Connector factory: constrói instâncias configuradas a partir do config.
pub trait BrokerFactory: Send + Sync {
    fn exchange(&self) -> &str;
    fn build(&self, config: &BrokerConfig) -> Result<Arc<dyn BrokerConnector>, BrokerError>;
}

/// Configuração de um conector de corretora.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(default)]
pub struct BrokerConfig {
    /// Liga ou desliga o conector.
    pub enabled: bool,
    /// Operar em sandbox/demo (true) ou conta real (false).
    pub sandbox: bool,
    /// Credenciais (API key, token, endpoint). São carregadas de environment
    /// ou vault externo — NÃO devem ser armazenadas em texto puro no repo.
    pub api_key_env: Option<String>,
    pub api_secret_env: Option<String>,
    pub base_url: Option<String>,
    /// Token bucket: burst máximo e refill por segundo.
    pub rate_limit_burst: u32,
    pub rate_limit_refill_per_sec: u32,
    /// Lista de símbolos locais mapeados para este broker.
    pub symbols: Vec<BrokerSymbolMapping>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(default)]
pub struct BrokerSymbolMapping {
    pub local_symbol: String,
    pub broker_symbol: String,
    pub point: f64,
    pub point_value_per_lot: f64,
}

impl Default for BrokerConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            sandbox: true,
            api_key_env: None,
            api_secret_env: None,
            base_url: None,
            rate_limit_burst: 10,
            rate_limit_refill_per_sec: 5,
            symbols: Vec::new(),
        }
    }
}

impl Default for BrokerSymbolMapping {
    fn default() -> Self {
        Self {
            local_symbol: String::new(),
            broker_symbol: String::new(),
            point: 0.01,
            point_value_per_lot: 10.0,
        }
    }
}
