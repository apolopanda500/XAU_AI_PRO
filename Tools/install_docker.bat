@echo off
REM ============================================================
REM  INSTALLER DOCKER - XAU AI PRO (Opcao A: Docker Desktop)
REM  Executa como ADMINISTRADOR (eleva privilegios automaticamente)
REM ============================================================
setlocal
set "SCRIPTS=%~dp0"
set "POST=%SCRIPTS%post_docker_cli_setup.ps1"

echo.
echo  Instalador Docker Desktop - XAU AI PRO
echo  Scripts dir: %SCRIPTS%
echo.

REM Elevar privilegios (UAC)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  Solicitando elevacao de privilegios (aceite o UAC)...
    powershell -Command "Start-Process -FilePath 'powershell' -ArgumentList '-ExecutionPolicy','Bypass','-File','%POST%' -Verb RunAs"
    goto :eof
)

REM Se ja estiver admin, executa direto
powershell -ExecutionPolicy Bypass -File "%POST%"