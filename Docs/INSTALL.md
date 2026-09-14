# XAU AI PRO — Guia de Instalação Completo

## Pré-requisitos

- Windows 10/11 (64 bits)
- Conexão com internet
- ~2 GB de espaço livre

---

## Passo 1 — Instalar Rust

### Opção A: Via Winget (recomendado)
```powershell
winget install Rustlang.Rustup
```

### Opção B: Via instalador manual
1. Acesse: https://rustup.rs/
2. Baixe o instalador
3. Execute e siga as instruções (aceite os defaults)

### Opção C: Via Chocolatey
```powershell
choco install rust
```

### Verificar instalação
```powershell
rustc --version
cargo --version
```

Saída esperada:
```
rustc 1.82.0 (...)
cargo 1.82.0 (...)
```

### Compilar o Core
```powershell
cd C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO\core
cargo build --release
```

---

## Passo 2 — Instalar Node.js

### Opção A: Via Winget (recomendado)
```powershell
winget install OpenJS.NodeJS.LTS
```

### Opção B: Via instalador manual
1. Acesse: https://nodejs.org/
2. Baixe a versão LTS (22.x)
3. Execute o instalador (aceite os defaults)

### Verificar instalação
```powershell
node --version
npm --version
```

Saída esperada:
```
v22.x.x
10.x.x
```

### Instalar dependências do Frontend
```powershell
cd C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO\frontend
npm install
```

---

## Passo 3 — Instalar Tauri CLI (opcional, para app desktop)

```powershell
cargo install tauri-cli
```

Ou via npm:
```powershell
npm install -g @tauri-apps/cli
```

### Pré-requisitos do Tauri no Windows
1. **Microsoft Visual C++ Build Tools**: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Instale com a carga de trabalho "Desktop development with C++"
2. **WebView2**: já vem no Windows 11. No Windows 10: https://developer.microsoft.com/en-us/microsoft-edge/webview2/

---

## Passo 4 — Instalar Docker (opcional)

### Opção A: Via Winget
```powershell
winget install Docker.DockerDesktop
```

### Opção B: Via instalador manual
1. Acesse: https://www.docker.com/products/docker-desktop/
2. Baixe e instale
3. Reinicie o computador

---

## Passo 5 — Rodar o Projeto

### Opção 1: Via script automático (recomendado)
```powershell
cd C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

### Opção 2: Manual

**Terminal 1 — Core Backend:**
```powershell
cd core
cargo run
```

**Terminal 2 — Frontend:**
```powershell
cd frontend
npm run dev
```

**Terminal 3 — App Desktop (Tauri):**
```powershell
cd frontend
npm run tauri dev
```

### Opção 3: Docker
```powershell
docker compose up -d
```

---

## Verificar se está funcionando

### Core Backend
- WebSocket: `ws://127.0.0.1:9002/ws/market`
- HTTP API: `http://127.0.0.1:9003/api/health`

### Frontend
- Web: `http://localhost:3000`

---

## Troubleshooting

### Rust não encontrado após instalação
1. Feche e reabra o terminal
2. Execute: `$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")`
3. Verifique: `rustc --version`

### Node.js não encontrado após instalação
1. Feche e reabra o terminal
2. Verifique: `node --version`

### Erro de compilação no Core
1. Verifique se o Rust está atualizado: `rustup update`
2. Limpe o cache: `cargo clean`
3. Tente novamente: `cargo build --release`

### Erro de dependências no Frontend
1. Delete `node_modules` e `package-lock.json`
2. Execute: `npm install`

### Erro do Tauri
1. Verifique se o WebView2 está instalado
2. Verifique se o Visual C++ Build Tools está instalado
3. Execute: `cargo install tauri-cli --force`

---

## Resumo dos Comandos

```powershell
# 1. Instalar Rust
winget install Rustlang.Rustup

# 2. Instalar Node.js
winget install OpenJS.NodeJS.LTS

# 3. Reabrir terminal e verificar
rustc --version
node --version

# 4. Compilar Core
cd core && cargo build --release

# 5. Instalar Frontend
cd ../frontend && npm install

# 6. Rodar (escolha uma opção)
# Terminal 1: cd core && cargo run
# Terminal 2: cd frontend && npm run dev
# Docker: docker compose up -d
```
