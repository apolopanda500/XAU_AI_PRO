# ============================================================
# Script de integracao com o Vercel Container Registry (VCR)
# Projeto: XAU_AI_PRO
# ============================================================
# Requisitos:
#   - Vercel CLI (npm i -g vercel)
#   - Docker, Podman ou Buildah instalado e no PATH
#   - Projeto linkado (`vercel link`)
#
# Uso:
#   .\Tools\vercel_vcr_setup.ps1
# ============================================================

$ErrorActionPreference = 'Stop'
$PROJECT_ROOT = Split-Path $PSScriptRoot -Parent

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  VERCEl CONTAINER REGISTRY (VCR) SETUP" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PROJECT_ROOT

# STEP 1 - Verificar Docker
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
$podmanCmd = Get-Command podman -ErrorAction SilentlyContinue
$buildahCmd = Get-Command buildah -ErrorAction SilentlyContinue

if ($dockerCmd) { $TOOL = "docker" }
elseif ($podmanCmd) { $TOOL = "podman" }
elseif ($buildahCmd) { $TOOL = "buildah" }
else {
    Write-Host "ERRO: Nenhum container tool encontrado (docker/podman/buildah)" -ForegroundColor Red
    Write-Host "Instale Docker Desktop ou use Podman."
    exit 1
}
Write-Host "Container tool encontrado: $TOOL" -ForegroundColor Green

# STEP 2 - Verificar CLI Vercel
$vercelCmd = Get-Command vercel -ErrorAction SilentlyContinue
if (-not $vercelCmd) {
    Write-Host "ERRO: Vercel CLI nao encontrada." -ForegroundColor Red
    Write-Host "Instale com: npm i -g vercel"
    exit 1
}
Write-Host "Vercel CLI: OK" -ForegroundColor Green

# STEP 3 - Verificar login
Write-Host "Verificando login Vercel..."
$who = vercel whoami 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Voce precisa fazer login na Vercel:" -ForegroundColor Yellow
    vercel login
} else {
    Write-Host "Logado como: $($who | Select-Object -First 1)" -ForegroundColor Green
}

# STEP 4 - Linkar projeto
$projFile = Join-Path $PROJECT_ROOT '.vercel\project.json'
if (Test-Path $projFile) {
    $proj = Get-Content $projFile -Raw | ConvertFrom-Json
    Write-Host "Projeto linkado: $($proj.projectName) (ID: $($proj.projectId))" -ForegroundColor Green
} else {
    Write-Host "Linkando projeto Vercel..."
    vercel link --yes
}

# STEP 5 - Autenticar container tool no VCR
Write-Host ""
Write-Host "Autenticando $TOOL com o Vercel Container Registry..." -ForegroundColor Yellow
vercel vcr login $TOOL
if ($LASTEXITCODE -ne 0) {
    Write-Host "FALHA ao autenticar no VCR." -ForegroundColor Red
    exit 1
}
Write-Host "Autenticado com sucesso!" -ForegroundColor Green

# STEP 6 - Build e push da imagem
Write-Host ""
Write-Host "Fazendo build e push da imagem no VCR..." -ForegroundColor Yellow
Write-Host "  Contexto: ./backend"
Write-Host "  Dockerfile: ./backend/Dockerfile"
Write-Host ""

# O vercel vcr build tem a sintaxe: vercel vcr build <tool> <path> [flags]
if ($TOOL -eq "docker") {
    vercel vcr build docker ./backend --push
} else {
    vercel vcr build $TOOL ./backend --push
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "FALHA no build/push da imagem." -ForegroundColor Red
    exit 1
}

# STEP 7 - Sumario
Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "  VCR SETUP CONCLUIDO COM SUCESSO!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Sua imagem foi publicada em:" -ForegroundColor Cyan
Write-Host "  vcr.vercel.com/apolopanda500/xau-ai-pro-api/xau-ai-pro-backend:latest" -ForegroundColor White
Write-Host ""
Write-Host "  Para usar com Vercel Functions:" -ForegroundColor Yellow
Write-Host "  1. O VCR cria o repositorio automaticamente no primeiro push"
Write-Host '  2. Consulte: vercel vcr tag list xau-ai-pro-backend'
Write-Host '  3. Deploy: vercel deploy --prebuilt'
Write-Host ""
Write-Host "  Pode usar a imagem em qualquer Docker/Podman host com:" -ForegroundColor Yellow
Write-Host "  docker pull vcr.vercel.com/apolopanda500/xau-ai-pro-api/xau-ai-pro-backend:latest"
Write-Host ""
Read-Host "Pressione Enter para sair"