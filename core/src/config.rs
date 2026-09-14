// Configuração do XAU AI PRO Core
// Carregada de arquivo JSON, environment variables, ou defaults.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use tracing::warn;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(default)]
pub struct Config {
    pub app: AppConfig,
    pub mt5: MT5Config,
    pub market: MarketConfig,
    pub websocket: WebSocketConfig,
    pub http: HttpConfig,
    pub database: DatabaseConfig,
    pub risk: crate::risk::RiskConfig,
    pub strategy: crate::strategy::StrategyConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct AppConfig {
    pub name: String,
    pub version: String,
    pub mode: String, // "development" | "production"
    pub data_dir: Option<PathBuf>,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            name: "XAU AI PRO Core".into(),
            version: env!("CARGO_PKG_VERSION").into(),
            mode: "production".into(),
            data_dir: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct MT5Config {
    pub enabled: bool,
    pub terminal_path: Option<String>,
    pub magic_number: u32,
    pub local_api_url: Option<String>, // URL do API local do MT5 se disponível
}

impl Default for MT5Config {
    fn default() -> Self {
        Self {
            enabled: true,
            terminal_path: None,
            magic_number: 2026001,
            local_api_url: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct MarketConfig {
    pub symbols: Vec<String>,
    pub refresh_interval_ms: u64,
    pub providers: Vec<String>, // "mt5" | "binance" | "mexc" | "yahoo" | "stooq"
    /// Permite cotacoes sinteticas somente em desenvolvimento/paper.
    /// Deve permanecer false em producao para impedir dados falsos.
    pub allow_simulated_data: bool,
}

impl Default for MarketConfig {
    fn default() -> Self {
        Self {
            symbols: vec![
                "XAUUSD".into(),
                "EURUSD".into(),
                "GBPUSD".into(),
                "USDJPY".into(),
                "BTCUSD".into(),
                "ETHUSD".into(),
            ],
            refresh_interval_ms: 1000,
            providers: vec!["mt5".into(), "binance".into(), "yahoo".into()],
            allow_simulated_data: false,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct WebSocketConfig {
    pub enabled: bool,
    pub bind_address: String,
    pub port: u16,
}

impl Default for WebSocketConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            bind_address: "127.0.0.1".into(),
            port: 9002,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct HttpConfig {
    pub enabled: bool,
    pub bind_address: String,
    pub port: u16,
}

impl Default for HttpConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            bind_address: "127.0.0.1".into(),
            port: 9003,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct DatabaseConfig {
    pub enabled: bool,
    pub path: Option<PathBuf>,
}

impl Default for DatabaseConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            path: None,
        }
    }
}

impl Config {
    pub fn data_dir_default() -> PathBuf {
        dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("XAU_AI_PRO")
    }

    pub fn load() -> Result<Self> {
        // Tenta carregar de config.json no data_dir ou current dir
        let paths = Self::config_paths();
        for path in &paths {
            if path.exists() {
                let contents = std::fs::read_to_string(path)?;
                let contents = contents.trim_start_matches('\u{feff}');
                let config: Config = serde_json::from_str(contents)
                    .with_context(|| format!("config invalido: {}", path.display()))?;
                info_configure(&config);
                return Ok(config);
            }
        }
        // Se não encontrou arquivo, usa defaults
        warn!("Arquivo de configuração não encontrado, usando defaults");
        let config = Config::default();
        info_configure(&config);
        Ok(config)
    }

    fn config_paths() -> Vec<PathBuf> {
        let mut paths = Vec::new();
        // 1) Caminho explicito definido pelo shell Tauri (var. de ambiente)
        if let Ok(p) = std::env::var("XAU_AI_PRO_CONFIG") {
            if !p.is_empty() {
                paths.push(PathBuf::from(p));
            }
        }
        // 2) Caminho canonico: %APPDATA%\XAU_AI_PRO\config.json (Roaming)
        //    Nao se usa mais %LOCALAPPDATA%\XAU_AI_PRO (legado, continha segredos)
        if let Some(base) = dirs::config_dir() {
            paths.push(base.join("XAU_AI_PRO").join("config.json"));
        }
        // 3) Diretorio atual (desenvolvedor / execucao manual do core)
        paths.push(PathBuf::from("config.json"));
        paths
    }
}

fn info_configure(config: &Config) {
    // Use tracing apenas se habilitado, evitando dependência cíclica com macros
    eprintln!(
        "[config] XAU AI PRO Core carregado — mode={}, ws={}:{}, http={}:{}",
        config.app.mode,
        config.websocket.bind_address,
        config.websocket.port,
        config.http.bind_address,
        config.http.port,
    );
}

// Manual implementação de Default para evitar dependência de serde defaults se não querer
// mas como já temos serde, podemos usar derive. Mantido para compatibilidade.
// impl Default for Config {
//     fn default() -> Self {
//         Self {
//             app: AppConfig::default(),
//             mt5: MT5Config::default(),
//             market: MarketConfig::default(),
//             websocket: WebSocketConfig::default(),
//             http: HttpConfig::default(),
//             database: DatabaseConfig::default(),
//         }
//     }
// }
