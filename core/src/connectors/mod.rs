// XAU AI PRO Core — Conectores de corretoras (item 9 do roadmap).
// Protocolo unificado de operação e auditoria com sandbox, rate limit e
// reconciliação de posições. Cada connector implementa a mesma interface
// para que a estratégia / paper trading / UI operem de forma agnóstica.

mod connector_trait;
mod rate_limiter;

pub use connector_trait::*;
pub use rate_limiter::*;
