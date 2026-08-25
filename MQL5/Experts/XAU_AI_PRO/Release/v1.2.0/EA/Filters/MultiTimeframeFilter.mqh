// XAU_AI_PRO v1.2.0
#ifndef MULTITIMEFRAMEFILTER_MQH
#define MULTITIMEFRAMEFILTER_MQH

//==================================================
// MULTI TIMEFRAME FILTER
// XAU_AI_PRO v1.2.0
// MULTI SYMBOL
//==================================================

//==================================================
// CONFIG
//==================================================

input ENUM_TIMEFRAMES ConfirmTF1 = PERIOD_M15;

input int MTF_FastEMA = 20;
input int MTF_SlowEMA = 50;

input bool MTFUseClosedCandle = true;


//==================================================
// INIT
// Mantido por compatibilidade com o EA atual
// Os handles agora são criados por símbolo sob demanda
//==================================================

bool InitMTF()
{
   Print(
      "MTF INIT | TF=",
      EnumToString(ConfirmTF1),
      " | FAST=",
      MTF_FastEMA,
      " | SLOW=",
      MTF_SlowEMA
   );

   return true;
}


//==================================================
// RELEASE
// Mantido por compatibilidade
//==================================================

void ReleaseMTF()
{
   // Handles são criados e liberados
   // por símbolo durante a consulta.
}


//==================================================
// CREATE EMA HANDLES
//==================================================

bool CreateMTFHandles(
   string symbol,
   int &fastHandle,
   int &slowHandle
)
{
   fastHandle=INVALID_HANDLE;
   slowHandle=INVALID_HANDLE;

   if(symbol=="")
      return false;

   if(!SymbolSelect(symbol,true))
   {
      Print(
         "MTF SYMBOL SELECT ERROR | ",
         symbol
      );

      return false;
   }

   fastHandle=
      iMA(
         symbol,
         ConfirmTF1,
         MTF_FastEMA,
         0,
         MODE_EMA,
         PRICE_CLOSE
      );

   slowHandle=
      iMA(
         symbol,
         ConfirmTF1,
         MTF_SlowEMA,
         0,
         MODE_EMA,
         PRICE_CLOSE
      );

   if(
      fastHandle==INVALID_HANDLE ||
      slowHandle==INVALID_HANDLE
   )
   {
      Print(
         "MTF HANDLE ERROR | ",
         symbol
      );

      if(fastHandle!=INVALID_HANDLE)
      {
         IndicatorRelease(
            fastHandle
         );

         fastHandle=INVALID_HANDLE;
      }

      if(slowHandle!=INVALID_HANDLE)
      {
         IndicatorRelease(
            slowHandle
         );

         slowHandle=INVALID_HANDLE;
      }

      return false;
   }

   return true;
}


//==================================================
// GET MTF EMA VALUES
//==================================================

bool GetMTFValues(
   string symbol,
   double &fastValue,
   double &slowValue
)
{
   fastValue=0.0;
   slowValue=0.0;

   if(symbol=="")
      return false;

   int fastHandle=INVALID_HANDLE;
   int slowHandle=INVALID_HANDLE;

   if(
      !CreateMTFHandles(
         symbol,
         fastHandle,
         slowHandle
      )
   )
   {
      return false;
   }

   double fastBuffer[];
   double slowBuffer[];

   ArrayResize(
      fastBuffer,
      2
   );

   ArrayResize(
      slowBuffer,
      2
   );

   ArraySetAsSeries(
      fastBuffer,
      true
   );

   ArraySetAsSeries(
      slowBuffer,
      true
   );

   int shift=0;

   if(MTFUseClosedCandle)
      shift=1;

   bool success=false;

   int fastCopied=
      CopyBuffer(
         fastHandle,
         0,
         shift,
         1,
         fastBuffer
      );

   int slowCopied=
      CopyBuffer(
         slowHandle,
         0,
         shift,
         1,
         slowBuffer
      );

   if(
      fastCopied>0 &&
      slowCopied>0
   )
   {
      fastValue=
         fastBuffer[0];

      slowValue=
         slowBuffer[0];

      success=true;
   }

   IndicatorRelease(
      fastHandle
   );

   IndicatorRelease(
      slowHandle
   );

   return success;
}


//==================================================
// UPDATE MTF
// Compatibilidade
//==================================================

bool UpdateMTF(
   string symbol=""
)
{
   if(symbol=="")
      symbol=_Symbol;

   double fastValue=0.0;
   double slowValue=0.0;

   return GetMTFValues(
      symbol,
      fastValue,
      slowValue
   );
}


//==================================================
// BUY CONFIRMATION
//==================================================

bool ConfirmBuyMTF(
   string symbol=""
)
{
   if(symbol=="")
      symbol=_Symbol;

   double fastValue=0.0;
   double slowValue=0.0;

   if(
      !GetMTFValues(
         symbol,
         fastValue,
         slowValue
      )
   )
   {
      return false;
   }

   return(
      fastValue>
      slowValue
   );
}


//==================================================
// SELL CONFIRMATION
//==================================================

bool ConfirmSellMTF(
   string symbol=""
)
{
   if(symbol=="")
      symbol=_Symbol;

   double fastValue=0.0;
   double slowValue=0.0;

   if(
      !GetMTFValues(
         symbol,
         fastValue,
         slowValue
      )
   )
   {
      return false;
   }

   return(
      fastValue<
      slowValue
   );
}


//==================================================
// MTF STRENGTH
//==================================================

double GetMTFStrength(
   string symbol=""
)
{
   if(symbol=="")
      symbol=_Symbol;

   double fastValue=0.0;
   double slowValue=0.0;

   if(
      !GetMTFValues(
         symbol,
         fastValue,
         slowValue
      )
   )
   {
      return 0.0;
   }

   double point=
      SymbolInfoDouble(
         symbol,
         SYMBOL_POINT
      );

   if(point<=0.0)
      return 0.0;

   double distance=
      MathAbs(
         fastValue-
         slowValue
      )
      /
      point;


   if(distance>300.0)
      return 100.0;

   if(distance>150.0)
      return 75.0;

   if(distance>50.0)
      return 50.0;

   return 25.0;
}


//==================================================
// FINAL FILTER
// MULTI SYMBOL
//==================================================

bool MTFApproved(
   int signal,
   string symbol
)
{
   if(symbol=="")
      return false;

   if(signal==1)
   {
      return ConfirmBuyMTF(
         symbol
      );
   }

   if(signal==-1)
   {
      return ConfirmSellMTF(
         symbol
      );
   }

   return false;
}


//==================================================
// COMPATIBILITY OVERLOAD
//==================================================

bool MTFApproved(
   int signal
)
{
   return MTFApproved(
      signal,
      _Symbol
   );
}


//==================================================
// COMPATIBILITY BUY
//==================================================

bool ConfirmBuyMTF()
{
   return ConfirmBuyMTF(
      _Symbol
   );
}


//==================================================
// COMPATIBILITY SELL
//==================================================

bool ConfirmSellMTF()
{
   return ConfirmSellMTF(
      _Symbol
   );
}


//==================================================
// COMPATIBILITY STRENGTH
//==================================================

double GetMTFStrength()
{
   return GetMTFStrength(
      _Symbol
   );
}


#endif
