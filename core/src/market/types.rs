// XAU AI PRO Core - Referencias do servidor WS.
// Estrutura pequena para nao estourar aridade nos handlers.

use std::sync::Arc;

use super::state::WsSharedState;
use crate::mt5session::Mt5SessionManager;

/// Referencias compartilhadas das rotas WS.
pub struct ServerRefs {
    pub shared: Arc<WsSharedState>,
    pub mt5: Arc<Mt5SessionManager>,
}
