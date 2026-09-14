// XAU AI PRO Core — Canais de atualização (item 10).
// Definição dos canais stable/beta/canary/emergency e regras de rollout.
// Cada canal tem prioridade, restrições e fallback.

use super::Channel;
use crate::config::Config;
use tracing::info;

/// Canais de rollout do XAU AI PRO Core.
/// Ordem de prioridade (do mais restrito para o menos):
///   Emergency > Canary > Beta > Stable
///
/// Regras:
/// - Stable: release geral para todos os usuários.
/// - Beta: clientes opt-in beta; pode conter features experimentais.
/// - Canary: rollout gradual (1% -> 10% -> 50% -> 100%), pode ser forçado via config.
/// - Emergency: hotfix crítico (segurança, corretora, mercado); liberação imediata independente de canal.
pub struct UpdateChannelPolicy {
    pub channel: Channel,
    pub enable_beta_opt_in: bool,
    pub canary_enabled: bool,
    pub emergency_enabled: bool,
    pub auto_updates: bool,
    pub rollback_on_failure: bool,
    pub min_stable_version: Option<String>,
}

impl Default for UpdateChannelPolicy {
    fn default() -> Self {
        Self {
            channel: Channel::Stable,
            enable_beta_opt_in: false,
            canary_enabled: false,
            emergency_enabled: false,
            auto_updates: true, // padrão: verificar atualizações automaticamente
            rollback_on_failure: true, // rollback automático se a atualização falhar
            min_stable_version: None,
        }
    }
}

impl UpdateChannelPolicy {
    pub fn from_config(config: &Config) -> Self {
        // Configuração atual é derivada do manifest + config.json (se houver).
        let channel = Channel::Stable; // padrão — pode ser alterado via config
        Self {
            channel,
            enable_beta_opt_in: false,
            canary_enabled: false,
            emergency_enabled: false,
            auto_updates: true,
            rollback_on_failure: true,
            min_stable_version: config.app.version.clone().into(),
        }
    }

    /// Se atualizações automáticas estão habilitadas para o canal atual.
    pub fn auto_updates_enabled(&self) -> bool {
        self.auto_updates
    }

    /// Se rollback automático está habilitado na falha.
    pub fn rollback_on_failure(&self) -> bool {
        self.rollback_on_failure
    }
}

pub fn current_channel() -> Channel {
    Channel::Stable
}

pub fn is_canary_channel() -> bool {
    Channel::Canary == current_channel()
}

pub fn is_emergency_channel() -> bool {
    Channel::Emergency == current_channel()
}

pub fn is_beta_channel() -> bool {
    Channel::Beta == current_channel()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn default_channel_stable() { assert_eq!(UpdateChannelPolicy::default().channel, Channel::Stable); }
    #[test]
    fn default_auto_updates_true() { assert!(UpdateChannelPolicy::default().auto_updates_enabled()); }
    #[test]
    fn default_rollback_on_failure_true() { assert!(UpdateChannelPolicy::default().rollback_on_failure()); }
    #[test]
    fn channel_eq() { assert_eq!(Channel::Stable, Channel::Stable); assert_ne!(Channel::Stable, Channel::Beta); }
}
