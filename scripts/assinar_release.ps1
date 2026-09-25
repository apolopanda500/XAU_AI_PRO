<#
.SYNOPSIS
    Assina os artefatos principais de uma pasta de release do XAU AI PRO.

.DESCRIPTION
    Usa Authenticode via signtool. Nao cria certificado e nao promete reputacao
    SmartScreen. Para confianca publica, use certificado de Code Signing de CA
    confiavel e timestamp RFC 3161.

    Exemplos:
      powershell -File .\scripts\assinar_release.ps1 -ReleaseRoot .\release\1.2.3 -Pfx C:\certs\xau.pfx -Password 'senha'
      powershell -File .\scripts\assinar_release.ps1 -ReleaseRoot .\release\1.2.3 -Thumbprint ABCDEF...
#>

[CmdletBinding()]
param(
    [string]$ReleaseRoot = 'release\1.2.3',
    [string]$Pfx = '',
    [string]$Password = '',
    [string]$Thumbprint = '',
    [string]$TimestampUrl = 'http://timestamp.digicert.com'
)

$ErrorActionPreference = 'Stop'

$signtool = Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\bin' -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
    Sort-Object FullName -Descending |
    Select-Object -First 1

if (-not $signtool) {
    throw 'signtool.exe nao encontrado. Instale o Windows SDK.'
}

$releasePath = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$targets = @(
    'pyinstaller-XAU_AI_PRO\XAU_AI_PRO.exe',
    'xau-ai-pro-core.exe',
    'bridge\mt5-gateway.exe',
    'tauri\XAU AI PRO.exe',
    'tauri\bundle\msi\XAU AI PRO_1.2.3_x64_en-US.msi',
    'tauri\bundle\nsis\XAU AI PRO_1.2.3_x64-setup.exe'
)

$signArgsBase = @('sign', '/fd', 'SHA256', '/tr', $TimestampUrl, '/td', 'SHA256', '/v')
if (-not [string]::IsNullOrWhiteSpace($Pfx)) {
    $pfxPath = (Resolve-Path -LiteralPath $Pfx).Path
    $signArgsBase += @('/f', $pfxPath)
    if (-not [string]::IsNullOrWhiteSpace($Password)) {
        $signArgsBase += @('/p', $Password)
    }
} elseif (-not [string]::IsNullOrWhiteSpace($Thumbprint)) {
    $signArgsBase += @('/sha1', $Thumbprint)
} else {
    $signArgsBase += @('/a')
}

foreach ($rel in $targets) {
    $path = Join-Path $releasePath $rel
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Artefato ausente: $path"
    }
    Write-Host "Assinando: $path"
    & $signtool.FullName @signArgsBase $path
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao assinar: $path"
    }
}

foreach ($rel in $targets) {
    $path = Join-Path $releasePath $rel
    Write-Host "Verificando: $path"
    & $signtool.FullName verify /pa /v $path
    if ($LASTEXITCODE -ne 0) {
        throw "Falha na verificacao Authenticode: $path"
    }
}

Write-Host 'Assinatura concluida. Recalcule hashes, atualize o manifest e rode Defender.'