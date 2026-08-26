@echo off
REM Setup completo do Vercel Workflows para XAU_AI_PRO
REM Execute este script na pasta raiz do projeto

set BACKEND_DIR=%~dp0backend
cd /d "%BACKEND_DIR%"

echo.
echo =========================================
echo  XAU_AI_PRO - Setup Vercel Workflows
echo =========================================
echo.

REM 1. Instalar dependencias
echo [1/4] Instalando dependencias do backend...
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha ao instalar dependencias
    pause
    exit /b 1
)
echo Dependencias instaladas com sucesso!
echo.

REM 2. Login no Vercel
echo [2/4] Fazendo login no Vercel...
echo (uma janela do navegador sera aberta)
call npx vercel login
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha no login
    pause
    exit /b 1
)
echo Login realizado!
echo.

REM 3. Linkar projeto
echo [3/4] Linkando projeto ao Vercel...
echo (seleciona a organizacao: apolopanda500)
echo (seleciona o projeto: xau-ai-pro)
call npx vercel link
if %ERRORLEVEL% NEQ 0 (
    echo AVISO: Link falhou - configure manualmente no dashboard
)
echo.

REM 4. Deploy
echo [4/4] Fazendo deploy para Vercel...
call npx vercel --prod --force
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Falha no deploy
    pause
    exit /b 1
)

echo.
echo =========================================
echo  DEPLOY CONCLUIDO!
echo =========================================
echo.
echo Acesse:
echo   - Dashboard: https://vercel.com/apolopanda500/xau-ai-pro
echo   - Workflows: https://vercel.com/apolopanda500/~/workflows
echo   - Analytics: https://vercel.com/apolopanda500/xau-ai-pro/analytics
echo.
echo Para inspeionar workflows localmente:
echo   npx workflow web
echo   npx workflow inspect runs
echo.
pause
