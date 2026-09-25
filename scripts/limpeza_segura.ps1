<#
.SYNOPSIS
    Lista ou remove somente artefatos temporarios conhecidos do XAU AI PRO.

.DESCRIPTION
    Por padrao roda em modo dry-run. Nao toca MQL5\Experts, MQL5\Include,
    Models, Data, Logs de trading, APPDATA fora do projeto nem pastas do Windows.
    Para remover, execute com -Apply apos revisar a lista.
#>

[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$BuildArtifacts,
    [switch]$PrebuildBackups,
    [string]$Root = ''
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($Root)) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    if ([string]::IsNullOrWhiteSpace($scriptDir)) { $scriptDir = (Get-Location).Path }
    $Root = Join-Path $scriptDir '..'
}
$rootPath = (Resolve-Path -LiteralPath $Root).Path
$allowed = @(
    '.pytest_cache', '.pytest-cycle-clean', '.pytest-runtime', '.pytest-suite-run',
    'frontend\.vite', 'frontend\dist', 'Temp\pyinstaller_latest.out.log',
    'Temp\pyinstaller_latest.err.log', 'Temp\pyinstaller_latest.pid'
)
if ($BuildArtifacts) {
    $allowed += @('build', 'dist', 'core\target', 'frontend\src-tauri\target', 'Temp\cargo-target')
}
if ($PrebuildBackups) {
    $allowed += @(Get-ChildItem -LiteralPath (Join-Path $rootPath 'Logs') -Directory -Filter 'backup_prebuild_*' -ErrorAction SilentlyContinue | ForEach-Object {
        $_.FullName.Substring($rootPath.Length).TrimStart('\')
    })
}

Write-Host "Raiz: $rootPath"
Write-Host ("Modo: {0}" -f ($(if ($Apply) { 'APLICAR' } else { 'DRY-RUN' })))

$items = @()
foreach ($rel in $allowed) {
    $path = Join-Path $rootPath $rel
    if (Test-Path -LiteralPath $path) {
        $resolved = (Resolve-Path -LiteralPath $path).Path
        if (-not $resolved.StartsWith($rootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Caminho fora da raiz bloqueado: $resolved"
        }
        $items += Get-Item -LiteralPath $resolved -Force
    }
}

if ($items.Count -eq 0) {
    Write-Host 'Nenhum temporario conhecido encontrado.'
    exit 0
}

foreach ($item in $items) {
    Write-Host ("{0}  {1}" -f ($(if ($item.PSIsContainer) { 'DIR ' } else { 'ARQ ' })), $item.FullName)
}

if (-not $Apply) {
    Write-Host 'Dry-run concluido. Reexecute com -Apply para remover somente estes itens.'
    exit 0
}

foreach ($item in $items) {
    Remove-Item -LiteralPath $item.FullName -Recurse -Force
}
Write-Host 'Limpeza segura concluida.'