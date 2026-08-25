//+------------------------------------------------------------------+
//|                                             FailureMode.mqh     |
//|                                     XAU_AI_PRO - Hardening E12  |
//|                  Revival Machine: ERROR->DETECT->CLASSIFY->SAFE |
//|                             ->RECOVERY->REVALIDATE->RESUME      |
//+------------------------------------------------------------------+
// ETAPA 12 (3/12) - RESILIENCIA / RECUPERACAO
//
// Maquina de estados de resiliencia do EA. Converte falhas criticas
// (broker desconectado, IA fora, execucion invalida) em um modo seguro
// e orquesta la recuperacion automatica:
//
//   NORMAL                              (operational)
//     | falha critica
//     v
//   SAFE_MODE                           (bloquea novas entradas)
//     | cooldown transcurrido
//     v
//   RECOVERY                            (espera reconexion completa)
//     | checks OK (revalidate)
//     v
//   REVALIDATED
//     | transicion automática
//     v
//   RESUME / NORMAL                     (operational de novo)
//
// PRINCIPIO: SAFE_MODE bloque NOVAS ENTRADAS, mas NUNCA interrompe a
// gestion de posiciones abertas (SL/TP/close) - isso é responsabilidad
// del OnTick/pipeline que llaman IsOperational() para entradas.
//+------------------------------------------------------------------+

#ifndef FAILURE_MODE_MQH
#define FAILURE_MODE_MQH

#include "../Core/Config.mqh"

//==================================================
// ENUM MODE
//==================================================
enum FailureModeState
{
   MODE_NORMAL   = 0,
   MODE_SAFE     = 1,
   MODE_RECOVERY = 2,
   MODE_REVALIDATE = 3,
   MODE_RESUME   = 4
};

//==================================================
// CONFIG (valores por defecto; cambia in run time)
//==================================================
#define FAILURE_SAFE_COOLDOWN_SEC      60     // tempo minimo em SAFE antes de tentar RECOVERY
#define FAILURE_RECOVERY_COOLDOWN_SEC 30     // tempo minimo en RECOVERY antes de validar
#define FAILURE_MAX_SAFE_CYCLES       5      // max ciclos SAFE continuos ante de pedir intervencion
#define FAILURE_REVALIDATE_WAIT_SEC   10     // espera corta na REVALIDATE

//==================================================
// ESTADO GLOBAL DEL MODO DE FALL
//==================================================
FailureModeState g_failureMode          = MODE_NORMAL;
string           g_failureReason        = "";
datetime         g_failureStateAt       = 0;
int              g_failureSafeCount     = 0;   // entradas repetidas en SAFE
bool             g_failureRevalidateOK  = false;

//==================================================
// CLASSIFY - Converte un evento de falla en modo segur
//==================================================
// isCritical = true  -> broker desconectado, IA offline, falla letal
// isCritical = false -> degradacion (dataset, colateral), no SAFE
void FailureClassify(const bool isCritical, const string reason)
{
   if(!isCritical)
   {
      // Degradacion suave: NO activa SAFE, solo log.
      Print("[FAILMODE] Non-critical issue: ", reason);
      return;
   }

   // Entra/en SAFE si el estado actual no es ya SAFE/RECOVERY
   if(g_failureMode != MODE_SAFE && g_failureMode != MODE_RECOVERY)
   {
      g_failureMode   = MODE_SAFE;
      g_failureReason = reason;
      g_failureStateAt = TimeCurrent();
      g_failureSafeCount = 0;
      PrintFormat("[FAILURE] ENTER SAFE_MODE | reason=%s", reason);
      return;
   }

   // Ya dentro de SAFE/RECOVERY: contabiliza repeticion
   g_failureSafeCount++;
   if(g_failureSafeCount < FAILURE_MAX_SAFE_CYCLES)
   {
      PrintFormat("[FAILURE] Reclassified while %s | reason=%s", GetFailureStateString(), reason);
   }
   else
   {
      Print("[FAILURE] Repetidas fallas en SAFE - posible intervencion manual necesaria");
   }
}

//==================================================
// STRING DO ESTADO
//==================================================
string GetFailureStateString()
{
   switch(g_failureMode)
   {
      case MODE_NORMAL:     return "NORMAL";
      case MODE_SAFE:       return "SAFE_MODE";
      case MODE_RECOVERY:   return "RECOVERY";
      case MODE_REVALIDATE: return "REVALIDATE";
      case MODE_RESUME:     return "RESUME";
   }
   return "UNKNOWN";
}

//==================================================
// CHECK RECONEXION - usada na RECOVERY/REVALIDATE
//==================================================
bool CanResumeFromSafe()
{
   // Verificacion de reconexion de BAJO NIVEL:
   // 1) Terminal MT5 conectado
   // 2) Trading permitido por la cuenta
   if(TerminalInfoInteger(TERMINAL_CONNECTED) == 0)
      return false;
   if(AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) == 0)
      return false;

   return true;
}

//==================================================================
// RUN - orquesta la maquina de estados (chamar cada timer/bar)
//==================================================================
void FailureModeRun()
{
   // -----------------------------------------------------
   // Si estamos en SAFE_MODE
   // -----------------------------------------------------
   if(g_failureMode == MODE_SAFE)
   {
      // espera cooldown: SAFE -> RECOVERY
      if(TimeCurrent() - g_failureStateAt >= FAILURE_SAFE_COOLDOWN_SEC)
      {
         g_failureStateAt = TimeCurrent();
         g_failureMode    = MODE_RECOVERY;
         Print("[FAILURE] STATE_SAFE->RECOVERY (cooldown elapsed)");
      }
      return;
   }

   // -----------------------------------------------------
   // RECOVERY
   // -----------------------------------------------------
   if(g_failureMode == MODE_RECOVERY)
   {
      if(TimeCurrent() - g_failureStateAt >= FAILURE_RECOVERY_COOLDOWN_SEC)
      {
         if(CanResumeFromSafe())
         {
            g_failureMode         = MODE_REVALIDATE;
            g_failureRevalidateOK = false;
            g_failureStateAt      = TimeCurrent();
            Print("[FAILURE] STATE_RECOVERY->REVALIDATE (connections restored)");
         }
         else
         {
            Print("[FAILURE] RECOVERY: broker/connections permanent");
         }
      }
      return;
   }

   // -----------------------------------------------------
   // REVALIDATE
   // -----------------------------------------------------
   if(g_failureMode == MODE_REVALIDATE)
   {
      if(TimeCurrent() - g_failureStateAt >= FAILURE_REVALIDATE_WAIT_SEC)
      {
         bool conexionOK = CanResumeFromSafe();
         bool iaOK       = CheckAICoreAvailable();

         if(conexionOK && iaOK)
         {
            g_failureMode         = MODE_RESUME;
            g_failureRevalidateOK = true;
            g_failureStateAt      = TimeCurrent();
            Print("[FAILURE] STATE_REVALIDATE->RESUME (all systems validated)");
         }
         else
         {
            g_failureMode   = MODE_SAFE;
            g_failureReason = "Revalidation failed";
            g_failureStateAt = TimeCurrent();
            Print("[FAILURE] Revalidation failed - returning to SAFE");
         }
      }
      return;
   }

   // -----------------------------------------------------
   // RESUME -> NORMAL (solo una vez el cooldown)
   // -----------------------------------------------------
   if(g_failureMode == MODE_RESUME && g_failureRevalidateOK)
   {
      if(TimeCurrent() - g_failureStateAt >= FAILURE_RECOVERY_COOLDOWN_SEC)
      {
         g_failureMode         = MODE_NORMAL;
         g_failureReason        = "";
         g_failureSafeCount     = 0;
         g_failureStateAt       = 0;
         Print("[FAILURE] STATE_RESUME->NORMAL (fully operational)");
      }
   }
}

//====================================================
// MANUAL SAFE ENTRY (call from command/kill switch)
//====================================================
void FailureModeEnterSafe(string reason)
{
   g_failureMode       = MODE_SAFE;
   g_failureReason     = reason;
   g_failureStateAt    = TimeCurrent();
   g_failureSafeCount  = 0;
   PrintFormat("[FAILURE] MANUAL SAFE | reason=%s", reason);
}

//====================================================
// IS OPERATIONAL - (bloque novas entradas, nao gestion)
//====================================================
bool FailureModeOperational()
{
   // Solo NORMAL/RESUME permiten nuevas entradas de trading
   return (g_failureMode == MODE_NORMAL || g_failureMode == MODE_RESUME);
}

//========================================================
// SET FAILURE MODE (para integraccion con RecoveryManager)
//========================================================
void FailureModeFeed(bool brokerOk, bool aiOk)
{
   // Caso critico: broker desconectado O IA indisponible
   if(!brokerOk)
   {
      FailureClassify(true, "Broker/connection unavailable");
   }
   else if(!aiOk && g_failureMode == MODE_NORMAL)
   {
      FailureClassify(true, "AI core unavailable");
   }
   else if(brokerOk && aiOk)
   {
      // Si ya estabamos en modo seguro y todo volvio, RESUME avanza no RUN
   }
}

//====================================================
// GET SUMMARY
//====================================================
string GetFailureSummary()
{
   return StringFormat("FailureMode | State=%s | Reason=%s | SafeCycles=%d | Entered=%s",
      GetFailureStateString(),
      g_failureReason,
      g_failureSafeCount,
      (g_failureStateAt > 0 ? TimeToString(g_failureStateAt, TIME_DATE|TIME_MINUTES) : "None"));
}

//=====================================================
// AI CORE AVAILABILITY (integra con RecoveryManager)
//=====================================================
bool CheckAICoreAvailable()
{
   if(!RequireAIJSON)
      return true;
   if(MQLInfoInteger(MQL_TESTER) != 0)
      return true;

   string fileName = "Data\\prediction_" + _Symbol + ".json";
   return FileIsExist(fileName, 0);
}

#endif // FAILURE_MODE_MQH