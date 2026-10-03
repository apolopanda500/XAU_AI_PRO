@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"
REM XAU AI PRO - Build Script
REM Compila e empacota frontend, core, gateway e os recursos do bundle.

echo.
echo === XAU AI PRO - Build Script ===
echo.

echo [1/7] Sincronizando versao...
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\sync_version.py"
if %ERRORLEVEL% neq 0 (
    echo ERRO: Sincronizacao de versao falhou
    exit /b 1
)

echo [2/7] Verificando versao...
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\sync_version.py" --check
if %ERRORLEVEL% neq 0 (
    echo ERRO: Manifestos de versao divergentes
    exit /b 1
)

echo [3/7] Compilando frontend...
cd /d "%ROOT%\frontend"
REM `call` e obrigatorio: npm resolve para npm.cmd, e um .bat/.cmd chamado sem
REM `call` transfere o controle e o script acaba ali (o build parava no passo 3).
call npm run build
if %ERRORLEVEL% neq 0 (
    echo ERRO: Build do frontend falhou
    exit /b 1
)
echo Frontend compilado com sucesso.

echo [4/7] Compilando core Rust...
cd /d "%ROOT%\core"
REM O cache do Rust saia do disco do codigo. Nesta maquina o `target` dentro do
REM repositorio chegou a 3,9 GB e o `cargo check` falhou DUAS vezes com
REM "Espaco insuficiente no disco (os error 112)" — antes de qualquer teste.
REM `Temp\cargo-target` ja esta na allowlist de `scripts\limpeza_segura.ps1`
REM (`Temp/` esta no .gitignore, linha 41), entao a limpeza segura o alcanca.
if not defined CARGO_TARGET_DIR set "CARGO_TARGET_DIR=%ROOT%\Temp\cargo-target"
echo CARGO_TARGET_DIR=%CARGO_TARGET_DIR%
cargo build --release --locked
if %ERRORLEVEL% neq 0 (
    echo ERRO: Build do core falhou
    exit /b 1
)
echo Core compilado com sucesso.

REM Compilar o gateway a partir do fonte atual para evitar bridge defasado
echo [5/7] Compilando gateway Python...
cd /d "%ROOT%"
if not exist "%ROOT%\build\mt5-gateway" mkdir "%ROOT%\build\mt5-gateway"
"%ROOT%\.venv\Scripts\python.exe" -m PyInstaller --noconfirm mt5-gateway.spec
if %ERRORLEVEL% neq 0 (
    echo ERRO: Build do gateway falhou
    exit /b 1
)

REM Copiar core, gateway e MODELOS para os recursos esperados pelo Tauri.
REM Sem esta etapa o bundle fica com um corte antigo de Python/models e o app
REM instalado enxerga so os simbolos que por acaso ja estavam em src-tauri.
echo [6/7] Sincronizando recursos do Tauri...
if not exist "%ROOT%\frontend\src-tauri\core" mkdir "%ROOT%\frontend\src-tauri\core"
REM O caminho do binario tem de vir da MESMA variavel usada na compilacao.
REM Antes era fixo em `core\target\release`, mas a etapa 4 pode redirecionar o
REM cache para `Temp\cargo-target` (linha 44) — e a copia quebrava com
REM "ERRO: Nao foi possivel copiar o binary do core". O binario estava
REM compilado, em outro lugar.
set "CORE_BIN=%CARGO_TARGET_DIR%\release\xau-ai-pro-core.exe"
if not exist "%CORE_BIN%" set "CORE_BIN=%ROOT%\core\target\release\xau-ai-pro-core.exe"
if not exist "%CORE_BIN%" (
    echo ERRO: binario do core nao encontrado em %CARGO_TARGET_DIR%\release nem em core\target\release
    exit /b 1
)
copy /Y "%CORE_BIN%" "%ROOT%\frontend\src-tauri\core\xau-ai-pro-core.exe" >nul
if %ERRORLEVEL% neq 0 (
    echo ERRO: Nao foi possivel copiar o binary do core
    exit /b 1
)
if not exist "%ROOT%\frontend\src-tauri\bridge" mkdir "%ROOT%\frontend\src-tauri\bridge"
robocopy "%ROOT%\dist\mt5-gateway" "%ROOT%\frontend\src-tauri\bridge" /MIR /NFL /NDL /NJH /NJS /NP
if %ERRORLEVEL% geq 8 (
    echo ERRO: Nao foi possivel sincronizar o gateway
    exit /b 1
)
if not exist "%ROOT%\frontend\src-tauri\Python\models" mkdir "%ROOT%\frontend\src-tauri\Python\models"

REM ---------------------------------------------------------------------------
REM POR QUE ESTE PASSO USA /E E NAO /MIR
REM ---------------------------------------------------------------------------
REM `/MIR` ESPELHA: apaga no destino tudo que nao esta na origem. E a origem
REM aqui (`Python\models`, raiz) tem 72 arquivos e ZERO `MULTI_*`; os tres
REM modelos MULTI sao publicados por `train_multi.MODELOS_DIR` (linha 80) em
REM `frontend\src-tauri\Python\models` — o proprio DESTINO deste comando.
REM
REM Resultado medido: com `/MIR`, o passo [6/7] apaga os 3
REM `MULTI_*.pkl` + `MULTI_*.meta.json` (174 MB) da pasta que
REM `mt5-gateway.spec:24` empacota e que `tauri.conf.json` inclui como
REM `Python/models/**/*`. Os artefatos so sobreviviam em `dist\`, `bridge\` e
REM `Temp\cargo-target\release\bridge\`, por accidento de outro passo.
REM
REM E o defeito 7.2 de `Docs\SESSAO_20261002_MODELOS_MULTI_E_SEGURANCA.md`:
REM os modelos somem e o BUILD PASSA LIMPO, sem excecao e sem log. As tres
REM ocorrencias descritas naquele doc foram creditadas a remocao manual de
REM `dist\`. A remocao manual foi um dos fatores, mas a causa ESTAVEL — a que
REM repete o defeito em qualquer build — e esta linha.
REM
REM `/E` copia subpastas e arquivos sem apagar o que ja existe no destino.
REM O espelhamento era desnecessario aqui: os dois lados sao pastas de
REM modelo, e apagar um `.pkl` ja treinado nunca e o que se quer ao empacotar.
REM
REM O `/XD _backup*` segue necessario: em 2026-09-29 um backup de metadados
REM foi criado dentro de `Python\models` e o MSI novo o empacotou no app
REM instalado, onde nao serve para nada. Backup pertence em `Temp\`.
robocopy "%ROOT%\Python\models" "%ROOT%\frontend\src-tauri\Python\models" /E /XD _backup* /XF *.tmp /NFL /NDL /NJH /NJS /NP
if %ERRORLEVEL% geq 8 (
    echo ERRO: Nao foi possivel sincronizar os modelos
    exit /b 1
)

REM ---------------------------------------------------------------------------
REM TRAVA DE ARTEFATO: o build NAO passa se os MULTI nao estiverem no destino
REM ---------------------------------------------------------------------------
REM Este e o passo que o `robocopy` acima NAO pode cumprir: ele so copia
REM `Python\models` para frente e nao sabe o que precisa existir no destino.
REM A trava fica aqui, depois da copia, medindo o ARTEFATO FINAL — a regra
REM do ciclo de 02/10 ("medir o artefato final, nao o codigo que o gera").
REM
REM Sem esta trava o defeito volta a ser invisivel: o `robocopy` termina com
REM codigo 0, o script segue para [7/7] e o instalador sai sem os 3 modelos.
REM
REM Cada modelo exige o `.pkl` E o `.meta.json`: o `.pkl` e o que o
REM `joblib.load` le, e o `.meta.json` e o que declara timeframe e classe para
REM o runtime (ver `Python\ai\train_multi.py:449-454`, que escreve os dois).
REM
REM Implementado como subrotina, e nao com `!VAR!` dentro do `for`: o script
REM roda sob `setlocal` SEM delayed expansion, e liga-lo agora mudaria a
REM interpretacao de `!` no `echo` do resto do build.
set "MODELOS_DESTINO=%ROOT%\frontend\src-tauri\Python\models"
for %%M in (MULTI_CRYPTO MULTI_FIAT MULTI_METALS) do (
    if not exist "%MODELOS_DESTINO%\%%M.pkl" (
        echo ERRO: modelo ausente: "%MODELOS_DESTINO%\%%M.pkl"
        goto :erro_modelos_multi
    )
    if not exist "%MODELOS_DESTINO%\%%M.meta.json" (
        echo ERRO: metadados ausentes: "%MODELOS_DESTINO%\%%M.meta.json"
        goto :erro_modelos_multi
    )
)
echo Modelos MULTI presentes no destino: OK.
goto :modelos_ok

:erro_modelos_multi
echo.
echo ERRO: os 3 modelos MULTI nao estao todos em "%MODELOS_DESTINO%".
echo.
echo O instalador sairia SEM os modelos MULTI e o app instalado diria
echo "modelos nao carregam" sem nenhuma excecao. Treine antes de empacotar:
echo     .venv\Scripts\python.exe Python\ai\train_multi.py
echo.
echo Se os `.pkl` existem em outro lugar (por exemplo em
echo frontend\src-tauri\bridge\_internal\Python\models\), restaure-os nesta
echo pasta antes de repetir o build. NAO apague o destino para "limpar": foi
echo essa remocao que repetiu o defeito tres vezes.
exit /b 1

:modelos_ok

REM Build e bundle Tauri (MSI/NSIS)
echo [7/7] Gerando bundle Tauri...
cd /d "%ROOT%\frontend"
call npm run tauri:build
if %ERRORLEVEL% neq 0 (
    echo ERRO: Bundle Tauri falhou
    exit /b 1
)

echo.
echo === Build e bundle completos! ===
REM O bundle nasce em `Temp\cargo-target`, e nao em `frontend\src-tauri\target`.
REM O `target-dir` do Cargo foi desviado para fora do disco de codigo de
REM proposito (ver `src-tauri\.cargo\config.toml` linha 23 e a etapa 4 acima),
REM e o Tauri empacota sempre a partir desse `target-dir`. Anunciar o caminho
REM padrao do Tauri levava o operador a procurar um diretorio que nunca teve o
REM artefato — foi o que `install_app.bat` fazia ate a correcao de 01/10/2026.
set "BUNDLE=%CARGO_TARGET_DIR%\release\bundle"
if not exist "%BUNDLE%" set "BUNDLE=%ROOT%\frontend\src-tauri\target\release\bundle"
echo Artefatos: "%BUNDLE%"
endlocal
exit /b 0
