@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"
REM XAU AI PRO - Instalador
REM Cria o pacote de instalacao

echo.
echo === XAU AI PRO - Instalador ===
echo.

REM POR QUE ESTE SCRIPT CHAMA O build_app.bat
REM =========================================
REM A versao anterior rodava `npx tauri build` direto e depois procurava o MSI
REM em `frontend\src-tauri\target\release\bundle\msi`. Esse caminho esta ERRADO
REM por dois motivos independentes, e ambos faziam o script falhar:
REM
REM 1. O bundle nao nasce em `src-tauri\target`. O Cargo deste projeto desvia o
REM    `target-dir` para fora do disco de codigo (`src-tauri\.cargo\config.toml`
REM    linha 23) e o `build_app.bat` faz o mesmo na linha 44. O Tauri empacota a
REM    partir desse `target-dir`, entao o bundle nasce em `Temp\cargo-target`.
REM    `Test-Path frontend\src-tauri\target` = False, e sempre foi.
REM
REM 2. `npx tauri build` sozinho nao executa as etapas 4, 5 e 6 do
REM    `build_app.bat`. Sem elas o MSI sai com `core\`, `bridge\` e
REM    `Python\models\` desatualizados, ou ausentes. O instalador gerado aqui
REM    nao era o mesmo do ciclo de build, apesar do mesmo nome.
REM
REM Chamar o `build_app.bat` elimina os dois modos de falha de uma vez: ele
REM compila core, gateway e modelos antes de empacotar, e o bundle sai no
REM lugar certo. Sobra para este script apenas conferir o resultado e mostrar
REM o caminho, a parte que ele sempre acertou conceitualmente.

call "%ROOT%\scripts\build_app.bat"
if %ERRORLEVEL% neq 0 (
    echo ERRO: Build completo falhou - veja as etapas acima
    endlocal
    exit /b 1
)

REM Onde o bundle REALMENTE nasce: o mesmo `target-dir` que o build usou.
set "BUNDLE=%ROOT%\Temp\cargo-target\release\bundle"
if not exist "%BUNDLE%" set "BUNDLE=%ROOT%\frontend\src-tauri\target\release\bundle"

echo.
if not exist "%BUNDLE%\msi" (
    echo ERRO: Instalador MSI nao foi gerado em "%BUNDLE%\msi"
    endlocal
    exit /b 1
)
echo Instalador criado em: "%BUNDLE%\msi"
echo.
endlocal
exit /b 0
