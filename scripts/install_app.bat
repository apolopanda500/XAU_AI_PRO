@echo off
REM XAU AI PRO - Instalador
REM Cria o pacote de instalacao

echo.
echo === XAU AI PRO - Instalador ===
echo.

cd frontend
echo [1/2] Compilando Tauri App...
npx tauri build
echo [2/2] Build concluido!

echo.
echo Instalador criado em: frontend\src-tauri\target\release\bundle\msi\
echo.
pause
