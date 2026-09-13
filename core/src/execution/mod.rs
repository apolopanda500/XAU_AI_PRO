// XAU AI PRO Core — Execution Engine
// Motor de execução de ordens: validação, envio, tracking, gestão de risco.

use crate::bridge::MT5Bridge;
use crate::protocol::{OrderRequest, OrderResponse, Position};

/// Engine de execução de ordens
pub struct ExecutionEngine {
    bridge: Option<MT5Bridge>,
    #[allow(dead_code)]
    positions: Vec<Position>,
    max_lot: f64,
    #[allow(dead_code)]
    max_risk_pct: f64,
    #[allow(dead_code)]
    max_daily_loss_pct: f64,
}

impl Default for ExecutionEngine {
    fn default() -> Self {
        Self::new()
    }
}

impl ExecutionEngine {
    pub fn new() -> Self {
        Self {
            bridge: None,
            positions: Vec::new(),
            max_lot: 0.5,
            max_risk_pct: 1.0,
            max_daily_loss_pct: 5.0,
        }
    }

    /// Define o bridge MT5
    pub fn set_bridge(&mut self, bridge: MT5Bridge) {
        self.bridge = Some(bridge);
    }

    /// Executa uma ordem (valida + envia via bridge)
    pub async fn execute(&self, request: OrderRequest) -> anyhow::Result<OrderResponse> {
        // 1. Validação básica
        if request.volume <= 0.0 || request.volume > self.max_lot {
            return Ok(OrderResponse {
                success: false,
                ticket: 0,
                message: format!(
                    "Volume inválido: {} (max: {})",
                    request.volume, self.max_lot
                ),
            });
        }

        // 2. Envia via bridge
        match &self.bridge {
            Some(bridge) => bridge.send_order(&request).await,
            None => Ok(OrderResponse {
                success: false,
                ticket: 0,
                message: "MT5 Bridge não conectado".to_string(),
            }),
        }
    }

    /// Fecha uma posição
    pub async fn close_position(&self, ticket: u64) -> anyhow::Result<OrderResponse> {
        match &self.bridge {
            Some(bridge) => bridge.close_position(ticket).await,
            None => Ok(OrderResponse {
                success: false,
                ticket,
                message: "MT5 Bridge não conectado".to_string(),
            }),
        }
    }

    /// Cancela ordem
    pub async fn cancel_order(&self, ticket: u64) -> anyhow::Result<OrderResponse> {
        match &self.bridge {
            Some(bridge) => bridge.cancel_order(ticket).await,
            None => Ok(OrderResponse {
                success: false,
                ticket,
                message: "MT5 Bridge não conectado".to_string(),
            }),
        }
    }

    /// Lista posições abertas
    pub async fn get_positions(&self) -> anyhow::Result<Vec<Position>> {
        match &self.bridge {
            Some(bridge) => bridge.get_positions().await,
            None => Ok(vec![]),
        }
    }
}
