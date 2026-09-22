# XAU AI PRO - Setup Script
# Executa: powershell -ExecutionPolicy Bypass -File scripts/setup.ps1

Write-Host "=== XAU AI PRO - Setup ===" -ForegroundColor Cyan

$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot

# 1. Verificar Python
Write-Host "`n[1/7] Verificando Python..." -ForegroundColor Yellow
$python = Join-Path $PROJECT_ROOT ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3 -m venv (Join-Path $PROJECT_ROOT ".venv")
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        python -m venv (Join-Path $PROJECT_ROOT ".venv")
    } else {
        Write-Host "  ERRO: Python 3 nao encontrado." -ForegroundColor Red
        exit 1
    }
}
& $python -m pip install --upgrade pip --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Write-Host "  ERRO: atualizacao do pip falhou" -ForegroundColor Red; exit 1 }
& $python -m pip install -r (Join-Path $PROJECT_ROOT "requirements.txt") -r (Join-Path $PROJECT_ROOT "requirements-dev.txt") --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Write-Host "  ERRO: dependencias Python falharam" -ForegroundColor Red; exit 1 }
Write-Host "  Python validado: $(& $python --version)" -ForegroundColor Green

# 2. Verificar Rust
Write-Host "`n[2/7] Verificando Rust..." -ForegroundColor Yellow
if (Get-Command rustc -ErrorAction SilentlyContinue) {
    Write-Host "  Rust instalado: $(rustc --version)" -ForegroundColor Green
} else {
    Write-Host "  ERRO: Rust nao encontrado. Instale rustup antes de continuar." -ForegroundColor Red
    exit 1
}

# 2. Verificar Node.js
Write-Host "`n[3/7] Verificando Node.js..." -ForegroundColor Yellow
if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeVersion = node --version
    Write-Host "  Node.js instalado: $nodeVersion" -ForegroundColor Green
} else {
    Write-Host "  ERRO: Node.js nao encontrado. Instale de https://nodejs.org/" -ForegroundColor Red
    exit 1
}

# 3. Instalar dependencias do frontend
Write-Host "`n[4/7] Instalando dependencias do frontend..." -ForegroundColor Yellow
Set-Location "$PROJECT_ROOT\frontend"
npm ci --no-audit --no-fund
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Dependencias instaladas!" -ForegroundColor Green
} else {
    Write-Host "  ERRO: npm install falhou" -ForegroundColor Red
    exit 1
}

# 4. Compilar Core Rust
Write-Host "`n[5/7] Compilando Core Rust..." -ForegroundColor Yellow
Set-Location "$PROJECT_ROOT\core"
cargo build --release --locked
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Core compilado com sucesso!" -ForegroundColor Green
} else {
    Write-Host "  ERRO na compilacao do Core" -ForegroundColor Red
    exit 1
}

# 5. Build Frontend
Write-Host "`n[6/7] Compilando Frontend..." -ForegroundColor Yellow
Set-Location "$PROJECT_ROOT\frontend"
npm run build
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Frontend compilado!" -ForegroundColor Green
} else {
    Write-Host "  ERRO: Build do frontend falhou" -ForegroundColor Red
    exit 1
}

# 6. Criar diretorio de dados
Write-Host "`n[7/7] Criando diretorio de dados..." -ForegroundColor Yellow
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
