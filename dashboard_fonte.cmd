@echo off
rem ============================================================
rem  dashboard_fonte.cmd - XAU AI PRO
rem  Inicia o dashboard (Streamlit) usando o .venv do projeto,
rem  que possui uvicorn instalado. Usar enquanto o XAU_AI_PRO.exe
rem  empacotado nao for reconstruido (fix uvicorn).
rem ============================================================
setlocal
title XAU AI PRO - Dashboard (fonte/venv)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERRO] Venv nao encontrado em .venv\Scripts\python.exe
  pause
  exit /b 1
)

echo [XAU AI PRO] Abrindo o painel em http://127.0.0.1:8501 ...
echo [XAU AI PRO] Mantenha esta janela aberta enquanto usar o painel.
echo.

".venv\Scripts\python.exe" -m streamlit run Python\dashboard\app.py ^
  --server.port=8501 --server.headless=true --server.address=127.0.0.1 ^
  --global.developmentMode=false --client.toolbarMode=viewer ^
  --browser.gatherUsageStats=false

pause
endlocal
