// XAU_AI_PRO v1.2.0
#ifndef SIGNALCORE_MQH
#define SIGNALCORE_MQH

#include "../Core/Config.mqh"

//==================================================
// SIGNAL CORE (baseline v1.2.0 restaurado)
// Revertido do backup v1.2.0 (24/08 17:36 -> cache de
// handles causou 'Falha ao copiar RSI' e travou sinais).
// Comportamento restaurado: handles criados, copiados e
// liberados a CADA chamada (como na versao que operava).
// Stubs SignalCoreInit/ReleaseSignalHandles mantidos
// apenas para compatibilidade com OnInit/OnDeinit.
//==================================================

// Stub por compatibilidade (chamado no OnInit).
void SignalCoreInit()
{
}

// Stub por compatibilidade (chamado no OnDeinit).
void ReleaseSignalHandles()
{
}

int GetSignal()
{
   return GetSignal(_Symbol);
}

//==================================================
// MULTI SYMBOL
//==================================================

int GetSignal(string symbol)
{
   // Log de diagnostico 1x por minuto (evita spam a cada tick)
   static datetime lastLogTime = 0;
   datetime logNow = TimeCurrent();
   bool logOnce = (logNow - lastLogTime >= 60);
   if(logOnce)
      lastLogTime = logNow;

   if(symbol=="")
      return 0;

   // Indicadores
   int emaFastHandle=iMA(
      symbol,
      PERIOD_CURRENT,
      FastEMA,
      0,
      MODE_EMA,
      PRICE_CLOSE
   );

   int emaSlowHandle=iMA(
      symbol,
      PERIOD_CURRENT,
      SlowEMA,
      0,
      MODE_EMA,
      PRICE_CLOSE
   );

   int signalRSIHandle=iRSI(
      symbol,
      PERIOD_CURRENT,
      RSIPeriod,
      PRICE_CLOSE
   );

   // Valida handles
   if(emaFastHandle==INVALID_HANDLE)
   {
      if(logOnce)
         Print("SIGNAL ERROR: EMA Fast invalido para ", symbol);
      return 0;
   }

   if(emaSlowHandle==INVALID_HANDLE)
   {
      if(logOnce)
         Print("SIGNAL ERROR: EMA Slow invalido para ", symbol);
      IndicatorRelease(emaFastHandle);
      return 0;
   }

   if(signalRSIHandle==INVALID_HANDLE)
   {
      if(logOnce)
         Print("SIGNAL ERROR: RSI invalido para ", symbol);
      IndicatorRelease(emaFastHandle);
      IndicatorRelease(emaSlowHandle);
      return 0;
   }

   double fast[];
   double slow[];
   double rsi[];

   ArrayResize(fast,3);
   ArrayResize(slow,3);
   ArrayResize(rsi,3);

   ArraySetAsSeries(fast,true);
   ArraySetAsSeries(slow,true);
   ArraySetAsSeries(rsi,true);

   // Copiar buffers
   bool copyOK=true;

   if(CopyBuffer(emaFastHandle,0,0,3,fast)<=0)
   {
      if(logOnce)
         Print("SIGNAL ERROR: Falha ao copiar EMA Fast para ", symbol);
      copyOK=false;
   }

   if(CopyBuffer(emaSlowHandle,0,0,3,slow)<=0)
   {
      if(logOnce)
         Print("SIGNAL ERROR: Falha ao copiar EMA Slow para ", symbol);
      copyOK=false;
   }

   if(CopyBuffer(signalRSIHandle,0,0,3,rsi)<=0)
   {
      if(logOnce)
         Print("SIGNAL ERROR: Falha ao copiar RSI para ", symbol);
      copyOK=false;
   }

   // Liberar handles em todos os casos
   IndicatorRelease(emaFastHandle);
   IndicatorRelease(emaSlowHandle);
   IndicatorRelease(signalRSIHandle);

   if(!copyOK)
      return 0;

   // Logica de sinal v1.21 - vela FECHADA (indice 1) + pullback com reversao
   // BUY: tendencia de alta M15 (EMA50>EMA200) + RSI fechou <45 (pullback) + RSI virando p/ cima
   if(fast[1]>slow[1] && rsi[1]<RSIPullbackBuy && rsi[1]>rsi[2])
   {
      if(logOnce)
         Print(symbol," SIGNAL BUY | RSI[1]=",DoubleToString(rsi[1],2));
      return 1;
   }

   // SELL: tendencia de baixa M15 (EMA50<EMA200) + RSI fechou >55 (rally) + RSI virando p/ baixo
   if(fast[1]<slow[1] && rsi[1]>RSIPullbackSell && rsi[1]<rsi[2])
   {
      if(logOnce)
         Print(symbol," SIGNAL SELL | RSI[1]=",DoubleToString(rsi[1],2));
      return -1;
   }

   return 0;
}

#endif