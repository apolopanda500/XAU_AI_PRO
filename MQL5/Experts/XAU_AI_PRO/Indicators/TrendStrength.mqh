// XAU_AI_PRO v1.2.0
#ifndef TRENDSTRENGTH_MQH
#define TRENDSTRENGTH_MQH


//==================================================
// TREND STRENGTH
// EMA FAST/SLOW
//==================================================


#define TS_FAST_EMA 50
#define TS_SLOW_EMA 200



//==================================================
// HANDLES
//==================================================

int tsFastEMAHandle = INVALID_HANDLE;
int tsSlowEMAHandle = INVALID_HANDLE;



//==================================================
// INIT
//==================================================

bool InitTrendStrength()
{

   tsFastEMAHandle =
      iMA(
         _Symbol,
         PERIOD_CURRENT,
         TS_FAST_EMA,
         0,
         MODE_EMA,
         PRICE_CLOSE
      );


   tsSlowEMAHandle =
      iMA(
         _Symbol,
         PERIOD_CURRENT,
         TS_SLOW_EMA,
         0,
         MODE_EMA,
         PRICE_CLOSE
      );


   return(
      tsFastEMAHandle != INVALID_HANDLE &&
      tsSlowEMAHandle != INVALID_HANDLE
   );

}



//==================================================
// RELEASE
//==================================================

void ReleaseTrendStrength()
{

   if(tsFastEMAHandle != INVALID_HANDLE)
      IndicatorRelease(tsFastEMAHandle);


   if(tsSlowEMAHandle != INVALID_HANDLE)
      IndicatorRelease(tsSlowEMAHandle);


   tsFastEMAHandle = INVALID_HANDLE;
   tsSlowEMAHandle = INVALID_HANDLE;

}



//==================================================
// GET FAST EMA
//==================================================

double GetTSFastEMA()
{

   double buffer[];

   if(
      CopyBuffer(
         tsFastEMAHandle,
         0,
         0,
         1,
         buffer
      ) <= 0
   )
      return 0;


   return buffer[0];

}



//==================================================
// GET SLOW EMA
//==================================================

double GetTSSlowEMA()
{

   double buffer[];

   if(
      CopyBuffer(
         tsSlowEMAHandle,
         0,
         0,
         1,
         buffer
      ) <= 0
   )
      return 0;


   return buffer[0];

}



//==================================================
// TREND STRENGTH
//==================================================

double GetTrendStrength()
{

   double fast =
      GetTSFastEMA();


   double slow =
      GetTSSlowEMA();



   if(fast<=0 || slow<=0)
      return 0;



   return NormalizeDouble(
      MathAbs(fast-slow)
      /
      _Point,
      2
   );

}



//==================================================
// DIRECTION
//==================================================

int GetTrendStrengthSignal()
{

   double fast =
      GetTSFastEMA();


   double slow =
      GetTSSlowEMA();



   if(fast > slow)
      return 1;



   if(fast < slow)
      return -1;



   return 0;

}



#endif