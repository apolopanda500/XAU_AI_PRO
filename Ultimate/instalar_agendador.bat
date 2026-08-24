@echo off
REM =========================================================
REM XAU AI PRO — Instalador da Tarefa Agendada (Auto-Watch)
REM Cria uma tarefa no Windows para rodar auto_approve
REM a cada 60 minutos (configurável abaixo).
REM
REM Uso: clique com botão direito -> Executar como Administrador
REM =========================================================

set INTERVAL=60
set TASK_NAME=XAU_AI_PRO_AutoWatch
set SCRIPT_PATH=C:\Users\Micro\Downloads\XAU_AI_PRO\Ultimate
set PYTHON=C:\Users\Micro\AppData\Local\Programs\Python\Python312\python.exe

echo.
echo  ========================================
echo   XAU AI PRO - Instalar Tarefa Agendada
echo  ========================================
echo.
echo  Tarefa: %TASK_NAME%
echo  Script: %SCRIPT_PATH%\auto_watch.py
echo  Intervalo: a cada %INTERVAL% minutos
echo  Python: %PYTHON%
echo.

REM Remove tarefa existente
schtasks /F /TN "%TASK_NAME%" >nul 2>&1

REM Cria nova tarefa
schtasks /Create /SC MINUTE /MO %INTERVAL% /TN "%TASK_NAME%" ^
    /TR "%PYTHON% %SCRIPT_PATH%\auto_watch.py --once --interval %INTERVAL%" ^
    /RU "%USERNAME%" /IT /F

if %ERRORLEVEL% equ 0 (
    echo  [OK] Tarefa criada com sucesso!
    echo  A cada %INTERVAL% minutos, o auto-watch sera executado.
    echo  Relatorios em: Reports/
) else (
    echo  [ERRO] Nao foi possivel criar a tarefa.
    echo  Tente executar como Administrador.
)

echo.
echo ========================================
pause