// XAU AI PRO Core â€” SessÃ£o MT5 (parte 2: gerente).
// Handshake, heartbeat, fila de comandos e reconciliaÃ§Ã£o.

use chrono::Utc;
use std::sync::Arc;
use tokio::sync::RwLock;

use super::types::{
    EaAck, EaCommand, EaHeartbeat, EaHello, Mt5LinkState, Mt5Session, MT5_HEARTBEAT_TIMEOUT_SEC,
};

/// DivergÃªncia entre posiÃ§Ãµes do Core e do EA (reconciliaÃ§Ã£o).
#[derive(Debug, Clone)]
pub struct ReconcileItem {
    pub ticket: u64,
    pub lado: ReconcileLado,
}

/// Onde a posiÃ§Ã£o existe.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReconcileLado {
    /// SÃ³ no EA (Core desconhece â€” ordem manual ou externa).
    SoNoEa,
    /// SÃ³ no Core (EA nÃ£o reporta â€” fechada fora ou ticket invÃ¡lido).
    SoNoCore,
}

/// Gerenciador da sessÃ£o MT5 (compartilhado entre HTTP do EA e WS).
pub struct Mt5SessionManager {
    session: Arc<RwLock<Option<Mt5Session>>>,
}

impl Mt5SessionManager {
    pub fn new() -> Self {
        Self {
            session: Arc::new(RwLock::new(None)),
        }
    }

    /// Handshake: registra (ou substitui) a sessÃ£o do EA.
    pub async fn hello(&self, hello: EaHello) -> EaAck {
        let now = Utc::now();
        let mut guard = self.session.write().await;
        let prev = guard.clone();
        let pending = prev.as_ref().map(|s| s.pending.clone()).unwrap_or_default();
        let connected_at = prev.as_ref().map(|s| s.connected_at).unwrap_or(now);
        let ea_positions = prev
            .as_ref()
            .map(|s| s.ea_positions.clone())
            .unwrap_or_default();
        let count = prev.as_ref().map(|s| s.heartbeat_count).unwrap_or(0);
        *guard = Some(Mt5Session {
            login: hello.login.clone(),
            server: hello.server.clone(),
            state: Mt5LinkState::Online,
            symbols: hello.symbols.clone(),
            magic: hello.magic,
            connected_at,
            last_heartbeat: now,
            ea_positions,
            pending: pending.clone(),
            heartbeat_count: count,
        });
        EaAck {
            ok: true,
            core_version: crate::VERSION.into(),
            protocol_version: crate::protocol::PROTOCOL_VERSION.into(),
            pending_commands: pending,
            message: format!("EA {} conectado ao Core", hello.login),
        }
    }

    /// Heartbeat: atualiza timestamp e posiÃ§Ãµes; retorna comandos pendentes.
    pub async fn heartbeat(&self, hb: EaHeartbeat) -> EaAck {
        let mut guard = self.session.write().await;
        match guard.as_mut() {
            Some(s) if s.login == hb.login => {
                s.last_heartbeat = Utc::now();
                s.state = Mt5LinkState::Online;
                s.ea_positions = hb.positions.clone();
                s.heartbeat_count += 1;
                let pending = std::mem::take(&mut s.pending);
                EaAck {
                    ok: true,
                    core_version: crate::VERSION.into(),
                    protocol_version: crate::protocol::PROTOCOL_VERSION.into(),
                    pending_commands: pending,
                    message: "heartbeat ok".into(),
                }
            }
            _ => EaAck {
                ok: false,
                core_version: crate::VERSION.into(),
                protocol_version: crate::protocol::PROTOCOL_VERSION.into(),
                pending_commands: Vec::new(),
                message: "sessao desconhecida: envie hello primeiro".into(),
            },
        }
    }

    /// Enfileira comando do React para o EA coletar no prÃ³ximo polling.
    pub async fn enqueue(&self, cmd: EaCommand) -> bool {
        match self.session.write().await.as_mut() {
            Some(s) if s.state == Mt5LinkState::Online => {
                s.pending.push(cmd);
                true
            }
            _ => false,
        }
    }

    /// Snapshot da sessÃ£o (aplica staleness por atraso de heartbeat).
    pub async fn snapshot(&self) -> Option<Mt5Session> {
        let mut guard = self.session.write().await;
        if let Some(s) = guard.as_mut() {
            let age = (Utc::now() - s.last_heartbeat).num_seconds();
            if s.state == Mt5LinkState::Online && age > MT5_HEARTBEAT_TIMEOUT_SEC {
                s.state = Mt5LinkState::Stale;
            }
        }
        guard.clone()
    }

    /// Verdadeiro se hÃ¡ EA online (roteamento de ordens permitido).
    pub async fn is_online(&self) -> bool {
        self.snapshot()
            .await
            .map(|s| s.state == Mt5LinkState::Online)
            .unwrap_or(false)
    }

    /// ReconciliaÃ§Ã£o: compara tickets do Core contra os do EA.
    /// `core_tickets`: tickets que o Core acredita estarem abertos.
    pub async fn reconcile(&self, core_tickets: Vec<u64>) -> Vec<ReconcileItem> {
        let snap = self.snapshot().await;
        let s = match snap {
            Some(v) => v,
            None => return Vec::new(),
        };
        let mut out = Vec::new();
        for p in &s.ea_positions {
            if !core_tickets.contains(&p.ticket) {
                out.push(ReconcileItem {
                    ticket: p.ticket,
                    lado: ReconcileLado::SoNoEa,
                });
            }
        }
        let ea_tickets: Vec<u64> = s.ea_positions.iter().map(|p| p.ticket).collect();
        for t in core_tickets {
            if !ea_tickets.contains(&t) {
                out.push(ReconcileItem {
                    ticket: t,
                    lado: ReconcileLado::SoNoCore,
                });
            }
        }
        out
    }
}

impl Default for Mt5SessionManager {
    fn default() -> Self {
        Self::new()
    }
}
