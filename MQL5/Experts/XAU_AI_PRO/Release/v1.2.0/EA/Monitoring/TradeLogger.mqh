// XAU_AI_PRO v1.2.0
#ifndef TRADELOGGER_MQH
#define TRADELOGGER_MQH

#include "../Indicators/VolatilityFilter.mqh"
#include "../Indicators/ADX.mqh"
#include "../Indicators/RSI.mqh"

//==================================================
// TRADE LOGGER ENGINE
//==================================================

int tradeLoggerHandle = INVALID_HANDLE;


//==================================================
// INIT
//==================================================

bool InitTradeLogger()
{
   // Evita abrir o mesmo arquivo novamente
   if(tradeLoggerHandle != INVALID_HANDLE)
      return true;

   tradeLoggerHandle = FileOpen(
      "trade_history.csv",
      FILE_COMMON |
      FILE_CSV |
      FILE_READ |
      FILE_WRITE |
      FILE_ANSI |
      FILE_SHARE_READ |
      FILE_SHARE_WRITE,
      ','
   );

   if(tradeLoggerHandle == INVALID_HANDLE)
   {
      Print(
         "Erro TradeLogger: ",
         GetLastError()
      );

      return false;
   }

   // Vai para o final do arquivo
   FileSeek(
      tradeLoggerHandle,
      0,
      SEEK_END
   );

   // Se estiver vazio, cria o cabeçalho
   if(FileTell(tradeLoggerHandle) == 0)
   {
      FileWrite(
         tradeLoggerHandle,
         "Time",
         "Symbol",
         "Type",
         "Entry",
         "Exit",
         "Profit",
         "ATR",
         "ADX",
         "RSI",
         "AI"
      );

      FileFlush(tradeLoggerHandle);
   }

   Print("TradeLogger inicializado.");

   return true;
}


//==================================================
// LOG TRADE
//==================================================

void LogTradeCSV(
   bool isBuy,
   double entry,
   double exit,
   double profit,
   double aiScore
)
{
   if(tradeLoggerHandle == INVALID_HANDLE)
      return;

   // Garante gravação no final do arquivo
   if(!FileSeek(
      tradeLoggerHandle,
      0,
      SEEK_END
   ))
   {
      Print(
         "Erro TradeLogger FileSeek: ",
         GetLastError()
      );

      return;
   }

   string tradeType = "SELL";

   if(isBuy)
      tradeType = "BUY";

   double atr = GetATR();
   double adx = GetADX();
   double rsi = GetRSI();

   FileWrite(
      tradeLoggerHandle,

      TimeToString(
         TimeCurrent(),
         TIME_DATE | TIME_SECONDS
      ),

      _Symbol,

      tradeType,

      DoubleToString(
         entry,
         _Digits
      ),

      DoubleToString(
         exit,
         _Digits
      ),

      DoubleToString(
         profit,
         2
      ),

      DoubleToString(
         atr,
         _Digits
      ),

      DoubleToString(
         adx,
         2
      ),

      DoubleToString(
         rsi,
         2
      ),

      DoubleToString(
         aiScore,
         2
      )
   );

   FileFlush(tradeLoggerHandle);
}


//==================================================
// CLOSE
//==================================================

void CloseTradeLogger()
{
   if(tradeLoggerHandle != INVALID_HANDLE)
   {
      FileClose(tradeLoggerHandle);

      tradeLoggerHandle = INVALID_HANDLE;
   }
}

#endif
