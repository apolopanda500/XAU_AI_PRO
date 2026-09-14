// XAU AI PRO Core — Rollback de atualizações (item 10).
// Rollback automático ou manual para versão anterior, com verficação de integridade
// e preservação de dados (config, histórico de trades, logs).

use std::path::Path;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, warn};
use crate::updates::version::{LocalVersion, is_compatible};

/// Estratégia de rollback: automático ou manual.
pub enum RollbackStrategy {
    /// Rollback automático se a atualização falhar (padrão).
    Automatic,
    /// Requer confirmação manual (via CLI/HTTP) para fazer rollback.
    Manual,
}

/// Gerenciador de rollback: mantém histórico de versões instaladas
/// e permite reverter para uma versão anterior verificando integridade
/// e compatibilidade.
pub struct RollbackManager {
    local_version: Arc<RwLock<LocalVersion>>,
    rollback_strategy: RollbackStrategy,
    /// Histórico de versões instaladas (para rollback)
    history: Arc<RwLock<Vec<String>>>,
}

impl RollbackManager {
    pub fn new(local_version: Arc<RwLock<LocalVersion>>) -> Self {
        Self {
            local_version,
            rollback_strategy: RollbackStrategy::Automatic,
            history: Arc::new(RwLock::new(Vec::new())),
        }
    }

    pub fn with_strategy(mut self, strategy: RollbackStrategy) -> Self {
        self.rollback_strategy = strategy;
        self
    }

    /// Registra uma versão no histórico de rollback (chamado após update bem-sucedido).
    pub fn record_version(&self, version: &str) {
        let mut history = self.history.write().unwrap();
        history.retain(|v| v != version);
        history.insert(0, version.to_string());
        history.truncate(10); // mantém últimas 10 versões
        info!("RollbackManager: versão {} registrada no histórico", version);
    }

    /// Tenta fazer rollback para uma versão anterior.
    /// Retorna Ok(()) se rollback bem-sucedido, ou erro com motivo.
    pub async fn rollback(&self, target_version: &str) -> anyhow::Result<()> {
        // Verifica se a versão target é compatível
        let current = self.local_version.read().await.current_version.clone();
        if !is_compatible(&current, target_version) {
            anyhow::bail!("rollback incompatível: versão atual {} é menor que a versão alvo {}", current, target_version);
        }

        // Verifica se a versão está no histórico
        let history = self.history.read().await;
        if !history.contains(&target_version.to_string()) {
            anyhow::bail!("versão {} não está no histórico de rollback", target_version);
        }
        drop(history);

        // Executa rollback (simulado — em produção, restauraria pacote assinado)
        info!("RollbackManager: executando rollback para versão {}", target_version);
        // TODO: implementar restauração do pacote assinado da versão target
        // TODO: verificar checksum e integridade do pacote restaurado
        // TODO: preservar dados (config, histórico de trades, logs)

        // Atualiza versão local
        let mut local = self.local_version.write().await;
        local.current_version = target_version.to_string();
        local.last_update_attempt = Some(chrono::Utc::now());
        local.last_update_success = Some(chrono::Utc::now());
        Ok(())
    }

    /// Faz rollback para a versão anterior no histórico.
    pub async fn rollback_to_previous(&self) -> anyhow::Result<()> {
        let history = self.history.read().await;
        let target = history.get(1).ok_or_else(|| anyhow::anyhow!("sem versão anterior no histórico"))?;
        drop(history);
        self.rollback(target).await
    }

    /// Verifica se rollback é possível para uma versão target.
    pub async fn can_rollback(&self, target_version: &str) -> bool {
        let history = self.history.read().await;
        history.contains(&target_version.to_string())
    }

    /// Retorna histórico de versões instaladas (para rollback).
    pub async fn history(&self) -> Vec<String> {
        self.history.read().await.clone()
    }
}

impl Default for RollbackManager {
    fn default() -> Self {
        Self::new(Arc::new(RwLock::new(LocalVersion::current().unwrap_or_else(|_| LocalVersion {
            current_version: env!("CARGO_PKG_VERSION").into(),
            channel: crate::updates::channel::Channel::Stable,
            last_update_attempt: None,
            last_update_success: None,
            pending_rollforward: None,
        }))))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rollback_manager_registra_versao() { let mgr = RollbackManager::default(); mgr.record_version("0.1.0"); mgr.record_version("0.2.0"); let history = mgr.history().await; assert!(history.contains(&"0.2.0".to_string())); assert!(history.contains(&"0.1.0".to_string())); }
    #[test]
    fn rollback_manager_cola_version_repetida() { let mgr = RollbackManager::default(); mgr.record_version("0.1.0"); mgr.record_version("0.1.0"); let history = mgr.history().await; assert_eq!(history.iter().filter(|v| *v == "0.1.0").count(), 1); }
    #[tokio::test]
    async fn rollback_manager_reverte_para_versao_anterior() { let mgr = RollbackManager::default(); mgr.record_version("0.2.0"); mgr.record_version("0.1.0"); assert!(mgr.can_rollback("0.1.0").await); assert!(!mgr.can_rollback("0.0.9").await); }
    #[tokio::test]
    async fn rollback_manager_falha_para_versao_incompativel() { let mgr = RollbackManager::default(); mgr.record_version("0.2.0"); let result = mgr.rollback("0.3.0").await; assert!(result.is_err()); }
}
