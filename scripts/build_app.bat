@echo off
REM XAU AI PRO - Build Script
REM Compila frontend e backend

echo.
echo === XAU AI PRO - Build Script ===
echo.

REM Build frontend
echo [1/3] Compilando frontend...
cd frontend
npm run build
if %ERRORLEVEL% neq 0 (
    echo ERRO: Build do frontend falhou
    exit /b 1
)
echo Frontend compilado com sucesso.

REM Build backend (Rust)
echo [2/3] Compilando backend Rust...
cd ..\core
cargo build --release
if %ERRORLEVEL% neq 0 (
    echo ERRO: Build do backend falhou
    exit /b 1
)
echo Backend compilado com sucesso.

REM Copy backend binary to frontend dist
echo [3/3] Copiando binaries...
copy /Y target\release\xau-ai-pro-core.exe frontend\dist\core.exe
if %ERRORLEVEL% neq 0 (
    echo AVISO: Nao foi possivel copiar o binary do core
)

echo.
echo === Build completo! ===
echo Para iniciar: frontend\npm run dev
exit /b 0
