// XAU AI PRO Core - HTTP do EA MT5 (item 6 do roadmap).
// Rotas: hello, heartbeat, status e reconciliação.
// O EA usa WebRequest (HTTP) — sem WebSocket no MQL5.

use std::sync::Arc;

use axum::extract::State;
use axum::routing::{get, post};
use axum::{Json, Router};
use serde::{Deserialize, Serialize};
use tracing::info;

use xau_ai_pro_core::config::HttpConfig;
use xau_ai_pro_core::market::MarketDataService;
use xau_ai_pro_core::mt5session::{EaAck, EaHeartbeat, EaHello, Mt5SessionManager};

#[derive(Clone)]
struct EaState {
    mt5: Arc<Mt5SessionManager>,
    market: Arc<MarketDataService>,
}

/// Sobe o HTTP do EA na porta configurada (padrão 9003).
pub async fn serve(
    config: &HttpConfig,
    mt5: Arc<Mt5SessionManager>,
    market: Arc<MarketDataService>,
) -> anyhow::Result<()> {
    let addr = format!("{}:{}", config.bind_address, config.port);
    info!("HTTP do EA em {}", addr);
    let state = EaState { mt5, market };
    let app = Router::new()
        .route("/api/ea/hello", post(route_hello))
        .route("/api/ea/heartbeat", post(route_heartbeat))
        .route("/api/ea/status", get(route_status))
        .route("/api/ea/reconcile", get(route_reconcile))
        .route("/health", get(route_health))
        .with_state(state);
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

async fn route_hello(State(s): State<EaState>, Json(h): Json<EaHello>) -> Json<EaAck> {
    let major_ok = h
        .version
        .split('.')
        .next()
        .map(|m| m == "1")
        .unwrap_or(false);
    if !major_ok {
        return Json(EaAck {
            ok: false,
            core_version: xau_ai_pro_core::VERSION.into(),
            protocol_version: xau_ai_pro_core::protocol::PROTOCOL_VERSION.into(),
            pending_commands: Vec::new(),
            message: format!("versao incompativel: {}", h.version),
        });
    }
    info!("EA hello: login={} server={}", h.login, h.server);
    Json(s.mt5.hello(h).await)
}

async fn route_heartbeat(State(s): State<EaState>, Json(h): Json<EaHeartbeat>) -> Json<EaAck> {
    if let Some(q) = h.quote.clone() {
        let _ = q;
    }
    Json(s.mt5.heartbeat(h).await)
}

#[derive(Debug, Serialize, Deserialize)]
struct StatusOut {
    online: bool,
    session: Option<xau_ai_pro_core::mt5session::Mt5Session>,
    quotes_cached: usize,
}

async fn route_status(State(s): State<EaState>) -> Json<StatusOut> {
    let session = s.mt5.snapshot().await;
    let online = session
        .as_ref()
        .map(|x| x.state == xau_ai_pro_core::mt5session::Mt5LinkState::Online)
        .unwrap_or(false);
    Json(StatusOut {
        online,
        session,
        quotes_cached: s.market.get_all_quotes().await.len(),
    })
}

#[derive(Debug, Serialize, Deserialize)]
struct ReconcileOut {
    online: bool,
    divergencias: Vec<ReconcileItemOut>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ReconcileItemOut {
    ticket: u64,
    lado: String,
}

async fn route_reconcile(State(s): State<EaState>) -> Json<ReconcileOut> {
    let snap = s.mt5.snapshot().await;
    let online = snap
        .as_ref()
        .map(|x| x.state == xau_ai_pro_core::mt5session::Mt5LinkState::Online)
        .unwrap_or(false);
    Json(ReconcileOut {
        online,
        divergencias: Vec::new(),
    })
}

async fn route_health() -> Json<serde_json::Value> {
    Json(serde_json::json!({"ok": true, "service": "xau-ai-pro-core"}))
}
