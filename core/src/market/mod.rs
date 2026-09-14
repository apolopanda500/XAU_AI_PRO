// XAU AI PRO Core - Servidor WebSocket (protocolo v1).
// Rota fina: handshake, roteamento de comandos e difusão.

mod dispatch;
mod handler;
mod service;
mod state;
mod types;

pub use service::MarketDataService;
pub use state::{encode_message, send_error, WsSharedState};
pub use types::ServerRefs;

use std::sync::Arc;
use tracing::info;

use axum::extract::ws::{WebSocket, WebSocketUpgrade};
use axum::extract::State;
use axum::response::IntoResponse;
use axum::routing::get;
use axum::Router;
use futures_util::StreamExt;

use crate::config::WebSocketConfig;
use crate::protocol::WsCommand;
use dispatch::{dispatch, maybe_push_quote};

/// Inicia o servidor WebSocket para distribuir market data (protocolo v1).
pub async fn start_market_ws(
    config: &WebSocketConfig,
    market: Arc<MarketDataService>,
) -> anyhow::Result<()> {
    let addr = format!("{}:{}", config.bind_address, config.port);
    info!("Iniciando WebSocket server (protocolo v1) em {}", addr);

    let shared = Arc::new(WsSharedState::new(market));
    let app = Router::new()
        .route("/ws/market", get(ws_handler))
        .with_state(shared);

    let listener = tokio::net::TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    State(shared): State<Arc<WsSharedState>>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, shared))
}

async fn handle_socket(socket: WebSocket, shared: Arc<WsSharedState>) {
    let (sender, mut receiver) = socket.split();
    let mut rx = shared.market.subscribe();

    // Handshake: primeira mensagem precisa ser Hello.
    let hello = handler::await_hello(sender, &mut receiver).await;
    let (mut sender, client, version) = match hello {
        Some(v) => v,
        None => return,
    };

    if !handler::validate_version(&version, &mut sender).await {
        return;
    }
    handler::answer_hello(&mut sender).await;
    info!("WS handshake OK — cliente={:?} versao={}", client, version);

    let refs = types::ServerRefs {
        shared: shared.clone(),
    };

    // Loop: comandos do cliente + difusão de cotações.
    loop {
        tokio::select! {
            incoming = receiver.next() => {
                match incoming {
                    Some(Ok(msg)) => {
                        let text = match msg {
                            axum::extract::ws::Message::Text(t) => t,
                            axum::extract::ws::Message::Close(_) => break,
                            _ => continue,
                        };
                        match serde_json::from_str::<WsCommand>(&text) {
                            Ok(cmd) => {
                                if !dispatch(cmd, &refs, &mut sender).await {
                                    break;
                                }
                            }
                            Err(e) => {
                                handler::reply_bad_request(
                                    &mut sender,
                                    format!("Comando invalido: {}", e),
                                )
                                .await;
                            }
                        }
                    }
                    _ => break,
                }
            }
            Ok(quote) = rx.recv() => {
                maybe_push_quote(&refs, &mut sender, quote).await;
            }
        }
    }
}
