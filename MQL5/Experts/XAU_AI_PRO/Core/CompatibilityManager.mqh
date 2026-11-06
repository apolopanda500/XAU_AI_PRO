// XAU_AI_PRO v1.2.9
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

   // v1.2.87 (02/11/2026) - P1.74: eram 16 linhas por arranque (256 num
   // reload de 16 graficos) para descrever a mesma conta. Passa a UMA.
   if(LogInicioDetalhe()) Print("[COMPAT] OK | ",GetBrokerName(),"/",GetBrokerServer(),
         " | TF entrada=",TimeFrameToString(GetEntryTF()),
         " trend=",TimeFrameToString(GetTrendTF()),
         " filtro=",TimeFrameToString(GetFilterTF()));

   return true;

}

#endif
