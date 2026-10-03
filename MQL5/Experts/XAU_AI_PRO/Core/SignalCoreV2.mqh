// XAU_AI_PRO v1.2.0 - Signal Core v2 (modulo paralelo)
#ifndef SIGNALCOREV2_MQH
#define SIGNALCOREV2_MQH



//==================================================
// SIGNAL CORE V2 - HIPOTESE: BREAKOUT DE TENDENCIA
// (sessao + niveis de referencia)
//==================================================
// Modulo PARALELO ao Signal Core v1 (baseline). Nao
// altera RiskHub / SafetyManager / ExecutionEngine /
// gestao de posicoes nem o SignalCore v1.
//
// Selecao pelo input SignalCoreVersion:
//   CORE_VERSION_V1 (default) -> mesmo comportamento
//   do baseline (GetSignal v1 puro, via dispatcher).
//   CORE_VERSION_V2 -> GetSignalV2() (este arquivo).
//
// Logica v2 (vela FECHADA, sem repaint - contrato igual
// ao v1: indice 1 do V2_EntryTF):
//   1. Janela de sessao: so avalia dentro de
//      [V2_SessionStartHour, V2_SessionEndHour) em HORA
//      DO SERVIDOR (TimeCurrent). 24 = fim do dia.
//   2. Nivel de rompimento (V2_LevelMode):
//        SESSION_RANGE  -> high/low das ultimas
//                          V2_RangeLookback velas fechadas;
//        PREV_DAY       -> PDH/PDL (D1 anterior);
//        SESSION_OR_PD  -> qualquer um dos dois.
//      Nivel so vale se o range >= V2_MinRangePoints.
//   3. Tendencia: EMA fast/slow no V2_TrendTF (vela
//      fechada). Obrigatoria quando V2_RequireTrend=true.
//   4. RSI opcional (V2_RequireRSI) no EntryTF.
//   BUY: close[1] acima do nivel + tendencia alta + RSI ok
//   SELL: close[1] abaixo do nivel + tendencia baixa + RSI ok
//
// Os defaults (13-21h servidor, M15, H1 trend, lookback
// 16, min 80 pontos) sao a HIPOTESE INICIAL para o
// backtest isolado V1 x V2 - nao representam edge
// comprovado. Handles de indicadores sao criados e
// liberados a cada chamada (padrao seguro do v1).
//==================================================

// Forward declaration do sinal v1 (definido em Core/SignalCore.mqh)
int GetSignal(string symbol);

// Forward declaration do sinal activo (dispatcher definido neste ficheiro)
int GetActiveSignal(string symbol);

//==================================================
// SELETOR DE CORE
//==================================================
enum ENUM_CORE_VERSION
{
   CORE_VERSION_V1 = 0,   // Signal Core v1 (baseline: EMA50/200 + RSI pullback)
   CORE_VERSION_V2 = 1    // Signal Core v2 (breakout de tendencia + sessao + niveis)
};

input ENUM_CORE_VERSION SignalCoreVersion = CORE_VERSION_V1;

//==================================================
// CONFIGURACAO V2
//==================================================
input ENUM_TIMEFRAMES V2_TrendTF        = PERIOD_H1;   // TF da tendencia (EMA fast/slow)
input int             V2_TrendFastEMA   = 50;
input int             V2_TrendSlowEMA   = 200;

input ENUM_TIMEFRAMES V2_EntryTF        = PERIOD_M15;  // TF do rompimento (vela fechada)
input int             V2_RangeLookback  = 16;          // velas ANTERIORES p/ range da sessao (min 5; exclui a vela de sinal)
input int             V2_MinRangePoints = 80;          // range minimo (pontos) p/ nivel valido

input bool            V2_UseSessionWindow = true;      // avalia so dentro da janela
input int             V2_SessionStartHour = 13;        // hora do servidor (inicio, inclusive)
input int             V2_SessionEndHour   = 21;        // hora do servidor (fim, exclusivo; 24=fim do dia)

enum ENUM_V2_LEVEL_MODE
{
   V2_LEVEL_SESSION_RANGE = 0,   // range da sessao (high/low das ultimas N velas fechadas)
   V2_LEVEL_PREV_DAY      = 1,   // PDH/PDL (dia anterior D1)
   V2_LEVEL_SESSION_OR_PD = 2    // qualquer um dos dois
};

input ENUM_V2_LEVEL_MODE V2_LevelMode  = V2_LEVEL_SESSION_RANGE;

input bool   V2_RequireTrend = true;      // BUY so em tendencia alta / SELL em baixa
input bool   V2_RequireRSI   = false;     // confirmacao RSI opcional (centro 50)
input int    V2_RSIPeriod    = 14;
input double V2_RSIMinConf   = 50.0;      // RSI[1] >= p/ BUY; RSI[1] <= (100-) p/ SELL
input bool   V2_LogSignals   = true;      // loga sinais e diagnostico (1x/min)

//==================================================
// ESTADO INTERNO
//==================================================
bool g_v2ConfigValid = true;

//==================================================
// LOG 1x/min (padrao do projeto - evita spam por tick)
//==================================================
bool V2_LogOnce()
{
   static datetime lastLog = 0;
   datetime now = TimeCurrent();
   if(now - lastLog >= 60)
   {
      lastLog = now;
      return true;
   }
   return false;
}

//==================================================
// INIT (validacao de inputs) / RELEASE (stub)
//==================================================
void SignalCoreV2Init()
{
   g_v2ConfigValid = true;

   if(V2_TrendFastEMA < 2 || V2_TrendSlowEMA <= V2_TrendFastEMA)
   {
      Print("[V2] CFG ERROR | EMA invalido: fast=", V2_TrendFastEMA,
            " slow=", V2_TrendSlowEMA);
      g_v2ConfigValid = false;
   }

   if(V2_RangeLookback < 5)
   {
      Print("[V2] CFG ERROR | V2_RangeLookback minimo 5, recebido ", V2_RangeLookback);
      g_v2ConfigValid = false;
   }

   if(V2_MinRangePoints < 1)
   {
      Print("[V2] CFG ERROR | V2_MinRangePoints minimo 1, recebido ", V2_MinRangePoints);
      g_v2ConfigValid = false;
   }

   if(V2_UseSessionWindow)
   {
      if(V2_SessionStartHour < 0 || V2_SessionStartHour >= 24 ||
         V2_SessionEndHour < 1 || V2_SessionEndHour > 24 ||
         V2_SessionStartHour >= V2_SessionEndHour)
      {
         Print("[V2] CFG ERROR | Janela de sessao invalida: ",
               V2_SessionStartHour, "-", V2_SessionEndHour);
         g_v2ConfigValid = false;
      }
   }

   Print("[V2] INIT | Core=",
         (SignalCoreVersion == CORE_VERSION_V2 ? "V2" : "V1"),
         " | TrendTF=", EnumToString(V2_TrendTF),
         " | EntryTF=", EnumToString(V2_EntryTF),
         " | Nivel=", EnumToString(V2_LevelMode));
}

void SignalCoreV2Release()
{
   // sem handles persistentes - nada a liberar
}

//==================================================
// SINAL V2
//==================================================
int GetSignalV2(string symbol)
{
   if(symbol == "")
      return 0;

   if(!g_v2ConfigValid)
      return 0;

   const bool logOnce = V2_LogOnce();

   //------------------------------------------------
   // 1) JANELA DE SESSAO (hora do servidor)
   //------------------------------------------------
   if(V2_UseSessionWindow)
   {
      MqlDateTime dt;
      TimeToStruct(TimeCurrent(), dt);

      if(dt.hour < V2_SessionStartHour || dt.hour >= V2_SessionEndHour)
         return 0;
   }

   const double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(point <= 0.0)
      return 0;

   //------------------------------------------------
   // 2) NIVEL DE BREAKOUT
   //------------------------------------------------
   double sHigh = 0.0, sLow = 0.0;
   bool   haveSession = false;
   double pdHigh = 0.0, pdLow = 0.0;
   bool   havePrevDay = false;

   if(V2_LevelMode == V2_LEVEL_SESSION_RANGE ||
      V2_LevelMode == V2_LEVEL_SESSION_OR_PD)
   {
      MqlRates rt[];
      ArraySetAsSeries(rt, true);
      // rt[0] = vela de sinal (fechada). O range usa as velas ANTERIORES:
      // fechar acima do proprio high da vela seria impossivel (close <= high).
      int copied = CopyRates(symbol, V2_EntryTF, 1, V2_RangeLookback + 1, rt);
      if(copied == V2_RangeLookback + 1)
      {
         double h = rt[1].high;
         double l = rt[1].low;
         for(int i = 2; i < copied; i++)
         {
            if(rt[i].high > h) h = rt[i].high;
            if(rt[i].low  < l) l = rt[i].low;
         }

         if((h - l) / point >= V2_MinRangePoints)
         {
            sHigh = h;
            sLow  = l;
            haveSession = true;
         }
      }
      else
      if(logOnce)
         Print("[V2] CopyRates range falhou | ", symbol, " | copied=", copied);
   }

   if(V2_LevelMode == V2_LEVEL_PREV_DAY ||
      V2_LevelMode == V2_LEVEL_SESSION_OR_PD)
   {
      MqlRates d1[];
      ArraySetAsSeries(d1, true);
      int copiedD1 = CopyRates(symbol, PERIOD_D1, 1, 1, d1);
      if(copiedD1 == 1)
      {
         if((d1[0].high - d1[0].low) / point >= V2_MinRangePoints)
         {
            pdHigh = d1[0].high;
            pdLow  = d1[0].low;
            havePrevDay = true;
         }
      }
      else
      if(logOnce)
         Print("[V2] CopyRates D1 falhou | ", symbol, " | copied=", copiedD1);
   }

   if(!haveSession && !havePrevDay)
      return 0;

   //------------------------------------------------
   // 3) TENDENCIA (EMA no V2_TrendTF, vela fechada)
   //------------------------------------------------
   bool trendUp = false, trendDown = false;

   if(V2_RequireTrend)
   {
      int hFast = iMA(symbol, V2_TrendTF, V2_TrendFastEMA, 0, MODE_EMA, PRICE_CLOSE);
      int hSlow = iMA(symbol, V2_TrendTF, V2_TrendSlowEMA, 0, MODE_EMA, PRICE_CLOSE);

      if(hFast == INVALID_HANDLE || hSlow == INVALID_HANDLE)
      {
         if(hFast != INVALID_HANDLE) IndicatorRelease(hFast);
         if(hSlow != INVALID_HANDLE) IndicatorRelease(hSlow);
         if(logOnce)
            Print("[V2] EMA trend invalido | ", symbol);
         return 0;
      }

      double fb[];
      double sb[];
      ArrayResize(fb, 2);
      ArrayResize(sb, 2);
      ArraySetAsSeries(fb, true);
      ArraySetAsSeries(sb, true);

      bool okF = (CopyBuffer(hFast, 0, 1, 1, fb) == 1);
      bool okS = (CopyBuffer(hSlow, 0, 1, 1, sb) == 1);

      IndicatorRelease(hFast);
      IndicatorRelease(hSlow);

      if(!okF || !okS)
      {
         if(logOnce)
            Print("[V2] CopyBuffer EMA falhou | ", symbol);
         return 0;
      }

      trendUp   = (fb[0] > sb[0]);
      trendDown = (fb[0] < sb[0]);
   }

   //------------------------------------------------
   // 4) RSI OPCIONAL (vela fechada do EntryTF)
   //------------------------------------------------
   bool rsiBuyOK = true, rsiSellOK = true;

   if(V2_RequireRSI)
   {
      int hRSI = iRSI(symbol, V2_EntryTF, V2_RSIPeriod, PRICE_CLOSE);
      if(hRSI == INVALID_HANDLE)
      {
         if(logOnce)
            Print("[V2] RSI invalido | ", symbol);
         return 0;
      }

      double rb[];
      ArrayResize(rb, 2);
      ArraySetAsSeries(rb, true);

      bool okR = (CopyBuffer(hRSI, 0, 1, 1, rb) == 1);

      IndicatorRelease(hRSI);

      if(!okR)
      {
         if(logOnce)
            Print("[V2] CopyBuffer RSI falhou | ", symbol);
         return 0;
      }

      rsiBuyOK  = (rb[0] >= V2_RSIMinConf);
      rsiSellOK = (rb[0] <= (100.0 - V2_RSIMinConf));
   }

   //------------------------------------------------
   // 5) PRECO DE ROMPIMENTO (vela fechada do EntryTF)
   //------------------------------------------------
   MqlRates entry[];
   ArraySetAsSeries(entry, true);

   if(CopyRates(symbol, V2_EntryTF, 1, 1, entry) != 1)
   {
      if(logOnce)
         Print("[V2] CopyRates entry falhou | ", symbol);
      return 0;
   }

   const double close1 = entry[0].close;

   //------------------------------------------------
   // 6) DECISAO
   //------------------------------------------------
   bool breakBuy = false, breakSell = false;

   if(V2_LevelMode == V2_LEVEL_SESSION_RANGE)
   {
      breakBuy  = haveSession && close1 > sHigh;
      breakSell = haveSession && close1 < sLow;
   }
   else
   if(V2_LevelMode == V2_LEVEL_PREV_DAY)
   {
      breakBuy  = havePrevDay && close1 > pdHigh;
      breakSell = havePrevDay && close1 < pdLow;
   }
   else // V2_LEVEL_SESSION_OR_PD
   {
      breakBuy  = (haveSession && close1 > sHigh) || (havePrevDay && close1 > pdHigh);
      breakSell = (haveSession && close1 < sLow)  || (havePrevDay && close1 < pdLow);
   }

   if(breakBuy && (!V2_RequireTrend || trendUp) && rsiBuyOK)
   {
      if(V2_LogSignals && logOnce)
         Print("[V2] SIGNAL BUY | ", symbol,
               " | close[1]=", DoubleToString(close1, _Digits),
               " | nivel=", DoubleToString((haveSession ? sHigh : pdHigh), _Digits));
      return 1;
   }

   if(breakSell && (!V2_RequireTrend || trendDown) && rsiSellOK)
   {
      if(V2_LogSignals && logOnce)
         Print("[V2] SIGNAL SELL | ", symbol,
               " | close[1]=", DoubleToString(close1, _Digits),
               " | nivel=", DoubleToString((haveSession ? sLow : pdLow), _Digits));
      return -1;
   }

   return 0;
}

//==================================================
// DISPATCHER - ponto unico de entrada do EA.
// Onde o baseline chamava GetSignal(), passa a
// chamar GetActiveSignal(). Default V1 = identico.
//==================================================
int GetActiveSignal(string symbol)
{
   if(SignalCoreVersion == CORE_VERSION_V2)
      return GetSignalV2(symbol);

   return GetSignal(symbol);

}
//==============================================
#endif
