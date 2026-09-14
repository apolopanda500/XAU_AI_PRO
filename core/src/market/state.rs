// XAU AI PRO Core - Estado compartilhado do servidor WS.
// Guarda o servico de mercado e a uniao de assinaturas.

use std::collections::HashSet;
use std::sync::Arc;
use tokio::sync::RwLock;

use axum::extract::ws::{Message, WebSocket};
use futures_util::stream::SplitSink;
use futures_util::SinkExt;

use super::service::MarketDataService;
use crate::protocol::{WsMessage, DEFAULT_SYMBOLS};

pub type WsSender = SplitSink<WebSocket, Message>;

/// Estado compartilhado do servidor WS (mercado + assinaturas).
pub struct WsSharedState {
    pub market: Arc<MarketDataService>,
    /// Simbolos assinados pelo conjunto de clientes (uniao).
    pub subscriptions: RwLock<HashSet<String>>,
}

impl WsSharedState {
    pub fn new(market: Arc<MarketDataService>) -> Self {
        let mut initial = HashSet::new();
        for s in DEFAULT_SYMBOLS {
            initial.insert((*s).to_string());
        }
        Self {
            market,
            subscriptions: RwLock::new(initial),
        }
    }

    pub async fn is_subscribed(&self, symbol: &str) -> bool {
        self.subscriptions.read().await.contains(symbol)
    }

    pub async fn add_all(&self, symbols: Vec<String>) {
        let mut subs = self.subscriptions.write().await;
        for s in symbols {
            subs.insert(s);
        }
    }

    pub async fn remove_all(&self, symbols: Vec<String>) {
        let mut subs = self.subscriptions.write().await;
        for s in symbols {
            subs.remove(&s);
        }
    }
}

/// Serializa uma mensagem do protocolo v1 para texto WS.
pub fn encode_message(msg: &WsMessage) -> String {
    serde_json::to_string(msg).unwrap_or_else(|_| {
        "{\"type\":\"Error\",\"code\":\"INTERNAL\",\"message\":\"Falha ao serializar\"}".into()
    })
}

/// Envia texto pronto ao cliente.
pub async fn push_text(sender: &mut WsSender, text: String) -> bool {
    sender.send(Message::Text(text)).await.is_ok()
}

/// Envia erro tipado ao cliente.
pub async fn send_error(
    sender: &mut WsSender,
    code: &str,
    message: String,
    request_id: Option<String>,
) {
    use crate::protocol::{ProtocolError, WsMessage};
    let msg = WsMessage::Error(ProtocolError {
        code: code.into(),
        message,
        request_id,
    });
    let _ = push_text(sender, encode_message(&msg)).await;
}
