# ============================================================
# POS-REBOOT DOCKER SETUP - XAU AI PRO
# Execute APÓS reiniciar o computador (ativa WSL2 + Docker)
#
#   .\Tools\pos_reboot_docker.ps1
#
# O que faz:
#   1. Verifica/atualiza WSL2
#   2. Garante Docker Desktop rodando
#   3. docker run hello-world (teste do daemon)
#   4. Valida docker-compose.yml do projeto
#   5. (Opcional) sobe a stack do projeto
# ============================================================

$ErrorActionPreference = 'Continue'
$PROJECT = Split-Path -Parent $PSScriptRoot

# Garantir Docker CLI no PATH (instalacao do Desktop)
$dockerBin = 'C:\Program Files\Docker\Docker\resources\bin'
if (Test-Path $dockerBin) { $env:PATH = "$dockerBin;$env:PATH" }

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  POS-REBOOT DOCKER SETUP - XAU AI PRO" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# -----------------------------------------------------------
# STEP 1 - WSL2
# -----------------------------------------------------------
Write-Host ""
Write-Host "STEP 1/5: Verificando WSL2..." -ForegroundColor Yellow
wsl --status 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  WSL ainda inativo. Tentando instalar..." -ForegroundColor DarkYellow
    wsl --install --no-distribution
    wsl --update
}
wsl --set-default-version 2 2>$null
wsl --version 2>&1 | Select-Object -First 3
Write-Host "  WSL verificado." -ForegroundColor Green

# -----------------------------------------------------------
# STEP 2 - Docker Desktop rodando
# -----------------------------------------------------------
Write-Host ""
Write-Host "STEP 2/5: Verificando Docker Desktop..." -ForegroundColor Yellow
$dd = Get-Process -Name 'Docker Desktop' -ErrorAction SilentlyContinue
if (-not $dd) {
    Write-Host "  Iniciando Docker Desktop..."
    Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
    Write-Host "  Aguardando engine (45s)..."
    Start-Sleep -Seconds 45
} else {
    Write-Host "  Docker Desktop ja esta rodando." -ForegroundColor Green
}

# -----------------------------------------------------------
# STEP 3 - Teste do daemon (hello-world)
# -----------------------------------------------------------
Write-Host ""
Write-Host "STEP 3/5: Testando o daemon (docker run hello-world)..." -ForegroundColor Yellow
docker run --rm hello-world 2>&1 | Select-String -Pattern 'Hello from Docker|error|Error' | Select-Object -First 3
if ($LASTEXITCODE -eq 0) {
    Write-Host "  DAEMON FUNCIONANDO!" -ForegroundColor Green
} else {
    Write-Host "  Daemon ainda nao respondeu." -ForegroundColor Red
    Write-Host "  Dica: abra o Docker Desktop e aguarde o icone ficar verde," -ForegroundColor Yellow
    Write-Host "  depois rode este script novamente." -ForegroundColor Yellow
}

# -----------------------------------------------------------
# STEP 4 - Validar compose do projeto
# -----------------------------------------------------------
Write-Host ""
Write-Host "STEP 4/5: Validando docker-compose.yml do projeto..." -ForegroundColor Yellow
Set-Location $PROJECT
docker compose config --quiet
if ($LASTEXITCODE -eq 0) { Write-Host "  Compose valido." -ForegroundColor Green }

# -----------------------------------------------------------
# STEP 5 - Subir a stack (pergunta)
# -----------------------------------------------------------
Write-Host ""
Write-Host "STEP 5/5: Deseja subir a stack do projeto agora (backend + litellm)?" -ForegroundColor Yellow
$resp = Read-Host "  Digite S para sim (ou Enter para pular)"
if ($resp -match '^[Ss]') {
    docker compose up -d
    docker compose ps
    Write-Host ""
    Write-Host "  Backend : http://localhost:3000/api/health" -ForegroundColor Cyan
    Write-Host "  LiteLLM : http://localhost:4000/v1/models" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "  POS-REBOOT CONCLUIDO" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Read-Host "Enter para sair"
