//+------------------------------------------------------------------+
//|                                               MarginChecker.mqh |
//|                                  Smart Execution Engine - Margin |
//|                                            XAU_AI_PRO v1.2.0       |
//+------------------------------------------------------------------+

#ifndef MARGIN_CHECKER_MQH
#define MARGIN_CHECKER_MQH

class CMarginChecker
{
private:
   static double m_required_margin;
   static double m_free_margin;
   static double m_margin_level;
   static bool   m_initialized;
   
public:
   static void Init();
   static bool CheckMargin(string symbol, double volume, double price);
   static double CalculateRequiredMargin(string symbol, double volume, double price);
   static double GetFreeMargin();
   static double GetMarginLevel();
   static string GetMarginError(string symbol, double volume, double price);
   static void LogMarginStatus();
};

double CMarginChecker::m_required_margin = 0;
double CMarginChecker::m_free_margin = 0;
double CMarginChecker::m_margin_level = 0;
bool CMarginChecker::m_initialized = false;

void CMarginChecker::Init()
{
   if(m_initialized) return;
   m_free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   m_margin_level = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
   m_initialized = true;
   PrintFormat("[MARGIN] Free: %.2f | Level: %.2f%%", m_free_margin, m_margin_level);
}

bool CMarginChecker::CheckMargin(string symbol, double volume, double price)
{
   if(!m_initialized) Init();
   if(symbol == "") symbol = _Symbol;
   m_required_margin = CalculateRequiredMargin(symbol, volume, price);
   m_free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   m_margin_level = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
   
   if(m_free_margin <= 0) return false;
   if(m_required_margin > m_free_margin * 0.9) return false;
   // Nivel de margem 0 = sem posicoes abertas (nao bloqueia).
   // So bloqueia quando existe nivel real abaixo de 200%.
   if(m_margin_level > 0 && m_margin_level < 200) return false;
   return true;
}

double CMarginChecker::CalculateRequiredMargin(string symbol, double volume, double price)
{
   if(symbol == "") symbol = _Symbol;

   // v1.3.0: OrderCalcMargin nativo converte moedas corretamente
   // (pares com USD na base como USDJPY, crosses, metais, indices).
   // A formula manual antiga multiplicava pelo preco mesmo quando
   // a moeda base ja era a da conta (USDJPY: $10 reais -> $159 calculados).
   double margin = 0.0;

   if(OrderCalcMargin(ORDER_TYPE_BUY, symbol, volume, price, margin) && margin > 0.0)
      return margin;

   // Fallback: calculo manual aproximado
   double contract_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   double leverage = (double)AccountInfoInteger(ACCOUNT_LEVERAGE);
   if(leverage <= 0) leverage = 100;
   return (volume * contract_size * price) / leverage;
}

double CMarginChecker::GetFreeMargin()
{
   return AccountInfoDouble(ACCOUNT_MARGIN_FREE);
}

double CMarginChecker::GetMarginLevel()
{
   return AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
}

string CMarginChecker::GetMarginError(string symbol, double volume, double price)
{
   double required = CalculateRequiredMargin(symbol, volume, price);
   double free = GetFreeMargin();
   double level = GetMarginLevel();
   
   if(free <= 0) return "Sem margem livre disponivel";
   if(required > free * 0.9)
      return StringFormat("Margem requerida (%.2f) excede 90%% da livre (%.2f)", required, free);
   if(level > 0 && level < 200)
      return StringFormat("Nivel de margem (%.2f%%) abaixo de 200%%", level);
   return "";
}

void CMarginChecker::LogMarginStatus()
{
   double free = GetFreeMargin();
   double level = GetMarginLevel();
   PrintFormat("[MARGIN] Free: %.2f | Level: %.2f%% | Required: %.2f", free, level, m_required_margin);
}

#endif // MARGIN_CHECKER_MQH
