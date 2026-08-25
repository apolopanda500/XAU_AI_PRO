//+------------------------------------------------------------------+
//|                                               BrokerAnalyzer.mqh |
//|                       XAU_AI_PRO v1.2.0 Professional               |
//+------------------------------------------------------------------+
#ifndef BROKER_ANALYZER_MQH
#define BROKER_ANALYZER_MQH

//==================================================
// STRUCT
//==================================================

struct BrokerConfig
{
   string symbol;
   string company;
   string server;

   double min_volume;
   double max_volume;
   double volume_step;

   double point;
   int    digits;

   int stop_level;
   int freeze_level;

   double tick_size;
   double tick_value;
   double contract_size;

   ENUM_ORDER_TYPE_FILLING fill_mode;

   ENUM_SYMBOL_TRADE_EXECUTION execution;

   double margin_initial;
   double margin_maintenance;

   int recommended_slippage;
};

class CBrokerAnalyzer
{
private:

   static BrokerConfig m_cfg;
   static bool initialized;

public:

   static bool Init(string symbol="")
{
   if(symbol=="")
      symbol = _Symbol;

   if(initialized && m_cfg.symbol==symbol)
      return true;

      m_cfg.symbol=symbol;

      m_cfg.company=
         AccountInfoString(
            ACCOUNT_COMPANY
         );

      m_cfg.server=
         AccountInfoString(
            ACCOUNT_SERVER
         );

      m_cfg.min_volume=
         SymbolInfoDouble(
            symbol,
            SYMBOL_VOLUME_MIN
         );

      m_cfg.max_volume=
         SymbolInfoDouble(
            symbol,
            SYMBOL_VOLUME_MAX
         );

      m_cfg.volume_step=
         SymbolInfoDouble(
            symbol,
            SYMBOL_VOLUME_STEP
         );

      m_cfg.point=
         SymbolInfoDouble(
            symbol,
            SYMBOL_POINT
         );

      m_cfg.digits=
         (int)SymbolInfoInteger(
            symbol,
            SYMBOL_DIGITS
         );

      m_cfg.stop_level=
         (int)SymbolInfoInteger(
            symbol,
            SYMBOL_TRADE_STOPS_LEVEL
         );

      m_cfg.freeze_level=
         (int)SymbolInfoInteger(
            symbol,
            SYMBOL_TRADE_FREEZE_LEVEL
         );

      m_cfg.tick_size=
         SymbolInfoDouble(
            symbol,
            SYMBOL_TRADE_TICK_SIZE
         );

      m_cfg.tick_value=
         SymbolInfoDouble(
            symbol,
            SYMBOL_TRADE_TICK_VALUE
         );

      m_cfg.contract_size=
         SymbolInfoDouble(
            symbol,
            SYMBOL_TRADE_CONTRACT_SIZE
         );

      m_cfg.execution=
         (ENUM_SYMBOL_TRADE_EXECUTION)
         SymbolInfoInteger(
            symbol,
            SYMBOL_TRADE_EXEMODE
         );

      long fill = (long)SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);

if((fill & (long)SYMBOL_FILLING_FOK) != 0)
{
   m_cfg.fill_mode = ORDER_FILLING_FOK;
}
else
if((fill & (long)SYMBOL_FILLING_IOC) != 0)
{
   m_cfg.fill_mode = ORDER_FILLING_IOC;
}
else
{
   m_cfg.fill_mode = ORDER_FILLING_RETURN;
}

if(m_cfg.point <= 0)
   m_cfg.point = _Point;

double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
double bid = SymbolInfoDouble(symbol, SYMBOL_BID);

double spread = (ask - bid) / m_cfg.point;

m_cfg.recommended_slippage =
   (int)MathMax(
      spread * 1.5,
      3.0
   );

      m_cfg.margin_initial=
         SymbolInfoDouble(
            symbol,
            SYMBOL_MARGIN_INITIAL
         );

      m_cfg.margin_maintenance=
         SymbolInfoDouble(
            symbol,
            SYMBOL_MARGIN_MAINTENANCE
         );

      double currentSpread =
(
   SymbolInfoDouble(symbol,SYMBOL_ASK)
   -
   SymbolInfoDouble(symbol,SYMBOL_BID)
)
/
m_cfg.point;

m_cfg.recommended_slippage =
(int)MathMax(
   currentSpread * 1.5,
   3.0
);

      initialized=true;

      Print("--------------------------------");

      Print("BROKER ANALYZER");

      Print("Company: ",m_cfg.company);

      Print("Server : ",m_cfg.server);

      Print("Symbol : ",m_cfg.symbol);

      Print("Digits : ",m_cfg.digits);

      Print("Point  : ",DoubleToString(m_cfg.point,m_cfg.digits));

      Print("MinLot : ",m_cfg.min_volume);

      Print("MaxLot : ",m_cfg.max_volume);

      Print("Step   : ",m_cfg.volume_step);

      Print("Stops  : ",m_cfg.stop_level);

      Print("Freeze : ",m_cfg.freeze_level);

      Print("TickSize : ",m_cfg.tick_size);

      Print("TickValue: ",m_cfg.tick_value);

      Print("Contract : ",m_cfg.contract_size);

      Print("Execution: ",EnumToString(m_cfg.execution));

      Print("Filling  : ",EnumToString(m_cfg.fill_mode));

      Print("Margin Initial: ",m_cfg.margin_initial);

      Print("Margin Maint : ",m_cfg.margin_maintenance);

      Print("Slippage: ",m_cfg.recommended_slippage);

      Print("--------------------------------");

      return true;
   }

   static BrokerConfig GetConfig()
   {
      return m_cfg;
   }

   static int GetRecommendedSlippage()
   {
      return m_cfg.recommended_slippage;
   }

   static ENUM_ORDER_TYPE_FILLING GetOptimalFillPolicy()
   {
      return m_cfg.fill_mode;
   }

   static int StopLevel()
   {
      return m_cfg.stop_level;
   }

   static int FreezeLevel()
   {
      return m_cfg.freeze_level;
   }

   static double MinLot()
   {
      return m_cfg.min_volume;
   }

   static double MaxLot()
   {
      return m_cfg.max_volume;
   }

   static double LotStep()
   {
      return m_cfg.volume_step;
   }

   static double TickValue()
   {
      return m_cfg.tick_value;
   }

   static double TickSize()
   {
      return m_cfg.tick_size;
   }

   static double ContractSize()
   {
      return m_cfg.contract_size;
   }
};

BrokerConfig CBrokerAnalyzer::m_cfg;
bool CBrokerAnalyzer::initialized=false;

#endif