@echo off
REM =====================================================================
REM  rotacionar_log_gateway.cmd  -  P1.3651
REM
REM  MEDIDO 16/11/2026 17:10: gateway_autostart.log = 174 514 114 B (166 MB)
REM  em 5 dias, sem rotacao. A causa e o access-log do uvicorn: uma linha
REM  INFO por pedido e o servico XAI_RefreshPredictions pede 13 simbolos a
REM  cada 180 s. Isso ja foi cortado na origem (--no-access-log no
REM  start_gateway_autostart.cmd); o que fica em log passa a ser so
REM  WARNING/ERROR - inclusive os "Invalid HTTP request received", que sao
REM  a origem medida dos http=1003 do EA.
REM
REM  Este script trata do que ja existe: acima de 20 MB roda o ficheiro para
REM  .1 (uma geracao anterior). E chamado pelo start_gateway_autostart.cmd no
REM  ramo em que o gateway vai subir, ou seja quando a porta esta livre e
REM  ninguem tem handle no ficheiro.
REM
REM  Nao mata processos, nao toca em ordens, nao apaga nada alem do .1
REM  anterior (um ficheiro de log que este proprio script criou).
REM =====================================================================
setlocal
set LOG=%~dp0gateway_autostart.log
set LIMITE=20971520
if not exist "%LOG%" goto :nada
for %%S in ("%LOG%") do set TAM=%%~zS
if %TAM% LSS %LIMITE% goto :abaixo
if exist "%LOG%.1" del /f /q "%LOG%.1" >nul 2>&1
move /y "%LOG%" "%LOG%.1" >nul 2>&1
if errorlevel 1 goto :preso
echo [rotacao] %TAM% B movidos para gateway_autostart.log.1
goto :fim
:abaixo
echo [rotacao] %TAM% B - abaixo do limite de %LIMITE% B, nada a fazer
goto :fim
:preso
echo [rotacao] FALHOU mover o log (handle preso?) - continua a crescer sem rotacao
goto :fim
:nada
echo [rotacao] sem gateway_autostart.log, nada a fazer
:fim
endlocal
exit /b 0