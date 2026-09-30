@echo off
rem ===================================================================
rem Status e quadro de tarefas dos agentes (cline e opencode).
rem
rem   sem argumento  : mostra STATUS.json + quadro de etapas
rem   sync           : so o quadro de tarefas (sync.py status)
rem   cline <msg>    : atualiza o bloco cline no STATUS.json
rem   opencode <msg> : atualiza o bloco opencode no STATUS.json
rem
rem Trava de um arquivo antes de mexer:
rem   .venv\Scripts\python.exe .agents_sync\sync.py --agente opencode claim E1.1
rem ===================================================================
cd /d "%~dp0.."

if /i "%~1"=="sync" (
  .venv\Scripts\python.exe .agents_sync\sync.py --agente opencode status
  goto :fim
)

if "%~1"=="" (
  .venv\Scripts\python.exe .agents_sync\agent_status.py
  echo.
  .venv\Scripts\python.exe .agents_sync\sync.py --agente opencode status
) else (
  .venv\Scripts\python.exe .agents_sync\agent_status.py %*
)
:fim
pause
