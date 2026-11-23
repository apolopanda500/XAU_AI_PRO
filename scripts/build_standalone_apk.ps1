param(
    [Parameter(Mandatory=$true)]
    [string]$GatewayUrl,
    [string]$WsUrl = "",
    [string]$BuildTarget = "production"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root "frontend"

if (-not $WsUrl) {
    $WsUrl = $GatewayUrl -replace "^http", "ws" -replace "/?$", "/ws/market"
}

$envFile = Join-Path $frontend ".env.production"
$lines = @(
    "VITE_API_BASE=$GatewayUrl",
    "VITE_WS_URL=$WsUrl"
)
$lines | Set-Content -Path $envFile -Encoding UTF8
Write-Host "[build] .env.production escrito: VITE_API_BASE=$GatewayUrl  VITE_WS_URL=$WsUrl"

Push-Location $frontend
try {
    Write-Host "[build] npm run build ..."
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build falhou (exit $LASTEXITCODE)" }

    Write-Host "[build] tauri android build ..."
    $env:NDK_HOME = "C:\Users\Micro\AppData\Local\Android\Sdk\ndk\28.2.13676358"
    $env:CARGO_TARGET_DIR = "C:\Users\Micro\AppData\Local\Temp\opencode\cargo-build"
    npx tauri android build --apk --debug --target aarch64
    if ($LASTEXITCODE -ne 0) { throw "tauri android build falhou (exit $LASTEXITCODE)" }

    $apk = Get-ChildItem -Path "src-tauri/gen/android/app/build/outputs/apk" -Filter "*.apk" -Recurse | Select-Object -First 1
    Write-Host "[build] APK gerado: $($apk.FullName) ($($apk.Length) bytes)"
    $hash = (Get-FileHash $apk.FullName -Algorithm SHA256).Hash.ToLower()
    Write-Host "[build] SHA256: $hash"
    "$hash  $($apk.Name)" | Set-Content (Join-Path $root "SHA256SUMS_standalone.txt") -Encoding ascii
    Write-Host "[build] Hash salvo em SHA256SUMS_standalone.txt"
} finally {
    Pop-Location
}

Write-Host "[build] CONCLUIDO. APK pronto para release."
