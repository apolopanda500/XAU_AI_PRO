# Verificador de sincronia - XAU AI PRO (leitura pura, nada altera)
$ErrorActionPreference = "Continue"
$target = (Get-Content "Docs/version.json" -Raw | ConvertFrom-Json).version
Write-Host "=== SINCRONIA XAU AI PRO v$target ===" -ForegroundColor Cyan
Write-Host "[1] Docs/version.json: v$target" -ForegroundColor Green
$branch = git rev-parse --abbrev-ref HEAD 2>$null
$sha = git rev-parse --short HEAD 2>$null
$dirty = (git status --porcelain 2>$null).Count
Write-Host "[2] Git: $branch @ $sha | pendentes: $dirty" -ForegroundColor $(if ($dirty -eq 0) { "Green" } else { "Yellow" })
try {
  $gw = Invoke-WebRequest -Uri "http://127.0.0.1:9027/api/health" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
  Write-Host "[3] Gateway 9027: HTTP $($gw.StatusCode) (ONLINE)" -ForegroundColor Green
} catch { Write-Host "[3] Gateway 9027: fail-closed 401 (esperado sem token)" -ForegroundColor Yellow }
$adb = adb shell dumpsys package com.xau_ai_pro.desktop 2>$null | Select-String "versionName=" | Select-Object -First 1
if ($adb) {
  $v = ($adb.ToString() -split "=")[1].Trim()
  Write-Host "[4] Android: v$v $(if ($v -eq $target) { '[SINCRONIZADO]' } else { '[DIVERGENTE]' })" -ForegroundColor $(if ($v -eq $target) { "Green" } else { "Red" })
} else { Write-Host "[4] Android: desconectado" -ForegroundColor Yellow }
try {
  $rel = gh release view v$target --repo apolopanda500/XAU_AI_PRO --json assets --jq '.assets | length' 2>$null
  Write-Host "[5] Release v$target: $rel assets" -ForegroundColor Green
} catch { Write-Host "[5] Release: falha na consulta" -ForegroundColor Yellow }
Write-Host "======================================" -ForegroundColor Cyan
