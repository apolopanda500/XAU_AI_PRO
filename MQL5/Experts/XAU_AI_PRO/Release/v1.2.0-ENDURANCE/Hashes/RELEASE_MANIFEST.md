# ============================================================
# XAU_AI_PRO v1.2.0 — ENDURANCE CANDIDATE MANIFEST (F4/1.2)
# Data: 2026-09-08 06:25 UTC
# Estado: ENDURANCE CANDIDATE (avalado por smoke PASS A/B + NORMAL_PROGRESS)
# ============================================================

[IDENTIFICACAO]
PRODUTO          = XAU_AI_PRO
VERSAO           = 1.2.0
BUILD            = endurance-candidate (watchdog LIVENESS vs PROGRESS funcional)
COMPILADOR       = MetaEditor MQL5 build 6182 (x64)
COMPILE          = 0 errors / 0 warnings
COMPILED_AT      = 2026-09-08 06:20 UTC (build final sin hook)
HOOK_SMOKE_RUN   = 7683044552102904285 (PASS_A=1, PASS_B=1, TICK_TIMEOUT=0, PRE_STALL_HEALTH_FAILURES=0, NORMAL_PROGRESS_PASS=1)

[HASHES — BUILD ENDURANCE CANDIDATE]
EX5              = eab9c4fc37c016f44f72100445d86ce47e127318e95835f60d849d1df3f43654
MQL5_SRC         = 725993ce07047583d3a29e2798efacbff4a400bfddd6305685b16a630829b47c
CONFIG_MQH       = a05e98a5a9c5743107a213a20d301577fea8ac784c3a349c4a4c3adeff7df5bc
HEALTH_MONITOR   = 80e1bc3cbfa0d7046860b830ca717bc71ccc50ca669711d844cd7cfd57a7ebf7
ADX_MQH          = b34df5e283fe9cd3672084e4b493a5265de33bb1429be6031538ee236480a334
MQLPROJ          = 36f3413ebd51de34f94f8b611a9cb0f2b56460346dc314a0527af1de84830588
SOURCES_FULL     = ver Hashes/SOURCES_SHA256.txt (SHA-256 de todos los .mq5/.mqh/.mqproj del arbol)

[CHANGES vs BASELINE v1.2.0 (bloque F4/1.2 + previos no congelados)]
ADX              = fix F4/20.15: metricas unavailable/valid, sentinel -1.0, fail-open en consumidores
HEALTH_MONITOR   = LIVENESS vs PROGRESS: HealthMonitorProgress (post-UpdateDataset) separado de HealthMonitorHeartbeat (cada tick); g_wdLastProgress/g_wdProgressFails; HealthGetPipelineProgressTimeoutSec()
CONFIG           = input HealthPipelineProgressTimeout (0 = auto: 2x cadencia da vela, min HealthWatchdogInterval)
EA               = UpdateDataset() bool (progresso REAL = nova vela); OnTick chama HealthMonitorProgress SOLO con datasetProgressed==true (nunca por tick); HealthTestHook REMOVIDO tras smoke

[ARVORE]
EA/              = XAU_AI_PRO.ex5 (build candidate)
Config/          = XAU_AI_PRO.ENDURANCE.set (snapshot inputs = FASE_FINAL 20.5 + HealthPipelineProgressTimeout=0)
Hashes/          = este manifesto + SOURCES_SHA256.txt
Documentation/   = PROMOCAO_ENDURANCE.md

[CONFIG_REFERENCIA — SNAPSHOT]
SIMBOLO          = XAUUSD + 10 graficos M5 (EURUSD, USDBRL, AUDUSD, NZDUSD, USDCHF, USDSEK, GBPUSD, USDCAD, USDJPY, USDCNH)
TIMEFRAME        = M5
HEALTH           = EnableHealthMonitor=true | HealthCheckInterval=60s | HealthWatchdogInterval=120s (liveness) | HealthPipelineProgressTimeout=0 auto (=600s en M5) | EnableDataset=true
MAGIC            = 2026001

[NOTA]
El watchdog de progresso del pipeline queda FUNCIONAL en produccion: falla tras 3 checks sin avance real (nueva vela), recupera al reanudar. Timeout de progresso separado del liveness (no hereda 120s; auto 2x cadencia). Hook de test eliminado del arbol, include, configs y .ex5.