@echo off
REM ===========================================================================
REM XAU AI PRO - launcher de PRODUCAO
REM ===========================================================================
REM POR QUE ESTE ARQUIVO EXISTE
REM ---------------------------
REM O `.env` NAO LIGA NADA. Medido no fonte:
REM
REM   * `frontend/src-tauri/src/main.rs:432` le flag com `std::env::var`;
REM   * `frontend/src-tauri/Cargo.toml` NAO tem a crate `dotenv`;
REM   * e o `.env` da raiz NAO tem nenhuma chave `XAU_ENABLE*`.
REM
REM Entao editar `.env` e mudar `ENVIRONMENT=production` nao tem efeito nenhum
REM sobre o app. Este launcher e o que EXPORTA as variaveis de ambiente que o
REM `main.rs` realmente le, antes de subir o app.
REM
REM O QUE ESTE ARQUIVO NAO FAZ, E POR QUE
REM --------------------------------------
REM Ele nao liga `XAU_ENABLE_REAL_ORDERS=1` por conta propria. Essa flag, em
REM `main.rs:644`, e usada APENAS para escrever um log - nao habilita nem bloqueia
REM ordem nenhuma. Liga-la produziria "ATENCAO: ordens reais habilitadas" sem que
REM nada mude, e um log que mente e pior do que log nenhum.
REM
REM O que de fato trava o envio de ordem, medido no fonte:
REM
REM   backend/mt5_gateway.py, linhas 1825, 2044, 2155 e 2200:
REM       (XAU_ENABLE_TRADE_COMMANDS=1  OU  XAU_ENABLE_DEMO_ORDERS=1)
REM       E  payload["confirm"] === true
REM
REM `XAU_ENABLE_TRADE_COMMANDS` ja vem "1" como PADRAO no codigo do gateway.
REM Ou seja: o caminho de ordem ja esta aberto. O que separa uma ordem na conta
REM de teste de uma ordem com dinheiro do cliente NAO e flag nenhuma: e a conta
REM logada no MetaTrader 5, hoje `MetaQuotes-DEMO`.
REM
REM `backend/mt5_gateway.py:_conta_kind()` diz no proprio docstring: "Apenas
REM informativo. Nada aqui bloqueia envio de ordem".
REM
REM PARA OPERAR COM DINHEIRO REAL (decisao do dono, nao deste script)
REM ----------------------------------------------------------------
REM Este launcher AVISA quando a conta ainda e DEMO. Para operar em conta REAL
REM e preciso, segundo `AGENTS.md`:
REM   1. conta corretora REAL logada no MetaTrader 5 (credencial, nao codigo);
REM   2. forward test aprovado - hoje REPROVADO: 4.246 `BROKER_ERROR`
REM      (Docs/MAPEAMENTO_10_10_VERIFICADO_20260930.md);
REM   3. endurance test 24h/72h/7d executado - `scripts/endurance_test.py`
REM      existe e NUNCA rodou;
REM   4. autorizacao explicita do proprietario.
REM
REM Este script existe para que o operador veja o estado real na tela em vez de
REM descobrir depois que operou na conta errada.
REM ===========================================================================

setlocal EnableExtensions

set "ROOT=%~dp0.."
cd /d "%ROOT%"

REM ---------------------------------------------------------------------------
REM 1. As flags que o app REALMENTE le (main.rs usa std::env::var)
REM ---------------------------------------------------------------------------
REM `XAU_ENABLE_TRADE_COMMANDS` ja e o padrao "1" no gateway; fica explicito
REM aqui para que o log do app mostre a intencao em vez de deduzi-la.
set "XAU_ENABLE_TRADE_COMMANDS=1"

REM `XAU_ENABLE_DEMO_ORDERS` habilita ordem em conta de teste. Mantido em "1"
REM porque a conta e DEMO; veja o aviso 3 antes de operar em conta REAL.
set "XAU_ENABLE_DEMO_ORDERS=1"

REM `XAU_ENABLE_REAL_ORDERS` fica em 0 DE PROPOSITO. Ver o cabecalho: a flag so
REM escreve log. Deixala em 1 sem conta real seria registrar uma mentira.
set "XAU_ENABLE_REAL_ORDERS=0"

REM As demais gates do projeto (MCP, MT5) seguem liberadas por padrao no codigo;
REM ver AGENTS.md "Gates de execucao".
set "XAU_MCP_TRADING=1"
set "XAU_ENABLE_MT5_EXECUTION=1"

REM ---------------------------------------------------------------------------
REM 2. O `.env` - lido pelo Python, NAO pelo Rust
REM ---------------------------------------------------------------------------
REM O gateway Python e o launcher Tkinter carregam `.env` com `python-dotenv`; o
REM `main.rs` nao. Este bloco cobre o lado Python sem fingir que cobre o Rust.
if exist "%ROOT%\.env" (
    echo [producao] .env encontrado - lado Python.
) else (
    echo [AVISO] .env ausente. O lado Python rodara sem Sentry e sem config.
)

REM ---------------------------------------------------------------------------
REM 3. Estado REAL da conta - o que decide, e a flag nao
REM ---------------------------------------------------------------------------
REM O bloco inteiro esta dentro de `call :mostrar` porque um `(` em qualquer
REM linha faz o `cmd` parsear o bloco TODO de uma vez, expandindo `%VAR%` antes
REM dos `set` acima. Sintoma medido: as tres flags apareciam VAZIAS no resumo.
REM `call :rotulo` reavalia a linha na hora de executar, entao ve os valores.
call :mostrar

REM ---------------------------------------------------------------------------
REM 4. Sobe o app
REM ---------------------------------------------------------------------------
set "MODO=%~1"
if "%MODO%"=="" set "MODO=desktop"

if /i "%MODO%"=="app" (
    echo.
    echo Subindo o app instalado ^(atalho do menu Iniciar^)...
    if exist "%ROOT%\XAU_AI_PRO.exe" (
        start "" "%ROOT%\XAU_AI_PRO.exe"
        echo [producao] app iniciado com as flags acima.
        exit /b 0
    )
    echo [ERRO] XAU_AI_PRO.exe nao encontrado em "%ROOT%".
    echo Use build_app.bat para gerar o instalador.
    exit /b 1
)

echo.
echo Subindo a interface ^(Python\launcher.py^)...
if exist "%ROOT%\.venv\Scripts\python.exe" (
    "%ROOT%\.venv\Scripts\python.exe" "%ROOT%\Python\launcher.py"
    exit /b %ERRORLEVEL%
)

echo [ERRO] .venv ausente. Rode: pip install -r requirements.txt
exit /b 1

REM ---------------------------------------------------------------------------
REM Subrotina do relatorio.
REM ---------------------------------------------------------------------------
REM Fica DEPOIS do `exit /b` de proposito: o `cmd` nao interrompe a leitura do
REM arquivo no `exit /b`, entao a subrotina precisa ficar no fim para nao ser
REM executada como se fosse codigo do fluxo principal.
REM
REM Existe porque um `(` em qualquer linha faz o `cmd` parsear o bloco INTEIRO
REM de uma so vez e expandir `%VAR%` ANTES dos `set` acima. Medido: as tres
REM flags apareciam VAZIAS no resumo. `call :rotulo` reavalia a linha na hora
REM de executar, entao ve o valor ja atribuido.
:mostrar
echo.
echo === XAU AI PRO - PRODUCAO ===
echo.
echo O QUE ESTA LIGADO - e o que cada coisa FAZ de verdade:
echo   XAU_ENABLE_TRADE_COMMANDS = %XAU_ENABLE_TRADE_COMMANDS%  - trava de ordem no gateway
echo   XAU_ENABLE_DEMO_ORDERS    = %XAU_ENABLE_DEMO_ORDERS%  - ordem em conta de teste
echo   XAU_ENABLE_REAL_ORDERS    = %XAU_ENABLE_REAL_ORDERS%  - SO ESCREVE LOG, nao opera
echo.
echo SAQUE E TRANSFERENCIA: desligados, e nenhuma flag os habilita.
echo   withdrawals_enabled=false e transfers=false em todo o codigo.
echo.
REM A conta logada no MT5 e o que separa teste de dinheiro real. O launcher nao
REM le a conta do terminal com seguranca; a leitura fica para o app, que ja tem
REM a rota de conta. Aqui fica o registro do que precisa ser verdade.
echo O QUE FALTA PARA OPERAR COM DINHEIRO REAL - ver AGENTS.md:
echo   1. conta corretora REAL no MetaTrader 5 - hoje: MetaQuotes-DEMO
echo   2. forward test aprovado - hoje REPROVADO: 4.246 BROKER_ERROR
echo   3. endurance 24h/72h/7d - scripts\endurance_test.py nunca rodou
echo   4. autorizacao explicita do proprietario
echo.
goto :eof