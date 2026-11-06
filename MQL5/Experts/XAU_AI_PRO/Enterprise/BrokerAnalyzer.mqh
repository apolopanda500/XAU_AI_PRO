//+------------------------------------------------------------------+
//|                                               BrokerAnalyzer.mqh |
//|                       XAU_AI_PRO v1.2.9 Professional               |
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

      // v1.2.87 (02/11/2026) - P1.74: eram 20 linhas de dump por arranque
      // (320 num reload de 16 graficos). O mesmo dado passa a UMA linha.
      if(LogSessaoPodeImprimir("broker_cfg_" + m_cfg.symbol))
      Print("[BROKER] ",m_cfg.symbol," | ",m_cfg.company,"/",m_cfg.server,
            " | digits=",m_cfg.digits," point=",DoubleToString(m_cfg.point,m_cfg.digits),
            " | lot=",m_cfg.min_volume,"-",m_cfg.max_volume," step=",m_cfg.volume_step,
            " | stops=",m_cfg.stop_level," freeze=",m_cfg.freeze_level,
            " | tick=",m_cfg.tick_size,"/",m_cfg.tick_value," contrato=",m_cfg.contract_size,
            " | fill=",EnumToString(m_cfg.fill_mode)," exec=",EnumToString(m_cfg.execution),
            " | margem=",m_cfg.margin_initial,"/",m_cfg.margin_maintenance,
            " | slippage=",m_cfg.recommended_slippage);

      return true;      return true;
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