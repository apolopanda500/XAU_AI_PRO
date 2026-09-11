// XAU_AI_PRO v1.2.0
#ifndef VOLATILITYFILTER_MQH
#define VOLATILITYFILTER_MQH


//==================================================
// VOLATILITY FILTER PRO (ATR)
//==================================================


#define VOLATILITY_ATR_PERIOD 14


//==================================================
// HANDLE
//==================================================

int volatilityATRHandle = INVALID_HANDLE;

double volatilityATRBuffer[];


//==================================================
// INIT
//==================================================

bool InitATR()
{

   volatilityATRHandle =
      iATR(
         _Symbol,
         PERIOD_CURRENT,
         VOLATILITY_ATR_PERIOD
      );


   if(volatilityATRHandle == INVALID_HANDLE)
   {
      Print("Erro criando ATR");
      return false;
   }


   ArraySetAsSeries(
      volatilityATRBuffer,
      true
   );


   return true;

}



//==================================================
// GET ATR
//==================================================

double GetATR()
{

   if(volatilityATRHandle == INVALID_HANDLE)
      return 0.0;



   if(
      CopyBuffer(
         volatilityATRHandle,
         0,
         0,
         3,
         volatilityATRBuffer
      ) <= 0
   )
      return 0.0;



   return NormalizeDouble(
      volatilityATRBuffer[0],
      _Digits
   );

}


double GetATR(string symbol)
{
   if(symbol=="")
      return GetATR();

   // Normaliza com os digitos do proprio simbolo (nao do chart),
   // senao ATR de pares com mais casas (ex: EURUSD, 5 digitos)
   // e arredondado a zero (NormalizeDouble(x,_Digits) com _Digits=2).
   int symbolDigits=(int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   if(symbolDigits<=0)
      symbolDigits=_Digits;

   int handle=iATR(symbol, PERIOD_CURRENT, VOLATILITY_ATR_PERIOD);
   if(handle==INVALID_HANDLE)
      return 0.0;

   double buf[];
   ArraySetAsSeries(buf, true);

   double result=0.0;
   if(CopyBuffer(handle, 0, 0, 1, buf) > 0)
      result=NormalizeDouble(buf[0], symbolDigits);

   IndicatorRelease(handle);
   return result;
}



//==================================================
// RELEASE
//==================================================

void ReleaseATR()
{

   if(volatilityATRHandle != INVALID_HANDLE)
   {

      IndicatorRelease(
         volatilityATRHandle
      );


      volatilityATRHandle = INVALID_HANDLE;

   }

}



//==================================================
// ATR POINTS
//==================================================

double GetATRPoints()
{

   double atr =
      GetATR();


   if(atr <= 0)
      return 0;



   return(
      atr /
      _Point
   );

}



//==================================================
// VOLATILITY FILTER
//==================================================

bool GoodVolatility(
   double minATRPoints
)
{

   double points =
      GetATRPoints();


   if(points <= 0)
      return false;


   return(
      points >= minATRPoints
   );

}



//==================================================
// AI VOLATILITY SCORE
//==================================================

double GetVolatilityScore()
{

   double atrPoints =
      GetATRPoints();



   if(atrPoints >= 300)
      return 100;


   if(atrPoints >= 150)
      return 80;


   if(atrPoints >= 70)
      return 60;


   if(atrPoints >= 30)
      return 40;


   return 20;

}



//==================================================
// HIGH VOLATILITY
//==================================================

bool HighVolatility(
   double multiplier
)
{

   double atr =
      GetATR();


   if(atr <= 0)
      return false;



   double averageATR = 0;


   int copied =
      CopyBuffer(
         volatilityATRHandle,
         0,
         1,
         20,
         volatilityATRBuffer
      );


   if(copied <= 0)
      return false;



   for(int i=0;i<copied;i++)
      averageATR += volatilityATRBuffer[i];


   averageATR /= copied;



   return(
      atr >=
      averageATR * multiplier
   );

}



//==================================================
// MARKET STATE
//==================================================

bool IsLowVolatility()
{

   return(
      GetATRPoints() < 30
   );

}



bool IsNormalVolatility()
{

   double p =
      GetATRPoints();


   return(
      p >= 30 &&
      p < 150
   );

}



bool IsExtremeVolatility()
{

   return(
      GetATRPoints() >= 300
   );

}



#endif