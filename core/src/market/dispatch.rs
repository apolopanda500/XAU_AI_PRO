// XAU AI PRO Core - Comandos WS v1 (parte 2 do handler).
// Subscribe, heartbeat, ordens e difusao de cotacoes.

use chrono::Utc;
use tracing::info;

use super::handler::reply_bad_request;
use super::state::{encode_message, push_text, send_error, WsSender};
use super::types::ServerRefs;
use crate::protocol::{error_codes, OrderResponse, PongMessage, Quote, WsCommand, WsMessage};

/// Roteia um comando ja parseado.
pub async fn dispatch(cmd: WsCommand, refs: &ServerRefs, sender: &mut WsSender) -> bool {
    match cmd {
        WsCommand::Hello { .. } => {
            reply_bad_request(sender, "Handshake ja concluido".into()).await;
        }
        WsCommand::Subscribe { symbols } => {
            refs.shared.add_all(symbols).await;
        }
        WsCommand::Unsubscribe { symbols } => {
            refs.shared.remove_all(symbols).await;
        }
        WsCommand::Ping { request_id, ts_ms } => {
            reply_pong(sender, request_id, ts_ms).await;
        }
        WsCommand::PlaceOrder(order_cmd) => {
            reply_place_order(sender, order_cmd.order.volume, order_cmd.request_id).await;
        }
        WsCommand::ClosePosition { ticket, request_id } => {
            send_error(
                sender,
                error_codes::MT5_OFFLINE,
                format!(
                    "Fechamento da posicao {} indisponivel: EA MT5 nao conectado (Fase 6)",
                    ticket
                ),
                Some(request_id),
            )
            .await;
        }
        WsCommand::CancelOrder { ticket, request_id } => {
            send_error(
                sender,
                error_codes::MT5_OFFLINE,
                format!(
                    "Cancelamento da ordem {} indisponivel: EA MT5 nao conectado (Fase 6)",
                    ticket
                ),
                Some(request_id),
            )
            .await;
        }
        WsCommand::GetAccount { request_id } => {
            send_error(
                sender,
                error_codes::MT5_OFFLINE,
                "Conta indisponivel: EA MT5 nao conectado (Fase 6)".into(),
                Some(request_id),
            )
            .await;
        }
        WsCommand::GetPositions { request_id } => {
            send_error(
                sender,
                error_codes::MT5_OFFLINE,
                "Posicoes indisponiveis: EA MT5 nao conectado (Fase 6)".into(),
                Some(request_id),
            )
            .await;
        }
    }
    true
}

/// Responde heartbeat com eco de timestamp.
async fn reply_pong(sender: &mut WsSender, request_id: String, ts_ms: i64) {
    let msg = WsMessage::Pong(PongMessage {
        request_id,
        ts_ms,
        server_ts_ms: Utc::now().timestamp_millis(),
    });
    push_text(sender, encode_message(&msg)).await;
}

/// Valida volume e responde (ordem real chega na Fase 6).
async fn reply_place_order(sender: &mut WsSender, volume: f64, request_id: String) {
    if !(0.01..=0.50).contains(&volume) {
        let resp = WsMessage::OrderResponse(OrderResponse {
            success: false,
            ticket: 0,
            message: format!("Volume invalido: {} (permitido: 0.01-0.50)", volume),
            request_id: Some(request_id),
        });
        push_text(sender, encode_message(&resp)).await;
        return;
    }
    send_error(
        sender,
        error_codes::MT5_OFFLINE,
        "Roteamento de ordens via WS sera ativado na Fase 6 (EA MT5)".into(),
        Some(request_id),
    )
    .await;
    info!("Ordem validada no Core; aguardando EA MT5 (Fase 6)");
}

/// Envia cotacao somente se o simbolo estiver assinado.
pub async fn maybe_push_quote(refs: &ServerRefs, sender: &mut WsSender, quote: Quote) {
    if refs.shared.is_subscribed(&quote.symbol).await {
        let msg = WsMessage::Quote(quote);
        push_text(sender, encode_message(&msg)).await;
    }
}
