<#
.SYNOPSIS
    Coordena agentes de IA que trabalham ao mesmo tempo no XAU AI PRO.

.DESCRIPTION
    Dois agentes editando o MESMO working tree sobrescrevem o trabalho um do
    outro sem aviso: o git diff deixa de dizer quem mudou o que, e um build
    pode sair com codigo pela metade. Este script isola cada agente em um
    git worktree (diretorio proprio, mesmo repositorio) e centraliza a
    entrega, para que a unica branch compartilhada seja a de integracao.

    MODELO DE USO
    --------------
      1. O agente DONO fica no diretorio principal e usa -Acao Status para
         ver o que o outro mexeu.
      2. Cada agente TRABALHADOR ganha um worktree proprio e nunca edita o
         diretorio principal.
      3. Nenhum agente faz merge por conta propria: o dono decide a ordem e
         depois roda -Acao Integrar.

    SEGURANCA DE DISCO
    ------------------
    Cada worktree novo copia a arvore versionada. Antes de criar, o script
    checa espaco livre e AVISA, sem criar, se o minimo de -EspacoMinimoGB nao
    estiver disponivel.

    NADA DESTE SCRIPT TOCA MQL5. O commit e barrado se houver alteracao em
    MQL5/Experts, conforme AGENTS.md.

.EXAMPLE
    .\scripts\agentes.ps1 -Acao Prep

.EXAMPLE
    .\scripts\agentes.ps1 -Acao Criar -Agente robo

.EXAMPLE
    .\scripts\agentes.ps1 -Acao Status
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Prep', 'Criar', 'Status', 'Commitar', 'Integrar', 'Remover', 'Liberar')]
    [string]$Acao,
    [string]$Agente = '',
    [string]$Branch = '',
    [string]$Mensagem = '',
    # Branch que recebe os merges. develop e onde o projeto integra.
    [string]$Base = 'develop',
    [switch]$DryRun,
    [switch]$Force,
    [double]$EspacoMinimoGB = 2.0
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path

# --------------------------------------------------------------------------- helpers

function Write-Titulo {
    param([string]$Texto)
    Write-Host ''
    Write-Host "== $Texto" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Texto)
    Write-Host "  [ok]   $Texto" -ForegroundColor Green
}

function Write-Aviso {
    param([string]$Texto)
    Write-Host "  [!]    $Texto" -ForegroundColor Yellow
}

function Write-Erro {
    param([string]$Texto)
    Write-Host "  [ERRO] $Texto" -ForegroundColor Red
}

function Get-EspacoLivreGB {
    $letra = [System.IO.Path]::GetPathRoot($repoRoot).Substring(0, 1)
    $drive = Get-PSDrive -Name $letra -ErrorAction SilentlyContinue
    if ($null -eq $drive) { return 0.0 }
    return [math]::Round($drive.Free / 1GB, 2)
}

function Invoke-Git {
    param([string[]]$Argumentos)
    # stderr de executavel nativo vira excecao sob ErrorActionPreference=Stop
    # (PowerShell 5): nem 2>$null nem *> resolvem em chamada direta. O
    # Start-Process captura os dois streams em arquivos sem passar pelo merger,
    # e o codigo de saida do git decide o que e erro.
    $saida = [System.IO.Path]::GetTempFileName()
    $erro = [System.IO.Path]::GetTempFileName()
    try {
        $args = @('-C', $repoRoot) + $Argumentos
        $proc = Start-Process -FilePath 'git' -ArgumentList $args -NoNewWindow -Wait -PassThru `
            -RedirectStandardOutput $saida -RedirectStandardError $erro
        $linhas = @(Get-Content -LiteralPath $saida -ErrorAction SilentlyContinue)
        if ($proc.ExitCode -ne 0) {
            $motivo = (Get-Content -LiteralPath $erro -ErrorAction SilentlyContinue) -join ' | '
            throw "git $($Argumentos -join ' ') falhou (exit $($proc.ExitCode)): $motivo"
        }
    } finally {
        Remove-Item -LiteralPath $saida, $erro -Force -ErrorAction SilentlyContinue
    }
    return @($linhas | Where-Object { $_ -and $_ -notmatch 'could not open directory' })
}

function Get-Pendencias {
    param([string]$Caminho)
    # Ver Invoke-Git: stderr nativo vira excecao sob ErrorActionPreference=Stop.
    # Start-Process contorna o merger de streams. O aviso de .pytest_cache
    # (ACL restrita) e descartado; o cache esta no .gitignore e nunca entra em
    # --porcelain.
    $saida = [System.IO.Path]::GetTempFileName()
    $erro = [System.IO.Path]::GetTempFileName()
    try {
        $proc = Start-Process -FilePath 'git' -ArgumentList @('-C', $Caminho, 'status', '--porcelain') `
            -NoNewWindow -Wait -PassThru -RedirectStandardOutput $saida -RedirectStandardError $erro
        if ($proc.ExitCode -ne 0) { return @() }
        $linhas = @(Get-Content -LiteralPath $saida -ErrorAction SilentlyContinue)
    } finally {
        Remove-Item -LiteralPath $saida, $erro -Force -ErrorAction SilentlyContinue
    }
    return @($linhas | Where-Object { $_ -and $_ -notmatch 'pytest_cache' })
}

function Get-BranchAtual {
    return (Invoke-Git @('rev-parse', '--abbrev-ref', 'HEAD')).Trim()
}

function Get-Short {
    param([string]$Caminho)
    return (& git -C $Caminho rev-parse --short HEAD 2>$null).Trim()
}

function Resolve-Worktree {
    param([string]$Nome)
    $lista = Invoke-Git @('worktree', 'list', '--porcelain')
    $atual = $null
    foreach ($linha in $lista) {
        if ($linha -like 'worktree *') { $atual = $linha.Substring(9).Trim() }
        elseif ($linha -like 'branch refs/heads/*' -and $atual) {
            if ($linha.Substring(18).Trim() -eq $Nome) { return $atual }
        }
    }
    return $null
}

# --------------------------------------------------------------------------- acoes

switch ($Acao) {

    'Prep' {
        Write-Titulo 'Pre-requisitos'
        if (Get-Command git -ErrorAction SilentlyContinue) {
            Write-Ok "git: $((& git --version))"
        } else {
            Write-Erro 'git nao encontrado no PATH.'
        }

        Write-Titulo 'Disco'
        $livre = Get-EspacoLivreGB
        if ($livre -ge $EspacoMinimoGB) {
            Write-Ok "$livre GB livres (minimo desejado: $EspacoMinimoGB GB)"
        } else {
            Write-Aviso "$livre GB livres. Minimo recomendado: $EspacoMinimoGB GB."
            Write-Aviso 'Liberar com: powershell -File scripts\limpeza_segura.ps1 -BuildArtifacts -Apply'
        }

        Write-Titulo 'Repositorio'
        Write-Ok "Raiz:   $repoRoot"
        Write-Ok "Branch: $(Get-BranchAtual)"
        Write-Ok "Commit: $(Get-Short -Caminho $repoRoot)"

        $sujo = Get-Pendencias -Caminho $repoRoot
        if ($sujo.Count -gt 0) {
            Write-Aviso "$($sujo.Count) arquivo(s) modificado(s) sem commit no diretorio principal."
            $sujo | Select-Object -First 10 | ForEach-Object { Write-Host "        $_" }
        } else {
            Write-Ok 'Diretorio principal limpo.'
        }

        Write-Titulo 'Protecoes MQL5'
        # Pathspec explicito evita descer em .pytest_cache (ver Get-Pendencias).
        $saidaMql = [System.IO.Path]::GetTempFileName()
        $erroMql = [System.IO.Path]::GetTempFileName()
        try {
            $p = Start-Process -FilePath 'git' `
                -ArgumentList @('-C', $repoRoot, 'status', '--porcelain', '--', 'MQL5/Experts') `
                -NoNewWindow -Wait -PassThru -RedirectStandardOutput $saidaMql -RedirectStandardError $erroMql
            $mql5 = @(Get-Content -LiteralPath $saidaMql -ErrorAction SilentlyContinue |
                Where-Object { $_ -and $_ -notmatch 'could not open directory' })
        } finally {
            Remove-Item -LiteralPath $saidaMql, $erroMql -Force -ErrorAction SilentlyContinue
        }
        if ($mql5.Count -eq 0) {
            Write-Ok 'MQL5/Experts intocado.'
        } else {
            Write-Aviso "$($mql5.Count) arquivo(s) MQL5 alterado(s): viola AGENTS.md."
        }
    }

    'Criar' {
        if ([string]::IsNullOrWhiteSpace($Agente)) { throw 'Informe -Agente (ex: robo, ui, backend).' }
        if ([string]::IsNullOrWhiteSpace($Branch)) { $Branch = "agente/$Agente" }

        if ((Invoke-Git @('branch', '--list', $Branch)).Trim()) {
            throw "branch '$Branch' ja existe. Escolha outro nome ou remova antes."
        }

        $livre = Get-EspacoLivreGB
        if ($livre -lt $EspacoMinimoGB) {
            throw "Espaco insuficiente: $livre GB livres, minimo $EspacoMinimoGB GB. Libere espaco antes."
        }

        $destino = Join-Path (Split-Path -Parent $repoRoot) "XAU_AI_PRO_$Agente"
        if (Test-Path -LiteralPath $destino) { throw "Destino ja existe: $destino" }

        Write-Titulo "Criando worktree do agente '$Agente'"
        Write-Host "  Branch:  $Branch"
        Write-Host "  Destino: $destino"
        if ($DryRun) { Write-Aviso 'Dry-run: nada foi criado.'; break }

        Invoke-Git @('worktree', 'add', '-b', $Branch, $destino, $Base) | Out-Null
        Write-Ok 'Worktree criado. O agente deve trabalhar APENAS em:'
        Write-Host "        $destino"
        Write-Aviso 'node_modules e .venv NAO vem junto. Rodar setup no worktree antes de testar.'
    }

    'Status' {
        Write-Titulo 'Diretorio principal'
        Write-Ok "Branch: $(Get-BranchAtual)  commit $(Get-Short -Caminho $repoRoot)"
        $sujo = Get-Pendencias -Caminho $repoRoot
        if ($sujo.Count) {
            Write-Aviso "$($sujo.Count) arquivo(s) modificado(s):"
            $sujo | ForEach-Object { Write-Host "        $_" }
        } else {
            Write-Ok 'Limpo.'
        }

        Write-Titulo 'Worktrees'
        $caminhos = @(Invoke-Git @('worktree', 'list', '--porcelain') |
            Where-Object { $_ -like 'worktree *' } | ForEach-Object { $_.Substring(9).Trim() })

        foreach ($c in $caminhos) {
            $marca = ''
            if ($c -eq $repoRoot) { $marca = '   <-- principal' }
            Write-Host "  $c$marca"
        }
        if ($caminhos.Count -le 1) {
            Write-Aviso 'Nenhum worktree de agente. Criar com: -Acao Criar -Agente <nome>'
            break
        }

        foreach ($c in ($caminhos | Where-Object { $_ -ne $repoRoot })) {
            Write-Titulo "Agente em $(Split-Path -Leaf $c)"
            $branch = (& git -C $c rev-parse --abbrev-ref HEAD 2>$null)
            if ($branch) { Write-Ok "Branch: $($branch.Trim())" }
            $pend = Get-Pendencias -Caminho $c
            if ($pend.Count) {
                Write-Aviso "$($pend.Count) arquivo(s) modificado(s), NAO commitado ainda:"
                $pend | Select-Object -First 12 | ForEach-Object { Write-Host "        $_" }
            } else {
                Write-Ok 'Nada pendente.'
            }
            @(& git -C $c log --oneline -3 2>$null) | ForEach-Object { Write-Host "        $_" }
        }
    }


    'Commitar' {
        if ([string]::IsNullOrWhiteSpace($Agente)) { throw 'Informe -Agente.' }
        $caminho = Resolve-Worktree -Nome $Branch
        if (-not $caminho) { $caminho = Join-Path (Split-Path -Parent $repoRoot) "XAU_AI_PRO_$Agente" }
        if (-not (Test-Path -LiteralPath $caminho)) { throw "worktree do agente '$Agente' nao encontrado." }

        $mql5 = @(& git -C $caminho status --porcelain -- 'MQL5/Experts' 2>$null)
        if ($mql5.Count -gt 0) {
            throw "Agente '$Agente' alterou MQL5/Experts. Viola AGENTS.md; commit barrado."
        }

        $pend = Get-Pendencias -Caminho $caminho
        if ($pend.Count -eq 0) { Write-Ok 'Nada a commitar.'; break }
        if ([string]::IsNullOrWhiteSpace($Mensagem)) { throw 'Informe -Mensagem com a descricao do que mudou.' }

        Write-Titulo "Commit do agente '$Agente'"
        $pend | ForEach-Object { Write-Host "        $_" }
        if ($DryRun) { Write-Aviso 'Dry-run: nada commitado.'; break }

        & git -C $caminho add -A
        & git -C $caminho diff --cached --check
        & git -C $caminho commit -m $Mensagem | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'commit falhou.' }
        Write-Ok "Commit em ${Branch}: $(Get-Short -Caminho $caminho)"
        Write-Aviso "Ainda nao foi para $Base. Integrar com: -Acao Integrar -Agente $Agente -Branch $Branch"
    }

    'Integrar' {
        if ([string]::IsNullOrWhiteSpace($Agente)) { throw 'Informe -Agente.' }
        $caminho = Resolve-Worktree -Nome $Branch
        if (-not $caminho) { throw "worktree para a branch '$Branch' nao encontrado." }

        $atual = Get-BranchAtual
        if ($atual -ne $Base) { throw "Voce esta em '$atual'. Mude para '$Base' antes de integrar." }

        $pend = Get-Pendencias -Caminho $caminho
        if ($pend.Count -gt 0) { throw "Agente '$Agente' tem trabalho sem commit. Commitar antes." }

        Write-Titulo "Integrando '$Branch' em '$Base'"
        & git -C $repoRoot diff --check
        if ($DryRun) { Write-Aviso "Dry-run. Seria executado: git merge $Branch"; break }

        $saida = & git -C $repoRoot merge --no-ff -m "merge: $Branch ($Agente)" $Branch 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Erro "Conflito de merge. Resolver manualmente em: $repoRoot"
            $saida | ForEach-Object { Write-Host "        $_" }
            Write-Aviso 'git status | resolver | git add <arquivo> | git merge --continue'
            exit 1
        }
        Write-Ok "Merge concluido: $(Get-Short -Caminho $repoRoot)"
        Write-Aviso 'Rodar a suite do componente alterado antes do proximo build.'
    }

    'Remover' {
        if ([string]::IsNullOrWhiteSpace($Agente)) { throw 'Informe -Agente.' }
        $caminho = Resolve-Worktree -Nome $Branch
        if (-not $caminho) { throw "worktree para '$Branch' nao encontrado." }
        $pend = Get-Pendencias -Caminho $caminho
        if ($pend.Count -gt 0 -and -not $Force) {
            throw "Agente '$Agente' tem trabalho sem commit. Nao removido. Use -Force para descartar."
        }
        Write-Titulo "Removendo worktree de '$Agente'"
        Write-Host "  $caminho"
        if ($DryRun) { Write-Aviso 'Dry-run: nada removido.'; break }
        Invoke-Git @('worktree', 'remove', $caminho) | Out-Null
        Write-Ok 'Worktree removido. A branch foi mantida (git branch -d se nao for mais usada).'
    }

    'Liberar' {
        Write-Titulo 'Worktrees registrados'
        Invoke-Git @('worktree', 'list') | ForEach-Object { Write-Host "  $_" }
        Write-Aviso 'Para liberar espaco: powershell -File scripts\limpeza_segura.ps1 -BuildArtifacts -DebugCache -Apply'
    }
}

