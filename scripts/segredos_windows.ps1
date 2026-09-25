<#
.SYNOPSIS
    Guarda e recupera segredos de build (keystore Android, certificado de
    assinatura Windows) com cifragem DPAPI nativa do Windows.

.DESCRIPTION
    Substitui o armazenamento em texto plano / em pasta temporaria.

    Cada senha e gravada em arquivo cifrado com DPAPI (Data Protection API),
    usando a chave da conta do Windows do usuario. Consequencias:

      - So a mesma conta, na mesma maquina, consegue decifrar.
      - Arquivo vazado para outro usuario ou outra maquina e ilegivel.
      - A senha NAO aparece em log, no console, no historico do Git ou no
        manifesto de release.

    O arquivo do keystore (.p12/.jks) e mantido em disco, mas em pasta com
    ACL restrita ao usuario e ao SYSTEM/Administradores. A protecao real do
    arquivo vem da combinacao ACL + senha guardada no DPAPI.

    AVISO: a senha nao e recuperavel. Se for perdida, o keystore precisa ser
    gerado de novo (e, para Android, isso quebra a continuidade de atualizacao
    do app publicado). Faca backup da senha em um gerenciador de senhas.

.PARAMETER Command
    acao a executar.

.EXAMPLE
    .\scripts\segredos_windows.ps1 -Command Initialize
    Move os segredos do Temp para a pasta protegida e cifra as senhas.

.EXAMPLE
    .\scripts\segredos_windows.ps1 -Command Status
    Lista os segredos guardados sem revelar nenhum valor.

.EXAMPLE
    .\scripts\segredos_windows.ps1 -Command Get -Name android_keystore
    Devolve a senha como SecureString, para uso em outro script.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('Initialize', 'Status', 'Set', 'Get', 'Remove')]
    [string]$Command,

    [string]$Name = '',
    [SecureString]$Secure = $null
)

$ErrorActionPreference = 'Stop'

# LocalAppData e nao Temp: sobrevive a limpeza de %TEMP% e a esta fora do repo.
$SecretsRoot = Join-Path $env:LOCALAPPDATA 'XAU_AI_PRO\secrets'
$UserSid = ([System.Security.Principal.WindowsIdentity]::GetCurrent()).User.Value

function Get-SecretsRoot {
    if (-not (Test-Path -LiteralPath $SecretsRoot)) {
        New-Item -ItemType Directory -Path $SecretsRoot -Force | Out-Null
    }
    # ACL: apenas o usuario atual, SYSTEM e Administradores. Remove heranca.
    $acl = Get-Acl -LiteralPath $SecretsRoot
    $acl.SetAccessRuleProtection($true, $false)
    $inherit = [System.Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit'
    $propagation = [System.Security.AccessControl.PropagationFlags]::None
    $allow = [System.Security.AccessControl.AccessControlType]::Allow
    $full = [System.Security.AccessControl.FileSystemRights]::FullControl
    foreach ($sidText in @($UserSid, 'S-1-5-18', 'S-1-5-32-544')) {
        $sid = New-Object System.Security.Principal.SecurityIdentifier($sidText)
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $sid, $full, $inherit, $propagation, $allow)
        $acl.SetAccessRule($rule)
    }
    Set-Acl -LiteralPath $SecretsRoot -AclObject $acl
    return $SecretsRoot
}

function Get-SecretFile([string]$Key) {
    return (Join-Path (Get-SecretsRoot) "$Key.dpapi")
}

function Set-Secret {
    param([string]$Key, [SecureString]$Value)
    if ($null -eq $Value) { throw 'SecureString obrigatorio.' }
    # ConvertFrom-SecureString sem -Key usa DPAPI com a conta do Windows.
    $cipher = ConvertFrom-SecureString -SecureString $Value
    [System.IO.File]::WriteAllText((Get-SecretFile $Key), $cipher)
    Write-Host "segredo guardado: $Key (cifrado com DPAPI)" -ForegroundColor Green
}

function Get-Secret {
    param([string]$Key)
    $file = Get-SecretFile $Key
    if (-not (Test-Path -LiteralPath $file)) { return $null }
    $cipher = [System.IO.File]::ReadAllText($file)
    return (ConvertTo-SecureString -String $cipher)
}

switch ($Command) {
    'Initialize' {
        $root = Get-SecretsRoot
        Write-Host "Pasta protegida: $root" -ForegroundColor Cyan

        # 1) keystore Android que estava no Temp
        $tmpKs = Join-Path $env:TEMP 'opencode\keystore\xau-local-test.p12'
        $tmpCreds = Join-Path $env:TEMP 'opencode\keystore\creds.txt'
        if (Test-Path -LiteralPath $tmpKs) {
            $dest = Join-Path $root 'xau-local-test.p12'
            Move-Item -LiteralPath $tmpKs -Destination $dest -Force
            Write-Host "keystore movido para: $dest" -ForegroundColor Green
        }
        if (Test-Path -LiteralPath $tmpCreds) {
            $line = (Select-String -LiteralPath $tmpCreds -Pattern '^storepass=').Line
            if ($line) {
                $pw = $line -replace '^storepass=', ''
                $sec = ConvertTo-SecureString -String $pw -AsPlainText -Force
                Set-Secret -Key 'android_keystore' -Value $sec
                $pw = $null
            }
            Remove-Item -LiteralPath $tmpCreds -Force
            Write-Host 'creds.txt (senha em texto plano) removido do Temp' -ForegroundColor Green
        }

        # 2) thumbprint do certificado Authenticode (nao e segredo, mas sai do Temp)
        $tmpThumb = Join-Path $env:TEMP 'opencode\signing_thumbprint.txt'
        if (Test-Path -LiteralPath $tmpThumb) {
            $thumb = (Get-Content -LiteralPath $tmpThumb -Raw).Trim()
            [System.IO.File]::WriteAllText((Join-Path $root 'authenticode_thumbprint.txt'), $thumb)
            Remove-Item -LiteralPath $tmpThumb -Force
            Write-Host "thumbprint guardado em: $(Join-Path $root 'authenticode_thumbprint.txt')" -ForegroundColor Green
        }

        Write-Host ''
        Write-Host 'RECADO: guarde a senha do keystore em um gerenciador de senhas.' -ForegroundColor Yellow
        Write-Host 'DPAPI impede vazamento, mas nao recupera senha perdida.' -ForegroundColor Yellow
    }

    'Status' {
        $root = Get-SecretsRoot
        Write-Host "Pasta: $root" -ForegroundColor Cyan
        $files = Get-ChildItem -LiteralPath $root -File -ErrorAction SilentlyContinue
        if (-not $files) { Write-Host 'nenhum segredo guardado' -ForegroundColor Yellow; break }
        foreach ($f in $files) {
            $state = if ($f.Extension -eq '.dpapi') { 'cifrado (DPAPI)' } else { 'texto claro' }
            Write-Host ("  {0,-34} {1,8:N0} bytes  {2}" -f $f.Name, $f.Length, $state)
        }
    }

    'Set' {
        if (-not $Name) { throw 'Informe -Name.' }
        if ($null -eq $Secure) { throw 'Informe -SecureString.' }
        Set-Secret -Key $Name -Value $Secure
    }

    'Get' {
        if (-not $Name) { throw 'Informe -Name.' }
        $sec = Get-Secret -Key $Name
        if ($null -eq $sec) { Write-Error "segredo '$Name' nao encontrado"; exit 1 }
        return $sec
    }

    'Remove' {
        if (-not $Name) { throw 'Informe -Name.' }
        $file = Get-SecretFile $Name
        if (Test-Path -LiteralPath $file) {
            Remove-Item -LiteralPath $file -Force
            Write-Host "segredo removido: $Name" -ForegroundColor Green
        } else { Write-Error "segredo '$Name' nao encontrado" }
    }
}
