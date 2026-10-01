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
REM O cache do Rust saia do disco do codigo. Nesta maquina o `target` dentro do
REM repositorio chegou a 3,9 GB e o `cargo check` falhou DUAS vezes com
REM "Espaco insuficiente no disco (os error 112)" — antes de qualquer teste.
REM `Temp\cargo-target` ja esta na allowlist de `scripts\limpeza_segura.ps1`
REM (`Temp/` esta no .gitignore, linha 41), entao a limpeza segura o alcanca.
if not defined CARGO_TARGET_DIR set "CARGO_TARGET_DIR=%ROOT%\Temp\cargo-target"
echo CARGO_TARGET_DIR=%CARGO_TARGET_DIR%
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
REM O caminho do binario tem de vir da MESMA variavel usada na compilacao.
REM Antes era fixo em `core\target\release`, mas a etapa 4 pode redirecionar o
REM cache para `Temp\cargo-target` (linha 44) — e a copia quebrava com
REM "ERRO: Nao foi possivel copiar o binary do core". O binario estava
REM compilado, em outro lugar.
set "CORE_BIN=%CARGO_TARGET_DIR%\release\xau-ai-pro-core.exe"
if not exist "%CORE_BIN%" set "CORE_BIN=%ROOT%\core\target\release\xau-ai-pro-core.exe"
if not exist "%CORE_BIN%" (
    echo ERRO: binario do core nao encontrado em %CARGO_TARGET_DIR%\release nem em core\target\release
    exit /b 1
)
copy /Y "%CORE_BIN%" "%ROOT%\frontend\src-tauri\core\xau-ai-pro-core.exe" >nul
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
REM /XD _backup* impede que um backup de metadados (criado quando um pipeline
REM legado corrompe a governanca) entre no bundle. Em 2026-09-29 o backup foi
REM para dentro de Python\models e o MSI novo o empacotou no app instalado,
REM onde nao serve para nada. Backup pertence em Temp\, nao na pasta de modelos.
robocopy "%ROOT%\Python\models" "%ROOT%\frontend\src-tauri\Python\models" /MIR /XD _backup* /XF *.tmp /NFL /NDL /NJH /NJS /NP
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
