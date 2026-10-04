# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_dynamic_libs

datas = []
binaries = []
# Docs/version.json e o que define GATEWAY_BUILD. Sem ele no pacote o gateway
# congelado cai no fallback hardcoded e o frontend recusa o bootstrap por
# identidade de build divergente.
datas.append(("Docs/version.json", "Docs"))

# MODELOS MULTI (2026-10-02)
#
# Os `.pkl` sao carregados por `ai_inference` em TEMPO DE EXECUCAO com caminho
# relativo a raiz do pacote. O PyInstaller so descobre modulos importados; arquivo
# aberto por `joblib.load()` ele nao enxerga. Sem estas linhas o instalador sai
# SEM os modelos MULTI e o app instalado volta a dizer "modelos nao carregam" —
# sem erro visivel, porque nada quebra: o arquivo simplesmente nao existe.
#
# O caminho e `frontend/src-tauri/Python/models` e NAO `Python/models`: e ali que
# `train_multi.MODELOS_DIR` publica (linha 79) e onde os 36 modelos unitarios ja
# moram. A pasta da raiz tem 72 arquivos e nenhum `MULTI_*` — apontar para ela
# seria compilar sem erro e entregar um instalador sem os 3 modelos.
datas.append(("frontend/src-tauri/Python/models", "Python/models"))
datas += collect_data_files('MetaTrader5')
binaries += collect_dynamic_libs('MetaTrader5')
numpy_binaries = collect_dynamic_libs('numpy')
binaries += numpy_binaries


a = Analysis(
    # ENTRYPOINT CORRETO
    # ==================
    # Era `backend/fastapi_gateway.py`. ERRADO: o app desktop executa este
    # binario na porta 9001, e quem sobe 9001 e o `main()` de
    # `backend/mt5_gateway.py` (ThreadingHTTPServer). O `fastapi_gateway` e o
    # servidor HOSPEDADO (Vercel/Nitro), nao o local.
    #
    # Empacotar o arquivo errado faz o `.exe` nascer sem `mt5_gateway` inteiro:
    # o que o Tauri lanca em `bridge/mt5-gateway.exe` nao e o gateway que
    # responde em 9001. Por isso o app instalado mostrava "modelos nao
    # carregam" e "erro no ciclo" sem causa visivel.
    ['backend/mt5_gateway.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    # `hiddenimports` NAO e opcional aqui.
    #
    # PyInstaller so segue import de nivel superior. Em `fastapi_gateway.py` os
    # imports de `mt5_gateway`, `auto_engine` e `gateway_server` estao DENTRO
    # de funcao (`from backend.mt5_gateway import _mt5_candles` na linha 288),
    # que e o padrao do projeto para nao pagar o custo do MT5 no import. O
    # analizador nao enxerga esses e deixa os modulos de fora do pacote.
    #
    # Sintoma observado em 30/09/2026: o app instalado tinha
    # `fastapi_gateway` mas nao `market_access`, `gateway_server` nem o motor —
    # e a tela mostrava "modelos nao carregam" e "erro no ciclo" sem causa.
    #
    # `ai_inference` entra pelo mesmo motivo: e lido por `auto_engine`.
    hiddenimports=[
        'MetaTrader5', 'numpy', 'fastapi', 'uvicorn',
        'uvicorn.logging', 'uvicorn.loops.auto', 'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets.auto', 'pydantic', 'starlette',
        # pacotes que o app usa e o analisador nao ve
        'backend.mt5_gateway',
        'backend.auto_engine',
        'backend.gateway_server',
        'backend.market_access',
        'backend.ai_inference',
        'backend.universal_router',
        'backend.connection_service',
        'backend.connection_store',
        'backend.intent_log',
        'backend.audit_log',
        'backend.plano_gate',
        'backend.risk_gate',
        # `latencia` entra pelo mesmo motivo dos acima: a rota `/api/latencia`
        # importa DENTRO do handler (`from backend import latencia as _`),
        # que o analisador nao enxerga. Sem esta linha o gateway congelado
        # responde 404 na rota — e o teste `test_nenhum_modulo_do_backend_fica_
        # de_fora_do_bundle` reprova, que e exatamente para onde isto aponta.
        'backend.latencia',
        # METAS E TRAVAS DO VIP (2026-10-02)
        #
        # Estes dois NAO entram sozinhos pelo mesmo motivo acima: o
        # `plano_gate` importa `subscriptions` dentro da funcao, e o novo
        # `acesso` importa `metas_vip` e `vip_progress` tambem dentro das
        # funcoes. Sem a lista, o PyInstaller empacota o `.exe` sem eles e o
        # app instalado sobe sem a arvore de acesso — que foi exatamente o que
        # aconteceu na primeira instalacao deste ciclo: `metas_vip` e `acesso`
        # ausentes do bundle, e a tela sem VIP funcional.
        'backend.metas_vip',
        'backend.acesso',
        'backend.vip_progress',
        # MODULOS QUE JÁ ESTAVAM DE FORA (achado por tests/test_spec_gateway.py)
        #
        # Este bloco foi escrito depois de `test_nenhum_modulo_do_backend_fica_
        # de_fora_do_bundle` reprovar com 14 nomes. Os quatro `*_client` sao
        # excecao: vem por import de nivel superior e o PyInstaller pega sozinho
        # (estao em IMPORTADOS_NO_TOPO, no teste).
        #
        # Os de execucao importam os clients DENTRO de funcao, entao nao entram
        # sozinhos — e sem eles o `UniversalRouter` cai no caminho unico do MT5.
        # `exchange_execution` e `reconciliation` sao o que o motor usa para
        # fechar posicao em corretora de exchange.
        'backend.mt5_execution',
        'backend.exchange_execution',
        'backend.binance_execution',
        'backend.bybit_execution',
        'backend.mexc_execution',
        'backend.okx_execution',
        'backend.reconciliation',
        'backend.execution_receipts',
        'backend.chart_attach',
        'backend.fastapi_gateway',
        # NORMALIZACAO DE PAR (2026-10-02)
        #
        # `exchange_symbols` e importado DENTRO de `_symbol()` dos quatro
        # clientes, entao o PyInstaller nao ve. Sem ele aqui, o app instalado
        # sobe com o `.upper()` antigo e volta a recusar par com HTTP 400.
        # Foi o `test_spec_gateway.py` que reprovou e apontou este nome.
        'backend.exchange_symbols',
        # CLASSES DE ATIVO (2026-10-02)
        #
        # `asset_classes` classifica CRYPTO / FIAT / METALS e recusa simbolo
        # invalido. Tambem importado dentro de funcao, entao so o `.spec` o
        # coloca no executavel. Sem ele, `classe_de` cai em `OUTROS` no app
        # instalado e a progressao VIP perde a separacao por grupo.
        'backend.asset_classes',
        # SIMBOLOS E ALIAS (2026-10-04)
        #
        # `symbols` e a fonte unica do simbolo canonico (importado dentro
        # de funcao em `ai_inference` e `broker_registry`); `symbol_aliases`
        # resolve modelo -> corretora (`XAUUSD` -> `GOLD` na XM) no motor.
        # Sem os dois, o app instalado volta a nao achar modelo para par
        # de exchange e a pedir `XAUUSD` a XM que so tem `GOLD`.
        'backend.symbols',
        'backend.symbol_aliases',
        'backend.watchdog',
        'backend.guardian_engine',
        'backend.persistent_queue',
        'backend.trading_mcp',
        'backend.copilot',
        'backend.copilot_data',
        'backend.backtest',
        'backend.broker_registry',
        'backend.asset_registry',
        'backend.universal_contracts',
        'backend.remote_auth',
        'backend.remote_gateway',
        'backend.third_party_ea',
        'backend.ea_map',
        'backend.ea_manager',
        'Python.model_registry',
        'Python.ai.train_v2',
        'pandas', 'sklearn', 'joblib', 'requests',
        'mexc_client', 'binance_client', 'bybit_client', 'okx_client',
        'mexc_execution', 'binance_execution', 'bybit_execution', 'okx_execution',
        'mt5_execution', 'exchange_execution',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='mt5-gateway',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='mt5-gateway',
)
