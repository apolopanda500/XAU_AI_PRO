//+------------------------------------------------------------------+
//| KCI Directional Matrix Wrapper                                   |
//| Wrapper para uso do indicador KCI-DX em EAs                      |
//| Original: https://www.mql5.com/en/code/74839                     |
//+------------------------------------------------------------------+
#ifndef KCI_DIRECTIONAL_MATRIX_MQH
#define KCI_DIRECTIONAL_MATRIX_MQH

//+------------------------------------------------------------------+
//| Handles globais por simbolo/timeframe                              |
//+------------------------------------------------------------------+
struct KCI_Handle
{
   string            symbol;
   ENUM_TIMEFRAMES   timeframe;
   int               handle;
};

KCI_Handle kci_handles[];

//+------------------------------------------------------------------+
//| Localiza handle existente                                        |
//+------------------------------------------------------------------+
int KCI_FindHandle(string symbol, ENUM_TIMEFRAMES timeframe)
{
   int total = ArraySize(kci_handles);
   for(int i = 0; i < total; i++)
   {
      if(kci_handles[i].symbol == symbol && kci_handles[i].timeframe == timeframe)
         return kci_handles[i].handle;
   }
   return INVALID_HANDLE;
}

//+------------------------------------------------------------------+
//| Cria ou reutiliza handle do iCustom                              |
//+------------------------------------------------------------------+
int KCI_GetHandle(string symbol, ENUM_TIMEFRAMES timeframe, int basePeriod=9, int zScorePeriod=30, double sensitivity=1.5)
{
   int existing = KCI_FindHandle(symbol, timeframe);
   if(existing != INVALID_HANDLE)
      return existing;

   int handle = iCustom(symbol, timeframe, "KCI_Directional_Matrix", basePeriod, zScorePeriod, sensitivity);
   if(handle == INVALID_HANDLE)
   {
      Print("[KCI DX] Erro ao criar iCustom | Simbolo=", symbol, " | TF=", EnumToString(timeframe), " | Erro=", GetLastError());
      return INVALID_HANDLE;
   }

   int newSize = ArraySize(kci_handles) + 1;
   ArrayResize(kci_handles, newSize);
   kci_handles[newSize - 1].symbol = symbol;
   kci_handles[newSize - 1].timeframe = timeframe;
   kci_handles[newSize - 1].handle = handle;

   return handle;
}

//+------------------------------------------------------------------+
//| Libera todos os handles                                            |
//+------------------------------------------------------------------+
void KCI_ReleaseAllHandles()
{
   int total = ArraySize(kci_handles);
   for(int i = 0; i < total; i++)
   {
      if(kci_handles[i].handle != INVALID_HANDLE)
         IndicatorRelease(kci_handles[i].handle);
   }
   ArrayFree(kci_handles);
}

//+------------------------------------------------------------------+
//| Obtem valores do KCI-DX                                          |
//+------------------------------------------------------------------+
bool GetKCIDirectionalMatrix(string symbol, ENUM_TIMEFRAMES timeframe,
                             double &kci_main, double &kdi_plus, double &kdi_minus,
                             int basePeriod=9, int zScorePeriod=30, double sensitivity=1.5)
{
   kci_main = 0.0;
   kdi_plus = 0.0;
   kdi_minus = 0.0;

   if(symbol == "") symbol = _Symbol;

   int handle = KCI_GetHandle(symbol, timeframe, basePeriod, zScorePeriod, sensitivity);
   if(handle == INVALID_HANDLE) return false;

   double main[], plus[], minus[];
   ArraySetAsSeries(main, true);
   ArraySetAsSeries(plus, true);
   ArraySetAsSeries(minus, true);

   if(CopyBuffer(handle, 0, 1, 1, main) != 1) return false;
   if(CopyBuffer(handle, 1, 1, 1, plus) != 1) return false;
   if(CopyBuffer(handle, 2, 1, 1, minus) != 1) return false;

   kci_main  = main[0];
   kdi_plus  = plus[0];
   kdi_minus = minus[0];

   return (kci_main > 0.0 || kdi_plus > 0.0 || kdi_minus > 0.0);
}

#endif
