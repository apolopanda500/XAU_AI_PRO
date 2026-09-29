@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"
REM XAU AI PRO - Build Script
REM Compila e empacota frontend, core, gateway e os recursos do bundle.

echo.
echo === XAU AI PRO - Build Script ===
echo.

echo [1/7] Sincronizando versao...
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\sync_version.py"
if %ERRORLEVEL% neq 0 (
    echo ERRO: Sincronizacao de versao falhou
    exit /b 1
)

echo [2/7] Verificando versao...
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\sync_version.py" --check
if %ERRORLEVEL% neq 0 (
    echo ERRO: Manifestos de versao divergentes
    exit /b 1
)

echo [3/7] Compilando frontend...
cd /d "%ROOT%\frontend"
REM `call` e obrigatorio: npm resolve para npm.cmd, e um .bat/.cmd chamado sem
REM `call` transfere o controle e o script acaba ali (o build parava no passo 3).
call npm run build
if %ERRORLEVEL% neq 0 (
    echo ERRO: Build do frontend falhou
    exit /b 1
)
echo Frontend compilado com sucesso.

echo [4/7] Compilando core Rust...
cd /d "%ROOT%\core"
cargo build --release --locked
if %ERRORLEVEL% neq 0 (
    echo ERRO: Build do core falhou
    exit /b 1
)
echo Core compilado com sucesso.

REM Compilar o gateway a partir do fonte atual para evitar bridge defasado
echo [5/7] Compilando gateway Python...
cd /d "%ROOT%"
if not exist "%ROOT%\build\mt5-gateway" mkdir "%ROOT%\build\mt5-gateway"
"%ROOT%\.venv\Scripts\python.exe" -m PyInstaller --noconfirm mt5-gateway.spec
if %ERRORLEVEL% neq 0 (
    echo ERRO: Build do gateway falhou
    exit /b 1
)

REM Copiar core, gateway e MODELOS para os recursos esperados pelo Tauri.
REM Sem esta etapa o bundle fica com um corte antigo de Python/models e o app
REM instalado enxerga so os simbolos que por acaso ja estavam em src-tauri.
echo [6/7] Sincronizando recursos do Tauri...
if not exist "%ROOT%\frontend\src-tauri\core" mkdir "%ROOT%\frontend\src-tauri\core"
copy /Y "%ROOT%\core\target\release\xau-ai-pro-core.exe" "%ROOT%\frontend\src-tauri\core\xau-ai-pro-core.exe" >nul
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
if not exist "%ROOT%\frontend\src-tauri\Python\models" mkdir "%ROOT%\frontend\src-tauri\Python\models"
robocopy "%ROOT%\Python\models" "%ROOT%\frontend\src-tauri\Python\models" /MIR /XF *.tmp /NFL /NDL /NJH /NJS /NP
if %ERRORLEVEL% geq 8 (
    echo ERRO: Nao foi possivel sincronizar os modelos
    exit /b 1
)

REM Build e bundle Tauri (MSI/NSIS)
echo [7/7] Gerando bundle Tauri...
cd /d "%ROOT%\frontend"
call npm run tauri:build
if %ERRORLEVEL% neq 0 (
    echo ERRO: Bundle Tauri falhou
    exit /b 1
)

echo.
echo === Build e bundle completos! ===
echo Artefatos: "%ROOT%\frontend\src-tauri\target\release\bundle"
endlocal
exit /b 0
