// XAU_AI_PRO v1.2.0
#ifndef BROKERCONFIG_MQH
#define BROKERCONFIG_MQH

string TradeGold   = "";
string TradeBTC    = "";
string TradeEURUSD = "";
string TradeGBPUSD = "";
string TradeUSDJPY = "";

bool SymbolExists(string symbol)
{
   return(SymbolSelect(symbol,true));
}

void LoadBrokerSymbols()
{
   // GOLD
   if(SymbolExists("XAUUSD"))       TradeGold="XAUUSD";
   else if(SymbolExists("XAUUSD.")) TradeGold="XAUUSD.";
   else if(SymbolExists("XAUUSDc")) TradeGold="XAUUSDc";
   else if(SymbolExists("GOLD"))    TradeGold="GOLD";
   else if(SymbolExists("GOLD#"))   TradeGold="GOLD#";

   // BTC
   if(SymbolExists("BTCUSD"))       TradeBTC="BTCUSD";
   else if(SymbolExists("BTCUSD#")) TradeBTC="BTCUSD#";
   else if(SymbolExists("BTCUSDc")) TradeBTC="BTCUSDc";

   // EURUSD
   if(SymbolExists("EURUSD"))       TradeEURUSD="EURUSD";
   else if(SymbolExists("EURUSD.")) TradeEURUSD="EURUSD.";
   else if(SymbolExists("EURUSDc")) TradeEURUSD="EURUSDc";

   // GBPUSD
   if(SymbolExists("GBPUSD"))       TradeGBPUSD="GBPUSD";
   else if(SymbolExists("GBPUSD.")) TradeGBPUSD="GBPUSD.";
   else if(SymbolExists("GBPUSDc")) TradeGBPUSD="GBPUSDc";

   // USDJPY
   if(SymbolExists("USDJPY"))       TradeUSDJPY="USDJPY";
   else if(SymbolExists("USDJPY.")) TradeUSDJPY="USDJPY.";
   else if(SymbolExists("USDJPYc")) TradeUSDJPY="USDJPYc";

   Print("========== BROKER CONFIG ==========");
   Print("GOLD    : ",TradeGold);
   Print("BTC     : ",TradeBTC);
   Print("EURUSD  : ",TradeEURUSD);
   Print("GBPUSD  : ",TradeGBPUSD);
   Print("USDJPY  : ",TradeUSDJPY);
   Print("==================================");
}

#endif