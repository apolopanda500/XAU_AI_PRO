// XAU_AI_PRO v1.2.0
#ifndef AICONNECTOR_MQH
#define AICONNECTOR_MQH

//==================================================
// AI CONNECTOR
// XAU_AI_PRO v1.2.0
// MULTI SYMBOL
//
// RESPONSABILIDADE:
// - Ler prediction_<SYMBOL>.json
// - Validar o sÃ­mbolo
// - Armazenar os dados da IA
// - Disponibilizar getters
//
// OBS:
// A funÃ§Ã£o AITradeAllowed() NÃƒO fica aqui.
// Ela pertence ao AIEngine.mqh.
//==================================================


//==================================================
// GLOBAL AI STATE
//==================================================

string AI_Symbol="";
string AI_Signal="";

double AI_Price=0.0;
double AI_BuyProbability=0.0;
double AI_SellProbability=0.0;
double AI_Score=0.0;
double AI_Confidence=0.0;

// Metadados do modelo (Contrato A v2 - ETAPA 15.3)
string AI_ModelVersion="";
string AI_ModelID="";
string AI_FeatureHash="";
double AI_InferenceMs=0.0;
string AI_TimestampUTC="";

// Staleness (ETAPA 15.3): idade da previsao em segundos.
// AI_IsStale=true quando a previsao excedeu MaxPredictionAgeSec
// e foi descartada (fail-safe -> fallback local / veto).
bool   AI_IsStale=false;
double AI_AgeSeconds=-1.0;


//==================================================
// RESET AI STATE
//==================================================

void ResetAIState()
{
   AI_Symbol="";
   AI_Signal="";

   AI_Price=0.0;
   AI_BuyProbability=0.0;
   AI_SellProbability=0.0;
   AI_Score=0.0;
   AI_Confidence=0.0;

   AI_ModelVersion="";
   AI_ModelID="";
   AI_FeatureHash="";
   AI_InferenceMs=0.0;
   AI_TimestampUTC="";

   AI_IsStale=false;
   AI_AgeSeconds=-1.0;
}


//==================================================
// NORMALIZE AI SYMBOL
// Converte o sÃ­mbolo do broker no nome base usado
// pelo pipeline Python. Ex: GOLD# -> XAUUSD,
// BTCUSD# -> BTCUSD, XAUUSDc -> XAUUSD.
//==================================================

string NormalizeAISymbol(string symbol)
{
   if(symbol=="")
      return "";

   StringTrimLeft(symbol);
   StringTrimRight(symbol);

   string up=symbol;
   StringToUpper(up);

   // Remove sufixos de classe: #, c, m, . , _i, .pro
   string suffixes[] = {"#", "C", "M", ".PRO", "_I", "."};
   for(int i=0; i<ArraySize(suffixes); i++)
   {
      int pos=StringFind(up, suffixes[i]);
      if(pos>0)
      {
         up=StringSubstr(up, 0, pos);
         break;
      }
   }

   // Mapeamento de aliases -> nome base do Python
   if(up=="GOLD" || up=="XAU")
      return "XAUUSD";

   if(up=="BTC")
      return "BTCUSD";

   if(up=="ETH")
      return "ETHUSD";

   return up;
}


//==================================================
// LOAD AI PREDICTION
//==================================================

bool LoadAIPrediction(string symbol="")
{
   // Log de diagnostico 1x por minuto (evita spam a cada tick)
   static datetime lastLogTime = 0;
   datetime logNow = TimeCurrent();
   bool logOnce = (logNow - lastLogTime >= 60);
   if(logOnce)
      lastLogTime = logNow;

   if(symbol=="")
      symbol=_Symbol;

   StringTrimLeft(symbol);
   StringTrimRight(symbol);

   if(symbol=="")
      return false;

   // SÃ­mbolo normalizado (nome base do pipeline Python)
   string normalized = NormalizeAISymbol(symbol);

   string fileName=
      "Data\\prediction_" +
      symbol +
      ".json";

   // Fallback: se o arquivo exato nÃ£o existe, tenta o nome normalizado
   // (pipeline Python gera prediction_XAUUSD.json, nÃ£o prediction_GOLD#.json)
   if(!FileIsExist(fileName) && normalized!=symbol)
   {
      string altName=
         "Data\\prediction_" +
         normalized +
         ".json";

      if(FileIsExist(altName))
         fileName=altName;
   }


   if(logOnce)
      Print(
         "AI LOAD | SYMBOL=",
         symbol,
         " | FILE=",
         fileName
      );


   ResetLastError();


   //================================================
   // FILE EXISTS
   //================================================

   if(!FileIsExist(fileName))
   {
      if(logOnce)
         Print(
            "AI FILE NOT FOUND | ",
            fileName
         );

      return false;
   }


   //================================================
   // OPEN FILE
   //================================================

   int file=
      FileOpen(
         fileName,
         FILE_READ |
         FILE_TXT |
         FILE_ANSI
      );


   if(file==INVALID_HANDLE)
   {
      if(logOnce)
         Print(
            "AI FILE ERROR | ",
            symbol,
            " | ERROR=",
            GetLastError()
         );

      return false;
   }


   //================================================
   // READ JSON
   //================================================

   string json="";


   while(!FileIsEnding(file))
   {
      string line=
         FileReadString(file);

      json+=line;
   }


   FileClose(file);


   //================================================
   // VALIDATE JSON
   //================================================

   if(json=="")
   {
      if(logOnce)
         Print(
            "AI JSON EMPTY | ",
            symbol
         );

      return false;
   }


   //================================================
   // EXTRACT VALUES
   //================================================

   string jsonSymbol=
      ExtractJSON(
         json,
         "symbol"
      );


   string jsonSignal=
      ExtractJSON(
         json,
         "signal"
      );


   string jsonPrice=
      ExtractJSON(
         json,
         "price"
      );


   string jsonBuy=
      ExtractJSON(
         json,
         "buy"
      );


   string jsonSell=
      ExtractJSON(
         json,
         "sell"
      );


   string jsonScore=
      ExtractJSON(
         json,
         "score"
      );


   string jsonConfidence=
      ExtractJSON(
         json,
         "confidence"
      );

   string jsonModelVersion=
      ExtractJSON(
         json,
         "model_version"
      );

   string jsonModelID=
      ExtractJSON(
         json,
         "model_id"
      );

   string jsonFeatureHash=
      ExtractJSON(
         json,
         "feature_hash"
      );

   string jsonInferenceMs=
      ExtractJSON(
         json,
         "inference_ms"
      );

   string jsonTimestampUTC=
      ExtractJSON(
         json,
         "timestamp_utc"
      );


   //================================================
   // VALIDATE SYMBOL
   //================================================

   if(jsonSymbol=="")
   {
      if(logOnce)
         Print(
            "AI INVALID JSON SYMBOL | ",
            symbol
         );

      return false;
   }


   //================================================
   // VALIDATE SIGNAL
   //================================================

   if(jsonSignal=="")
   {
      if(logOnce)
         Print(
            "AI INVALID JSON SIGNAL | ",
            symbol
         );

      return false;
   }


   //================================================
   // SYMBOL MATCH
   // Aceita o sÃ­mbolo exato ou o normalizado
   // (ex: arquivo prediction_XAUUSD.json com symbol=XAUUSD
   //  Ã© aceito para o sÃ­mbolo do broker GOLD#).
   //================================================

   bool symbolOk =
      StringCompare(jsonSymbol, symbol, false)==0 ||
      StringCompare(jsonSymbol, normalized, false)==0;

   if(!symbolOk)
   {
      if(logOnce)
         Print(
            "AI SYMBOL MISMATCH | REQUEST=",
            symbol,
            " | JSON=",
            jsonSymbol
         );

      return false;
   }


   //================================================
   // UPDATE GLOBAL STATE
   //================================================

   AI_Symbol=
      symbol;


   AI_Signal=
      jsonSignal;


   AI_Price=
      StringToDouble(
         jsonPrice
      );


   AI_BuyProbability=
      StringToDouble(
         jsonBuy
      );


   AI_SellProbability=
      StringToDouble(
         jsonSell
      );


   AI_Score=
      StringToDouble(
         jsonScore
      );


   AI_Confidence=
      StringToDouble(
         jsonConfidence
      );


   //================================================
   // FALLBACK CONFIDENCE
   //================================================

   if(AI_Confidence<=0.0)
      AI_Confidence=
         AI_Score;

   //=================================
   // ATUALIZAR METADADOS (Contrato A v2)
   //=================================

   AI_ModelVersion=
      jsonModelVersion;

   AI_ModelID=
      jsonModelID;

   AI_FeatureHash=
      jsonFeatureHash;

   AI_InferenceMs=
      StringToDouble(
         jsonInferenceMs
      );

   AI_TimestampUTC=
      jsonTimestampUTC;


   //================================================
   // STALENESS CHECK (ETAPA 15.3)
   // Idade da previsao = TimeGMT() - timestamp_utc.
   // Previsao mais antiga que MaxPredictionAgeSec (>0)
   // e descartada como indisponivel (fail-safe):
   // o AIEngine usa o fallback local e o RequireAIJSON=true
   // bloqueia novas entradas (fail-closed).
   //================================================

   AI_IsStale=false;
   AI_AgeSeconds=-1.0;

   if(jsonTimestampUTC!="")
   {
      string ts=jsonTimestampUTC;

      if(StringLen(ts)>=19)
      {
         // ISO "yyyy-mm-ddTHH:MM:SS[.ffffff][+HH:MM]"
         StringReplace(ts,"-",".");
         StringReplace(ts,"T"," ");
         ts=StringSubstr(ts,0,19);

         datetime predUtc=StringToTime(ts);

         if(predUtc>0)
         {
            long age=(long)TimeGMT()-(long)predUtc;

            if(age<0)
               age=0;

            AI_AgeSeconds=(double)age;

            if(MaxPredictionAgeSec>0 && age>(long)MaxPredictionAgeSec)
            {
               AI_IsStale=true;

               Print(
                  "AI PREDICTION STALE | ",
                  symbol,
                  " | AGE=",
                  (string)age,
                  "s > LIMIT=",
                  IntegerToString(MaxPredictionAgeSec),
                  "s"
               );

               ResetAIState();
               return false;
            }
         }
      }
   }


   //================================================
   // LOG
   //================================================

   if(logOnce)
      Print(
         "AI PYTHON | ",
         AI_Symbol,
         " | ",
         AI_Signal,
         " | PRICE=",
         DoubleToString(
            AI_Price,
            _Digits
         ),
         " | BUY=",
         DoubleToString(
            AI_BuyProbability,
            2
         ),
         "%",
         " | SELL=",
         DoubleToString(
            AI_SellProbability,
            2
         ),
         "%",
         " | SCORE=",
         DoubleToString(
            AI_Score,
            2
         ),
         " | CONF=",
         DoubleToString(
            AI_Confidence,
            2
         ),
         "%"
      );


   return true;
}


//==================================================
// EXTRACT JSON VALUE
//==================================================

string ExtractJSON(
   string json,
   string key
)
{
   string search=
      "\"" +
      key +
      "\"";


   int start=
      StringFind(
         json,
         search
      );


   if(start<0)
      return "";


   start=
      StringFind(
         json,
         ":",
         start
      );


   if(start<0)
      return "";


   start++;


   int length=
      StringLen(
         json
      );


   //================================================
   // SKIP SPACES
   //================================================

   while(start<length)
   {
      int ch=
         StringGetCharacter(
            json,
            start
         );


      if(
         ch==' ' ||
         ch=='\t' ||
         ch=='\r' ||
         ch=='\n'
      )
      {
         start++;
      }
      else
      {
         break;
      }
   }


   //================================================
   // CHECK QUOTED VALUE
   //================================================

   bool quoted=false;


   if(
      start<length &&
      StringGetCharacter(
         json,
         start
      )=='"'
   )
   {
      quoted=true;
      start++;
   }


   int end=start;


   //================================================
   // READ VALUE
   //================================================

   if(quoted)
   {
      while(
         end<length &&
         StringGetCharacter(
            json,
            end
         )!='"'
      )
      {
         end++;
      }
   }
   else
   {
      while(
         end<length &&
         StringGetCharacter(
            json,
            end
         )!=',' &&
         StringGetCharacter(
            json,
            end
         )!='}' &&
         StringGetCharacter(
            json,
            end
         )!='\r' &&
         StringGetCharacter(
            json,
            end
         )!='\n'
      )
      {
         end++;
      }
   }


   if(end<=start)
      return "";


   string value=
      StringSubstr(
         json,
         start,
         end-start
      );


   StringTrimLeft(
      value
   );


   StringTrimRight(
      value
   );


   StringReplace(
      value,
      "\"",
      ""
   );


   return value;
}


//==================================================
// BUY SIGNAL CHECK
//==================================================

bool AIBuyAllowed(
   string symbol=""
)
{
   if(symbol=="")
      symbol=_Symbol;


   if(
      AI_Symbol!=symbol
   )
   {
      if(
         !LoadAIPrediction(
            symbol
         )
      )
      {
         return false;
      }
   }


   if(
      AI_Signal=="UNAVAILABLE" ||
      AI_Signal=="ERROR" ||
      AI_Signal=="HOLD"
   )
   {
      Print(
         "AI BLOCK | Estado nao executa vel: ",
         AI_Signal,
         " | ",
         symbol
      );
      EventAIBlock(symbol, "AI_" + AI_Signal);  // ETAPA 15.6
      return false;
   }

   return(
      AI_Signal=="BUY" ||
      AI_Signal=="STRONG_BUY"
   );
}


//==================================================
// SELL SIGNAL CHECK
//==================================================

bool AISellAllowed(
   string symbol=""
)
{
   if(symbol=="")
      symbol=_Symbol;


   if(
      AI_Symbol!=symbol
   )
   {
      if(
         !LoadAIPrediction(
            symbol
         )
      )
      {
         return false;
      }
   }


   if(
      AI_Signal=="UNAVAILABLE" ||
      AI_Signal=="ERROR" ||
      AI_Signal=="HOLD"
   )
   {
      Print(
         "AI BLOCK | Estado nao executa vel: ",
         AI_Signal,
         " | ",
         symbol
      );
      EventAIBlock(symbol, "AI_" + AI_Signal);  // ETAPA 15.6
      return false;
   }

   return(
      AI_Signal=="SELL" ||
      AI_Signal=="STRONG_SELL"
   );
}


//==================================================
// GET AI CONNECTOR SIGNAL
//==================================================

string GetAIConnectorSignal()
{
   return AI_Signal;
}


//==================================================
// GET AI SCORE
//==================================================

double GetAIScore()
{
   return AI_Score;
}


//==================================================
// GET AI CONFIDENCE
//==================================================

double GetAIConfidence()
{
   return AI_Confidence;
}


//==================================================
// GET AI BUY PROBABILITY
//==================================================

double GetAIBuy()
{
   return AI_BuyProbability;
}


//==================================================
// GET AI SELL PROBABILITY
//==================================================

double GetAISell()
{
   return AI_SellProbability;
}


//==================================================
// GET AI PRICE
//==================================================

double GetAIPrice()
{
   return AI_Price;
}


//==================================================
// GET AI SYMBOL
//==================================================

string GetAISymbol()
{
   return AI_Symbol;
}


//==================================================
// CHECK DATA FOR SYMBOL
//==================================================

bool AIDataForSymbol(
   string symbol
)
{
   if(symbol=="")
      return false;


   return(
      AI_Symbol==
      symbol
   );
}


//==================================================
// END
//==================================================

//==================================================
// GET AI META STRING (ETAPA 15/16 - ModelGovernance)
// Retorna "" com seguranca quando o campo nao existe.
// O parse atual do JSON NAO expoe metadados de modelo;
// portanto retornamos "" (honesto) e o ModelGovernance
// fica NAO-governado (fail-open, comportamento v1.2.0).
// Quando o pipeline Python publicar estes campos no JSON,
// basta adicionar a leitura aqui.
//==================================================
string GetAIMetaString(string key)
{
   // STATUS_DO_MODELO: derivado (producao) - politica v1.2.0
   if(key == "MODEL_STATUS")
      return "production";

   // Campos publicados pelo pipeline Python (Contrato A v2 - ETAPA 15.2.3)
   if(key == "MODEL_VERSION")
      return AI_ModelVersion;

   if(key == "MODEL_ID")
      return AI_ModelID;

   if(key == "FEATURE_HASH")
      return AI_FeatureHash;

   if(key == "INFERENCE_MS")
      return DoubleToString(AI_InferenceMs, 2);

   if(key == "TIMESTAMP_UTC")
      return AI_TimestampUTC;

   // Campo desconhecido -> "" (honesto)
   return "";
}

#endif
  
