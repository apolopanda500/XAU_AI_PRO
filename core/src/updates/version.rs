// XAU AI PRO Core — Versionamento do Core e das atualizações (item 10).
// Controle de versão com semântica e canais de rollout (stable/beta/canary/emergency).

use serde::{Deserialize, Serialize};
use std::path::Path;
use tracing::info;

/// Versão semântica do Core (MAJOR.MINOR.PATCH) + canal de rollout.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Channel {
    Stable,
    Beta,
    Canary,
    Emergency,
}

impl Default for Channel {
    fn default() -> Self {
        Channel::Stable
    }
}

/// Metadados de uma atualização disponível.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateInfo {
    pub version: String, // MAJOR.MINOR.PATCH
    pub channel: Channel,
    pub artifact_url: String, // URL do pacote assinado
    pub signature_url: String, // URL da assinatura (SHA-256 + assinatura privada do mantenedor)
    pub checksum_sha256: String,
    pub release_notes: String,
    pub min_version: Option<String>, // versão mínima compatível
    pub rollback_to: Option<String>, // versão anterior recomendada para rollback
    pub published_at: chrono::DateTime<chrono::Utc>,
}

/// Estado do versionamento local do Core.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocalVersion {
    pub current_version: String,
    pub channel: Channel,
    pub last_update_attempt: Option<chrono::DateTime<chrono::Utc>>,
    pub last_update_success: Option<chrono::DateTime<chrono::Utc>>,
    pub pending_rollforward: Option<UpdateInfo>, // se há atualização aguardando rollback
}

impl LocalVersion {
    pub fn current() -> anyhow::Result<Self> {
        // Lê do manifest local (gerado na instalação ou na primeira execução)
        let manifest_path = crate::config::Config::data_dir_default()
            .join("manifest.json");
        if manifest_path.exists() {
            let content = std::fs::read_to_string(&manifest_path)?;
            let manifest: LocalVersion =
                serde_json::from_str(&content).map_err(|e| anyhow::anyhow!(e))?;
            Ok(manifest)
        } else {
            // Primeira execução: gera manifest local padrão
            let manifest = LocalVersion {
                current_version: env!("CARGO_PKG_VERSION").into(),
                channel: Channel::Stable,
                last_update_attempt: None,
                last_update_success: None,
                pending_rollforward: None,
            };
            Ok(manifest)
        }
    }

    /// Salva o manifest local (após update bem-sucedido ou rollback)
    pub fn persist(&self) -> anyhow::Result<()> {
        let path = crate::config::Config::data_dir_default()
            .join("manifest.json");
        let dir = path.parent().unwrap();
        std::fs::create_dir_all(dir)?;
        let content = serde_json::to_string_pretty(self)?;
        std::fs::write(path, content)?;
        Ok(())
    }
}

/// Verifica se uma versão é compatível com a mínima exigida.
pub fn is_compatible(current: &str, min: &str) -> bool {
    parse_version(current) >= parse_version(min)
}

fn parse_version(v: &str) -> (u32, u32, u32) {
    let parts: Vec<&str> = v.split('.').collect();
    let major = parts.first().and_then(|p| p.parse().ok()).unwrap_or(0);
    let minor = parts.get(1).and_then(|p| p.parse().ok()).unwrap_or(0);
    let patch = parts.get(2).and_then(|p| p.parse().ok()).unwrap_or(0);
    (major, minor, patch)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_version_leve() { assert_eq!(parse_version("0.1.0"), (0, 1, 0)); assert_eq!(parse_version("1.2.3"), (1, 2, 3)); }
    #[test]
    fn is_compatible_true() { assert!(is_compatible("0.1.5", "0.1.0")); assert!(is_compatible("1.0.0", "0.9.9")); }
    #[test]
    fn is_compatible_false() { assert!(!is_compatible("0.1.0", "0.2.0")); }
    #[test]
    fn version_default_stable() { assert_eq!(Channel::default(), Channel::Stable); }
}
