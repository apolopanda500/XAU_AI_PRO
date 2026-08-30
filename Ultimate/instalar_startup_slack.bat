@echo off
REM ============================================================
REM  XAU AI PRO - Instala o Slack Watcher na inicializacao do Windows
REM  Executa uma vez como administrador (ou usuario normal) e pronto:
REM  o watcher roda oculto a cada login, notificando trades no Slack.
REM ============================================================
set SRC=%~dp0slack_watcher_startup.vbs
set DST=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\XAU_AI_PRO_SlackWatcher.vbs

copy /Y "%SRC%" "%DST%" >nul
if %ERRORLEVEL%==0 (
    echo [OK] Slack Watcher instalado na inicializacao do Windows!
    echo      Local: %DST%
    echo      Ele iniciara oculto a cada login do Windows.
) else (
    echo [ERRO] Falha ao copiar para a pasta Startup.
)
pause