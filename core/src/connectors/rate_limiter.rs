// XAU AI PRO Core — Rate limiter com token bucket por connector/exchange.
// Garante conformidade com limites de API das corretoras e protege contra
// thundering herd quando múltiplas estratégias operam no mesmo gateway.

use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::debug;

/// Bucket de tokens por exchange/connector.
pub struct RateLimiter {
    buckets: std::sync::Mutex<std::collections::HashMap<String, Bucket>>,
}

struct Bucket {
    /// Tokens disponíveis no momento.
    tokens: f64,
    /// Capacidade máxima (burst).
    capacity: f64,
    /// Refill por segundo.
    refill_per_sec: f64,
    last_refill: std::time::Instant,
}

impl Bucket {
    fn new(capacity: f64, refill_per_sec: f64) -> Self {
        Self {
            tokens: capacity,
            capacity,
            refill_per_sec,
            last_refill: std::time::Instant::now(),
        }
    }

    /// Tenta consumir 1 token; retorna true se permitido.
    fn try_consume(&mut self) -> bool {
        self.refill();
        if self.tokens >= 1.0 {
            self.tokens -= 1.0;
            true
        } else {
            false
        }
    }

    fn refill(&mut self) {
        let now = std::time::Instant::now();
        let elapsed = now.duration_since(self.last_refill).as_secs_f64();
        if elapsed > 0.0 {
            self.tokens = (self.tokens + elapsed * self.refill_per_sec).min(self.capacity);
            self.last_refill = now;
        }
    }
}

impl RateLimiter {
    pub fn new() -> Self {
        Self {
            buckets: std::sync::Mutex::new(std::collections::HashMap::new()),
        }
    }

    /// Adiciona ou ajusta o bucket de uma exchange.
    pub fn configure(&self, exchange: &str, capacity: f64, refill_per_sec: f64) {
        let mut buckets = self.buckets.lock().unwrap();
        let entry = buckets
            .entry(exchange.to_string())
            .or_insert_with(|| Bucket::new(capacity.max(1.0), refill_per_sec.max(0.0)));
        // Ajuste dinâmico para reconfiguração em runtime.
        entry.capacity = capacity.max(1.0);
        entry.refill_per_sec = refill_per_sec.max(0.0);
        entry.tokens = entry.tokens.min(entry.capacity);
    }

    /// Adquire permissão para chamar a API da exchange.
    /// Retorna Ok(()) quando o token está disponível, bloqueando brevemente
    /// se necessário (backoff dinâmico no contexto do caller).
    pub async fn acquire(
        &self,
        exchange: &str,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let mut buckets = self.buckets.lock().unwrap();
        let bucket = buckets
            .get_mut(exchange)
            .ok_or_else(|| format!("exchange sem bucket configurado: {}", exchange))?;
        let retries = 3_usize;
        for _ in 0..retries {
            if bucket.try_consume() {
                return Ok(());
            }
            // Espera o tempo necessário para o próximo token.
            let wait = 1.0 / bucket.refill_per_sec.max(1.0);
            tokio::time::sleep(std::time::Duration::from_secs_f64(wait.max(0.05))).await;
            bucket.refill();
        }
        Err(format!("rate limit excedido para {}", exchange).into())
    }
}

impl Default for RateLimiter {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn rate_limiter_bloqueia_acoes_acima_do_limit() {
        let rl = Arc::new(RateLimiter::new());
        rl.configure("binance", 2.0, 1.0); // 2 burst, 1/seg refill
        assert!(rl.acquire("binance").await.is_ok());
        assert!(rl.acquire("binance").await.is_ok());
        assert!(rl.acquire("binance").await.is_err());
    }

    #[tokio::test]
    async fn rate_limiter_recupera_apos_refill() {
        let rl = Arc::new(RateLimiter::new());
        rl.configure("mexc", 1.0, 2.0);
        for _ in 0..3 {
            assert!(rl.acquire("mexc").await.is_ok());
            tokio::time::sleep(std::time::Duration::from_secs_f64(0.6));
        }
        // Após um breve pause, o bucket se recupera.
        assert!(rl.acquire("mexc").await.is_ok());
    }

    #[tokio::test]
    fn configuracao_dinamica_aumenta_o_burst() {
        let rl = RateLimiter::new();
        rl.configure("binance", 1.0, 1.0);
        rl.configure("binance", 5.0, 2.0);
        let buckets = rl.buckets.lock().unwrap();
        let b = buckets.get("binance").unwrap();
        assert_eq!(b.capacity, 5.0);
        assert_eq!(b.refill_per_sec, 2.0);
    }
}
