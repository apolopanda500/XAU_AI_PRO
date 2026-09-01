@echo off
rem =====================================================================
rem build_installer.cmd - Full build of XAU_AI_PRO (Windows)
rem ---------------------------------------------------------------------
rem Flow:
rem   1) EXE one-file (PyInstaller)   -> dist\XAU_AI_PRO.exe
rem   2) Installer (Inno Setup)       -> installer\XAU_AI_PRO_Setup.exe
rem   3) Signing (optional)           -> installer\sign.cmd
rem
rem USAGE:
rem    build_installer.cmd                  (no signing)
rem    build_installer.cmd SIGN             (best cert from store)
rem    build_installer.cmd "C:\certs\x.pfx" "senha"
rem
rem IMPORTANT: paths like "C:\Program Files (x86)\..." must NOT be expanded
rem inside parenthesized IF blocks (cmd expands %VAR% at parse time and the
rem parentheses break the block parser). All expansions happen at top level.
rem =====================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0.."

set "ROOT=%CD%"
set "PY=%ROOT%\.venv\Scripts\python.exe"
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

rem ---- 0) pre-flight ---------------------------------------------------
if not exist "%PY%" goto :nopy
if not exist "%ISCC%" goto :noiscc

rem ---- 1) Qualidade (testes automatizados) -----------------------------
echo.
echo == [1/4] Testes automatizados ==
"%PY%" -m pytest -q tests
if errorlevel 1 goto :fail

rem ---- 2) EXE (PyInstaller) -------------------------------------------
echo.
echo == [2/4] PyInstaller: dist\XAU_AI_PRO.exe ==
"%PY%" -m PyInstaller --noconfirm --clean launcher.spec
if errorlevel 1 goto :fail

echo.== Smoke test: XAU_AI_PRO.exe versao ==
"%ROOT%\dist\XAU_AI_PRO.exe" versao
if errorlevel 1 echo [AVISO] smoke test de versao falhou

rem ---- 3) Installer (Inno Setup) ---------------------------------------
echo.
echo == [3/4] Inno Setup: installer\XAU_AI_PRO_Setup.exe ==
"%ISCC%" "%ROOT%\installer\installer.iss" /Qp
if errorlevel 1 goto :fail

rem ---- 4) Signing (optional) -------------------------------------------
if "%~1"=="" goto :done
echo.
echo == [4/4] Authenticode signing ==
call installer\sign.cmd %*
if errorlevel 1 goto :fail

:done
echo.
echo Build concluido:
echo   EXE       : %ROOT%\dist\XAU_AI_PRO.exe
echo   Instalador: %ROOT%\installer\XAU_AI_PRO_Setup.exe
endlocal
exit /b 0

:nopy
echo [ERRO] venv nao encontrado: %PY%
echo        Crie com: uv venv .venv ^& uv pip install -r requirements.txt
exit /b 1

:noiscc
echo [ERRO] Inno Setup 6 nao encontrado em:
echo %ISCC%
exit /b 1

:fail
echo.
echo [ERRO] build falhou. Verifique os logs acima.
exit /b 1