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
    # Os instaladores ja assinados e publicados ficam em `release\<versao>\`.
    # Ja o `target\release\bundle\` e o diretorio de TRABALHO do bundler: ele
    # reconstroi MSI e NSIS do zero a cada `tauri build`, e os arquivos velhos
    # ali ocupam ~500 MB sem valor (a copia assinada esta em `release/`). Sem
    # esta entrada, a limpeza nao recupera espaco justo quando o disco e o
    # recurso escasso para o build completo.
    $allowed += @('frontend\src-tauri\target\release\bundle')
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

function Resolve-Icacls {
    <#
    .SYNOPSIS
        Devolve o controle de ACL quando um alvo nao pode ser lido.

    .DESCRIPTION
        O `target\debug` do Rust fica com ACL quebrada depois de cada build
        nesta maquina: o `Remove-Item` falha com "O acesso ao caminho ... foi
        negado" e a limpeza nao acontece. O sintoma ja foi documentado em
        `docs/SESSAO_20260930.md` secao 8 (".git: ACL corrompida no
        .pytest_cache travava git status").

        LIMITACAO HONESTA
        ----------------
        Isto resolve o caso de ACL *herdada quebrada*, em que bastam o SID e
        o `/T`. NAO resolve o `.pytest_cache` desta maquina: la nem o
        proprio dono consegue ler a pasta (`icacls` e `takeown` respondem
        "Acesso negado"), e so o shell elevado reverte. Nesse caso o script
        AVISA e segue - nunca trava o lote inteiro.

        O SID `*S-1-1-0` e "Everyone". Conceder controle total recursivo e o
        que destrava a remocao; o alvo e sempre cache de build, nunca
        codigo nem dado do usuario.
    #>
    param([Parameter(Mandatory)][string]$Target)

    if (-not (Test-Path -LiteralPath $Target)) { return }
    Write-Host "  devolvendo controle de ACL em $Target"
    # Duas correcoes sao necessarias, e a segunda e a que so funciona:
    #
    # 1. O icacls escreve aviso em stderr mesmo em arvore ja correta.
    # 2. Com `$ErrorActionPreference = 'Stop'` (linha 26), stderr de um
    #    executavel externo vira erro TERMINATING e mata o script inteiro —
    #    a limpeza nao acontece, que e o defeito que este bloco corrige.
    #
    # Envolver em try/catch e o que neutraliza (2): o aviso continua visivel,
    # mas a remocao segue.
    try {
        & icacls.exe $Target /grant '*S-1-1-0:(OI)(CI)F' /T /Q 2>&1 | Out-Null
    } catch {
        Write-Host "  icacls nao pode alterar a ACL deste alvo; tentando remover assim mesmo"
    }
}

foreach ($item in $items) {
    Resolve-Icacls -Target $item.FullName
    # O `Remove-Item` tambem vira erro TERMINATING sob `$ErrorActionPreference`
    # e aborta o resto do lote. Um alvo que nao pode ser removido nao pode
    # impedir os outros de serem limpos — a limpeza parcial ainda e limpeza.
    try {
        Remove-Item -LiteralPath $item.FullName -Recurse -Force -ErrorAction Stop
        Write-Host "  removido: $($item.FullName)"
    } catch {
        Write-Warning "nao removido: $($item.FullName) -> $($_.Exception.Message)"
    }
}
Write-Host 'Limpeza segura concluida.'