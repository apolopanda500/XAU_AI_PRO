// XAU_AI_PRO v1.2.0
#ifndef SIGNALCORE_MQH
#define SIGNALCORE_MQH

#include "../Core/Config.mqh"

//==================================================
// SIGNAL CORE v1.2.0
// Cache de handles de indicadores.
//
// ANTES: GetSignal() criava 3 handles (2x iMA + iRSI)
// e destruia a CADA tick, para cada simbolo escaneado.
// Custo alto no scanner multi-symbol (ate 11 simbolos
// x 3 instancias do EA).
//
// AGORA: handles criados UMA vez por simbolo e
// reutilizados. Liberados em ReleaseSignalHandles()
// (chamado no OnDeinit).
//==================================================

struct SignalHandleEntry
{
   string symbol;
   int    emaFastHandle;
   int    emaSlowHandle;
   int    rsiH;
};

SignalHandleEntry g_signalHandles[];
int g_signalHandleCount = 0;

//==================================================
// INIT / DEINIT DO CACHE
//==================================================

void SignalCoreInit()
{
   g_signalHandleCount = 0;
   ArrayResize(g_signalHandles, 0);
}

void ReleaseSignalHandles()
{
   for(int i = 0; i < g_signalHandleCount; i++)
   {
      if(g_signalHandles[i].emaFastHandle != INVALID_HANDLE)
         IndicatorRelease(g_signalHandles[i].emaFastHandle);
      if(g_signalHandles[i].emaSlowHandle != INVALID_HANDLE)
         IndicatorRelease(g_signalHandles[i].emaSlowHandle);
      if(g_signalHandles[i].rsiH != INVALID_HANDLE)
         IndicatorRelease(g_signalHandles[i].rsiH);
   }
   g_signalHandleCount = 0;
   ArrayResize(g_signalHandles, 0);
}

//==================================================
// BUSCA/CADASTRO DE HANDLES POR SIMBOLO
//==================================================

int FindSignalHandleEntry(string symbol)
{
   for(int i = 0; i < g_signalHandleCount; i++)
   {
      if(g_signalHandles[i].symbol == symbol)
         return i;
   }
   return -1;
}

bool GetSignalHandles(string symbol,
                      int &emaFastHandle,
                      int &emaSlowHandle,
                      int &rsiH)
{
   int idx = FindSignalHandleEntry(symbol);

   if(idx >= 0)
   {
      emaFastHandle = g_signalHandles[idx].emaFastHandle;
      emaSlowHandle = g_signalHandles[idx].emaSlowHandle;
      rsiH          = g_signalHandles[idx].rsiH;
      return true;
   }

   // Cria os 3 handles para o simbolo (1a vez)
   emaFastHandle = iMA(symbol, PERIOD_CURRENT, FastEMA, 0, MODE_EMA, PRICE_CLOSE);
   emaSlowHandle = iMA(symbol, PERIOD_CURRENT, SlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   rsiH          = iRSI(symbol, PERIOD_CURRENT, RSIPeriod, PRICE_CLOSE);

   if(emaFastHandle == INVALID_HANDLE ||
      emaSlowHandle == INVALID_HANDLE ||
      rsiH          == INVALID_HANDLE)
   {
      if(emaFastHandle != INVALID_HANDLE)
         IndicatorRelease(emaFastHandle);
      if(emaSlowHandle != INVALID_HANDLE)
         IndicatorRelease(emaSlowHandle);
      if(rsiH != INVALID_HANDLE)
         IndicatorRelease(rsiH);
      return false;
   }

   int size = ArraySize(g_signalHandles);
   ArrayResize(g_signalHandles, size + 1);
   g_signalHandles[size].symbol        = symbol;
   g_signalHandles[size].emaFastHandle = emaFastHandle;
   g_signalHandles[size].emaSlowHandle = emaSlowHandle;
   g_signalHandles[size].rsiH          = rsiH;
   g_signalHandleCount = size + 1;

   return true;
}

//==================================================
// GET SIGNAL
//==================================================

int GetSignal()
{
   return GetSignal(_Symbol);
}

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

   // Handles do cache (criados sob demanda, 1x por simbolo)
   int emaFastHandle = INVALID_HANDLE;
   int emaSlowHandle = INVALID_HANDLE;
   int rsiH          = INVALID_HANDLE;

   if(!GetSignalHandles(symbol, emaFastHandle, emaSlowHandle, rsiH))
   {
      if(logOnce)
         Print("SIGNAL ERROR: Handles invalidos para ", symbol);
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

   if(CopyBuffer(rsiH,0,0,3,rsi)<=0)
   {
      if(logOnce)
         Print("SIGNAL ERROR: Falha ao copiar RSI para ", symbol);
      copyOK=false;
   }

   if(!copyOK)
      return 0;

   // Logica de sinal v1.2.0 - vela FECHADA (indice 1) + pullback com reversao
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
