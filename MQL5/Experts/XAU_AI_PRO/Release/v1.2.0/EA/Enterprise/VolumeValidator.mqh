//+------------------------------------------------------------------+
//|                                              VolumeValidator.mqh |
//|                         XAU_AI_PRO v1.2.0 Professional             |
//+------------------------------------------------------------------+
#ifndef VOLUME_VALIDATOR_MQH
#define VOLUME_VALIDATOR_MQH

class CVolumeValidator
{
private:

   static double m_min_volume;
   static double m_max_volume;
   static double m_volume_step;
   static double m_volume_limit;

   static bool   m_initialized;
   static string m_symbol;


   //===============================================================
   // PRECISAO DO STEP
   //===============================================================

   static int VolumeDigits()
   {
      if(m_volume_step <= 0.0)
         return 2;

      int digits = 0;
      double step = m_volume_step;

      while(digits < 8)
      {
         double rounded = NormalizeDouble(step, digits);

         if(MathAbs(step - rounded) < 0.000000001)
            break;

         digits++;
      }

      return digits;
   }


   //===============================================================
   // CARREGA ESPECIFICACAO DO SIMBOLO
   //===============================================================

   static bool LoadSymbol(string symbol)
   {
      if(symbol == "")
         symbol = _Symbol;

      if(!SymbolSelect(symbol, true))
      {
         Print(
            "[VOLUME] SymbolSelect failed: ",
            symbol,
            " | Error=",
            GetLastError()
         );

         return false;
      }


      double min_volume =
         SymbolInfoDouble(
            symbol,
            SYMBOL_VOLUME_MIN
         );

      double max_volume =
         SymbolInfoDouble(
            symbol,
            SYMBOL_VOLUME_MAX
         );

      double step =
         SymbolInfoDouble(
            symbol,
            SYMBOL_VOLUME_STEP
         );

      double limit =
         SymbolInfoDouble(
            symbol,
            SYMBOL_VOLUME_LIMIT
         );


      if(min_volume <= 0.0)
      {
         Print(
            "[VOLUME] Invalid minimum volume: ",
            symbol
         );

         return false;
      }


      if(max_volume <= 0.0)
      {
         Print(
            "[VOLUME] Invalid maximum volume: ",
            symbol
         );

         return false;
      }


      if(step <= 0.0)
      {
         Print(
            "[VOLUME] Invalid volume step: ",
            symbol
         );

         return false;
      }


      m_min_volume  = min_volume;
      m_max_volume  = max_volume;
      m_volume_step = step;
      m_volume_limit = limit;
      m_symbol = symbol;

      m_initialized = true;

      return true;
   }


public:

   //===============================================================
   // INIT
   //===============================================================

   static bool Init(string symbol="")
   {
      return LoadSymbol(symbol);
   }


   //===============================================================
   // GARANTE SIMBOLO CORRETO
   //===============================================================

   static bool EnsureSymbol(string symbol="")
   {
      if(symbol == "")
         symbol = _Symbol;

      if(
         !m_initialized ||
         m_symbol != symbol
      )
      {
         return LoadSymbol(symbol);
      }

      return true;
   }


   //===============================================================
   // VALIDATE
   //===============================================================

   static bool ValidateVolume(
      double volume,
      string symbol=""
   )
   {
      if(!EnsureSymbol(symbol))
         return false;


      if(volume <= 0.0)
         return false;


      if(volume < m_min_volume)
         return false;


      if(volume > m_max_volume)
         return false;


      //============================================================
      // STEP
      //============================================================

      double steps =
         volume /
         m_volume_step;

      double roundedSteps =
         MathRound(steps);

      double normalized =
         roundedSteps *
         m_volume_step;


      double tolerance =
         m_volume_step *
         0.000001;


      if(
         MathAbs(
            volume - normalized
         ) > tolerance
      )
      {
         return false;
      }


      return true;
   }


   //===============================================================
   // NORMALIZE
   //===============================================================

   static double NormalizeVolume(
      double volume,
      string symbol=""
   )
   {
      if(!EnsureSymbol(symbol))
         return 0.0;


      if(volume <= 0.0)
         return 0.0;


      //============================================================
      // LIMITES
      //============================================================

      if(volume < m_min_volume)
         volume = m_min_volume;


      if(volume > m_max_volume)
         volume = m_max_volume;


      //============================================================
      // ARREDONDAMENTO PARA STEP
      //============================================================

      double steps =
         MathFloor(
            volume /
            m_volume_step
         );


      volume =
         steps *
         m_volume_step;


      //============================================================
      // GARANTE MINIMO
      //============================================================

      if(volume < m_min_volume)
         volume = m_min_volume;


      //============================================================
      // GARANTE MAXIMO
      //============================================================

      if(volume > m_max_volume)
         volume = m_max_volume;


      //============================================================
      // PRECISAO DINAMICA
      //============================================================

      volume =
         NormalizeDouble(
            volume,
            VolumeDigits()
         );


      return volume;
   }


   //===============================================================
   // VALIDATE + NORMALIZE
   //===============================================================

   static bool PrepareVolume(
      double requestedVolume,
      double &normalizedVolume,
      string symbol=""
   )
   {
      normalizedVolume =
         NormalizeVolume(
            requestedVolume,
            symbol
         );


      if(normalizedVolume <= 0.0)
         return false;


      return ValidateVolume(
         normalizedVolume,
         symbol
      );
   }


   //===============================================================
   // ERROR
   //===============================================================

   static string GetValidationError(
      double volume,
      string symbol=""
   )
   {
      if(!EnsureSymbol(symbol))
         return "Nao foi possivel carregar especificacao do simbolo.";


      if(volume <= 0.0)
         return "Volume invalido.";


      if(volume < m_min_volume)
      {
         return StringFormat(
            "Volume abaixo do minimo: %.8f < %.8f",
            volume,
            m_min_volume
         );
      }


      if(volume > m_max_volume)
      {
         return StringFormat(
            "Volume acima do maximo: %.8f > %.8f",
            volume,
            m_max_volume
         );
      }


      double steps =
         volume /
         m_volume_step;


      double roundedSteps =
         MathRound(steps);


      double normalized =
         roundedSteps *
         m_volume_step;


      double tolerance =
         m_volume_step *
         0.000001;


      if(
         MathAbs(
            volume - normalized
         ) > tolerance
      )
      {
         return StringFormat(
            "Volume incompatível com STEP %.8f",
            m_volume_step
         );
      }


      return "";
   }


   //===============================================================
   // LOG
   //===============================================================

   static void LogValidation(
      double volume,
      bool valid
   )
   {
      if(valid)
      {
         Print(
            "[VOLUME] OK | Symbol=",
            m_symbol,
            " | Volume=",
            DoubleToString(
               volume,
               VolumeDigits()
            ),
            " | Min=",
            DoubleToString(
               m_min_volume,
               VolumeDigits()
            ),
            " | Max=",
            DoubleToString(
               m_max_volume,
               VolumeDigits()
            ),
            " | Step=",
            DoubleToString(
               m_volume_step,
               VolumeDigits()
            )
         );
      }
      else
      {
         Print(
            "[VOLUME] ERROR | Symbol=",
            m_symbol,
            " | ",
            GetValidationError(volume)
         );
      }
   }


   //===============================================================
   // GETTERS
   //===============================================================

   static double MinVolume(
      string symbol=""
   )
   {
      if(!EnsureSymbol(symbol))
         return 0.0;

      return m_min_volume;
   }


   static double MaxVolume(
      string symbol=""
   )
   {
      if(!EnsureSymbol(symbol))
         return 0.0;

      return m_max_volume;
   }


   static double Step(
      string symbol=""
   )
   {
      if(!EnsureSymbol(symbol))
         return 0.0;

      return m_volume_step;
   }


   static double VolumeLimit(
      string symbol=""
   )
   {
      if(!EnsureSymbol(symbol))
         return 0.0;

      return m_volume_limit;
   }


   static string Symbol()
   {
      return m_symbol;
   }


   static bool IsInitialized()
   {
      return m_initialized;
   }
};


//+------------------------------------------------------------------+
//| STATIC MEMBERS                                                   |
//+------------------------------------------------------------------+

double CVolumeValidator::m_min_volume   = 0.0;
double CVolumeValidator::m_max_volume   = 0.0;
double CVolumeValidator::m_volume_step  = 0.01;
double CVolumeValidator::m_volume_limit = 0.0;

bool CVolumeValidator::m_initialized = false;

string CVolumeValidator::m_symbol = "";


//+------------------------------------------------------------------+
//| END                                                              |
//+------------------------------------------------------------------+

#endif // VOLUME_VALIDATOR_MQH