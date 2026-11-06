// XAU_AI_PRO v1.2.154
#ifndef TRENDFILTER_MQH
#define TRENDFILTER_MQH

#include "../Core/Config.mqh"
#include "../Indicators/SymbolDataReady.mqh"   // v1.2.152 - P1.113

#define TREND_EMA_PERIOD 200

//==================================================
// v1.2.154 (05/11/2026) - P1.115: GUARDA LOCAL AO SIMBOLO
//
// A P1.113 comparava a EMA do simbolo estrangeiro com a EMA do simbolo do
// grafico e descartava o handle quando os dois valores eram indistinguiveis.
// Essa comparacao produz falsos positivos, medidos as 23:40:51 de 04/11 no
// grafico USDCNH:
//   [TREND] VALOR DE OUTRO SIMBOLO | AUDUSD | EMA=0.70084 | grafico=USDCNH
// 0.70084 e a EMA200 H1 verdadeira do AUDUSD (bid 0.70188): a leitura estava
// CERTA e o handle foi descartado a mesma. O que estava contaminado era o
// handle do proprio grafico, criado em OnInit antes de a serie do par existir.
// A guarda passa a ser local ao simbolo: a EMA200 H1 nao pode estar a mais de
// TREND_EMA_MAX_DEVIATION_PCT do preco do PROPRIO simbolo. Assim apanha a
// contaminacao nos dois sentidos sem depender do valor do grafico.
#define TREND_EMA_MAX_DEVIATION_PCT 50.0

input ENUM_TIMEFRAMES TrendTF = PERIOD_H1;

int trendEMAHandle = INVALID_HANDLE;

double trendEMABuffer[];

//==================================================
// v1.2.152 (05/11/2026) - P1.113: CACHE DE EMA POR SIMBOLO
//
// GetTrendEMA(valor, symbol) criava um handle iMA() e chamava
// IndicatorRelease() na MESMA leitura, para CADA simbolo estrangeiro. E o
// defeito do ATR (P1.108) e do ADX (P1.85) outra vez, medido no journal:
//   [SIGNAL] SEM LEITURA | USDCAD | EMA Fast em aquecimento (MT5 calcula
//   apos reload) | BarsCalc=-1 | Error=4022
// repetido em NZDUSD, USDCHF, USDSEK e USDCNH. Sem EMA nao ha direcao, logo
// TrendBuy e TrendSell devolvem false e o [CENARIO] imprime tendencia=RANGING
// mesmo com ADX de tendencia forte - foi exactamente o que saiu as 23:26:34
// de 04/11 no grafico USDCNH (ADX=33.8 e RANGING na mesma linha).
// O handle passa a ser criado UMA vez por simbolo e reutilizado; o handle do
// simbolo do grafico continua a ser o da instancia (InitTrendFilter).
//==================================================
#define TREND_SYMBOL_CACHE 64

string g_trendCacheSymbol[TREND_SYMBOL_CACHE];
int    g_trendCacheHandle[TREND_SYMBOL_CACHE];
int    g_trendCacheCount = 0;

int TrendSymbolHandle(string symbol)
{
   for(int i = 0; i < g_trendCacheCount; i++)
      if(g_trendCacheSymbol[i] == symbol)
         return g_trendCacheHandle[i];

   if(g_trendCacheCount >= TREND_SYMBOL_CACHE)
      return INVALID_HANDLE;

   // v1.2.152 - P1.113: handle so nasce com a serie do simbolo provada.
   XAI_WaitSeriesReady(symbol, TrendTF);

   int handle = iMA(symbol, TrendTF, TREND_EMA_PERIOD, 0, MODE_EMA, PRICE_CLOSE);

   if(handle == INVALID_HANDLE)
      return INVALID_HANDLE;

   g_trendCacheSymbol[g_trendCacheCount] = symbol;
   g_trendCacheHandle[g_trendCacheCount] = handle;
   g_trendCacheCount++;

   return handle;
}

void TrendCacheDrop(string symbol)
{
   for(int i = 0; i < g_trendCacheCount; i++)
     {
      if(g_trendCacheSymbol[i] != symbol)
         continue;

      if(g_trendCacheHandle[i] != INVALID_HANDLE)
         IndicatorRelease(g_trendCacheHandle[i]);

      for(int j = i; j < g_trendCacheCount - 1; j++)
        {
         g_trendCacheSymbol[j] = g_trendCacheSymbol[j + 1];
         g_trendCacheHandle[j] = g_trendCacheHandle[j + 1];
        }

      g_trendCacheCount--;
      g_trendCacheSymbol[g_trendCacheCount] = "";
      g_trendCacheHandle[g_trendCacheCount] = INVALID_HANDLE;

      return;
     }
}

void TrendReleaseSymbolHandles()
{
   for(int i = 0; i < g_trendCacheCount; i++)
      if(g_trendCacheHandle[i] != INVALID_HANDLE)
         IndicatorRelease(g_trendCacheHandle[i]);

   g_trendCacheCount = 0;
}

//==================================================
// v1.2.154 - P1.115: PLAUSIBILIDADE DA EMA (LOCAL AO SIMBOLO)
//==================================================

bool TrendEMAImplausivel(double ema, string symbol)
{
   if(ema <= 0.0)
      return false;   // ausencia de leitura nao e leitura suspeita

   if(symbol == "")
      symbol = _Symbol;

   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);

   if(bid <= 0.0)
      return false;   // sem preco do proprio simbolo nao se julga

   return ((MathAbs(ema - bid) / bid) * 100.0 > TREND_EMA_MAX_DEVIATION_PCT);
}

// O handle do simbolo do grafico tambem pode nascer contaminado em OnInit
// (antes de a serie do par existir). Aqui ele e recriado para sarar sozinho.
void TrendChartHandleReset()
{
   if(trendEMAHandle != INVALID_HANDLE)
   {
      IndicatorRelease(trendEMAHandle);
      trendEMAHandle = INVALID_HANDLE;
   }

   trendEMAHandle = iMA(
      _Symbol,
      TrendTF,
      TREND_EMA_PERIOD,
      0,
      MODE_EMA,
      PRICE_CLOSE
   );
}

//==================================================
// INIT
//==================================================

bool InitTrendFilter()
{
   // v1.2.152 - P1.113: o timeframe entra no handle, a cache e limpa.
   TrendReleaseSymbolHandles();

   if(trendEMAHandle != INVALID_HANDLE)
      IndicatorRelease(trendEMAHandle);

   trendEMAHandle = iMA(
      _Symbol,
      TrendTF,
      TREND_EMA_PERIOD,
      0,
      MODE_EMA,
      PRICE_CLOSE
   );

   if(trendEMAHandle == INVALID_HANDLE)
   {
      Print(
         "[TREND] INIT ERROR | Error=",
         GetLastError()
      );

      return false;
   }

   ArrayResize(trendEMABuffer, 3);
   ArraySetAsSeries(trendEMABuffer, true);

   if(LogSessaoPodeImprimir("trend_init_" + _Symbol))
   Print(
      "[TREND] INIT OK | ",
      _Symbol,
      " | TF=",
      EnumToString(TrendTF),
      " | EMA=",
      TREND_EMA_PERIOD
   );

   return true;
}

//==================================================
// GET EMA
//==================================================

bool GetTrendEMA(double &value)
{
   value = 0.0;

   if(trendEMAHandle == INVALID_HANDLE)
      return false;

   if(CopyBuffer(
      trendEMAHandle,
      0,
      0,
      1,
      trendEMABuffer
   ) != 1)
   {
      return false;
   }

   value = trendEMABuffer[0];

   // v1.2.154 - P1.115: leitura impossivel para o proprio simbolo = handle
   // contaminado. Descarta o valor e recria o handle do grafico.
   if(TrendEMAImplausivel(value, _Symbol))
   {
      if(AccountLogGatePodeImprimir("trend_chart_suspeito", 3600))
         Print("[TREND] LEITURA SUSPEITA | ", _Symbol,
               " | EMA=", DoubleToString(value, 5),
               " | bid=", DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_BID), 5),
               " | handle do grafico RECRIADO (proxima leitura)");

      TrendChartHandleReset();
      value = 0.0;

      return false;
   }

   return (value > 0.0);
}

//==================================================
// MULTI SYMBOL
//==================================================

bool GetTrendEMA(
   double &value,
   string symbol
)
{
   value = 0.0;

   if(symbol == "" || symbol == _Symbol)
      return GetTrendEMA(value);

   if(!SymbolSelect(symbol, true))
      return false;

   int handle = TrendSymbolHandle(symbol);   // v1.2.152 - P1.113: handle em cache por simbolo

   if(handle == INVALID_HANDLE)
      return false;

   double buffer[];

   ArraySetAsSeries(buffer, true);

   bool ok = false;

   if(CopyBuffer(
      handle,
      0,
      0,
      1,
      buffer
   ) == 1)
   {
      value = buffer[0];
      ok = (value > 0.0);
   }

   // v1.2.152 (05/11/2026) - P1.113: o handle NAO e libertado na leitura.
   // Criar e libertar no mesmo instante era o que impedia a EMA de aquecer
   // (Error=4022) e deixava TrendBuy/TrendSell sem direcao.
   // v1.2.154 - P1.115: sem leitura, ou com uma EMA impossivel para o PROPRIO
   // simbolo, a entrada da cache e descartada para o par sarar na leitura
   // seguinte. A comparacao com a EMA do grafico foi removida (falso positivo).
   bool suspeito = (ok && TrendEMAImplausivel(value, symbol));

   if(!ok || suspeito)
     {
      if(suspeito && AccountLogGatePodeImprimir("trend_leitura_suspeita_" + symbol, 3600))
         Print("[TREND] LEITURA SUSPEITA | ", symbol,
               " | EMA=", DoubleToString(value, 5),
               " | bid=", DoubleToString(SymbolInfoDouble(symbol, SYMBOL_BID), 5),
               " | desvio acima de ", DoubleToString(TREND_EMA_MAX_DEVIATION_PCT, 0),
               "% | handle DESCARTADO (recriado na proxima leitura)");

      TrendCacheDrop(symbol);
      value = 0.0;
      ok = false;
     }

   return ok;
}

//==================================================
// BUY
//==================================================

bool TrendBuy(string symbol = "")
{
   if(symbol == "")
      symbol = _Symbol;

   double ema = 0.0;

   if(!GetTrendEMA(ema, symbol))
      return false;

   double bid = SymbolInfoDouble(
      symbol,
      SYMBOL_BID
   );

   if(bid <= 0.0)
      return false;

   return (bid > ema);
}

//==================================================
// SELL
//==================================================

bool TrendSell(string symbol = "")
{
   if(symbol == "")
      symbol = _Symbol;

   double ema = 0.0;

   if(!GetTrendEMA(ema, symbol))
      return false;

   double bid = SymbolInfoDouble(
      symbol,
      SYMBOL_BID
   );

   if(bid <= 0.0)
      return false;

   return (bid < ema);
}

//==================================================
// SIGNAL
//==================================================

int GetTrendSignal()
{
   if(TrendBuy())
      return 1;

   if(TrendSell())
      return -1;

   return 0;
}

//==================================================
// DISTANCE
//==================================================

double GetTrendDistance()
{
   double ema = 0.0;

   if(!GetTrendEMA(ema))
      return 0.0;

   double bid = SymbolInfoDouble(
      _Symbol,
      SYMBOL_BID
   );

   if(bid <= 0.0)
      return 0.0;

   double point = SymbolInfoDouble(
      _Symbol,
      SYMBOL_POINT
   );

   if(point <= 0.0)
      return 0.0;

   return NormalizeDouble(
      MathAbs(bid - ema) / point,
      2
   );
}

//==================================================
// RELEASE
//==================================================

void ReleaseTrendFilter()
{
   TrendReleaseSymbolHandles();   // v1.2.152 - P1.113

   if(trendEMAHandle != INVALID_HANDLE)
   {
      IndicatorRelease(trendEMAHandle);
      trendEMAHandle = INVALID_HANDLE;
   }

   ArrayFree(trendEMABuffer);
}

#endif
