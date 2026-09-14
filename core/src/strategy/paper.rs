// XAU AI PRO Core — Paper trading (item 8 do roadmap).
// Executa a estratégia em modo simulação: sinais do item 8 + lote
// sugerido pelo RiskEngine (item 7). Nenhum movimento de ativos:
// apenas registra trades simulados para auditoria e aprendizado.

use std::sync::Arc;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;
use tracing::{info, warn};

use crate::protocol::Quote;
use crate::risk::{RiskEngine, RiskMarketData};
use crate::strategy::{evaluate, CandleStore, Signal, StrategyConfig};

/// Tamanho do ponto em unidades de preço (XAU: 1 ponto = 0.01).
pub const POINT_SIZE: f64 = 0.01;
/// Valor do ponto por lote (USD) — mesma convenção do RiskEngine.
pub const POINT_VALUE_PER_LOT: f64 = 10.0;

/// Posição simulada aberta.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaperPosition {
    pub side: String,
    pub volume: f64,
    pub entry_price: f64,
    pub sl_price: f64,
    pub tp_price: f64,
    pub opened_at: DateTime<Utc>,
}

/// Trade simulado encerrado (registro auditável).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaperTrade {
    pub side: String,
    pub volume: f64,
    pub entry_price: f64,
    pub exit_price: f64,
    /// Resultado em USD.
    pub pnl_usd: f64,
    pub reason: String,
    pub closed_at: DateTime<Utc>,
}

/// Snapshot do paper trader para UI/auditoria.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PaperSnapshot {
    pub open: Option<PaperPosition>,
    pub closed_trades: Vec<PaperTrade>,
    pub realized_usd: f64,
    pub last_signal: Option<String>,
}

/// Executor de paper trading.
pub struct PaperTrader {
    cfg: RwLock<StrategyConfig>,
    position: RwLock<Option<PaperPosition>>,
    trades: RwLock<Vec<PaperTrade>>,
    realized: RwLock<f64>,
    last_signal: RwLock<Option<Signal>>,
    risk: Arc<RiskEngine>,
}

impl PaperTrader {
    pub fn new(cfg: StrategyConfig, risk: Arc<RiskEngine>) -> Self {
        Self {
            cfg: RwLock::new(cfg),
            position: RwLock::new(None),
            trades: RwLock::new(Vec::new()),
            realized: RwLock::new(0.0),
            last_signal: RwLock::new(None),
            risk,
        }
    }

    /// Atualiza a configuração (ex.: ao recarregar config.json).
    pub async fn set_config(&self, cfg: StrategyConfig) {
        *self.cfg.write().await = cfg;
    }

    /// Estado atual (UI/auditoria).
    pub async fn snapshot(&self) -> PaperSnapshot {
        PaperSnapshot {
            open: self.position.read().await.clone(),
            closed_trades: self.trades.read().await.clone(),
            realized_usd: *self.realized.read().await,
            last_signal: self
                .last_signal
                .read()
                .await
                .map(|s| s.as_str().to_string()),
        }
    }

    /// Ciclo principal: recebe closes + preço atual e opera a simulação.
    pub async fn on_closes(&self, closes: &[f64], bid: f64, ask: f64) {
        let cfg = self.cfg.read().await.clone();
        let mid = (bid + ask) / 2.0;
        let sig = evaluate(closes, &cfg);
        *self.last_signal.write().await = Some(sig);

        // 1. Gerencia posição aberta (stop/alvo).
        let open_now = self.position.read().await.clone();
        if let Some(pos) = open_now {
            let dir = if pos.side == "buy" { 1.0 } else { -1.0 };
            let hit_sl = (mid - pos.sl_price) * dir <= 0.0;
            let hit_tp = (mid - pos.tp_price) * dir >= 0.0;
            if hit_sl || hit_tp {
                let reason = if hit_sl { "stop_loss" } else { "take_profit" };
                self.close_position(mid, reason).await;
            }
            return; // posição aberta: não entra em outra
        }

        // 2. Sem autopilot: apenas observa.
        if !cfg.autopilot_enabled {
            return;
        }
        if sig == Signal::Flat {
            return;
        }

        // 3. Kill switch / regras de risco (item 7) antes de abrir.
        let sl_points = cfg.stop_loss_points / POINT_SIZE;
        let mkt = RiskMarketData {
            bid,
            ask,
            spread_points: ((ask - bid) / POINT_SIZE).round() as u64,
            equity: cfg.paper_equity,
            point_value_per_lot: POINT_VALUE_PER_LOT,
        };
        let probe = crate::protocol::OrderRequest {
            symbol: cfg.symbol.clone(),
            side: if sig == Signal::Sell {
                "sell".into()
            } else {
                "buy".into()
            },
            volume: 0.01,
            sl: None,
            tp: None,
            magic: None,
        };
        let decision = self.risk.evaluate(&probe, Some(&mkt)).await;
        if !decision.approved {
            return; // risco bloqueou — paper também respeita
        }

        // 4. Abre posição simulada com lote sugerido.
        let volume = self.risk.suggested_lot(sl_points, &mkt).await;
        let dir = if sig == Signal::Buy { 1.0 } else { -1.0 };
        let pos = PaperPosition {
            side: if dir > 0.0 {
                "buy".into()
            } else {
                "sell".into()
            },
            volume,
            entry_price: mid,
            sl_price: mid - dir * cfg.stop_loss_points,
            tp_price: mid + dir * cfg.take_profit_points,
            opened_at: Utc::now(),
        };
        info!(
            "PAPER: aberta {} {} @ {:.2} (sl {:.2}, tp {:.2})",
            pos.side, pos.volume, pos.entry_price, pos.sl_price, pos.tp_price
        );
        *self.position.write().await = Some(pos);
    }

    /// Fecha a posição simulada ao preço dado.
    async fn close_position(&self, exit_price: f64, reason: &str) {
        let Some(pos) = self.position.write().await.take() else {
            return;
        };
        let dir = if pos.side == "buy" { 1.0 } else { -1.0 };
        let points = (exit_price - pos.entry_price) * dir / POINT_SIZE;
        let pnl = points * POINT_VALUE_PER_LOT * pos.volume;
        *self.realized.write().await += pnl;
        let trade = PaperTrade {
            side: pos.side.clone(),
            volume: pos.volume,
            entry_price: pos.entry_price,
            exit_price,
            pnl_usd: pnl,
            reason: reason.into(),
            closed_at: Utc::now(),
        };
        info!(
            "PAPER: fechada {} @ {:.2} ({}): {:.2} USD",
            trade.side, exit_price, reason, pnl
        );
        let mut trades = self.trades.write().await;
        trades.push(trade);
        let excess = trades.len().saturating_sub(200);
        if excess > 0 {
            trades.drain(..excess);
        }
    }

    /// Ingestão contínua: candles + quotes → decisões de paper trading.
    pub async fn run(
        self: Arc<Self>,
        candles: Arc<CandleStore>,
        mut rx: tokio::sync::broadcast::Receiver<Quote>,
        symbol: String,
    ) {
        loop {
            match rx.recv().await {
                Ok(q) if q.symbol == symbol => {
                    candles.on_quote(q.bid, q.ask).await;
                    let closes = candles.closes().await;
                    self.on_closes(&closes, q.bid, q.ask).await;
                }
                Ok(_) => continue,
                Err(tokio::sync::broadcast::error::RecvError::Lagged(n)) => {
                    warn!("Paper trader atrasado ({} perdidas)", n);
                }
                Err(tokio::sync::broadcast::error::RecvError::Closed) => break,
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn trader() -> PaperTrader {
        let risk_config = crate::risk::RiskConfig {
            trading_enabled: true,
            ..Default::default()
        };
        PaperTrader::new(
            StrategyConfig::default(),
            Arc::new(RiskEngine::new(risk_config)),
        )
    }

    #[tokio::test]
    async fn sem_autopilot_nao_abre_posicao() {
        let t = trader();
        let closes: Vec<f64> = (0..40).map(|i| 100.0 - i as f64).collect();
        t.on_closes(&closes, 100.0, 100.02).await;
        assert!(t.snapshot().await.open.is_none());
    }

    #[tokio::test]
    async fn com_autopilot_abre_e_fecha_por_stop() {
        let cfg = StrategyConfig {
            autopilot_enabled: true,
            stop_loss_points: 1.0, // 1 unidade de preço
            take_profit_points: 100.0,
            ..Default::default()
        };
        let risk_config = crate::risk::RiskConfig {
            trading_enabled: true,
            ..Default::default()
        };
        let t = PaperTrader::new(cfg.clone(), Arc::new(RiskEngine::new(risk_config)));

        // Queda longa + retomada: encontra o prefixo que dispara Buy
        // (mesma lógica do `evaluate` — sinal no último candle).
        let mut closes: Vec<f64> = (0..40).map(|i| 100.0 - i as f64).collect();
        for i in 0..27 {
            closes.push(60.0 + i as f64 * 3.0);
        }
        let n = (cfg.ema_slow..=closes.len())
            .find(|&k| evaluate(&closes[..k], &StrategyConfig::default()) == Signal::Buy)
            .expect("série deveria disparar Buy em algum prefixo");
        let closes = &closes[..n];
        let last = *closes.last().unwrap();
        t.on_closes(closes, last, last + 0.02).await;
        let snap = t.snapshot().await;
        assert!(snap.open.is_some(), "deveria ter aberto paper");

        // Queda forte abaixo do stop (entry ~last, sl 1.0).
        t.on_closes(closes, last - 5.0, last - 4.98).await;
        let snap = t.snapshot().await;
        assert!(snap.open.is_none(), "deveria ter fechado no stop");
        assert_eq!(snap.closed_trades.len(), 1);
        assert_eq!(snap.closed_trades[0].reason, "stop_loss");
        assert!(snap.realized_usd < 0.0);
    }

    #[tokio::test]
    async fn kill_switch_bloqueia_paper() {
        let cfg = StrategyConfig {
            autopilot_enabled: true,
            ..Default::default()
        };
        let risk = Arc::new(RiskEngine::default());
        risk.set_trading_enabled(false).await;
        let t = PaperTrader::new(cfg.clone(), risk);
        let mut closes: Vec<f64> = (0..40).map(|i| 100.0 - i as f64).collect();
        for i in 0..27 {
            closes.push(60.0 + i as f64 * 3.0);
        }
        let n = (cfg.ema_slow..=closes.len())
            .find(|&k| evaluate(&closes[..k], &StrategyConfig::default()) == Signal::Buy)
            .expect("série deveria disparar Buy em algum prefixo");
        let last = closes[n - 1];
        t.on_closes(&closes[..n], last, last + 0.02).await;
        assert!(t.snapshot().await.open.is_none());
    }
}
