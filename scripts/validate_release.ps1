[CmdletBinding()]
param(
    [switch]$SkipPython,
    [switch]$SkipCargo
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root 'frontend'
$Tauri = Join-Path $Frontend 'src-tauri'
$Failures = [System.Collections.Generic.List[string]]::new()

function Invoke-ReleaseCheck {
    param(
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [scriptblock]$Command
    )

    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    try {
        & $Command
        if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) {
            throw "Comando finalizou com código $LASTEXITCODE."
        }
        Write-Host "OK: $Name" -ForegroundColor Green
    } catch {
        $Failures.Add("${Name}: $($_.Exception.Message)")
        Write-Host "FALHOU: $Name" -ForegroundColor Red
    }
}

function Assert-Path {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Description
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Description não encontrado: $Path"
    }
}

Write-Host 'XAU AI PRO - Validação de release não destrutiva' -ForegroundColor White
Write-Host "Raiz: $Root"
Write-Host 'Este script não gera instaladores, não instala dependências e não altera o Git.' -ForegroundColor DarkGray

Invoke-ReleaseCheck -Name 'Pré-requisitos do repositório' -Command {
    Assert-Path -Path (Join-Path $Frontend 'package.json') -Description 'frontend/package.json'
    Assert-Path -Path (Join-Path $Tauri 'Cargo.toml') -Description 'frontend/src-tauri/Cargo.toml'
    Assert-Path -Path (Join-Path $Root 'tests/test_universal_account.py') -Description 'Teste de conta universal'
    Assert-Path -Path (Join-Path $Tauri 'core/xau-ai-pro-core.exe') -Description 'Recurso core do Tauri'
    Assert-Path -Path (Join-Path $Tauri 'bridge') -Description 'Diretório bridge do Tauri'
}

if (-not $SkipPython) {
    $ProjectPython = Join-Path $Root '.venv/Scripts/python.exe'
    if (Test-Path -LiteralPath $ProjectPython) {
        Invoke-ReleaseCheck -Name 'Testes Python direcionados' -Command {
            Push-Location $Root
            try { & $ProjectPython -m pytest tests/test_universal_account.py -q } finally { Pop-Location }
        }
    } else {
        $Failures.Add("Testes Python direcionados: Python do projeto não encontrado em $ProjectPython. Crie/recupere .venv antes da release.")
        Write-Host "FALHOU: Testes Python direcionados (Python do projeto ausente)" -ForegroundColor Red
    }
} else {
    Write-Host "`nIGNORADO: Testes Python direcionados (-SkipPython)" -ForegroundColor Yellow
}

Invoke-ReleaseCheck -Name 'Testes frontend (Vitest)' -Command {
    Push-Location $Frontend
    try { npm test } finally { Pop-Location }
}

Invoke-ReleaseCheck -Name 'Checagem TypeScript' -Command {
    Push-Location $Frontend
    try { npx tsc --noEmit } finally { Pop-Location }
}

Invoke-ReleaseCheck -Name 'Build frontend (Vite)' -Command {
    Push-Location $Frontend
    try { npm run build } finally { Pop-Location }
}

if (-not $SkipCargo) {
    Invoke-ReleaseCheck -Name 'Checagem Rust/Tauri' -Command {
        Push-Location $Tauri
        try { cargo check } finally { Pop-Location }
    }
} else {
    Write-Host "`nIGNORADO: Checagem Rust/Tauri (-SkipCargo)" -ForegroundColor Yellow
}

Invoke-ReleaseCheck -Name 'Configuração de bundle Windows' -Command {
    $Config = Get-Content -LiteralPath (Join-Path $Tauri 'tauri.conf.json') -Raw | ConvertFrom-Json
    $Targets = @($Config.bundle.targets)
    if ($Targets -notcontains 'msi' -or $Targets -notcontains 'nsis') {
        throw 'A configuração Tauri deve incluir os targets msi e nsis.'
    }
    if (-not $Config.bundle.active) {
        throw 'O bundle Tauri está desativado.'
    }
}

Invoke-ReleaseCheck -Name 'Pre-flight de ambiente' -Command {
    # Falha cedo e com mensagem clara: disco, ferramentas, guarda de MQL5 e
    # scripts bloqueados. Sem isso os problemas so apareciam no meio de um build
    # de 15 minutos, quando ja custou caro.
    Assert-Path -Path (Join-Path $Root '.venv/Scripts/python.exe') -Description 'Python do projeto'
    Push-Location $Root
    try {
        & (Join-Path $Root '.venv/Scripts/python.exe') (Join-Path $Root 'scripts/preflight.py') --etapa longa
        if ($LASTEXITCODE -ne 0) { throw 'O pre-flight de ambiente reprovou; a release esta bloqueada.' }
    } finally { Pop-Location }
}

Invoke-ReleaseCheck -Name 'Nenhum script perigoso reintroduzido' -Command {
    # Bloqueados em 2026-09-26. Motivos:
    #   - cmd.exe na raiz: binario solto que sombreia o cmd.exe do sistema para
    #     qualquer processo com esta pasta como diretorio de trabalho (ja foi
    #     executado pelo MoNotificationUx.exe do Office) e e magnet de heuristica
    #     de antivirus, conforme o relatorio de seguranca;
    #   - XAU_AI_PRO_START.vbs: inicializador silencioso com entrada de
    #     autoexecucao, padrao classificado como comportamento de PUP;
    #   - overnight_session.ps1 / ciclo_limpo_123.py: automacao permanente de
    #     build, assinatura, instalacao e limpeza, sem revisao de staging;
    #   - pos_reboot_docker.ps1 / post_docker_cli_setup.ps1: execucao no boot e
    #     instalador silencioso;
    #   - setup/connect_sandbox_claude: setup de sandbox de terceiros, sem
    #     qualquer relacao com o produto;
    #   - install_docker* / vercel_vcr_setup / setup-vercel: instaladores que
    #     baixam e executam binarios em silencio.
    $Proibidos = @(
        'cmd.exe', 'XAU_AI_PRO_START.vbs',
        'scripts/overnight_session.ps1', 'scripts/ciclo_limpo_123.py',
        'Tools/pos_reboot_docker.ps1', 'Tools/post_docker_cli_setup.ps1',
        'Tools/connect_sandbox_claude.ps1', 'Tools/setup_sandbox_claude.ps1',
        'Tools/vercel_vcr_setup.ps1', 'Tools/install_docker.bat',
        'Tools/install_docker_windows.ps1', 'setup-vercel.bat'
    )
    $Encontrados = @($Proibidos | Where-Object { Test-Path -LiteralPath (Join-Path $Root $_) })
    if ($Encontrados.Count -gt 0) {
        throw "scripts perigosos presentes no repositorio: $($Encontrados -join ', ')"
    }
    # Nenhum binario solto na raiz: sombreamento de caminho e magnet de AV.
    $Binarios = @(Get-ChildItem -LiteralPath $Root -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -match '^\.(exe|dll|vbs|scr|sys)$' })
    if ($Binarios.Count -gt 0) {
        throw "binarios na raiz do repositorio: $(($Binarios | ForEach-Object { $_.Name }) -join ', ')"
    }
}

Invoke-ReleaseCheck -Name 'Integridade da diff Git' -Command {
    Push-Location $Root
    try { git diff --check } finally { Pop-Location }
}

if ($Failures.Count -gt 0) {
    Write-Host "`nValidação de release BLOQUEADA ($($Failures.Count) falha(s)):" -ForegroundColor Red
    $Failures | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    exit 1
}

Write-Host "`nValidação de release aprovada." -ForegroundColor Green
exit 0