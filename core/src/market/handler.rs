// XAU AI PRO Core - Handlers do protocolo WS v1 (parte 1).
// Handshake: aguarda Hello, valida versao, responde Hello.

use axum::extract::ws::{Message, WebSocket};
use futures_util::StreamExt;
use tokio::time::Duration;

use super::state::{encode_message, push_text, send_error, WsSender};
use crate::protocol::{
    error_codes, ClientKind, HelloMessage, WsCommand, WsMessage, DEFAULT_SYMBOLS, PROTOCOL_VERSION,
    WS_PING_INTERVAL_MS,
};

type SplitRecv = futures_util::stream::SplitStream<WebSocket>;

/// Aguarda o Hello do cliente (timeout 10s).
/// Retorna o sender, a origem e a versao.
pub async fn await_hello(
    sender: WsSender,
    receiver: &mut SplitRecv,
) -> Option<(WsSender, ClientKind, String)> {
    let mut sender = sender;
    let found = tokio::time::timeout(Duration::from_secs(10), async {
        while let Some(Ok(Message::Text(text))) = receiver.next().await {
            match serde_json::from_str::<WsCommand>(&text) {
                Ok(WsCommand::Hello { client, version }) => {
                    return Some((client, version));
                }
                Ok(_) => {
                    send_error(
                        &mut sender,
                        error_codes::BAD_REQUEST,
                        "Envie Hello antes de outros comandos".into(),
                        None,
                    )
                    .await;
                }
                Err(_) => {
                    send_error(
                        &mut sender,
                        error_codes::BAD_REQUEST,
                        "Comando invalido: JSON fora do protocolo v1".into(),
                        None,
                    )
                    .await;
                }
            }
        }
        None
    })
    .await
    .unwrap_or(None);

    found.map(|(client, version)| (sender, client, version))
}

/// Valida o major da versao (v1.x aceito).
pub async fn validate_version(version: &str, sender: &mut WsSender) -> bool {
    let ok = version
        .split('.')
        .next()
        .map(|major| major == "1")
        .unwrap_or(false);
    if !ok {
        send_error(
            sender,
            error_codes::VERSION_MISMATCH,
            format!(
                "Versao incompativel: cliente={}, esperado={}",
                version, PROTOCOL_VERSION
            ),
            None,
        )
        .await;
        return false;
    }
    true
}

/// Responde o Hello do handshake.
pub async fn answer_hello(sender: &mut WsSender) {
    let msg = WsMessage::Hello(HelloMessage {
        version: PROTOCOL_VERSION.into(),
        core_version: crate::VERSION.into(),
        symbols: DEFAULT_SYMBOLS.iter().map(|s| (*s).to_string()).collect(),
        ping_interval_ms: WS_PING_INTERVAL_MS,
    });
    push_text(sender, encode_message(&msg)).await;
}

/// Responde erro BAD_REQUEST simples.
pub async fn reply_bad_request(sender: &mut WsSender, message: String) {
    send_error(sender, error_codes::BAD_REQUEST, message, None).await;
}
