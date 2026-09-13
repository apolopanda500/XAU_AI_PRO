// XAU AI PRO Core — Account Service
// Gerenciamento de conta, sincronização, e informações da conta.

use crate::bridge::MT5Bridge;
use crate::protocol::AccountInfo;

/// Serviço de conta
pub struct AccountService {
    bridge: Option<MT5Bridge>,
    cached_info: Option<AccountInfo>,
}

impl Default for AccountService {
    fn default() -> Self {
        Self::new()
    }
}

impl AccountService {
    pub fn new() -> Self {
        Self {
            bridge: None,
            cached_info: None,
        }
    }

    /// Define o bridge MT5
    pub fn set_bridge(&mut self, bridge: MT5Bridge) {
        self.bridge = Some(bridge);
    }

    /// Sincroniza dados da conta via MT5
    pub async fn sync(&mut self) -> anyhow::Result<()> {
        if let Some(ref bridge) = self.bridge {
            let info = bridge.get_account_info().await?;
            self.cached_info = Some(info);
        }
        Ok(())
    }

    /// Retorna info da conta (cache ou busca nova)
    pub async fn get_info(&mut self) -> anyhow::Result<Option<AccountInfo>> {
        if self.cached_info.is_none() {
            self.sync().await?;
        }
        Ok(self.cached_info.clone())
    }

    /// Retorna info do cache sem buscar
    pub fn get_cached(&self) -> Option<AccountInfo> {
        self.cached_info.clone()
    }
}
