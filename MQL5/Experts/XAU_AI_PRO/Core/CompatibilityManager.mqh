// XAU_AI_PRO v1.2.0
#ifndef COMPATIBILITYMANAGER_MQH
#define COMPATIBILITYMANAGER_MQH

#include "BrokerInfo.mqh"
#include "BrokerConfig.mqh"
#include "SymbolManager.mqh"
#include "PathManager.mqh"
#include "EnvironmentManager.mqh"
#include "TimeFrameManager.mqh"

//==================================================
// COMPATIBILITY MANAGER
//==================================================

bool InitCompatibility()
{

   Print("========================================");
   Print("XAU_AI_PRO COMPATIBILITY CHECK");
   Print("========================================");

   if(!InitBrokerInfo())
      return false;

   if(!InitEnvironment())
      return false;

   if(!InitPathManager())
      return false;

   if(!InitTimeFrames())
      return false;

   LoadBrokerSymbols();

   // Nota (v1.2.0): InitSymbolManager() agora e chamado uma unica vez
   // em InitializeModules() (XAU_AI_PRO.mq5), e nao aqui. Isso evita
   // a dupla resolucao de simbolos e permite o retry automatico quando
   // os simbolos ainda nao sincronizaram na abertura do terminal.

   Print("----------------------------------------");
   Print("Broker     : ",GetBrokerName());
   Print("Servidor   : ",GetBrokerServer());
   Print("Simbolos   : (inicializado em InitializeModules)");
   Print("Entrada TF : ",TimeFrameToString(GetEntryTF()));
   Print("Trend TF   : ",TimeFrameToString(GetTrendTF()));
   Print("Filtro TF  : ",TimeFrameToString(GetFilterTF()));
   Print("----------------------------------------");

   Print("Compatibility OK");

   return true;

}

#endif
