# Verificador de sincronia — XAU AI PRO (leitura pura, nada altera)
# Mostra o estado de: version.json, git, gateway 9027, app no Android,
# release publicada no GitHub e o .ex5 de producao.
$ErrorActionPreference = "Continue"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " SINCRONIA - XAU AI PRO" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Versao no codigo-fonte
$target = (Get-Content "Docs/version.json" -Raw | ConvertFrom-Json).version
Write-Host "[1/6] Docs/version.json: v$target" -ForegroundColor Green

# 2. Git
$branch = git rev-parse --abbrev-ref HEAD 2>$null
$sha = git rev-parse --short HEAD 2>$null
$dirty = (git status --porcelain 2>$null).Count
$cor = if ($dirty -eq 0) { "Green" } else { "Yellow" }
Write-Host "[2/6] git: $branch @ $sha | pendentes: $dirty" -ForegroundColor $cor

# 3. Gateway 9027 (fail-closed 401 e esperado sem token)
try {
    $gw = Invoke-WebRequest -Uri "http://127.0.0.1:9027/api/health" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
    Write-Host "[3/6] Gateway 9027: HTTP $($gw.StatusCode) (ONLINE)" -ForegroundColor Green
} catch {
    $code = $_.Exception.Response.StatusCode.value__
    if ($code -eq 401) {
        Write-Host "[3/6] Gateway 9027: 401 fail-closed (ONLINE, aguardando token)" -ForegroundColor Yellow
    } else {
        Write-Host "[3/6] Gateway 9027: SEM RESPOSTA ($($_.Exception.Message))" -ForegroundColor Red
    }
}

# 4. App instalado no Android
$adb = (Get-Command adb -ErrorAction SilentlyContinue).Source
if ($adb) {
    $raw = & adb shell dumpsys package com.xau_ai_pro.desktop 2>$null | Select-String "versionName"
    if ($raw) {
        $v = ($raw -split "=")[1].Trim()
        $match = ($v -eq $target)
        Write-Host "[4/6] Android: v$v $(if ($match) { '[SINCRONIZADO]' } else { '[DIVERGENTE - alvo v' + $target + ']' })" -ForegroundColor $(if ($match) { "Green" } else { "Red" })
    } else {
        Write-Host "[4/6] Android: app nao instalado neste aparelho" -ForegroundColor Yellow
    }
} else {
    Write-Host "[4/6] Android: adb nao encontrado" -ForegroundColor Yellow
}

# 5. Release no GitHub (via gh ou HTTPS publico)
try {
    if (Get-Command gh -ErrorAction SilentlyContinue) {
        $rel = gh api "repos/apolopanda500/XAU_AI_PRO/releases/latest" --jq '.tag_name' 2>$null
    } else {
        $rel = (Invoke-RestMethod -Uri "https://api.github.com/repos/apolopanda500/XAU_AI_PRO/releases/latest" -TimeoutSec 5).tag_name
    }
    $ghv = $rel -replace "^v", ""
    $match = ($ghv -eq $target)
    Write-Host "[5/6] GitHub latest: v$ghv $(if ($match) { '[SINCRONIZADO]' } else { '[DIVERGENTE - alvo v' + $target + ']' })" -ForegroundColor $(if ($match) { "Green" } else { "Red" })
} catch {
    Write-Host "[5/6] GitHub latest: falha na consulta ($($_.Exception.Message))" -ForegroundColor Yellow
}

# 6. EA MQL5 de producao (caminho fora do repo)
$ex5 = "C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\XAU_AI_PRO\XAU_AI_PRO.ex5"
if (Test-Path $ex5) {
    $md5 = (Get-FileHash $ex5 -Algorithm MD5).Hash
    Write-Host "[6/6] EA producao: $(Get-Item $ex5 | ForEach-Object { $_.Length }) bytes | MD5 $md5 (NAO TOCADO)" -ForegroundColor Cyan
} else {
    Write-Host "[6/6] EA producao: nao encontrado no caminho esperado" -ForegroundColor Red
}
Write-Host "=================================================================" -ForegroundColor Cyan
