// XAU AI PRO Core — MT5 Bridge
// Comunicação com o MetaTrader 5 via HTTP local ou named pipe.
// O EA MQL5 pode expor uma API local que este módulo consome.

use reqwest;
use tracing::info;

use crate::config::MT5Config;
use crate::protocol::{AccountInfo, OrderRequest, OrderResponse, Position, Quote};

/// Bridge para comunicação com o gateway local do XAU AI PRO.
///
/// O comentario antigo desta linha dizia "o EA MQL5 pode expor uma API local".
/// Quem ocupa a porta 9001 e o **gateway Python** (empacotado como
/// `mt5-gateway.exe`), nao o EA. Isso fazia o core chamar rotas que o
/// gateway nao tem.
#[derive(Clone)]
pub struct MT5Bridge {
    config: MT5Config,
    base_url: String,
    client: reqwest::Client,
    /// Token do gateway. O core so recebe `XAU_CORE_HEALTH_TOKEN`; o
    /// `XAU_GATEWAY_TOKEN` precisa ser repassado pelo launcher, senao toda
    /// chamada autenticada volta 401.
    token: Option<String>,
}

impl MT5Bridge {
    pub async fn new(config: &MT5Config) -> anyhow::Result<Self> {
        let base_url = config
            .local_api_url
            .clone()
            .unwrap_or_else(|| "http://127.0.0.1:9001".to_string());

        let token = std::env::var("XAU_GATEWAY_TOKEN")
            .ok()
            .filter(|value| !value.trim().is_empty());

        info!(
            "MT5Bridge iniciando — URL base: {} (token: {})",
            base_url,
            if token.is_some() { "sim" } else { "nao" }
        );

        let mut builder = reqwest::Client::builder().timeout(std::time::Duration::from_secs(5));
        if let Some(value) = token.as_deref() {
            builder = builder.default_headers(
                [(
                    reqwest::header::AUTHORIZATION,
                    format!("Bearer {value}").parse()?,
                )]
                .into_iter()
                .collect(),
            );
        }
        let client = builder.build()?;

        let bridge = Self {
            config: config.clone(),
            base_url,
            client,
            token,
        };

        // Testa conexão
        bridge.health_check().await?;
        info!("MT5 Bridge conectado com sucesso");

        Ok(bridge)
    }

    /// Verifica saúde da conexão.
    ///
    /// A rota e `/api/health`. O caminho `/health` devolvia 404: o gateway
    /// expoe `/` e `/api/health` (mt5_gateway.py) e FastAPI expoe
    /// `/api/health`. Com o 404 o `MT5Bridge::new` falhava, `bridge` ficava
    /// `None` para sempre e o WebSocket 9002 nao entregava nenhuma cotacao.
    pub async fn health_check(&self) -> anyhow::Result<bool> {
        let url = format!("{}/api/health", self.base_url);
        match self.client.get(&url).send().await {
            Ok(resp) if resp.status().is_success() => Ok(true),
            Ok(resp) => Err(anyhow::anyhow!("MT5 health check: HTTP {}", resp.status())),
            Err(e) => Err(anyhow::anyhow!("MT5 health check erro: {}", e)),
        }
    }

    /// Busca cotação de um símbolo via MT5
    pub async fn get_quote(&self, symbol: &str) -> anyhow::Result<Quote> {
        let url = format!("{}/api/mt5/quote", self.base_url);
        let resp = self
            .client
            .get(&url)
            .query(&[("symbol", symbol)])
            .send()
            .await?;
        let quote: Quote = resp.json().await?;
        Ok(quote)
    }

    /// Busca todas as cotações
    pub async fn get_all_quotes(&self) -> anyhow::Result<Vec<Quote>> {
        let url = format!("{}/api/mt5/quotes", self.base_url);
        let resp = self.client.get(&url).send().await?;
        let quotes: Vec<Quote> = resp.json().await?;
        Ok(quotes)
    }

    /// Busca informações da conta
    pub async fn get_account_info(&self) -> anyhow::Result<AccountInfo> {
        let url = format!("{}/api/mt5/account", self.base_url);
        let resp = self.client.get(&url).send().await?;
        let info: AccountInfo = resp.json().await?;
        Ok(info)
    }

    /// Busca posições abertas
    pub async fn get_positions(&self) -> anyhow::Result<Vec<Position>> {
        let url = format!(
            "{}/api/mt5/positions?magic={}",
            self.base_url, self.config.magic_number
        );
        let resp = self.client.get(&url).send().await?;
        let positions: Vec<Position> = resp.json().await?;
        Ok(positions)
    }

    /// Envia ordem para MT5
    pub async fn send_order(&self, request: &OrderRequest) -> anyhow::Result<OrderResponse> {
        let url = format!("{}/api/mt5/order", self.base_url);
        let resp = self.client.post(&url).json(request).send().await?;
        let response: OrderResponse = resp.json().await?;
        Ok(response)
    }

    /// Fecha posição
    pub async fn close_position(&self, ticket: u64) -> anyhow::Result<OrderResponse> {
        let url = format!("{}/api/mt5/close/{}", self.base_url, ticket);
        let resp = self.client.post(&url).send().await?;
        let response: OrderResponse = resp.json().await?;
        Ok(response)
    }

    /// Cancela ordem pendente
    pub async fn cancel_order(&self, ticket: u64) -> anyhow::Result<OrderResponse> {
        let url = format!("{}/api/mt5/cancel/{}", self.base_url, ticket);
        let resp = self.client.post(&url).send().await?;
        let response: OrderResponse = resp.json().await?;
        Ok(response)
    }
}
