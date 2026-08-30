@echo off
REM ============================================================
REM  start_proxy.bat - XAU AI PRO
REM  Inicia o proxy LiteLLM na porta 4000 (usado por validation.py
REM  e dashboard/app.py via OpenAI(base_url="http://localhost:4000")).
REM  Conforme Docs/LITELLM_FIX.md.
REM
REM  Modelo padrao: ollama/deepseek-v4-flash:cloud (Ollama)
REM  Para trocar o modelo, edite a linha "set MODEL=..." abaixo.
REM ============================================================
setlocal

REM Fix UnicodeEncodeError do banner do LiteLLM no console Windows (cp1252)
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

REM Caminho do venv do projeto (ajuste se necessario)
set "VENV=%~dp0..\.venv\Scripts"
if not exist "%VENV%\python.exe" (
  echo [ERRO] Venv nao encontrado em %VENV%
  echo        Instale as dependencias:  .venv\Scripts\pip install -r requirements.txt
  pause
  exit /b 1
)

REM Modelo padrao - edite aqui se quiser outro (ex.: gpt-4o, deepseek-chat)
set "MODEL=ollama/deepseek-v4-flash:cloud"

echo [XAU AI PRO] Iniciando proxy LiteLLM na porta 4000...
echo [XAU AI PRO] Modelo: %MODEL%
echo [XAU AI PRO] Mantenha esta janela aberta enquanto usar a IA.
echo.

"%VENV%\litellm.exe" --model "%MODEL%" --port 4000

echo.
echo [XAU AI PRO] Proxy encerrado.
pause
endlocal