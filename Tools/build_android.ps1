# Build Android assincrono do XAU AI PRO.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File Tools\build_android.ps1 [-Mode debug|release]
#
# Este script:
#   1. Fixa JAVA_HOME no JBR do Android Studio (OpenJDK 25). O Gradle do
#      Android NAO aceita Java 8 -- causa historica de falha do build.
#   2. Exporta ANDROID_HOME/NDK_HOME para o Tauri CLI.
#   3. Roda `npx tauri android build` gravando saida em Logs\android_build.log.
#
# O build NAO e interrompido por timeouts do shell interativo: gravamos tudo
# em log e o resultado final aparece em Logs\android_build.log.

param(
    [ValidateSet('debug', 'release')]
    [string]$Mode = 'debug'
)

$ErrorActionPreference = 'Continue'

$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root 'frontend'
$logDir = Join-Path $root 'Logs'
$logFile = Join-Path $logDir 'android_build.log'

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# --- Requisitos ---------------------------------------------------------------
$jbr = 'C:\Program Files\Android\Android Studio\jbr'
if (-not (Test-Path $jbr)) {
    Write-Error "JBR do Android Studio nao encontrado em: $jbr"
    exit 1
}

$env:JAVA_HOME = $jbr
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
if (-not $env:ANDROID_HOME) {
    $env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
}
$ndkRoot = Join-Path $env:ANDROID_HOME 'ndk'
if (Test-Path $ndkRoot) {
    $ndk = (Get-ChildItem $ndkRoot -Directory | Sort-Object Name -Descending | Select-Object -First 1).FullName
    if ($ndk) { $env:NDK_HOME = $ndk }
}

function Write-Log([string]$text) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $text
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding utf8
}

"" | Set-Content -Path $logFile -Encoding utf8
Write-Log "=== BUILD ANDROID ($Mode) ==="
Write-Log "JAVA_HOME   = $env:JAVA_HOME"
Write-Log "ANDROID_HOME= $env:ANDROID_HOME"
Write-Log "NDK_HOME    = $env:NDK_HOME"

Push-Location $frontend
$exitCode = 1
try {
    $tauriArgs = @('tauri', 'android', 'build')
    if ($Mode -eq 'debug') { $tauriArgs += @('--debug', '--apk') }

    Write-Log "Comando: npx $($tauriArgs -join ' ')"
    & npx @tauriArgs 2>&1 | ForEach-Object {
        $line = "$_"
        Add-Content -Path $logFile -Value $line -Encoding utf8
        Write-Host $line
    }
    $exitCode = $LASTEXITCODE
    Write-Log "EXIT=$exitCode"
}
finally {
    Pop-Location
}

# --- Localiza os artefatos gerados --------------------------------------------
$genApp = Join-Path $frontend 'src-tauri\gen\android\app'
$apkRoot = Join-Path $genApp 'build\outputs\apk'
$aabRoot = Join-Path $genApp 'build\outputs\bundle'

Write-Log "=== ARTEFATOS ==="
Get-ChildItem -Path $apkRoot, $aabRoot -Recurse -Include '*.apk', '*.aab' -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Log ("{0}  ({1:N2} MB)" -f $_.FullName, ($_.Length / 1MB)) }

if ($exitCode -ne 0) {
    Write-Log "BUILD FALHOU -- veja $logFile"
    exit $exitCode
}
Write-Log "BUILD OK -- veja $logFile"
