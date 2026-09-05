# ============================================================
# CONECTAR AO SANDBOX COM CLAUDE - XAU AI PRO
# Sandbox: my-sandbox-448760 (apolopanda500 / xau-ai-pro-api)
#
# Uso:
#   .\Tools\connect_sandbox_claude.ps1
#
# Fluxo:
#   1. Carrega o token (sem login interativo)
#   2. Retoma o sandbox e abre o shell interativo
#   3. Dentro do shell, rode: claude
#      - Pressione [c] para copiar a URL de login
#      - Cole no navegador, faca login e volte
#   4. Ao terminar: claude auth logout; exit
# ============================================================

$ErrorActionPreference = 'Stop'

# Carregar token do .env.local (evita login interativo da CLI)
$envFile = Join-Path $PSScriptRoot '..\sandbox-quickstart\.env.local'
if (Test-Path $envFile) {
    $m = [regex]::Match((Get-Content $envFile -Raw), 'VERCEL_OIDC_TOKEN="([^"]+)"')
    if ($m.Success) {
        $env:VERCEL_AUTH_TOKEN = $m.Groups[1].Value
        Write-Host "Token carregado." -ForegroundColor Green
    }
}
if (-not $env:VERCEL_AUTH_TOKEN) {
    Write-Host "Token nao encontrado em sandbox-quickstart\.env.local" -ForegroundColor Red
    Write-Host "Rode: cd sandbox-quickstart; npx vercel link --yes; npx vercel env pull .env.local --yes"
    Read-Host "Enter para sair"
    exit 1
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  SANDBOX: my-sandbox-448760" -ForegroundColor Cyan
Write-Host "  Claude Code 2.1.259 instalado" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Dentro do shell, rode: claude" -ForegroundColor Yellow
Write-Host "  Primeiro uso: pressione [c] para copiar a" -ForegroundColor Yellow
Write-Host "  URL de login, cole no navegador e faca login." -ForegroundColor Yellow
Write-Host "  Sair: claude auth logout (opcional) e exit" -ForegroundColor Yellow
Write-Host ""

# Abre o shell interativo (retoma o sandbox automaticamente)
sandbox ssh my-sandbox-448760 --project xau-ai-pro-api --scope apolopanda500

Write-Host ""
Write-Host "Sessao encerrada. Sandbox permanece salvo (snapshot)." -ForegroundColor Green
Write-Host "Para parar de vez: sandbox stop my-sandbox-448760 --project xau-ai-pro-api --scope apolopanda500" -ForegroundColor Yellow
Read-Host "Enter para fechar"