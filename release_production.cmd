@echo off
rem ============================================================
rem XAU_AI_PRO - RELEASE DE PRODUCCION (reproducible y protegido)
rem ------------------------------------------------------------
rem Flujo: 0) backup pre-build  1) pytest  2) AST check
rem        3) PyInstaller       4) Inno Setup
rem        -> dist\XAU_AI_PRO_Setup_{VERSION}.exe
rem
rem HISTORIA 2026-09-11: un build con --clean VACIO el arbol fuente
rem de este entorno (FileNotFoundError app\ai_client.py durante el
rem ensamblado del EXE). Por eso este script:
rem   - copia app/ + Python/ a Logs\backup_prebuild_* ANTES del build;
rem   - NO usa --clean (build incremental; el cache no borra fuentes);
rem   - verifica el conteo de app\*.py antes/despues del build y
rem     ABORTA si el build borro archivos.
rem
rem Requisitos:
rem   - .venv activo con requirements-lock.txt instalado
rem   - ISCC.exe de Inno Setup 6 en PATH o variable INNO_ISCC
rem ------------------------------------------------------------
setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo [ERROR] .venv no encontrado. Cree la venv:
    echo   python -m venv .venv
    echo   .venv\Scripts\python -m pip install -r requirements-lock.txt
    exit /b 1
)

echo === 0/4 BACKUP PRE-BUILD (proteccion del working tree) ===
set "STAMP=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%"
set "STAMP=%STAMP: =0%"
set "BK=Logs\backup_prebuild_%STAMP%"
xcopy /e /i /q "app" "%BK%\app" >nul
xcopy /e /i /q "Python" "%BK%\Python" >nul
if exist "%BK%\app" (
    echo Backup pre-build: %BK%
) else (
    echo [AVISO] Backup no creado. Continuo igualmente.
)
set "PY_COUNT_BEFORE=0"
for /f %%n in ('dir /b /s app\*.py ^| find /c ".py"') do set "PY_COUNT_BEFORE=%%n"
echo Archivos app\*.py antes del build: %PY_COUNT_BEFORE%

echo === 1/4 TEST SUITE (gate) ===
"%PY%" -m pytest -q tests -p no:cacheprovider
if errorlevel 1 (
    echo [ERROR] Test suite fallido - release cancelado.
    exit /b 1
)

echo === 2/4 AST CHECK (sintaxis) ===
"%PY%" -c "import ast,glob; [ast.parse(open(f,encoding='utf-8-sig').read()) for f in glob.glob('app/**/*.py',recursive=True)+glob.glob('Python/**/*.py',recursive=True)]; print('AST OK')"
if errorlevel 1 (
    echo [ERROR] Error de sintaxis - release cancelado.
    exit /b 1
)

echo === 3/4 BUILD EXE (launcher.spec) ===
rem SIN --clean: protege el arbol fuente (ver HISTORIA arriba).
"%PY%" -m PyInstaller --noconfirm launcher.spec
if errorlevel 1 (
    echo [ERROR] Build PyInstaller fallido.
    exit /b 2
)
if not exist "dist\XAU_AI_PRO.exe" (
    echo [ERROR] dist\XAU_AI_PRO.exe no generado.
    exit /b 2
)
rem Verificacion de integridad DESPUES del build (el conteo no debe bajar).
set "PY_COUNT_AFTER=0"
for /f %%n in ('dir /b /s app\*.py ^| find /c ".py"') do set "PY_COUNT_AFTER=%%n"
echo Archivos app\*.py despues del build: %PY_COUNT_AFTER% (antes: %PY_COUNT_BEFORE%)
if not "%PY_COUNT_AFTER%"=="%PY_COUNT_BEFORE%" (
    echo [CRITICO] El build borro archivos fuente. Abortando antes del instalador.
    exit /b 4
)

echo === 4/4 INSTALADOR (ISCC) ===
rem Version unica desde el archivo VERSION de la raiz -> nombre y metadatos.
set "REL_VERSION=1.2.0"
if exist "VERSION" set /p REL_VERSION=<VERSION
set "ISCC=%INNO_ISCC%"
if defined ISCC goto run_iscc
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if defined ISCC goto run_iscc
where ISCC >nul 2>nul && goto where_iscc
echo [AVISO] ISCC no encontrado; el EXE ya esta en dist\XAU_AI_PRO.exe
echo         Compile el instalador manualmente con:
echo         "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\installer.iss
exit /b 0

:run_iscc
"%ISCC%" /DMyAppVersion=%REL_VERSION% installer\installer.iss
if errorlevel 1 (
    echo [ERROR] Inno Setup fallido.
    exit /b 3
)
goto release_done

:where_iscc
ISCC /DMyAppVersion=%REL_VERSION% installer\installer.iss
if errorlevel 1 (
    echo [ERROR] Inno Setup fallido.
    exit /b 3
)

:release_done
echo.
echo === RELEASE COMPLETO ===
dir /b dist\XAU_AI_PRO_Setup_*.exe 2>nul
echo Instalador: %~dp0dist\XAU_AI_PRO_Setup_%REL_VERSION%.exe
exit /b 0