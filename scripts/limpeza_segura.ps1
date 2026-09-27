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
    [switch]$DebugCache,
    [switch]$PrebuildBackups,
    # -DryRun e o padrao; existe como switch explicito porque a documentacao e
    # os operadores o citam. Sem efeito quando -Apply esta presente.
    [switch]$DryRun,
    # Remove apenas os itens informados (caminhos relativos da allowlist).
    # Sem este parametro vale a allowlist inteira das opcoes acima.
    [string[]]$Only = @(),
    [string]$Root = ''
)

$ErrorActionPreference = 'Stop'
if ($Apply -and $DryRun) {
    Write-Warning '-DryRun junto de -Apply: o dry-run nao tem efeito. Seguindo com -Apply.'
    $DryRun = $false
}
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
if ($DebugCache) {
    # Cache de compilacao de depuracao: nunca e necessario para build, teste ou
    # release, e era ~1 GB ocupando espaco quando o disco estava critico.
    $allowed += @('frontend\src-tauri\target\debug', 'core\target\debug')
}
if ($PrebuildBackups) {
    $allowed += @(Get-ChildItem -LiteralPath (Join-Path $rootPath 'Logs') -Directory -Filter 'backup_prebuild_*' -ErrorAction SilentlyContinue | ForEach-Object {
        $_.FullName.Substring($rootPath.Length).TrimStart('\')
    })
}

Write-Host "Raiz: $rootPath"
Write-Host ("Modo: {0}" -f ($(if ($Apply) { 'APLICAR' } else { 'DRY-RUN' })))

$items = @()
$selecionados = if ($Only.Count -gt 0) { $Only } else { $allowed }
foreach ($rel in $selecionados) {
    $path = Join-Path $rootPath $rel
    if (Test-Path -LiteralPath $path) {
        $resolved = (Resolve-Path -LiteralPath $path).Path
        if (-not $resolved.StartsWith($rootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Caminho fora da raiz bloqueado: $resolved"
        }
        $items += Get-Item -LiteralPath $resolved -Force
    }
}
if ($Only.Count -gt 0) {
    $naoPermitidos = @($Only | Where-Object { $allowed -notcontains $_ })
    if ($naoPermitidos.Count -gt 0) {
        throw "caminho fora da allowlist: $($naoPermitidos -join ', ')"
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