//+------------------------------------------------------------------+
//| KCI Volatility Distance Wrapper                                  |
//| Wrapper para uso do indicador KCI Volatility Distance em EAs     |
//| Original: https://www.mql5.com/en/code/74838                     |
//+------------------------------------------------------------------+
#ifndef KCI_VOLATILITY_DISTANCE_MQH
#define KCI_VOLATILITY_DISTANCE_MQH

//+------------------------------------------------------------------+
//| CKCIVolatilityDistance (extraido do indicador original)          |
//+------------------------------------------------------------------+
class CKCIVolatilityDistance
{
private:
   int    m_kinetic_period;
   double m_point;

public:
                     CKCIVolatilityDistance(void)
   {
      m_kinetic_period = 14;
      m_point          = _Point;
   }
                    ~CKCIVolatilityDistance(void) {}

   bool Init(const int period)
   {
      if(period < 2)
      {
         Print("[KCI VD Error] Period must be at least 2");
         return(false);
      }
      m_kinetic_period = period;
      m_point          = _Point;
      if(m_point <= 0) m_point = 0.00001;
      return(true);
   }

   double Calculate(const int index,
                    const double &high[],
                    const double &low[],
                    const double &close[])
   {
      double sum_TR = 0.0;
      double sum_sq_TR = 0.0;
      double path_length = 0.0;

      for(int j = 0; j < m_kinetic_period; j++)
      {
         int curr_idx = index + j;

         double hl = high[curr_idx] - low[curr_idx];
         double hc = MathAbs(high[curr_idx] - close[curr_idx + 1]);
         double lc = MathAbs(low[curr_idx] - close[curr_idx + 1]);

         double tr = hl;
         if(hc > tr) tr = hc;
         if(lc > tr) tr = lc;

         sum_TR    += tr;
         sum_sq_TR += (tr * tr);

         if(j < m_kinetic_period - 1)
         {
            path_length += MathAbs(close[curr_idx] - close[curr_idx + 1]);
         }
      }

      double net_distance = MathAbs(close[index] - close[index + m_kinetic_period - 1]);

      if(path_length < net_distance) path_length = net_distance;
      if(path_length == 0.0)         path_length = m_point;

      double efficiency_ratio = net_distance / path_length;

      double mean_TR  = sum_TR / m_kinetic_period;
      double variance = (sum_sq_TR / m_kinetic_period) - (mean_TR * mean_TR);
      if(variance < 0.0) variance = 0.0;

      double std_TR = MathSqrt(variance);

      return(std_TR * (2.0 - efficiency_ratio));
   }
};

//+------------------------------------------------------------------+
//| Funcao helper: calcula KCI VD para um simbolo/timeframe          |
//+------------------------------------------------------------------+
double GetKCIVolatilityDistance(string symbol, ENUM_TIMEFRAMES timeframe, int period=14, int shift=1)
{
   if(symbol == "") symbol = _Symbol;

   int needed = period + 2;
   double high[], low[], close[];
   ArraySetAsSeries(high, true);
   ArraySetAsSeries(low, true);
   ArraySetAsSeries(close, true);

   if(CopyHigh(symbol, timeframe, shift, needed, high) < needed) return 0.0;
   if(CopyLow(symbol, timeframe, shift, needed, low) < needed) return 0.0;
   if(CopyClose(symbol, timeframe, shift, needed, close) < needed) return 0.0;

   CKCIVolatilityDistance engine;
   if(!engine.Init(period)) return 0.0;

   return engine.Calculate(0, high, low, close);
}

#endif
