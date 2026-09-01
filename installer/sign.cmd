@echo off
rem =====================================================================
rem sign.cmd - Sign EXE and Installer of XAU_AI_PRO (Authenticode SHA-256)
rem ---------------------------------------------------------------------
rem USAGE (cert from store - auto):
rem     sign.cmd
rem USAGE (real certificate .pfx):
rem     sign.cmd "C:\certs\meu-cert.pfx" "senha"
rem
rem Requires: signtool from Windows SDK (10.0.26100.0 x64) and a code
rem signing certificate in the "My" (CurrentUser) store or supplied as .pfx.
rem
rem IMPORTANT: the signtool path contains "(x86)" - never expand it inside
rem a parenthesized IF block (cmd expands %VAR% at parse time and the
rem parentheses break the block parser). All expansions happen at top level.
rem =====================================================================
setlocal EnableDelayedExpansion
set "SIGNTOOL=C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"
set "ROOT=%~dp0.."
set "TS=http://timestamp.digicert.com"

if not exist "%SIGNTOOL%" goto :nosigntool

rem Optional args (no nested quotes to avoid cmd parse errors)
set "CERT="
set "PASS="
if not "%~1"=="" set "CERT=%~1"
if not "%~2"=="" set "PASS=%~2"

echo == Assinando EXE ==
call :sign "%ROOT%\dist\XAU_AI_PRO.exe"
if errorlevel 1 goto :fail

echo == Assinando Instalador ==
call :sign "%ROOT%\installer\XAU_AI_PRO_Setup.exe"
if errorlevel 1 goto :fail

echo == Verificacao ==
"%SIGNTOOL%" verify /pa /v "%ROOT%\dist\XAU_AI_PRO.exe"
"%SIGNTOOL%" verify /pa /v "%ROOT%\installer\XAU_AI_PRO_Setup.exe"

echo.
echo Concluido. Use um certificado de CA comercial para confianca publica.
endlocal
exit /b 0

:nosigntool
echo [ERRO] signtool nao encontrado em
echo %SIGNTOOL%
exit /b 2

:fail
echo [ERRO] falha na assinatura
exit /b 1

:sign
rem %1 = arquivo a assinar (caminho completo)
set "OPTS="
if defined CERT if defined PASS set "OPTS=/f !CERT! /p !PASS!"
if defined CERT if not defined PASS set "OPTS=/f !CERT!"
"%SIGNTOOL%" sign !OPTS! /a /fd SHA256 /t %TS% /v "%~1"
exit /b %errorlevel%