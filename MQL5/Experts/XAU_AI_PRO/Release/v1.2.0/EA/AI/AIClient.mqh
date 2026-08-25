// XAU_AI_PRO v1.2.0
#ifndef AICLIENT_MQH
#define AICLIENT_MQH

#include "../Core/Config.mqh"

#include "../Indicators/ADX.mqh"
#include "../Indicators/RSI.mqh"

#include "../AI/AdaptiveWeights.mqh"

//==================================================
// AI CLIENT v1.2.0
//==================================================

bool g_AIConnected=false;
double g_LastConfidence=0.0;
int g_LastSignal=0;

//==================================================

bool AIClientConnected()
{
   return g_AIConnected;
}

//==================================================

bool UseExternalAI()
{
   return false;
}

//==================================================

double RequestExternalAIConfidence(int signal)
{
   if(!AIClientConnected())
      return -1.0;

   return -1.0;
}

//==================================================

int RequestExternalAISignal()
{
   if(!AIClientConnected())
      return 0;

   return 0;
}

//==================================================

double GetLocalAIFallback(int signal)
{
   double score=50.0;

   double adx=GetADX();
   double rsi=GetRSI();

   //----------------------------------------
   // TREND
   //----------------------------------------

   if(adx>=30)
      score+=25.0*GetTrendWeight();
   else
   if(adx>=20)
      score+=15.0*GetTrendWeight();
   else
      score-=15.0;

   //----------------------------------------
   // RSI
   //----------------------------------------

   if(signal>0)
   {
      if(rsi>35 && rsi<65)
         score+=15.0*GetMomentumWeight();

      if(rsi>=70)
         score-=20.0;

      if(rsi<=20)
         score+=8.0;
   }

   if(signal<0)
   {
      if(rsi>35 && rsi<65)
         score+=15.0*GetMomentumWeight();

      if(rsi<=30)
         score-=20.0;

      if(rsi>=80)
         score+=8.0;
   }

   //----------------------------------------
   // LIMITS
   //----------------------------------------

   if(score>100.0)
      score=100.0;

   if(score<0.0)
      score=0.0;

   g_LastConfidence=
      NormalizeDouble(score,2);

   g_LastSignal=signal;

   return g_LastConfidence;
}

//==================================================

double GetAIConfidence(int signal)
{
   if(UseExternalAI())
   {
      double ext=
         RequestExternalAIConfidence(signal);

      if(ext>=0.0)
      {
         g_LastConfidence=ext;
         return ext;
      }
   }

   return GetLocalAIFallback(signal);
}

//==================================================

int GetClientAISignal()
{
   if(UseExternalAI())
   {
      int ext=
         RequestExternalAISignal();

      if(ext!=0)
      {
         g_LastSignal=ext;
         return ext;
      }
   }

   return g_LastSignal;
}

//==================================================

double LastAIConfidence()
{
   return g_LastConfidence;
}

//==================================================

void AIClientUpdate()
{
   g_AIConnected=true;
}

//==================================================

void AIClientInit()
{
   g_AIConnected=true;

   Print("[AI] Client initialized");
}

//==================================================

void AIClientShutdown()
{
   g_AIConnected=false;

   Print("[AI] Client shutdown");
}

#endif