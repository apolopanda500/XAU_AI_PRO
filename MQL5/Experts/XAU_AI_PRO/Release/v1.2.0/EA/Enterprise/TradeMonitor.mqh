// XAU_AI_PRO v1.2.0
//+------------------------------------------------------------------+
//|                                                   TradeMonitor.mqh|
//|                         XAU_AI_PRO - Enterprise / Multi-Symbol   |
//+------------------------------------------------------------------+
#ifndef TRADEMONITOR_MQH
#define TRADEMONITOR_MQH

#include "../Core/Config.mqh"

//==================================================
// ESTADO
//==================================================

bool TradeMonitorInitialized = false;

int TradeMonitorOpenPositions = 0;
int TradeMonitorTotalTrades   = 0;
int TradeMonitorWins          = 0;
int TradeMonitorLosses        = 0;

double TradeMonitorProfit      = 0.0;
double TradeMonitorGrossProfit = 0.0;
double TradeMonitorGrossLoss   = 0.0;

datetime TradeMonitorLastUpdate = 0;


//==================================================
// INICIALIZAÇÃO
//==================================================

void TradeMonitorInit()
{
   TradeMonitorInitialized = true;

   TradeMonitorOpenPositions = 0;
   TradeMonitorTotalTrades   = 0;
   TradeMonitorWins          = 0;
   TradeMonitorLosses        = 0;

   TradeMonitorProfit      = 0.0;
   TradeMonitorGrossProfit = 0.0;
   TradeMonitorGrossLoss   = 0.0;

   TradeMonitorLastUpdate = TimeCurrent();

   Print("[TRADE MONITOR] Inicializado");
}


//==================================================
// VERIFICA POSIÇÃO DO EA
//==================================================

bool TradeMonitorIsOurPosition(ulong ticket)
{
   if(ticket == 0)
      return false;

   if(!PositionSelectByTicket(ticket))
      return false;

   long magic =
      PositionGetInteger(
         POSITION_MAGIC
      );

   if(magic != MagicNumber)
      return false;

   return true;
}


//==================================================
// CONTAGEM DE POSIÇÕES
//==================================================

int TradeMonitorCountPositions()
{
   if(!TradeMonitorInitialized)
      TradeMonitorInit();

   int count = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket =
         PositionGetTicket(i);

      if(!TradeMonitorIsOurPosition(ticket))
         continue;

      count++;
   }

   TradeMonitorOpenPositions = count;

   return count;
}


//==================================================
// CONTAGEM POR SYMBOL
//==================================================

int TradeMonitorCountSymbol(
   string symbol
)
{
   if(symbol == "")
      return 0;

   int count = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket =
         PositionGetTicket(i);

      if(!TradeMonitorIsOurPosition(ticket))
         continue;

      string positionSymbol =
         PositionGetString(
            POSITION_SYMBOL
         );

      if(positionSymbol != symbol)
         continue;

      count++;
   }

   return count;
}


//==================================================
// LUCRO ABERTO
//==================================================

double TradeMonitorFloatingProfit()
{
   double profit = 0.0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket =
         PositionGetTicket(i);

      if(!TradeMonitorIsOurPosition(ticket))
         continue;

      profit +=
         PositionGetDouble(
            POSITION_PROFIT
         );

      profit +=
         PositionGetDouble(
            POSITION_SWAP
         );
   }

   return NormalizeDouble(
      profit,
      2
   );
}


//==================================================
// LUCRO ABERTO POR SYMBOL
//==================================================

double TradeMonitorSymbolProfit(
   string symbol
)
{
   if(symbol == "")
      return 0.0;

   double profit = 0.0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket =
         PositionGetTicket(i);

      if(!TradeMonitorIsOurPosition(ticket))
         continue;

      string positionSymbol =
         PositionGetString(
            POSITION_SYMBOL
         );

      if(positionSymbol != symbol)
         continue;

      profit +=
         PositionGetDouble(
            POSITION_PROFIT
         );

      profit +=
         PositionGetDouble(
            POSITION_SWAP
         );
   }

   return NormalizeDouble(
      profit,
      2
   );
}


//==================================================
// VOLUME ABERTO
//==================================================

double TradeMonitorOpenVolume()
{
   double volume = 0.0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket =
         PositionGetTicket(i);

      if(!TradeMonitorIsOurPosition(ticket))
         continue;

      volume +=
         PositionGetDouble(
            POSITION_VOLUME
         );
   }

   return NormalizeDouble(
      volume,
      8
   );
}


//==================================================
// VOLUME POR SYMBOL
//==================================================

double TradeMonitorSymbolVolume(
   string symbol
)
{
   if(symbol == "")
      return 0.0;

   double volume = 0.0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket =
         PositionGetTicket(i);

      if(!TradeMonitorIsOurPosition(ticket))
         continue;

      string positionSymbol =
         PositionGetString(
            POSITION_SYMBOL
         );

      if(positionSymbol != symbol)
         continue;

      volume +=
         PositionGetDouble(
            POSITION_VOLUME
         );
   }

   return NormalizeDouble(
      volume,
      8
   );
}


//==================================================
// ATUALIZA MONITOR
//==================================================

void TradeMonitorUpdate()
{
   if(!TradeMonitorInitialized)
      TradeMonitorInit();

   TradeMonitorCountPositions();

   TradeMonitorLastUpdate =
      TimeCurrent();
}


//==================================================
// REGISTRA TRADE
//==================================================

void TradeMonitorRegisterTrade(
   double profit
)
{
   TradeMonitorTotalTrades++;

   TradeMonitorProfit += profit;

   if(profit > 0.0)
   {
      TradeMonitorWins++;

      TradeMonitorGrossProfit +=
         profit;
   }
   else if(profit < 0.0)
   {
      TradeMonitorLosses++;

      TradeMonitorGrossLoss +=
         MathAbs(profit);
   }
}


//==================================================
// WIN RATE
//==================================================

double TradeMonitorWinRate()
{
   if(TradeMonitorTotalTrades <= 0)
      return 0.0;

   return NormalizeDouble(
      (
         (double)TradeMonitorWins /
         TradeMonitorTotalTrades
      ) * 100.0,
      2
   );
}


//==================================================
// PROFIT FACTOR
//==================================================

double TradeMonitorProfitFactor()
{
   if(TradeMonitorGrossLoss <= 0.0)
   {
      if(TradeMonitorGrossProfit > 0.0)
         return 999.0;

      return 0.0;
   }

   return NormalizeDouble(
      TradeMonitorGrossProfit /
      TradeMonitorGrossLoss,
      2
   );
}


//==================================================
// EQUITY
//==================================================

double TradeMonitorEquity()
{
   return AccountInfoDouble(
      ACCOUNT_EQUITY
   );
}


//==================================================
// BALANCE
//==================================================

double TradeMonitorBalance()
{
   return AccountInfoDouble(
      ACCOUNT_BALANCE
   );
}


//==================================================
// DRAWDOWN
//==================================================

double TradeMonitorDrawdown()
{
   double balance =
      TradeMonitorBalance();

   double equity =
      TradeMonitorEquity();

   if(balance <= 0.0)
      return 0.0;

   double dd =
      (
         (balance - equity) /
         balance
      ) * 100.0;

   if(dd < 0.0)
      dd = 0.0;

   return NormalizeDouble(
      dd,
      2
   );
}


//==================================================
// SPREAD
//==================================================

double TradeMonitorSpread(
   string symbol
)
{
   if(symbol == "")
      return 0.0;

   double point =
      SymbolInfoDouble(
         symbol,
         SYMBOL_POINT
      );

   double bid =
      SymbolInfoDouble(
         symbol,
         SYMBOL_BID
      );

   double ask =
      SymbolInfoDouble(
         symbol,
         SYMBOL_ASK
      );

   if(point <= 0.0)
      return 0.0;

   if(bid <= 0.0 || ask <= 0.0)
      return 0.0;

   return NormalizeDouble(
      (ask - bid) / point,
      1
   );
}


//==================================================
// STATUS DO SYMBOL
//==================================================

string TradeMonitorSymbolStatus(
   string symbol
)
{
   if(symbol == "")
      return "INVALID";

   int positions =
      TradeMonitorCountSymbol(
         symbol
      );

   double profit =
      TradeMonitorSymbolProfit(
         symbol
      );

   if(positions <= 0)
      return "NO POSITION";

   if(profit > 0.0)
      return "PROFIT";

   if(profit < 0.0)
      return "LOSS";

   return "BREAK EVEN";
}


//==================================================
// RESUMO GERAL
//==================================================

string TradeMonitorSummary()
{
   string text = "";

   text += "TRADE MONITOR\n";

   text +=
      "Positions: " +
      IntegerToString(
         TradeMonitorCountPositions()
      ) +
      "\n";

   text +=
      "Volume: " +
      DoubleToString(
         TradeMonitorOpenVolume(),
         2
      ) +
      "\n";

   text +=
      "Floating: " +
      DoubleToString(
         TradeMonitorFloatingProfit(),
         2
      ) +
      "\n";

   text +=
      "Trades: " +
      IntegerToString(
         TradeMonitorTotalTrades
      ) +
      "\n";

   text +=
      "Wins: " +
      IntegerToString(
         TradeMonitorWins
      ) +
      "\n";

   text +=
      "Losses: " +
      IntegerToString(
         TradeMonitorLosses
      ) +
      "\n";

   text +=
      "WinRate: " +
      DoubleToString(
         TradeMonitorWinRate(),
         2
      ) +
      "%\n";

   text +=
      "ProfitFactor: " +
      DoubleToString(
         TradeMonitorProfitFactor(),
         2
      ) +
      "\n";

   text +=
      "Drawdown: " +
      DoubleToString(
         TradeMonitorDrawdown(),
         2
      ) +
      "%";

   return text;
}


//==================================================
// SHUTDOWN
//==================================================

void TradeMonitorShutdown()
{
   TradeMonitorInitialized = false;

   Print(
      "[TRADE MONITOR] Finalizado"
   );
}


//==================================================
// END
//==================================================

#endif // TRADEMONITOR_MQH