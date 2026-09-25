# XAU AI PRO Core — Dockerfile
# Build e runtime do backend Rust

FROM rust:1.82-slim AS builder

WORKDIR /app

# Copiar manifesto e build dependencies
COPY core/Cargo.toml core/Cargo.lock* rust-toolchain.toml ./
COPY core/src ./src

# Compilar release
RUN cargo build --release

# Runtime mínimo
FROM debian:bookworm-slim AS runtime

RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar binário compilado
COPY --from=builder /app/target/release/xau-ai-pro-core /usr/local/bin/xau-ai-pro-core

# Portas
# 9002 = WebSocket (market data)
# 9003 = HTTP API
EXPOSE 9002 9003

# Diretório de dados
VOLUME ["/app/data"]

ENV RUST_LOG=info
ENV WS_BIND=0.0.0.0:9002
ENV HTTP_BIND=0.0.0.0:9003

ENTRYPOINT ["/usr/local/bin/xau-ai-pro-core"]
