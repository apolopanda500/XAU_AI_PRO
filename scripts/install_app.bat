@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"
REM XAU AI PRO - Instalador
REM Cria o pacote de instalacao

echo.
echo === XAU AI PRO - Instalador ===
echo.

cd /d "%ROOT%\frontend"
echo [1/2] Compilando Tauri App...
npx tauri build
if %ERRORLEVEL% neq 0 (
    echo ERRO: Build Tauri falhou
    endlocal
    exit /b 1
)
echo [2/2] Build concluido!

echo.
if not exist "%ROOT%\frontend\src-tauri\target\release\bundle\msi" (
    echo ERRO: Instalador MSI nao foi gerado
    endlocal
    exit /b 1
)
echo Instalador criado em: %ROOT%\frontend\src-tauri\target\release\bundle\msi\
echo.
endlocal
exit /b 0
