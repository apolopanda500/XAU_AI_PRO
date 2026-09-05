# ============================================================
# SETUP CLAUDE NO VERcel SANDBOX - XAU AI PRO
# ============================================================
# Este script configura o Claude Code dentro de um Vercel Sandbox.
#
# Target:  apolopanda500 / xau-ai-pro-api
# Sandbox: my-sandbox-448760
#
# Como usar:
#   .\Tools\setup_sandbox_claude.ps1
# ============================================================

$ErrorActionPreference = 'Stop'

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  SETUP CLAUDE NO VERcel SANDBOX" -ForegroundColor Cyan
Write-Host "  Sandbox: my-sandbox-448760" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# -----------------------------------------------------------
# STEP 1 - Verificar npx / Node
# -----------------------------------------------------------
$npxCmd = Get-Command npx -ErrorAction SilentlyContinue
if (-not $npxCmd) {
    Write-Host "ERRO: Node.js/npx nao encontrado." -ForegroundColor Red
    Write-Host "Instale Node.js LTS de: https://nodejs.org/"
    Read-Host "Pressione Enter para sair"
    exit 1
}
Write-Host "npx encontrado: $($npxCmd.Source)" -ForegroundColor Green

# -----------------------------------------------------------
# STEP 2 - Autenticacao (token OIDC salvo, evita login interativo)
# -----------------------------------------------------------
$envFile = Join-Path $PSScriptRoot '..\sandbox-quickstart\.env.local'
if (Test-Path $envFile) {
    $m = [regex]::Match((Get-Content $envFile -Raw), 'VERCEL_OIDC_TOKEN="([^"]+)"')
    if ($m.Success) {
        $env:VERCEL_AUTH_TOKEN = $m.Groups[1].Value
        Write-Host "Token VERCEL_AUTH_TOKEN carregado de sandbox-quickstart\.env.local" -ForegroundColor Green
    }
}

# Login interativo somente se nao houver token
if (-not $env:VERCEL_AUTH_TOKEN) {
    Write-Host ""
    Write-Host "STEP 1/4: Login na Sandbox CLI..." -ForegroundColor Yellow
    Write-Host "  Se abrir uma janela no navegador, complete a autenticacao e volte aqui."
    Write-Host ""
    npx sandbox login
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FALHA no login. Verifique o navegador." -ForegroundColor Red
        Read-Host "Pressione Enter para tentar novamente (ou Ctrl+C para sair)"
        npx sandbox login
    }
}
Write-Host "Autenticacao OK!" -ForegroundColor Green

# -----------------------------------------------------------
# STEP 3 - Criar o Sandbox
# -----------------------------------------------------------
Write-Host ""
Write-Host "STEP 2/4: Criando Sandbox 'my-sandbox-448760'..." -ForegroundColor Yellow
Write-Host "  Scope: apolopanda500"
Write-Host "  Project: xau-ai-pro-api"
Write-Host "  Network: allow-all"
Write-Host ""

# Verificar se ja existe
$existing = npx sandbox list --scope apolopanda500 --project xau-ai-pro-api 2>$null
if ($existing -match "my-sandbox-448760") {
    Write-Host "Sandbox 'my-sandbox-448760' JA EXISTE. Conectando..." -ForegroundColor DarkYellow
    npx sandbox connect my-sandbox-448760 --scope apolopanda500 --project xau-ai-pro-api
} else {
    npx sandbox create --name "my-sandbox-448760" --scope "apolopanda500" --project "xau-ai-pro-api" --network-policy allow-all --connect
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "FALHA ao criar sandbox." -ForegroundColor Red
    Read-Host "Pressione Enter para sair"
    exit 1
}

# -----------------------------------------------------------
# STEP 4 - Rodar Claude
# -----------------------------------------------------------
Write-Host ""
Write-Host "STEP 3/4: Rodando Claude dentro do sandbox..." -ForegroundColor Yellow
Write-Host "  Se o Claude pedir autenticacao, complete o login no navegador (ou use 'c' para copiar a URL)."
Write-Host ""

# Dentro do sandbox: instalar e rodar Claude
npx sandbox exec my-sandbox-448760 --scope apolopanda500 --project xau-ai-pro-api -- bash -c "npm install -g @anthropic-ai/claude-code && claude" 2>&1

# -----------------------------------------------------------
# STEP 5 - Conclusao
# -----------------------------------------------------------
Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  SETUP CONCLUIDO!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Para conectar novamente ao sandbox:" -ForegroundColor Yellow
Write-Host "  npx sandbox connect my-sandbox-448760 --scope apolopanda500 --project xau-ai-pro-api"
Write-Host ""
Write-Host "  Para parar o sandbox (importante!):" -ForegroundColor Yellow
Write-Host "  npx sandbox stop my-sandbox-448760 --scope apolopanda500 --project xau-ai-pro-api"
Write-Host ""
Write-Host "  Dentro do Claude, quando terminar, rode:" -ForegroundColor Cyan
Write-Host "  claude auth logout"
Write-Host ""
Read-Host "Pressione Enter para sair"