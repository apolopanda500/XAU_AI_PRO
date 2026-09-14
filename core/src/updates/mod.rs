// XAU AI PRO Core — Atualizações versionadas com rollback (item 10 do roadmap).
// Canais stable/beta/canary/emergency com verificação de integridade,
// rollback automático e guia de migração.

mod channel;
mod rollback;
mod version;

pub use channel::*;
pub use rollback::*;
pub use version::*;
