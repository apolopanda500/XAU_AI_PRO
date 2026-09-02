@echo off
rem ============================================================
rem  start_dashboard.cmd - XAU AI PRO
rem  Abre o dashboard web (Streamlit) com o executavel corrigido
rem  (build com uvicorn embutido). Pode ser usado manualmente
rem  ou pelo Agendador de Tarefas (sessao independente).
rem ============================================================
title XAU AI PRO - Dashboard
cd /d "%~dp0"

if not exist "%~dp0XAU_AI_PRO.exe" (
  echo [ERRO] XAU_AI_PRO.exe nao encontrado: %~dp0
  pause
  exit /b 1
)

echo [XAU AI PRO] Iniciando dashboard em http://127.0.0.1:8501 ...
echo [XAU AI PRO] Feche esta janela para encerrar o painel.
echo.
"%~dp0XAU_AI_PRO.exe" dashboard
echo.
echo [XAU AI PRO] Dashboard encerrado.
pause