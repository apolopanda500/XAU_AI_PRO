[CmdletBinding()]
param(
    [string]$Deadline = '2026-09-25T05:00:00-03:00',
    [switch]$DryRun,
    [switch]$CleanBuild,
    [switch]$Android,
    [switch]$LocalSign,
    [switch]$Install
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$Frontend = Join-Path $Root 'frontend'
$Tauri = Join-Path $Frontend 'src-tauri'
$Core = Join-Path $Root 'core'
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$LogDirectory = Join-Path $Root 'Logs'
$LogFile = Join-Path $LogDirectory ("overnight_session_{0}.log" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
$DeadlineUtc = ([DateTimeOffset]::Parse($Deadline)).ToUniversalTime()
$StartedUtc = [DateTimeOffset]::UtcNow

New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $line = '[{0}] [{1}] {2}' -f ([DateTimeOffset]::Now.ToString('yyyy-MM-dd HH:mm:ss zzz')), $Level, $Message
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Assert-Deadline {
    if ([DateTimeOffset]::UtcNow -ge $DeadlineUtc) {
        throw "DeadlineExceeded: $($DeadlineUtc.ToLocalTime().ToString('yyyy-MM-dd HH:mm:ss zzz'))"
    }
}

function Invoke-Native {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory = $Root
    )
    Assert-Deadline
    $display = @($FilePath) + $Arguments
    Write-Log ("EXEC {0}" -f ($display -join ' '))
    if ($DryRun) { return }
    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "CommandFailed($LASTEXITCODE): $FilePath"
        }
    } finally {
        Pop-Location
    }
}

function Invoke-PowerShellStep {
    param([string]$Name, [scriptblock]$Action)
    Assert-Deadline
    Write-Log ("STEP {0}" -f $Name)
    if ($DryRun) {
        Write-Log "DRY-RUN $Name"
        return
    }
    & $Action
    Write-Log ("OK {0}" -f $Name)
}

function Invoke-PyInstaller {
    param([string]$Spec)
    Invoke-Native -FilePath $Python -Arguments @('-m', 'PyInstaller', '--noconfirm', $Spec)
}

function Sync-Bridge {
    if ($DryRun) {
        Write-Log 'DRY-RUN Sync bridge'
        return
    }
    $source = Join-Path $Root 'dist\mt5-gateway'
    $destination = Join-Path $Tauri 'bridge'
    if (-not (Test-Path -LiteralPath $source -PathType Container)) {
        throw "Gateway bundle ausente: $source"
    }
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    & robocopy.exe $source $destination /MIR /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -ge 8) { throw "Robocopy falhou: $LASTEXITCODE" }
    $sourceHash = (Get-FileHash -LiteralPath (Join-Path $source 'mt5-gateway.exe') -Algorithm SHA256).Hash
    $destinationHash = (Get-FileHash -LiteralPath (Join-Path $destination 'mt5-gateway.exe') -Algorithm SHA256).Hash
    if ($sourceHash -ne $destinationHash) { throw 'Bridge sem integridade' }
    Write-Log "Bridge SHA256 $destinationHash"
}

function Sync-Core {
    if ($DryRun) { Write-Log 'DRY-RUN Sync core'; return }
    $source = Join-Path $Core 'target\release\xau-ai-pro-core.exe'
    $destinationDirectory = Join-Path $Tauri 'core'
    $destination = Join-Path $destinationDirectory 'xau-ai-pro-core.exe'
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Core release ausente: $source" }
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
    $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
    $destinationHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
    if ($sourceHash -ne $destinationHash) { throw 'Core sem integridade' }
    Write-Log "Core SHA256 $destinationHash"
}

function Find-SignTool {
    $candidate = Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\bin' -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
        Sort-Object FullName -Descending |
        Select-Object -First 1
    if (-not $candidate) { throw 'signtool.exe não encontrado' }
    return $candidate.FullName
}

function Invoke-LocalSigning {
    param([switch]$PostBundle)
    if ($DryRun) { Write-Log "DRY-RUN Assinatura local postBundle=$PostBundle"; return }
    $subject = 'CN=XAU AI PRO Local Development'
    $certificate = Get-ChildItem 'Cert:\CurrentUser\My' |
        Where-Object { $_.Subject -eq $subject -and $_.HasPrivateKey -and $_.NotAfter -gt (Get-Date).AddDays(30) } |
        Sort-Object NotAfter -Descending |
        Select-Object -First 1
    if (-not $certificate) {
        $certificate = New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject -CertStoreLocation 'Cert:\CurrentUser\My' -KeyExportPolicy NonExportable -KeyUsage DigitalSignature
    }
    $signtool = Find-SignTool
    $targets = if ($PostBundle) {
        @(
            (Join-Path $Tauri 'target\release\XAU AI PRO.exe'),
            (Join-Path $Tauri 'target\release\bundle\msi\XAU AI PRO_1.2.3_x64_en-US.msi'),
            (Join-Path $Tauri 'target\release\bundle\nsis\XAU AI PRO_1.2.3_x64-setup.exe'),
            (Join-Path $Root 'dist\XAU_AI_PRO_Setup_1.2.3.exe')
        )
    } else {
        @(
            (Join-Path $Root 'dist\XAU_AI_PRO\XAU_AI_PRO.exe'),
            (Join-Path $Root 'dist\mt5-gateway\mt5-gateway.exe'),
            (Join-Path $Tauri 'bridge\mt5-gateway.exe'),
            (Join-Path $Root 'core\target\release\xau-ai-pro-core.exe'),
            (Join-Path $Tauri 'core\xau-ai-pro-core.exe')
        )
    }
    foreach ($target in $targets) {
        if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "Artefato de assinatura ausente: $target" }
        Invoke-Native -FilePath $signtool -Arguments @('sign', '/fd', 'SHA256', '/tr', 'http://timestamp.digicert.com', '/td', 'SHA256', '/sha1', $certificate.Thumbprint, $target)
        $status = (Get-AuthenticodeSignature -LiteralPath $target).Status
        Write-Log "SIGNED $([System.IO.Path]::GetFileName($target)) status=$status thumbprint=$($certificate.Thumbprint)"
    }
}

function Install-And-Launch {
    if ($DryRun) { Write-Log 'DRY-RUN Instalação e atalho'; return }
    $setup = Join-Path $Tauri 'target\release\bundle\nsis\XAU AI PRO_1.2.3_x64-setup.exe'
    if (-not (Test-Path -LiteralPath $setup -PathType Leaf)) { throw "NSIS ausente: $setup" }
    $process = Start-Process -FilePath $setup -ArgumentList '/S' -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "NSIS falhou: $($process.ExitCode)" }
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'XAU AI PRO\XAU AI PRO.exe'),
        (Join-Path $env:LOCALAPPDATA 'com.xau-ai-pro.desktop\XAU AI PRO.exe'),
        (Join-Path $env:ProgramFiles 'XAU AI PRO\XAU AI PRO.exe')
    )
    $installed = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if (-not $installed) { throw 'Executável instalado não encontrado' }
    $desktop = [Environment]::GetFolderPath('Desktop')
    $shortcutPath = Join-Path $desktop 'XAU AI PRO.lnk'
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $installed
    $shortcut.WorkingDirectory = Split-Path -Parent $installed
    $shortcut.IconLocation = "$installed,0"
    $shortcut.Description = 'XAU AI PRO'
    $shortcut.Save()
    $launched = Start-Process -FilePath $shortcutPath -PassThru
    Start-Sleep -Seconds 20
    foreach ($port in 9001, 9002, 9003) {
        if (-not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) {
            throw "Porta $port não iniciou pelo atalho"
        }
    }
    Write-Log "INSTALLED $installed"
    Write-Log "SHORTCUT $shortcutPath"
    $null = $launched.CloseMainWindow()
    if (-not $launched.WaitForExit(15000)) { Stop-Process -Id $launched.Id -Force }
}

function Write-ArtifactManifest {
    if ($DryRun) { Write-Log 'DRY-RUN Manifesto de artefatos'; return }
    $artifacts = @(
        (Join-Path $Root 'dist\XAU_AI_PRO\XAU_AI_PRO.exe'),
        (Join-Path $Root 'dist\XAU_AI_PRO_Setup_1.2.3.exe'),
        (Join-Path $Root 'dist\mt5-gateway\mt5-gateway.exe'),
        (Join-Path $Root 'core\target\release\xau-ai-pro-core.exe'),
        (Join-Path $Tauri 'target\release\XAU AI PRO.exe'),
        (Join-Path $Tauri 'target\release\bundle\msi\XAU AI PRO_1.2.3_x64_en-US.msi'),
        (Join-Path $Tauri 'target\release\bundle\nsis\XAU AI PRO_1.2.3_x64-setup.exe')
    )
    $records = foreach ($artifact in $artifacts) {
        if (-not (Test-Path -LiteralPath $artifact -PathType Leaf)) { throw "Artefato final ausente: $artifact" }
        $file = Get-Item -LiteralPath $artifact
        $signature = Get-AuthenticodeSignature -LiteralPath $artifact
        [pscustomobject]@{
            path = $artifact
            bytes = $file.Length
            sha256 = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash
            signature_status = [string]$signature.Status
            signature_subject = if ($signature.SignerCertificate) { $signature.SignerCertificate.Subject } else { $null }
        }
    }
    $manifest = Join-Path $Root 'release-manifest.json'
    [IO.File]::WriteAllText($manifest, ($records | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))
    Write-Log "MANIFEST $manifest"
}

function Invoke-DefenderScan {
    if ($DryRun) { Write-Log 'DRY-RUN Defender'; return }
    foreach ($path in @((Join-Path $Root 'dist'), (Join-Path $Tauri 'target\release'))) {
        try {
            Start-MpScan -ScanType CustomScan -ScanPath $path
            Write-Log "DEFENDER $path"
        } catch {
            Write-Log "DEFENDER_FAILED $path $($_.Exception.Message)"
        }
    }
}

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class SessionPowerState {
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint flags);
}
'@

$previousState = [SessionPowerState]::SetThreadExecutionState([uint32]2147483648)
$env:XAU_MCP_TRADING = '0'
$env:XAU_ENABLE_REAL_ORDERS = '0'
$env:XAU_ENABLE_EMERGENCY_RESUME = '0'
$env:XAU_THIRD_PARTY_EA_READ_ONLY = '0'

try {
    Write-Log "INICIO root=$Root deadline=$($DeadlineUtc.ToLocalTime().ToString('yyyy-MM-dd HH:mm:ss zzz')) dryRun=$DryRun"
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw "Python ausente: $Python" }

    Invoke-PowerShellStep 'Estado Git' {
        & git status --short
        & git diff --check
        if ($LASTEXITCODE -ne 0) { throw 'git diff --check falhou' }
    }

    if ($CleanBuild) {
        Invoke-PowerShellStep 'Limpeza scoped' {
            & (Join-Path $Root 'scripts\limpeza_segura.ps1') -Apply -BuildArtifacts -Root $Root
        }
    }

    Invoke-Native -FilePath $Python -Arguments @('scripts/sync_version.py', '--check')
    Invoke-Native -FilePath $Python -Arguments @('-m', 'pytest', '-q', 'tests', '-p', 'no:cacheprovider')
    Invoke-Native -FilePath $Python -Arguments @('-m', 'pylint', 'backend/fastapi_gateway.py', 'backend/mt5_gateway.py', 'backend/risk_gate.py', 'backend/connection_store.py', 'backend/universal_contracts.py', 'backend/universal_router.py', 'backend/binance_client.py', 'backend/mexc_client.py', 'backend/bybit_client.py', 'backend/okx_client.py', 'backend/mexc_execution.py')
    Invoke-Native -FilePath 'npm.cmd' -Arguments @('test', '--', '--reporter=dot') -WorkingDirectory $Frontend
    Invoke-Native -FilePath 'npm.cmd' -Arguments @('run', 'typecheck') -WorkingDirectory $Frontend
    Invoke-Native -FilePath 'npm.cmd' -Arguments @('run', 'build') -WorkingDirectory $Frontend
    Invoke-Native -FilePath 'npm.cmd' -Arguments @('run', 'lint') -WorkingDirectory (Join-Path $Root 'backend')
    Invoke-Native -FilePath 'npm.cmd' -Arguments @('run', 'build') -WorkingDirectory (Join-Path $Root 'backend')
    Invoke-Native -FilePath 'cargo.exe' -Arguments @('fmt', '--all', '--', '--check') -WorkingDirectory $Core
    Invoke-Native -FilePath 'cargo.exe' -Arguments @('check', '--locked') -WorkingDirectory $Core
    Invoke-Native -FilePath 'cargo.exe' -Arguments @('test', '--locked') -WorkingDirectory $Core
    Invoke-Native -FilePath 'cargo.exe' -Arguments @('build', '--release', '--locked') -WorkingDirectory $Core
    Sync-Core
    Invoke-PyInstaller 'mt5-gateway.spec'
    Sync-Bridge
    Invoke-PyInstaller 'launcher.spec'
    Invoke-Native -FilePath 'npm.cmd' -Arguments @('run', 'tauri:build') -WorkingDirectory $Frontend
    $iscc = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
    Invoke-Native -FilePath $iscc -Arguments @("/DMyRoot=$Root", (Join-Path $Root 'installer\installer.iss'), '/Qp')

    if ($Android) {
        $javaHome = 'C:\Program Files\Android\Android Studio\jbr'
        if (Test-Path -LiteralPath (Join-Path $javaHome 'bin\java.exe') -PathType Leaf) {
            $env:JAVA_HOME = $javaHome
            $env:ANDROID_HOME = 'C:\Users\Micro\AppData\Local\Android\Sdk'
            $env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
            Invoke-Native -FilePath 'npm.cmd' -Arguments @('run', 'tauri', '--', 'android', 'init', '--ci') -WorkingDirectory $Frontend
            Invoke-Native -FilePath 'npm.cmd' -Arguments @('run', 'tauri', '--', 'android', 'build', '--ci', '--apk', '--aab') -WorkingDirectory $Frontend
        } else {
            Write-Log 'ANDROID_SKIPPED JDK Android Studio não encontrado' 'WARN'
        }
    }

    if ($LocalSign) { Invoke-LocalSigning }
    if ($Install) { Install-And-Launch }
    if ($LocalSign) { Invoke-LocalSigning -PostBundle }
    Write-ArtifactManifest
    Invoke-DefenderScan
    Invoke-PowerShellStep 'Git status final' {
        & git status --short
        & git diff --check
        if ($LASTEXITCODE -ne 0) { throw 'git diff --check final falhou' }
    }

    $status = [ordered]@{
        ok = $true
        started_at = $StartedUtc.ToString('o')
        finished_at = [DateTime]::UtcNow.ToString('o')
        deadline = $DeadlineUtc.ToString('o')
        real_trading_enabled = $false
        root = $Root
    }
    $status | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $LogDirectory 'overnight_session_result.json') -Encoding UTF8
    Write-Log 'SUCESSO ciclo noturno concluído'
    exit 0
} catch {
    $status = [ordered]@{
        ok = $false
        started_at = $StartedUtc.ToString('o')
        failed_at = [DateTime]::UtcNow.ToString('o')
        deadline = $DeadlineUtc.ToString('o')
        real_trading_enabled = $false
        error = $_.Exception.Message
        log = $LogFile
    }
    $status | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $LogDirectory 'overnight_session_result.json') -Encoding UTF8
    Write-Log $_.Exception.Message 'ERROR'
    exit 1
} finally {
    [void][SessionPowerState]::SetThreadExecutionState($previousState)
}
