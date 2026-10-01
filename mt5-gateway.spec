# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_dynamic_libs

datas = []
binaries = []
# Docs/version.json e o que define GATEWAY_BUILD. Sem ele no pacote o gateway
# congelado cai no fallback hardcoded e o frontend recusa o bootstrap por
# identidade de build divergente.
datas.append(("Docs/version.json", "Docs"))
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
