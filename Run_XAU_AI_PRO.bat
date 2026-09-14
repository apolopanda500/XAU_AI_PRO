@echo off
REM XAU_AI_PRO v1.2.0 - Launcher Windows
REM Executa a interface Tkinter usando o ambiente virtual .venv local.
REM Funciona em qualquer maquina com Python 3.11 ja instalado.

SETLOCAL
SET "XAU_AI_PRO_ROOT=%~dp0"
cd /d "%~dp0"

echo.
echo.  XAU AI PRO v1.2.0 - Trading Desk
echo.  Fenomeno de mercado | Inteligencia Artificial | Execucao assistida
echo.

IF EXIST ".venv\Scripts\python.exe" (
    echo.  Executando Python venv .venv...
    .venv\Scripts\python.exe Python\launcher.py "%~*"
) ELSE (
    echo.
    echo. [AVISO] Ambiente virtual .venv/ nao encontrado.
    echo. Execute: pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
@echo Lancamento concluido. Pressione ENTER para sair...
pause >nul