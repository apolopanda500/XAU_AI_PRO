# ============================================================
# POST-DOCKER-CLI SETUP - XAU AI PRO
# Executa apos instalar o Docker CLI manualmente (C:\Users\Micro\docker-cli)
#
# EXECUTE COMO ADMINISTRADOR:
#   Right-click PowerShell -> "Run as administrator"
#   Set-ExecutionPolicy Bypass -Scope Process -Force
#   .\Tools\post_docker_cli_setup.ps1
# ============================================================

$ErrorActionPreference = 'Stop'
Set-ExecutionPolicy Bypass -Scope Process -Force

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  POST DOCKER CLI SETUP - XAU AI PRO" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar admin
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERRO: Execute como ADMINISTRADOR!" -ForegroundColor Red
    Read-Host "Enter para sair"
    exit 1
}

# STEP 1 - Habilitar WSL
Write-Host "STEP 1/3: Habilitando WSL2..." -ForegroundColor Yellow
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart | Out-Null
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart | Out-Null

# Instalar WSL se possivel
wsl --install --no-distribution 2>&1 | Out-Null
wsl --update 2>&1 | Out-Null
wsl --set-default-version 2 2>&1 | Out-Null

Write-Host "  Feito (pode ser necessario reiniciar)." -ForegroundColor Green

# STEP 2 - Baixar Docker Desktop
Write-Host ""
Write-Host "STEP 2/3: Baixando Docker Desktop..." -ForegroundColor Yellow
$url = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
$installer = "$env:TEMP\DockerDesktopInstaller.exe"
curl.exe -L -o $installer $url --connect-timeout 15 --max-time 300 -s
if (Test-Path $installer) {
    $size = [math]::Round((Get-Item $installer).Length / 1MB)
    Write-Host "  Download OK: $size MB" -ForegroundColor Green
} else {
    Write-Host "  FALHA no download" -ForegroundColor Red
}

# STEP 3 - Instalar Docker Desktop (silencioso)
Write-Host "STEP 3/3: Instalando Docker Desktop..." -ForegroundColor Yellow
if (Test-Path $installer) {
    $p = Start-Process -FilePath $installer -ArgumentList 'install','--quiet','--accept-license' -Wait -PassThru
    if ($p.ExitCode -eq 0) {
        Write-Host "  Docker Desktop instalado!" -ForegroundColor Green
    } else {
        Write-Host "  Exit code: $($p.ExitCode)" -ForegroundColor DarkYellow
    }
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "  RESUMO" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Docker CLI (manual):    C:\Users\Micro\docker-cli\docker" -ForegroundColor Cyan
Write-Host "  Docker Desktop:         instalado (se baixou)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  PROXIMOS PASSOS:" -ForegroundColor Yellow
Write-Host "  1. REINICIE o computador (obrigatorio apos habilitar WSL)" -ForegroundColor Yellow
Write-Host "  2. Abra Docker Desktop" -ForegroundColor Yellow
Write-Host "  3. Em Settings -> Resources -> WSL Integration, ative" -ForegroundColor Yellow
Write-Host "  4. Teste: docker run hello-world" -ForegroundColor Yellow
Write-Host "  5. Projeto: cd ...\\XAU_AI_PRO && docker compose up -d" -ForegroundColor Cyan
Write-Host ""
Read-Host "Enter para sair"
