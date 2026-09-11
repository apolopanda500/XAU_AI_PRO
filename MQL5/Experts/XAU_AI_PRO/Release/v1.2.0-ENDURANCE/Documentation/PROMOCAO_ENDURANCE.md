# XAU_AI_PRO v1.2.0 — PROMOCIÓN A CANDIDATO DE ENDURANCE

Fecha: 2026-09-08 06:25 UTC | Build: MetaEditor 6182, 0 errores / 0 warnings

## Decisión
Se corrigió producción ANTES del freeze (opción 1 del usuario): el watchdog de
progresso del pipeline estaba inerte (HealthMonitorProgress se llamaba a cada
tick y reseteaba g_wdProgressFails). NO se congela un watchdog inerte.

## Fix de producción (F4/1.2)
1. `UpdateDataset()` → `bool`: retorna TRUE solo cuando hay progresso REAL
   (nueva vela detectada vía `candle==LastDatasetBar`). Nunca por tick.
2. `OnTick` → `bool datasetProgressed = UpdateDataset();` y
   `if(EnableHealthMonitor && EnableDataset && datasetProgressed)`
   → `HealthMonitorProgress("CSV"/"JSON"/"PYTHON")` avanza solo con progresso.
3. Timeout separado: `HealthPipelineProgressTimeout` (0 = auto) en
   `HealthMonitorCheckHeartbeatModule` para el canal de progresso; el liveness
   conserva `HealthWatchdogInterval=120s`.
   - Auto: 2× cadencia de velas del timeframe (M1→120s, M5→600s, H1→7200s),
     mínimo HealthWatchdogInterval → nunca falsos HEALTH_FAILURE por cadencia.

## Validación (smoke hook, run 7683044552102904285 — XAUUSD M5, 2 días)
| Criterio | Resultado |
|---|---|
| Property A — stall del pipeline → 3 faltas → HEALTH FAILURE | PASS_A=1 |
| Property B — recovery real del watchdog al reanudar | PASS_B=1 |
| Tick timeout | 0 |
| Falsos HEALTH_FAILURE pre-stall | 0 |
| NORMAL_PROGRESS_PASS (cadencia normal sin stall) | 1 |

## Limpieza post-smoke
- HealthTestHook.mqh eliminado (árbol + include + llamada OnTick + flag)
- TEST_HOOK.ini / TEST_HOOK.set eliminados
- Recompile final: 0 errores / 0 warnings; verificación de 0 referencias al hook
- Diff revisado: sin código de hook, ADX fix presente, LIVENESS/PROGRESS separados,
  progress no renovado por tick

## Artefactos (carpeta Release/v1.2.0-ENDURANCE)
- EA/XAU_AI_PRO.ex5 — build candidato (sha256 eab9c4fc...43654)
- Hashes/RELEASE_MANIFEST.md + Hashes/SOURCES_SHA256.txt — registro de hashes
- Config/XAU_AI_PRO.ENDURANCE.set — snapshot de inputs de producción

## Pendiente (requiere entorno/T0)
1. Reload controlado en demo/forward (11 gráficos M5)
2. Confirmación 7/7 de charts+EA
3. Nuevo T0 → ventanas 24H / 72H / 7D con watchdog de progresso activo