@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"
REM XAU AI PRO - Build Script 1.2.3
REM Compila e empacota frontend, core e Tauri.

echo.
echo === XAU AI PRO - Build Script ===
echo.

echo [1/5] Sincronizando versao...
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\sync_version.py"
if %ERRORLEVEL% neq 0 (
    echo ERRO: Sincronizacao de versao falhou
    exit /b 1
)

REM Build frontend
echo [2/5] Compilando frontend...
cd /d "%ROOT%\frontend"
npm run build
if %ERRORLEVEL% neq 0 (
    echo ERRO: Build do frontend falhou
    exit /b 1
)
echo Frontend compilado com sucesso.

REM Build core Rust
echo [3/5] Compilando core Rust...
cd /d "%ROOT%\core"
cargo build --release --locked
if %ERRORLEVEL% neq 0 (
    echo ERRO: Build do backend falhou
    exit /b 1
)
echo Backend compilado com sucesso.

REM Compilar o gateway a partir do fonte atual para evitar bridge defasado
echo [4/6] Compilando gateway Python...
cd /d "%ROOT%"
if not exist "%ROOT%\build\mt5-gateway" mkdir "%ROOT%\build\mt5-gateway"
"%ROOT%\.venv\Scripts\python.exe" -m PyInstaller --noconfirm mt5-gateway.spec

if %ERRORLEVEL% neq 0 (
    echo ERRO: Build do gateway falhou
    exit /b 1
)

REM Copiar core e gateway para os recursos esperados pelo Tauri
echo [5/6] Sincronizando recursos do Tauri...
if not exist "%ROOT%\frontend\src-tauri\core" mkdir "%ROOT%\frontend\src-tauri\core"
copy /Y "%ROOT%\core\target\release\xau-ai-pro-core.exe" "%ROOT%\frontend\src-tauri\core\xau-ai-pro-core.exe"
if %ERRORLEVEL% neq 0 (
    echo ERRO: Nao foi possivel copiar o binary do core
    exit /b 1
)
if not exist "%ROOT%\frontend\src-tauri\bridge" mkdir "%ROOT%\frontend\src-tauri\bridge"
robocopy "%ROOT%\dist\mt5-gateway" "%ROOT%\frontend\src-tauri\bridge" /MIR /NFL /NDL /NJH /NJS /NP
if %ERRORLEVEL% geq 8 (
    echo ERRO: Nao foi possivel sincronizar o gateway
    exit /b 1
)

REM Build e bundle Tauri (MSI/NSIS)
echo [6/6] Gerando bundle Tauri...
cd /d "%ROOT%\frontend"
npm run tauri:build
if %ERRORLEVEL% neq 0 (
    echo ERRO: Bundle Tauri falhou
    exit /b 1
)

echo.
echo === Build e bundle completos! ===
echo Artefatos: "%ROOT%\frontend\src-tauri\target\release\bundle"
endlocal
exit /b 0
