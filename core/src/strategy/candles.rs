// XAU AI PRO Core — Coleta de candles para a estratégia (item 8).
// Histórico persistido em SQLite (banco do projeto, tabela candles).

use std::collections::BTreeMap;
use std::path::Path;
use std::sync::Arc;

use rusqlite::Connection;
use tokio::sync::{broadcast, RwLock};
use tokio::time::{interval, Duration};
use tracing::{info, warn};

use crate::market::MarketDataService;

/// Candle de 1 minuto do símbolo da estratégia.
#[derive(Debug, Clone, Copy, serde::Serialize, serde::Deserialize)]
pub struct Candle {
    /// Timestamp de abertura (ms desde epoch).
    pub ts_ms: i64,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
}

/// Armazenamento de candles: em memória (BTreeMap por ts) + espelho em SQLite.
pub struct CandleStore {
    symbol: String,
    candles: Arc<RwLock<BTreeMap<i64, Candle>>>,
    db: std::sync::Mutex<Connection>,
}

impl CandleStore {
    /// Abre/cria o banco e carrega o histórico existente em memória.
    pub fn new(db_path: &Path, symbol: &str) -> rusqlite::Result<Self> {
        let conn = Connection::open(db_path)?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS candles (
                symbol TEXT NOT NULL,
                ts_ms  INTEGER NOT NULL,
                open   REAL NOT NULL,
                high   REAL NOT NULL,
                low    REAL NOT NULL,
                close  REAL NOT NULL,
                PRIMARY KEY (symbol, ts_ms)
             );
             PRAGMA journal_mode=WAL;",
        )?;
        // Carrega histórico existente (limite de leitura para memória).
        let candles = {
            let mut candles = BTreeMap::new();
            let mut stmt = conn.prepare(
                "SELECT ts_ms, open, high, low, close FROM candles
                 WHERE symbol = ?1 ORDER BY ts_ms DESC LIMIT 3000",
            )?;
            let rows = stmt.query_map([symbol], |r| {
                Ok(Candle {
                    ts_ms: r.get(0)?,
                    open: r.get(1)?,
                    high: r.get(2)?,
                    low: r.get(3)?,
                    close: r.get(4)?,
                })
            })?;
            for row in rows {
                let c = row?;
                candles.insert(c.ts_ms, c);
            }
            candles
        }; // stmt encerrado aqui — conn pode ser movido para o Mutex
        Ok(Self {
            symbol: symbol.to_string(),
            candles: Arc::new(RwLock::new(candles)),
            db: std::sync::Mutex::new(conn),
        })
    }

    /// Converte um tick (quote) em candle de 1 minuto e persiste.
    pub async fn on_quote(&self, bid: f64, ask: f64) {
        let mid = (bid + ask) / 2.0;
        let now = chrono::Utc::now();
        let minute = now.timestamp_millis() - (now.timestamp_millis().rem_euclid(60_000));
        let mut candles = self.candles.write().await;
        let entry = candles.entry(minute).or_insert(Candle {
            ts_ms: minute,
            open: mid,
            high: mid,
            low: mid,
            close: mid,
        });
        entry.high = entry.high.max(mid);
        entry.low = entry.low.min(mid);
        entry.close = mid;
        let snapshot = *entry;
        drop(candles);
        let conn = match self.db.lock() {
            Ok(c) => c,
            Err(_) => return,
        };
        let _ = conn.execute(
            "INSERT OR REPLACE INTO candles (symbol, ts_ms, open, high, low, close)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            rusqlite::params![
                self.symbol,
                snapshot.ts_ms,
                snapshot.open,
                snapshot.high,
                snapshot.low,
                snapshot.close
            ],
        );
    }

    /// Fechamentos na ordem cronológica (cópia leve para cálculo).
    pub async fn closes(&self) -> Vec<f64> {
        self.candles
            .read()
            .await
            .values()
            .map(|c| c.close)
            .collect()
    }

    /// Total de candles em memória.
    pub async fn total(&self) -> usize {
        self.candles.read().await.len()
    }

    /// Loop de ingestão: assina o broadcast de quotes do MarketDataService.
    pub async fn run_ingest(
        self: Arc<Self>,
        _market: Arc<MarketDataService>,
        mut rx: broadcast::Receiver<crate::protocol::Quote>,
        symbol: String,
    ) {
        info!("Ingestão de candles iniciada para {}", symbol);
        let mut ticker = interval(Duration::from_secs(30)); // prune periódico
        loop {
            tokio::select! {
                q = rx.recv() => {
                    match q {
                        Ok(quote) if quote.symbol == symbol => {
                            self.on_quote(quote.bid, quote.ask).await;
                        }
                        Ok(_) => continue,
                        Err(broadcast::error::RecvError::Lagged(n)) => {
                            warn!("Ingestão atrasada ({} mensagens perdidas)", n);
                        }
                        Err(broadcast::error::RecvError::Closed) => break,
                    }
                }
                _ = ticker.tick() => {
                    // Mantém no máximo 3000 candles (50 h de 1m).
                    let mut candles = self.candles.write().await;
                    while candles.len() > 3000 {
                        if let Some(first) = candles.keys().next().copied() {
                            candles.remove(&first);
                        }
                    }
                }
            }
        }
    }
}
