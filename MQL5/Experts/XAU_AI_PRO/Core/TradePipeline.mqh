// XAU_AI_PRO v1.2.0
#ifndef TRADEPIPELINE_MQH
#define TRADEPIPELINE_MQH

#include "../Core/SymbolManager.mqh"
#include "../Core/MarketScanner.mqh"

//==================================================
// TRADE PIPELINE
// XAU_AI_PRO
// MULTI SYMBOL + DIAGNOSTIC
//==================================================

void RunTradePipeline()
{
   // Log de diagnostico 1x por minuto (evita spam a cada tick)
   static datetime lastLogTime = 0;
   datetime now = TimeCurrent();
   bool logOnce = (now - lastLogTime >= 60);
   if(logOnce)
      lastLogTime = now;

   int total=
      TotalSymbols();

   if(logOnce)
      Print(
         "[PIPELINE] INICIO | Symbols=",
         total
      );

   if(total<=0)
   {
      if(logOnce)
         Print(
            "[PIPELINE] BLOQUEADO | Nenhum símbolo configurado"
         );

      return;
   }


   for(int i=0; i<total; i++)
   {
      string symbol=
         GetTradeSymbol(i);

      if(symbol=="")
      {
         if(logOnce)
            Print(
               "[PIPELINE] Symbol vazio | Index=",
               i
            );

         continue;
      }


      if(logOnce)
         Print(
            "[PIPELINE] PROCESSANDO | Index=",
            i,
            " | Symbol=",
            symbol
         );


      if(!SymbolSelect(symbol,true))
      {
         if(logOnce)
            Print(
               "[PIPELINE] BLOQUEADO | SymbolSelect | ",
               symbol,
               " | Error=",
               GetLastError()
            );

         continue;
      }


      // ETAPA 11 - NEWS FILTER (bloqueia novas entradas, nao mata o EA)
      if(EnableNewsFilter && !CanTradeNews())
         continue;

      ProcessSymbol(symbol);
   }


   if(logOnce)
      Print(
         "[PIPELINE] FINALIZADO"
      );
}


//==================================================
// PROCESS SINGLE SYMBOL
//==================================================

bool RunTradePipelineSymbol(
   string symbol
)
{
   if(symbol=="")
      return false;


   if(!SymbolSelect(symbol,true))
   {
      Print(
         "[PIPELINE] SymbolSelect falhou | ",
         symbol,
         " | Error=",
         GetLastError()
      );

      return false;
   }


   ProcessSymbol(symbol);

   return true;
}

#endif
