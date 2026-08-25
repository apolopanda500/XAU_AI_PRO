//+------------------------------------------------------------------+
// XAU_AI_PRO - Warm-Up de Historico (UTILITARIO, sem trading)
// Objetivo: forc. : prer. : carrega as velas dos ultimos N dias para
// cada simbolo/periodo usado pelo EA, destravando o CopyBuffer dos
// indicadores (RSI/ADX/EMA) que falhava com "No Signal" por falta
// de dados no terminal.
// NAO envia ordens. Pode ser solto no grafico e executado 1x.
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

// Quantidade minima de barras por simbolo/TF a garantir
input int    N_BARS_Min       = 10000;   // barras a tentar garantir
input int    N_Days_Back      = 15;      // dias de historia a puxar
input bool   LogResultado     = true;

// Periodos usados pelo EA (M5 principal + H1 TrendFilter + M15/backtest)
input bool   do_M1  = true;
input bool   do_M5  = true;
input bool   do_M15 = true;
input bool   do_H1  = true;

// Simbolos escaneados (mesma lista do Config.mqh) - descomente/ajuste
// string SYMBOLS[] = {"XAUUSD","EURUSD","GBPUSD","USDJPY","AUDUSD",
//                     "USDCAD","NZDUSD","USDCHF","XAGUSD"};
string SYMBOLS[] = {"XAUUSD","EURUSD","GBPUSD","USDJPY","AUDUSD",
                    "USDCAD","NZDUSD","USDCHF","XAGUSD"};

//+------------------------------------------------------------------+
void OnStart()
{
   Print("=== Warm-Up de Historico XAU_AI_PRO (SEM trading) ===");
   Print("Alvo minimo: ", N_BARS_Min, " barras | Dias: ", N_Days_Back);

   for(int i = 0; i < ArraySize(SYMBOLS); i++)
   {
      string sym = SYMBOLS[i];
      if(!SymbolSelect(sym, true))
      {
         Print("SymbolSelect FALHOU: ", sym, " (erro ", GetLastError(), ")");
         continue;
      }

      Print("---- ", sym, " ----");

      if(do_M1)  WarmUp(sym, PERIOD_M1);
      if(do_M5)  WarmUp(sym, PERIOD_M5);
      if(do_M15) WarmUp(sym, PERIOD_M15);
      if(do_H1)  WarmUp(sym, PERIOD_H1);
   }

   Print("=== Warm-Up concluido. Rode o EA para verificar os sinais. ===");
}

//+------------------------------------------------------------------+
// Força o download/cache de barras de um simbolo/TF e reporta.
// Usa CopyRates (com timestamp antigo) para disparar o download
// e SeriesInfoInteger para medir quantas barras ficaram disponiveis.
//+------------------------------------------------------------------+
void WarmUp(string sym, ENUM_TIMEFRAMES tf)
{
   string tfName = TimeframeToString(tf);
   datetime from = TimeCurrent() - N_Days_Back * 86400;
   if(from < 0) from = 0;

   MqlRates rates[];
   ArraySetAsSeries(rates, false);

   int copied = CopyRates(sym, tf, from, N_BARS_Min, rates);

   if(copied <= 0)
   {
      // tenta novamente esperando o download (alguns servidores atrasam)
      Sleep(2000);
      copied = CopyRates(sym, tf, from, N_BARS_Min, rates);
   }

   Print("  TF ", tfName, " barras=", copied,
         " | erro=", (copied <= 0 ? IntegerToString(GetLastError()) : "OK"));

   // Debug extra: quantas barras o terminal diz ter para esse TF agora
   long bars = 0;
   if(SeriesInfoInteger(sym, tf, SERIES_BARS_COUNT, bars))
      Print("  TF ", tfName, " SERIES_BARS_COUNT=", bars);
}

//+------------------------------------------------------------------+
string TimeframeToString(ENUM_TIMEFRAMES tf)
{
   switch(tf)
   {
      case PERIOD_M1:  return "M1";
      case PERIOD_M5:  return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_H1:  return "H1";
      default:         return EnumToString(tf);
   }
}
//+------------------------------------------------------------------+