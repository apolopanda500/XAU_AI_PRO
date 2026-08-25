// XAU_AI_PRO v1.2.0
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

   Print("======================================");
   Print("XAU_AI_PRO INITIALIZING");
   Print("======================================");

   if(!InitCompatibility())
   {
      Print("Compatibility FAILED");
      return false;
   }

   SystemReady=true;

   Print("======================================");
   Print("SYSTEM READY");
   Print("======================================");

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

   Print("======================================");
   Print("SYSTEM CLOSED");
   Print("======================================");

}

#endif