@echo off
rem =====================================================================
rem release_all.cmd - Automacao completa de release do XAU_AI_PRO (local)
rem ---------------------------------------------------------------------
rem Fluxo (tudo em um comando):
rem   1) EXE one-file (PyInstaller)      -> dist\XAU_AI_PRO.exe
rem   2) Smoke test (versao)
rem   3) Setup (Inno Setup)              -> installer\XAU_AI_PRO_Setup.exe
rem   4) Manifest dos modelos            -> Models\manifest.json
rem   5) (opcional) Upload dos modelos   -> GitHub Release via gh CLI
rem
rem USO:
rem   Tools\release_all.cmd               (exe + setup + manifest)
rem   Tools\release_all.cmd MODELS        (+ upload dos modelos M5 no release)
rem   Tools\release_all.cmd MODELS H1     (upload dos modelos H1)
rem
rem Pre-requisitos: .venv com requirements-build.txt + Inno Setup 6 +
rem                 gh CLI autenticado (gh auth login) para o modo MODELS.
rem =====================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0.."

set "ROOT=%CD%"
set "PY=%ROOT%\.venv\Scripts\python.exe"
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set "TF=%~2"
if "%TF%"=="" set "TF=M5"

rem ---- 0) pre-flight ---------------------------------------------------
if not exist "%PY%" (
  echo [ERRO] venv nao encontrado: %PY%
  echo        Crie com: uv venv .venv ^& uv pip install -r requirements-build.txt
  exit /b 1
)
if not exist "%ISCC%" (
  echo [ERRO] Inno Setup 6 nao encontrado em: %ISCC%
  exit /b 1
)

rem ---- 1) EXE (PyInstaller) --------------------------------------------
echo.
echo == [1/4] PyInstaller: dist\XAU_AI_PRO.exe ==
"%PY%" -m PyInstaller --noconfirm --clean launcher.spec
if errorlevel 1 goto :fail

rem ---- 2) Smoke test ---------------------------------------------------
echo.
echo == [2/4] Smoke test ==
"%ROOT%\dist\XAU_AI_PRO.exe" versao
if errorlevel 1 echo [AVISO] smoke test de versao falhou

rem ---- 3) Setup (Inno Setup) -------------------------------------------
echo.
echo == [3/4] Inno Setup: installer\XAU_AI_PRO_Setup.exe ==
"%ISCC%" /DMyRoot="%ROOT%" installer\installer.iss
if errorlevel 1 goto :fail

rem ---- 4) Manifest de modelos -------------------------------------------
echo.
echo == [4/4] Manifest dos modelos (Models\manifest.json) ==
"%PY%" Tools\publish_models.py --tf %TF%
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo Release local concluido:
echo   EXE     : %ROOT%\dist\XAU_AI_PRO.exe
echo   Setup   : %ROOT%\installer\XAU_AI_PRO_Setup.exe
echo   Manifest: %ROOT%\Models\manifest.json
echo ============================================================
echo Proximos passos:
echo   git add Models\manifest.json ^&^& git commit ^&^& git push
if not "%~1"=="MODELS" (
  echo   Para publicar os modelos: Tools\release_all.cmd MODELS %TF%
  goto :done
)
rem ---- (opcional) Upload dos modelos no GitHub Release ------------------
echo.
echo == Upload dos modelos %TF% no GitHub Release ==
"%PY%" Tools\publish_models.py --tf %TF% --upload
if errorlevel 1 goto :fail

:done
endlocal
exit /b 0

:fail
echo.
echo [ERRO] release falhou. Verifique os logs acima.
exit /b 1