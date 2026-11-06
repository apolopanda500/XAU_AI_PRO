// XAU_AI_PRO v1.2.9
#ifndef SYSTEMMANAGER_MQH
#define SYSTEMMANAGER_MQH

#include "CompatibilityManager.mqh"

//==================================================
// SYSTEM STATUS
//==================================================

bool SystemReady=false;

//==================================================
// INIT SYSTEM
//==================================================

bool InitSystem()
{

   // v1.2.88 (02/11/2026) - P1.75: "XAU_AI_PRO INITIALIZING" e "SYSTEM READY"
   // nao traziam valor nenhum e saiam 16 vezes por reload; o [START] e o
   // [INIT] system + signalcore OK ja dizem o mesmo com dados. A falha de
   // compatibilidade passa a sair com tag, para nao se perder a informacao.
   if(!InitCompatibility())
   {
      Print("[SYSTEM] FAIL | Compatibility FAILED");
      return false;
   }

   SystemReady=true;

   return true;

}

//==================================================
// STATUS
//==================================================

bool IsSystemReady()
{
   return SystemReady;
}

//==================================================
// SHUTDOWN
//==================================================

void ShutdownSystem()
{

   ReleaseSymbolManager();

   SystemReady=false;

   // v1.2.88 (02/11/2026) - P1.75: "SYSTEM CLOSED" saia 1x por instancia e nao
   // dizia nada que o [STOP] do OnDeinit nao diga com simbolo, motivo e equity.
}

#endif