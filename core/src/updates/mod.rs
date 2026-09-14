// XAU AI PRO Core — Atualizações versionadas com rollback (item 10 do roadmap).
// Canais stable/beta/canary/emergency com verificação de integridade,
// rollback automático e guia de migração.

mod version;
mod channel;
mod rollback;

pub use version::*;
pub use channel::*;
pub use rollback::*;
