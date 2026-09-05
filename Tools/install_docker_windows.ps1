# ============================================================
# Script de instalacao do Docker Desktop no Windows para o
# projeto XAU_AI_PRO
#
# IMPORTANTE: execute como ADMINISTRADOR (PowerShell Admin):
#   Right-click PowerShell -> Run as administrator
#   Set-ExecutionPolicy Bypass -Scope Process -Force; .\Tools\install_docker_windows.ps1
# ============================================================

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Set-ExecutionPolicy Bypass -Scope Process -Force

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  INSTALACAO DO DOCKER DESKTOP - WINDOWS  " -ForegroundColor Cyan
Write-Host "  Projeto: XAU_AI_PRO" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
    Write-Host "ERRO: Execute este script como ADMINISTRADOR!" -ForegroundColor Red
    Write-Host "Clique com botao direito no PowerShell e 'Run as administrator'" -ForegroundColor Yellow
    Read-Host "Pressione Enter para sair"
    exit 1
}
# -----------------------------------------------------------
# STEP 1 - Habilitar WSL2
# -----------------------------------------------------------
Write-Host ""
Write-Host "STEP 1/5: Habilitando WSL2..." -ForegroundColor Yellow

# Habilitar Windows Subsystem for Linux
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [!] WSL feature pode ja estar habilitada" -ForegroundColor DarkYellow
}

# Habilitar Virtual Machine Platform
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [!] Virtual Machine Platform pode ja estar habilitada" -ForegroundColor DarkYellow
}

# Instalar WSL
Write-Host ""
Write-Host "  Instalando WSL 2..."
wsl --install --no-distribution 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [!] wsl --install falhou, tentando wsl --update..."
    wsl --update 2>$null
    wsl --set-default-version 2 2>$null
}

# -----------------------------------------------------------
# STEP 2 - Instalar Docker Desktop
# -----------------------------------------------------------
Write-Host ""
Write-Host "STEP 2/5: Instalando Docker Desktop..." -ForegroundColor Yellow

# Definir pasta de download
$downloadDir = "$env:TEMP\docker_install"
New-Item -ItemType Directory -Path $downloadDir -Force | Out-Null
$installer = "$downloadDir\DockerDesktopInstaller.exe"

# Download do instalador oficial
$url = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
Write-Host "  Baixando Docker Desktop de: $url" -ForegroundColor Gray
Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing

Write-Host "  Arquivo baixado: $installer ($([math]::Round((Get-Item $installer).Length / 1MB)) MB)"
Write-Host ""

# Instalar silent
Write-Host "  Instalando Docker Desktop (silencioso)..."
Start-Process -FilePath $installer -ArgumentList 'install', '--quiet', '--accept-license' -Wait
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [!] Instalador retornou codigo: $LASTEXITCODE" -ForegroundColor DarkYellow
}

# -----------------------------------------------------------
# STEP 3 - Conclusao
# -----------------------------------------------------------
Write-Host ""
Write-Host "STEP 3/5: Finalizando..." -ForegroundColor Yellow

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "  INSTALACAO PREPARADA" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  FASE 1 concluida! Para continuar:" -ForegroundColor Yellow
Write-Host "  1. REINICIE o computador agora" -ForegroundColor Yellow
Write-Host "  2. Apos reiniciar, abra o Docker Desktop (primeira vez)" -ForegroundColor Yellow
Write-Host "  3. No projeto execute:" -ForegroundColor Cyan
Write-Host "     cd `"$(Split-Path -Parent $PSScriptRoot)`"" -ForegroundColor Cyan
Write-Host "     docker compose up -d" -ForegroundColor Cyan
Write-Host ""

Read-Host "Pressione Enter para sair (voce deve reiniciar)"
