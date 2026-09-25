<#
.SYNOPSIS
    Assinatura unificada dos artefatos Windows (Authenticode) e Android (APK).

.DESCRIPTION
    Um comando para as duas plataformas, com o mesmo desenho:

      1. resolve as credenciais por scripts/segredos_windows.ps1 (DPAPI);
      2. assina (Windows: signtool. Android: zipalign + apksigner);
      3. verifica a assinatura depois de assinar;
      4. imprime os SHA-256 resultantes.

    Por que um script só: as duas plataformas precisam ser assinadas com o
    mesmo par de identidade e no mesmo passo de release. Manter dois
    procedures分开 é como um deles fica para trás e é publicado sem assinar.

    O certificado do Windows e o keystore do Android ficam em
    %LOCALAPPDATA%\XAU_AI_PRO\secrets, fora do repositorio e fora do %TEMP%.
    A senha do keystore e cifrada com DPAPI: só a conta do Windows do usuario
    decifra, na mesma maquina.

    ATENCAO - este script assina com identidade de TESTE (self-signed).
    Isso serve para desenvolvimento e para validar o pipeline. NAO e confiavel,
    nao remove o SmartScreen e nao vale para Google Play. Para producao:
      - Windows: certificado de CA (ou SignPath Foundation, que exige projeto
        open source). Ver Docs/DECISOES_PRODUTO_20260925.md, conflito A1 x B3.
      - Android: keystore de release guardado com seguranca + conta de
        desenvolvedor do Google Play (US$ 25 unico).

.PARAMETER Plataforma
    windows  -> apenas artefatos Authenticode
    android  -> apenas APK
    ambas    -> o padrao; assina os dois

.PARAMETER ReleaseRoot
    Pasta montada no formato esperado por scripts/assinar_release.ps1.

.PARAMETER Apk
    Caminho do APK a assinar. Se omitido, procura em Temp\opencode\artifacts.

.EXAMPLE
    .\scripts\assinar_tudo.ps1 -Plataforma ambas
#>

[CmdletBinding()]
param(
    [ValidateSet('windows', 'android', 'ambas')]
    [string]$Plataforma = 'ambas',

    [string]$ReleaseRoot = 'release\1.2.3',

    [string]$Apk = '',

    [string]$TimestampUrl = 'http://timestamp.digicert.com'
)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
$Secrets = Join-Path $env:LOCALAPPDATA 'XAU_AI_PRO\secrets'
$AndroidSdk = Join-Path $env:LOCALAPPDATA 'Android\Sdk'

# --- resolucao de ferramentas -------------------------------------------------

function Get-SignTool {
    $t = Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\bin' -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
        Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $t) { throw 'signtool.exe nao encontrado. Instale o Windows SDK.' }
    return $t.FullName
}

function Get-BuildTool([string]$Name) {
    $dir = Get-ChildItem (Join-Path $AndroidSdk 'build-tools') -Directory -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | Select-Object -First 1
    if (-not $dir) { throw 'build-tools do Android SDK nao encontrado.' }
    $path = Join-Path $dir.FullName $Name
    if (-not (Test-Path -LiteralPath $path)) { throw "$Name nao encontrado em $($dir.FullName)" }
    return $path
}

# --- credenciais (mesma fonte do restante do projeto) ------------------------

function Get-SecretValue([string]$Key) {
    . (Join-Path $PSScriptRoot 'segredos_windows.ps1') -Command Status | Out-Null
    $sec = Get-Secret -Key $Key
    if ($null -eq $sec) { return '' }
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    try { return [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

# --- Windows -----------------------------------------------------------------

function Invoke-WindowsSigning {
    Write-Host "`n=== Windows: Authenticode ===" -ForegroundColor Cyan

    $thumbFile = Join-Path $Secrets 'authenticode_thumbprint.txt'
    if (-not (Test-Path -LiteralPath $thumbFile)) {
        throw "certificado nao encontrado. Crie com New-SelfSignedCertificate e grave o thumbprint em $thumbFile"
    }
    $thumb = (Get-Content -LiteralPath $thumbFile -Raw).Trim()

    $signtool = Get-SignTool
    $root = (Resolve-Path -LiteralPath $ReleaseRoot).Path

    $alvos = @(
        'pyinstaller-XAU_AI_PRO\XAU_AI_PRO.exe',
        'xau-ai-pro-core.exe',
        'bridge\mt5-gateway.exe',
        'tauri\XAU AI PRO.exe',
        'tauri\bundle\msi\XAU AI PRO_1.2.3_x64_en-US.msi',
        'tauri\bundle\nsis\XAU AI PRO_1.2.3_x64-setup.exe',
        'XAU_AI_PRO_Setup_1.2.3.exe'
    ) | ForEach-Object { Join-Path $root $_ } | Where-Object { Test-Path -LiteralPath $_ }

    if (-not $alvos) { throw "nenhum artefato Windows encontrado em $root" }

    foreach ($alvo in $alvos) {
        Write-Host "  assinando: $(Split-Path $alvo -Leaf)"
        & $signtool sign /fd SHA256 /tr $TimestampUrl /td SHA256 /sha1 $thumb $alvo | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "falha ao assinar: $alvo" }
    }

    Write-Host "  verificando..." -ForegroundColor DarkGray
    foreach ($alvo in $alvos) {
        $sig = Get-AuthenticodeSignature -FilePath $alvo
        $temCert = if ($sig.SignerCertificate) { 'presente' } else { 'AUSENTE' }
        $temTs = if ($sig.TimeStamperCertificate) { 'presente' } else { 'ausente' }
        Write-Host ("    {0,-44} status={1} cert={2} ts={3}" -f (Split-Path $alvo -Leaf), $sig.Status, $temCert, $temTs)
        # Em certificado self-signed o Status e UnknownError por definicao:
        # a cadeia termina em raiz nao confiavel. O que precisa ser verificado
        # e que o certificado esta embutido e que o hash nao divergiu.
        if (-not $sig.SignerCertificate) { throw "assinatura ausente em: $alvo" }
        if ($sig.Status -eq 'HashMismatch' -or $sig.Status -eq 'Corrupt') {
            throw "assinatura corrompida em: $alvo"
        }
    }
    return $alvos
}

# --- Android -----------------------------------------------------------------

function Invoke-AndroidSigning {
    Write-Host "`n=== Android: APK ===" -ForegroundColor Cyan

    $apkPath = $Apk
    if (-not $apkPath) {
        $dir = Join-Path $env:TEMP 'opencode\artifacts'
        # Prefere o APK sem assinatura: assinar um APK ja assinado cria
        # '<nome>.apk.signed' e um .idsig orfao, o que confunde a release.
        $achado = Get-ChildItem $dir -Filter '*.apk' -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime |
            ForEach-Object {
                if ($_.Name -like '*unsigned*') { $_; break }
                if ($_.Name -notlike '*.signed') { $_; break }
            } | Select-Object -First 1
        if (-not $achado) { throw "nenhum APK em $dir" }
        $apkPath = $achado.FullName
    }
    if (-not (Test-Path -LiteralPath $apkPath)) { throw "APK nao encontrado: $apkPath" }

    $keystore = Join-Path $Secrets 'xau-local-test.p12'
    if (-not (Test-Path -LiteralPath $keystore)) { throw "keystore nao encontrado: $keystore" }
    $senha = Get-SecretValue 'android_keystore'
    if (-not $senha) { throw "senha do keystore ausente. Guarde com scripts/segredos_windows.ps1 -Command Set -Name android_keystore" }

    $zipalign = Get-BuildTool 'zipalign.exe'
    $apksigner = Get-BuildTool 'apksigner.bat'
    $alinhado = "$apkPath.aligned"
    # unsigned -> mesmo nome sem o sufixo; ja assinado -> .resigned
    $saida = if ($apkPath -like '*-unsigned.apk') {
        $apkPath -replace '-unsigned\.apk$', '.apk'
    } elseif ($apkPath -like '*.signed') {
        $apkPath -replace '\.signed$', '.resigned'
    } else {
        "$apkPath.signed"
    }

    # O Java do PATH pode ser o 8 ou o 25; o apksigner precisa de 17+.
    $jdk = Join-Path $env:TEMP 'opencode\jdk21-temurin\jdk'
    if (Test-Path (Join-Path $jdk 'bin\java.exe')) { $env:JAVA_HOME = $jdk }
    $env:Path = "$($env:JAVA_HOME)\bin;$env:Path"

    Write-Host "  alignando: $(Split-Path $apkPath -Leaf)"
    & $zipalign -p -f 4 $apkPath $alinhado
    if ($LASTEXITCODE -ne 0) { throw 'zipalign falhou' }

    Write-Host "  assinando: $(Split-Path $saida -Leaf)"
    & $apksigner sign --ks $keystore --ks-type PKCS12 --ks-key-alias xau-local-test `
        --ks-pass "pass:$senha" --key-pass "pass:$senha" `
        --v2-signing-enabled true --v3-signing-enabled true --out $saida $alinhado | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'apksigner falhou' }
    Remove-Item $alinhado -Force -ErrorAction SilentlyContinue

    Write-Host "  verificando..." -ForegroundColor DarkGray
    $verifica = & $apksigner verify --verbose --print-certs $saida 2>&1
    if ($LASTEXITCODE -ne 0) { throw "verificacao falhou: $verifica" }
    $verifica | Where-Object { $_ -match 'Verifies|scheme \(|certificate SHA-256' } |
        ForEach-Object { Write-Host "    $_" }

    return $saida
}

# --- execucao ----------------------------------------------------------------

$assinados = @()
try {
    if ($Plataforma -in @('windows', 'ambas')) { $assinados += Invoke-WindowsSigning }
    if ($Plataforma -in @('android', 'ambas')) { $assinados += Invoke-AndroidSigning }
} finally {
    Remove-Variable senha -ErrorAction SilentlyContinue
}

Write-Host "`n=== SHA-256 dos artefatos assinados ===" -ForegroundColor Cyan
foreach ($a in $assinados) {
    $h = (Get-FileHash -LiteralPath $a -Algorithm SHA256).Hash
    $mb = [math]::Round((Get-Item -LiteralPath $a).Length / 1MB, 2)
    Write-Host ("  {0,-46} {1,8:N2} MB  {2}" -f (Split-Path $a -Leaf), $mb, $h)
}

Write-Host "`nRecalcule o manifesto e rode o Defender antes de distribuir." -ForegroundColor Yellow
Write-Host "Certificado self-signed: nao remove SmartScreen e nao vale para Google Play." -ForegroundColor Yellow
