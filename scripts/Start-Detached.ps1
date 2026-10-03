<#
.SYNOPSIS
    Inicia um processo de forma DESTACADA da sessao que o chamou.

.DESCRIPTION
    Start-Process, no Windows, cria o filho dentro do mesmo job object do
    processo que o chamou. Quando a sessao do PowerShell termina, o Windows
    mata o job inteiro e o filho morre junto.

    Isso foi observado nesta maquina de forma repetida: o gateway subia e
    respondia 200, e segundos depois nao existia mais e a porta 9001 estava
    livre; o emulador Android bootava, aparecia no `adb devices` e sumia. Nao
    era travamento: era o job object encerrando os filhos.

    Win32_Process.Create cria o processo fora do job da sessao atual, que e o
    que precisamos para o gateway e o emulador sobreviverem a sessao.

.EXAMPLE
    .\scripts\Start-Detached.ps1 -FilePath ".\.venv\Scripts\python.exe" `
        -ArgumentList '-m','backend.mt5_gateway' -LogFile "$env:TEMP\gw.log"

.EXAMPLE
    .\scripts\Start-Detached.ps1 -FilePath "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" `
        -ArgumentList '-avd','xau_test','-no-snapshot' -WaitPort 5554
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$FilePath,
    [string[]]$ArgumentList = @(),
    # Linha de comando completa, sem aspas do chamador. Use quando o argumento
    # tem virgula ou aspas: com `powershell -File`, um array vira um unico
    # elemento e as aspas sao engolidas pelo proprio PowerShell.
    [string]$CommandLine = '',
    [string]$WorkingDirectory = '',
    [string]$LogFile = '',
    # Depois de iniciar, espera o processo responder nesta porta TCP.
    [int]$WaitPort = 0,
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $FilePath)) {
    throw "executavel nao encontrado: $FilePath"
}

# O WMI resolve caminho relativo contra o diretorio do proprio servico, nao
# contra o do chamador: com caminho relativo, Create devolve 9 (PATH_NOT_FOUND).
$FilePath = (Resolve-Path -LiteralPath $FilePath).Path
if ($WorkingDirectory) {
    $WorkingDirectory = (Resolve-Path -LiteralPath $WorkingDirectory -ErrorAction SilentlyContinue).Path
}

# Linha de comando: o Executavel precisa vir entre aspas quando tem espaco.
$executavel = '"' + $FilePath + '"'
if ($CommandLine) {
    $argumentos = $CommandLine
} else {
    $argumentos = ($ArgumentList | ForEach-Object { '"' + $_ + '"' }) -join ' '
}
$comando = if ($argumentos) { "$executavel $argumentos" } else { $executavel }

# O log e anexado via cmd para que a saida do filho nao seja perdida quando a
# sessao que o-starteduvira.
if ($LogFile) {
    $dir = Split-Path -Parent $LogFile
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    Remove-Item $LogFile -Force -ErrorAction SilentlyContinue
    $comando = "$comando >> `"$LogFile`" 2>&1"
}

# O `cmd.exe /c` e obrigatorio. Sem ele, CreateProcess tenta tratar a linha
# inteira como nome de programa e devolve 9 (PATH_NOT_FOUND): `&&`, `>>` e
# `2>&1` sao sintaxe de cmd, nao de CreateProcess.
$linha = "cmd.exe /c $comando"
if ($WorkingDirectory) {
    $linha = "cmd.exe /c cd /d `"$WorkingDirectory`" && $comando"
}

# A invocacao precisa ser pela classe. Usar -InputObject com uma instancia de
# Win32_Process falha com "Metodo invalido" (HRESULT 0x8004102e), porque WMI
# recusa a criacao a partir de um processo existente.
$criado = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $linha }
if ($criado.ReturnValue -ne 0) {
    throw "Win32_Process.Create falhou com codigo $($criado.ReturnValue)"
}

$pidNovo = $criado.ProcessId
Write-Host "iniciado (pid $pidNovo): $FilePath"

if ($WaitPort -gt 0) {
    $limite = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $limite) {
        $pronto = Test-NetConnection -ComputerName 127.0.0.1 -Port $WaitPort -InformationLevel Quiet -WarningAction SilentlyContinue
        if ($pronto) {
            Write-Host "pronto: porta $WaitPort respondendo"
            return $pidNovo
        }
        Start-Sleep -Seconds 2
    }
    throw "timeout de ${TimeoutSeconds}s aguardando a porta $WaitPort (pid $pidNovo)"
}

return $pidNovo
