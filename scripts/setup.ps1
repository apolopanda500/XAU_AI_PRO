# XAU AI PRO - Setup Script
# Executa: powershell -ExecutionPolicy Bypass -File scripts/setup.ps1

Write-Host "=== XAU AI PRO - Setup ===" -ForegroundColor Cyan

$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot

# 1. Verificar Rust
Write-Host "`n[1/6] Verificando Rust..." -ForegroundColor Yellow
try {
    $rustVersion = rustc --version 2>$null
    Write-Host "  Rust instalado: $rustVersion" -ForegroundColor Green
} catch {
    Write-Host "  Rust nao encontrado. Instalando via rustup..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri https://win.rustup.rs/x86_64 -OutFile "$env:TEMP\rustup-init.exe"
    & "$env:TEMP\rustup-init.exe" -y --default-toolchain stable
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
    Write-Host "  Rust instalado com sucesso!" -ForegroundColor Green
}

# 2. Verificar Node.js
Write-Host "`n[2/6] Verificando Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>$null
    Write-Host "  Node.js instalado: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERRO: Node.js nao encontrado. Instale de https://nodejs.org/" -ForegroundColor Red
    exit 1
}

# 3. Instalar dependencias do frontend
Write-Host "`n[3/6] Instalando dependencias do frontend..." -ForegroundColor Yellow
Set-Location "$PROJECT_ROOT\frontend"
npm install --no-audit --no-fund
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Dependencias instaladas!" -ForegroundColor Green
} else {
    Write-Host "  ERRO: npm install falhou" -ForegroundColor Red
    exit 1
}

# 4. Compilar Core Rust
Write-Host "`n[4/6] Compilando Core Rust..." -ForegroundColor Yellow
Set-Location "$PROJECT_ROOT\core"
cargo build --release
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Core compilado com sucesso!" -ForegroundColor Green
} else {
    Write-Host "  ERRO na compilacao do Core" -ForegroundColor Red
    exit 1
}

# 5. Build Frontend
Write-Host "`n[5/6] Compilando Frontend..." -ForegroundColor Yellow
Set-Location "$PROJECT_ROOT\frontend"
npm run build
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Frontend compilado!" -ForegroundColor Green
} else {
    Write-Host "  AVISO: Build do frontend teve erros (continuando)" -ForegroundColor Yellow
}

# 6. Criar diretorio de dados
Write-Host "`n[6/6] Criando diretorio de dados..." -ForegroundColor Yellow
$dataDir = "$PROJECT_ROOT\data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    Write-Host "  Diretorio criado: $dataDir" -ForegroundColor Green
}

Write-Host "`n=== Setup concluido! ===" -ForegroundColor Cyan
Write-Host "`nPara iniciar:" -ForegroundColor White
Write-Host "  1. Core Rust:    cd core && cargo run" -ForegroundColor Gray
Write-Host "  2. Frontend:     cd frontend && npm run dev" -ForegroundColor Gray
Write-Host "  3. Desktop:      cd frontend && npm run tauri dev" -ForegroundColor Gray
Write-Host "  4. Instalador:   cd frontend && npm run tauri build" -ForegroundColor Gray
Write-Host "  5. Docker:       docker compose up -d" -ForegroundColor Gray
