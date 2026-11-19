param(
  [switch]$BootEmulator = $true
)
# Bateria total 10/10 — XAU AI PRO
# Roda as camadas na ordem e reporta cada resultado. Nada toca no EA producao.
$ErrorActionPreference = "Continue"
$StartTime = Get-Date
$ReportFile = "Docs/BATERIA_COMPLETA_10_10.md"
$Results = @()

function Add-Result($Layer, $Check, $Passed, $Detail) {
  $status = if ($Passed) { "PASSOU" } else { "FALHOU" }
  $script:Results += "| $Layer | $Check | **$status** | $Detail |"
  Write-Host "[$status] $Layer - $Check : $Detail"
}

# Camada 1 — Governanca e seguranca
& ".venv\Scripts\python.exe" -m pytest -q tests/test_sem_codigo_morto.py tests/test_mobile_control.py tests/test_mobile_command.py tests/test_chaos_persistence.py
Add-Result "Camada 1 (Governanca)" "Zero codigo morto + comandos moveis" ($LASTEXITCODE -eq 0) "pytest exit=$LASTEXITCODE"

# Camada 2 — Rust
cargo test --locked --manifest-path core/Cargo.toml
Add-Result "Camada 2 (Rust Core)" "cargo test locked" ($LASTEXITCODE -eq 0) "cargo exit=$LASTEXITCODE"

# Camada 3 — Frontend
Push-Location frontend
npx tsc --noEmit; $tsc = ($LASTEXITCODE -eq 0)
npx vitest run; $ui = ($LASTEXITCODE -eq 0)
npm audit --audit-level=high; $aud = ($LASTEXITCODE -eq 0)
Pop-Location
Add-Result "Camada 3 (Frontend)" "tsc + vitest + audit" ($tsc -and $ui -and $aud) "tsc=$tsc vitest=$ui audit=$aud"

# Camada 4 — Android
if (Test-Path "frontend/src-tauri/gen/android/app/build/outputs/apk") {
  $apk = Get-ChildItem "frontend/src-tauri/gen/android/app/build/outputs/apk" -Filter "*.apk" -Recurse | Select-Object -First 1
  foreach ($d in (adb devices | Select-String "`tdevice$")) {
    $serial = ($d.ToString() -split "`t")[0].Trim()
    adb -s $serial install -r "$($apk.FullName)" | Out-Null
  }
  $script:exit4 = 0
} else { $script:exit4 = 1 }
& ".venv\Scripts\python.exe" tests/e2e_vision_multi_device.py
Add-Result "Camada 4 (Android Vision)" "screencap + uiautomator" ($LASTEXITCODE -eq 0) "vision exit=$LASTEXITCODE"

# Camada 5 — Producao
$gw = Get-NetTCPConnection -LocalPort 9027 -State Listen -ErrorAction SilentlyContinue
Add-Result "Camada 5 (Producao)" "Gateway 9027 online" ($null -ne $gw) "9027=$(if ($gw) { 'ONLINE' } else { 'OFFLINE' })"

$Duration = [math]::Round(((Get-Date) - $StartTime).TotalSeconds, 1)
$Doc = "# BATERIA COMPLETA (10/10)`n`n- Data: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n- Duracao: ${Duration}s`n`n$($Results -join "`n")"
$Doc | Set-Content -Encoding UTF8 $ReportFile
Write-Host "[CONCLUIDO] $ReportFile"
