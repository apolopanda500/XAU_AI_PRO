// XAU_AI_PRO v1.2.0
#ifndef SYMBOLVALIDATOR_MQH
#define SYMBOLVALIDATOR_MQH


#include "Config.mqh"

//==================================================
// INIT
//==================================================

void InitSymbolValidator()
{
   // reservado para futuras regras
}



//==================================================
// VALIDAÇÃO DE EXECUÇÃO REAL
//==================================================

bool ValidateSymbol(
   const string symbol,
   double lot,
   double slPoints
)
{

   if(symbol == "")
      return false;



   // símbolo disponível
   if(!SymbolInfoInteger(symbol,SYMBOL_SELECT))
      return false;



   // lote
   if(lot <= 0)
      return false;



   // stop
   if(slPoints <= 0)
      return false;



   double minLot =
      SymbolInfoDouble(
         symbol,
         SYMBOL_VOLUME_MIN
      );


   double maxLot =
      SymbolInfoDouble(
         symbol,
         SYMBOL_VOLUME_MAX
      );


   double stepLot =
      SymbolInfoDouble(
         symbol,
         SYMBOL_VOLUME_STEP
      );



   if(lot < minLot || lot > maxLot)
      return false;



   // valida múltiplo do lote
   double normalized =
      MathFloor(lot/stepLot)*stepLot;


   if(normalized != lot)
      return false;



   // spread
   double ask =
      SymbolInfoDouble(
         symbol,
         SYMBOL_ASK
      );


   double bid =
      SymbolInfoDouble(
         symbol,
         SYMBOL_BID
      );


   double point =
      SymbolInfoDouble(
         symbol,
         SYMBOL_POINT
      );



   if(ask <= 0 || bid <= 0 || point <= 0)
      return false;



   double spread =
      (ask-bid)/point;



   if(spread > GetMaxSpread(symbol))
      return false;



   // stops mínimos do broker
   long stopLevel =
      SymbolInfoInteger(
         symbol,
         SYMBOL_TRADE_STOPS_LEVEL
      );



   if(slPoints < stopLevel)
   {
      Print(
      "SL menor que StopLevel do broker"
      );

      return false;
   }



   return true;

}



#endif
