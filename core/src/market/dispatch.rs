// XAU AI PRO Core - Comandos WS v1 (parte 2 do handler).
// Subscribe, heartbeat, ordens e difusao de cotacoes.

use chrono::Utc;
use tracing::info;

use super::handler::reply_bad_request;
use super::state::{encode_message, push_text, send_error, WsSender};
use super::types::ServerRefs;
use crate::mt5session::{EaCommand, EaCommandKind};
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
            route_place_order(sender, refs, order_cmd.order.volume, order_cmd).await;
        }
        WsCommand::ClosePosition { ticket, request_id } => {
            let cmd = EaCommand {
                request_id: request_id.clone(),
                kind: EaCommandKind::ClosePosition { ticket },
            };
            route_ea_command(sender, refs, cmd, "fechamento de posição").await;
        }
        WsCommand::CancelOrder { ticket, request_id } => {
            let cmd = EaCommand {
                request_id: request_id.clone(),
                kind: EaCommandKind::CancelOrder { ticket },
            };
            route_ea_command(sender, refs, cmd, "cancelamento de ordem").await;
        }
        WsCommand::GetAccount { request_id } => {
            answer_account(sender, refs, request_id).await;
        }
        WsCommand::GetPositions { request_id } => {
            answer_positions(sender, refs, request_id).await;
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

/// Valida lote y riesgo, y enfileira ordem para el EA.
async fn route_place_order(
    sender: &mut WsSender,
    refs: &ServerRefs,
    volume: f64,
    order_cmd: crate::protocol::OrderCommand,
) {
    if !(0.01..=0.50).contains(&volume) {
        let resp = WsMessage::OrderResponse(OrderResponse {
            success: false,
            ticket: 0,
            message: format!("Volume invalido: {} (permitido: 0.01-0.50)", volume),
            request_id: Some(order_cmd.request_id.clone()),
        });
        push_text(sender, encode_message(&resp)).await;
        return;
    }

    // Item 7: aplicar Risk Engine antes de operar.
    let decision = refs.risk.evaluate(&order_cmd.order, None).await;
    if !decision.approved {
        let resp = WsMessage::OrderResponse(OrderResponse {
            success: false,
            ticket: 0,
            message: decision.reason.clone(),
            request_id: Some(order_cmd.request_id.clone()),
        });
        push_text(sender, encode_message(&resp)).await;
        info!(
            "Orden rechazada por riesgo (code={}, req={})",
            decision.code.as_deref().unwrap_or("-"),
            order_cmd.request_id,
        );
        return;
    }

    let cmd = EaCommand {
        request_id: order_cmd.request_id.clone(),
        kind: EaCommandKind::PlaceOrder(order_cmd.order.clone()),
    };
    route_ea_command(sender, refs, cmd, "envio de ordem").await;
}

/// Enfileira comando para o EA; sem EA online responde MT5_OFFLINE.
async fn route_ea_command(sender: &mut WsSender, refs: &ServerRefs, cmd: EaCommand, acao: &str) {
    let request_id = cmd.request_id.clone();
    if refs.mt5.enqueue(cmd).await {
        let resp = WsMessage::OrderResponse(OrderResponse {
            success: true,
            ticket: 0,
            message: format!("{} enfileirado para o EA MT5 (acompanhe a execução)", acao),
            request_id: Some(request_id.clone()),
        });
        push_text(sender, encode_message(&resp)).await;
        info!("Comando {} enfileirado p/ EA (req={})", acao, request_id);
    } else {
        send_error(
            sender,
            error_codes::MT5_OFFLINE,
            "EA MT5 offline: conecte o Expert Advisor (item 6 do roadmap)".into(),
            Some(request_id),
        )
        .await;
    }
}

/// Responde GetAccount com a sessão ativa do EA.
async fn answer_account(sender: &mut WsSender, refs: &ServerRefs, request_id: String) {
    match refs.mt5.snapshot().await {
        Some(s) => {
            let info = crate::protocol::AccountInfo {
                login: s.login.clone(),
                balance: 0.0,
                equity: 0.0,
                margin: 0.0,
                free_margin: 0.0,
                leverage: 0,
                server: s.server.clone(),
                currency: "".into(),
                profit: s.ea_positions.iter().map(|p| p.profit).sum(),
            };
            let msg = WsMessage::Account(info);
            push_text(sender, encode_message(&msg)).await;
            let _ = request_id;
        }
        None => {
            send_error(
                sender,
                error_codes::MT5_OFFLINE,
                "Conta indisponivel: EA MT5 ainda não conectado".into(),
                Some(request_id),
            )
            .await;
        }
    }
}

/// Responde GetPositions com as posições do último heartbeat.
async fn answer_positions(sender: &mut WsSender, refs: &ServerRefs, request_id: String) {
    match refs.mt5.snapshot().await {
        Some(s) => {
            for p in &s.ea_positions {
                let pos = crate::protocol::Position {
                    ticket: p.ticket,
                    symbol: p.symbol.clone(),
                    side: p.side.clone(),
                    volume: p.volume,
                    open_price: p.open_price,
                    current_price: p.current_price,
                    sl: None,
                    tp: None,
                    profit: p.profit,
                    open_time: chrono::Utc::now(),
                    magic: p.magic,
                };
                let msg = WsMessage::PositionUpdate(pos);
                if !push_text(sender, encode_message(&msg)).await {
                    return;
                }
            }
            let _ = request_id;
        }
        None => {
            send_error(
                sender,
                error_codes::MT5_OFFLINE,
                "Posições indisponíveis: EA MT5 ainda não conectado".into(),
                Some(request_id),
            )
            .await;
        }
    }
}

/// Envia cotacao somente se o simbolo estiver assinado.
pub async fn maybe_push_quote(refs: &ServerRefs, sender: &mut WsSender, quote: Quote) {
    if refs.shared.is_subscribed(&quote.symbol).await {
        let msg = WsMessage::Quote(quote);
        push_text(sender, encode_message(&msg)).await;
    }
}
