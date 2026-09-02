@echo off
rem XAU_AI_PRO - Inicia o CLI launcher apontando para o diretorio instalado.
title XAU AI PRO - Painel e Comandos
set "XAU_AI_PRO_ROOT=%~dp0"
cd /d "%~dp0"
"%~dp0XAU_AI_PRO.exe" %*