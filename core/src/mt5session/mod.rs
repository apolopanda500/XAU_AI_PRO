// XAU AI PRO Core — Sessão MT5 (item 6 do roadmap).
// Estado de conexão do EA MT5: handshake, heartbeat e reconciliação.

mod manager;
mod types;

pub use manager::{Mt5SessionManager, ReconcileItem, ReconcileLado};
pub use types::{
    EaAck, EaCommand, EaCommandKind, EaHeartbeat, EaHello, EaPosition, Mt5LinkState, Mt5Session,
    MT5_HEARTBEAT_TIMEOUT_SEC,
};
