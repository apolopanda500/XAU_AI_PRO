@echo off
REM =====================================================================
REM  start_gateway_autostart.cmd  -  AUTOSTART da tarefa agendada
REM  (AIGateway9011_Watchdog  ->  AIGateway9027_Watchdog)
REM
REM  CORRIGIDO 22/11/2026 (bug que derrubava o gateway):
REM  1) O caminho do bridge tem ESPACO ("XAU AI PRO"). O `start ... cmd /c
REM     call "%BRIDGE%"` quebrava: ""C:\Users\Micro\AppData\Local\XAU' nao e
REM     reconhecido. Corrigido com `start "" /min "%BRIDGE%"`.
REM  2) O script matava QUALQUER processo na 9027 (taskkill), inclusive o
REM     FastAPI que o APP e o EA consomem. Agora ele SO age se a porta estiver
REM     ocupada por processo que NAO responde /api/health.
REM  3) Se o gateway FastAPI ja responde, NAO faz nada (goto :ok) — foi essa
REM     checagem que faltou e fez o watchdog matar o gateway vivo.
REM
REM  O gateway HTTP e o `backend.fastapi_gateway:app` (uvicorn). O binario
REM  mt5-gateway.exe e o bridge/MCP do MT5, que fala outro protocolo e nao
REM  serve /api/health — nao pode ocupar a 9027 quando o app a consome.
REM
REM  SEGURANCA: MODO LEITURA. Todas as portas de ordem ficam em 0.
REM  Nao arma execucao real, nao toca em ordens, nao apaga nada.
REM =====================================================================
setlocal EnableExtensions
set PROJ=%~dp0
set PORTA=9027
set LOG=%PROJ%gateway_autostart.log
set PY=%PROJ%.venv\Scripts\python.exe

REM  Se o gateway FastAPI JA responde, nao faz NADA (evita duplicar e evita
REM  matar o processo vivo). Este e o guarda que faltava.
set SERVE=000
for /f "delims=" %%C in ('curl.exe -s -o nul -w "%%{http_code}" --max-time 3 http://127.0.0.1:%PORTA%/api/health -H "Authorization: Bearer %XAU_GATEWAY_TOKEN%" 2^>nul') do set SERVE=%%C
if not "%SERVE%"=="000" (
   if not "%SERVE%"=="401" goto :ok
)

REM  Nenhum gateway respondendo (000) ou sem autenticacao (401): verifica
REM  quem esta na porta. So mata se for um processo que NAO e o uvicorn do
REM  fastapi_gateway (ex.: bridge residual travado).
set PID_ANTIGO=
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%PORTA% " ^| findstr LISTENING') do set PID_ANTIGO=%%P
if not "%PID_ANTIGO%"=="" (
   set EH_GATEWAY=
   for /f "delims=" %%C in ('powershell -NoProfile -Command "$p=Get-CimInstance Win32_Process -Filter 'ProcessId=%PID_ANTIGO%'; if($p){ $cmd=$p.CommandLine; if($cmd -match 'uvicorn' -and $cmd -match 'fastapi_gateway'){ 'SIM' } }" 2^>nul') do set EH_GATEWAY=%%C
   if not "%EH_GATEWAY%"=="SIM" (
      taskkill /PID %PID_ANTIGO% /F >nul 2>&1
   )
)

REM  Sobe o gateway em modo leitura com o uvicorn/FastAPI.
set XAU_GATEWAY_PORT=%PORTA%
set XAU_ENABLE_REAL_ORDERS=0
set XAU_ENABLE_DEMO_ORDERS=0
set XAU_ENABLE_MT5_EXECUTION=0
set XAU_ENABLE_TRADE_COMMANDS=0
set XAU_ENABLE_EMERGENCY_RESUME=0
set XAU_MCP_TRADING=0
cd /d "%PROJ%"
start "XAU gateway FastAPI (leitura)" /min "%PY%" -m uvicorn backend.fastapi_gateway:app --host 127.0.0.1 --port %PORTA% >> "%LOG%" 2>&1

:ok
exit /b 0
