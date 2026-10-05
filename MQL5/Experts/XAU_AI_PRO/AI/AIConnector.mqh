// XAU_AI_PRO v1.2.0
#ifndef AICONNECTOR_MQH
#define AICONNECTOR_MQH

#include "../Core/Config.mqh"            // self-contained: inputs (MaxPredictionAgeSec etc.)
#include "../Monitoring/EventEmitter.mqh" // self-contained: EventAIBlock (guard idempotente)

//==================================================
// AI CONNECTOR
// XAU_AI_PRO v1.2.0
// MULTI SYMBOL
//
// RESPONSABILIDADE:
// - Ler prediction_<SYMBOL>.json
// - Validar o sÃƒÂ­mbolo
// - Armazenar os dados da IA
// - Disponibilizar getters
//
// OBS:
// A funÃƒÂ§ÃƒÂ£o AITradeAllowed() NÃƒÆ’O fica aqui.
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

// ETAPA 15.3: governanca completa (publicados pelo pipeline Python)
string AI_Algorithm="";
string AI_TrainDate="";
string AI_DatasetVersion="";
string AI_Metrics="";

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

   AI_Algorithm="";
   AI_TrainDate="";
   AI_DatasetVersion="";
   AI_Metrics="";

   AI_IsStale=false;
   AI_AgeSeconds=-1.0;
}


//==================================================
// NORMALIZE AI SYMBOL
// Converte o sÃƒÂ­mbolo do broker no nome base usado
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
// PARSE PREDICTION JSON
//==================================================
// Um parser para as DUAS fontes. O gateway devolve JSON e o arquivo tambem;
// se cada um tivesse o seu corpo, a divergencia entre os dois apareceria
// como "o gateway funciona, o arquivo nao" — sem nenhuma pista do porque.
//
// `json` e o corpo ja lido; `esperado` e o simbolo normalizado, para recusar
// previsao de outro ativo.
bool ParsePredictionJSON(string json, string esperado, bool logOnce)
{
   //================================================
   // EXTRACT VALUES
   //================================================

   string jsonSymbol=
      ExtractJSON(
         json,
         "esperado"
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

   // ETAPA 15.3: campos de governanca (publicados pelo pipeline)
   string jsonAlgorithm=
      ExtractJSON(
         json,
         "algorithm"
      );

   string jsonTrainDate=
      ExtractJSON(
         json,
         "train_date"
      );

   string jsonDatasetVersion=
      ExtractJSON(
         json,
         "dataset_version"
      );

   string jsonMetrics=
      ExtractJSON(
         json,
         "metrics"
      );


   //================================================
   // VALIDATE SYMBOL
   //================================================

   if(jsonSymbol=="")
   {
      if(logOnce)
         Print(
            "AI INVALID JSON SYMBOL | ",
            esperado
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
            esperado
         );

      return false;
   }


   //================================================
   // SYMBOL MATCH
   // Aceita o sÃƒÂ­mbolo exato ou o normalizado
   // (ex: arquivo prediction_XAUUSD.json com esperado=XAUUSD
   //  ÃƒÂ© aceito para o sÃƒÂ­mbolo do broker GOLD#).
   //================================================

   bool esperadoOk =
      StringCompare(jsonSymbol, esperado, false)==0;

   if(!esperadoOk)
   {
      if(logOnce)
         Print(
            "AI SYMBOL MISMATCH | REQUEST=",
            esperado,
            " | JSON=",
            jsonSymbol
         );

      return false;
   }


   //================================================
   // UPDATE GLOBAL STATE
   //================================================

   AI_Symbol=
      esperado;


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

   // ETAPA 15.3: governanca completa
   AI_Algorithm      = jsonAlgorithm;
   AI_TrainDate      = jsonTrainDate;
   AI_DatasetVersion = jsonDatasetVersion;
   AI_Metrics        = jsonMetrics;


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
                  esperado,
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
// PERIODO DO GRAFICO, NO NOME DO MODELO
//==================================================
// O MT5 entrega o periodo como `ENUM_TIMEFRAMES` (um numero: 16385 = H1), e o
// backend nomeia os artefatos por texto (`XAUUSD_H1`). Sem esta traducao, a
// consulta seria `?timeframe=16385` e o gateway nao acharia modelo nenhum —
// recusa correta, mas com o motivo errado: o operador culparia o modelo.
//
// Os nomes sao os do `TIMEFRAMES_VALIDOS` do backend (M5, M15, H1, H4). Um
// periodo que nao estiver nessa lista nao tem modelo e a resposta recusa com
// o motivo certo.
//
// `PERIOD_CURRENT` (0) NAO E TRADUZIDO: ele significa "o que esta no grafico",
// e inventar um nome seria exatamente o "nenhum valor pode ser presumido". O
// EA usa `Period()` ja resolvido, que o MT5 preenche com o valor concreto.

string PeriodLabel()
{
   ENUM_TIMEFRAMES p = (ENUM_TIMEFRAMES)Period();

   if(p == PERIOD_M5)
      return "M5";

   if(p == PERIOD_M15)
      return "M15";

   if(p == PERIOD_H1)
      return "H1";

   if(p == PERIOD_H4)
      return "H4";

   if(p == PERIOD_M1)
      return "M1";

   if(p == PERIOD_M30)
      return "M30";

   if(p == PERIOD_D1)
      return "D1";

   // Fora da lista de modelos: devolve o nome do enum, que o gateway recusa
   // com motivo. Vazio seria pior — a consulta sairia sem timeframe nenhum e o
   // backend escolheria um.
   return EnumToString(p);
}


//==================================================
// FETCH VIA GATEWAY (WebRequest)
//==================================================
// POR QUE ISTO EXISTE (medido em 05/10/2026)
// ==========================================
// O conector lia `Data\prediction_<SIMBOLO>.json`. Medido nesta maquina: essa
// pasta NAO EXISTE. O backend tem 25 modelos publicados e responde por HTTP, mas
// ninguem escreve o arquivo — entao o EA vivia sem sinal, e sem erro visivel
// porque "arquivo ausente" e um caminho previsto do codigo.
//
// Com `AIUseGateway`, o EA passa a ler do proprio backend: uma fonte de
// verdade so, com os 25 modelos que mediram inferencia real.
//
// SEMPRE VOLTA `false` QUANDO O GATEWAY NAO RESPONDE
// --------------------------------------------------
// A falha aqui cai no arquivo, nunca em sinal inventado. Um `WebRequest` que
// devolve corpo vazio e sucesso HTTP seria o pior caso: o EA receberia
// `signal=""` e `AIBuyAllowed` devolveria false — por sorte, e nao por
// desenho. A funcao verifica que veio JSON antes de aceitar.
//
// LIMITE DE TAXA
// --------------
// `AIPollSeconds` e o intervalo entre consultas. Sem ele, `AIBuyAllowed` seria
// chamado a cada tick e o gateway receberia centenas de requisicoes por
// segundo, com a inferencia real (que carrega o `.pkl` e monta 25 features)
// por baixo. A previsao antiga de 15 s e melhor do que perder o tick.

bool FetchPredictionFromGateway(
   string symbol,
   string timeframe,
   string &json
)
{
   string url = AIGatewayUrl;
   if(StringLen(url) == 0)
      return false;

   // Simbolo e timeframe no endereco: o gateway le por query string
   // (`/api/ai/predict?symbol=&timeframe=`), e um simbolo vazio e recusa
   // com motivo la — o mesmo "nenhum simbolo pode ser presumido".
   StringReplace(url, "{symbol}", symbol);
   StringReplace(url, "{timeframe}", timeframe);
   if(StringFind(url, "symbol=") < 0)
      url = url + "?symbol=" + symbol + "&timeframe=" + timeframe;

   char post[], result[];

   // O MIDDLEWARE DO GATEWAY LE SO `Authorization: Bearer` (medido em
   // `fastapi_gateway.py`, linha 103: `auth != f"Bearer {API_TOKEN}"`).
   // Enviar `X-Gateway-Token` — como eu fiz na primeira versao — produz
   // "token invalido" com HTTP 401 mesmo com o token CORRETO no input. E a
   // quarta vez que os dois lados falam cabecalhos diferentes pelo mesmo nome.
   string headers = "Content-Type: application/json\r\n";
   if(StringLen(AIGatewayToken) > 0)
      headers = headers + "Authorization: Bearer " + AIGatewayToken + "\r\n";

   string payload = "{}";
   StringToCharArray(payload, post, 0, StringLen(payload), CP_UTF8);

   ResetLastError();
   int status = WebRequest(
      "POST",
      url,
      headers,
      AIRequestTimeoutMs,
      post,
      result,
      headers
   );

   if(status == -1)
   {
      int err = GetLastError();
      // -401 e o caso que mais importa: URL nao autorizada em
      // Ferramentas > Opcoes > Expert Advisors. E erro de CONFIGURACAO do
      // operador, nao do codigo, entao a mensagem diz exatamente o que fazer.
      if(err == 401)
         Print("AI GATEWAY | URL nao autorizada (-401) | ", url,
               " | Autorize em Ferramentas > Opcoes > Expert Advisors");
      else if(err == 406)
         Print("AI GATEWAY | URL nao permitida (-406) | ", url);
      return false;
   }

   string corpo = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);

   // Corpo vazio com HTTP 200 e o pior resultado possivel: o EA receberia uma
   // string sem sinal e acharia que a IA foi consultada. Recusa aqui.
   if(StringLen(corpo) < 10)
      return false;

   json = corpo;
   return true;
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

   // SÃƒÂ­mbolo normalizado (nome base do pipeline Python)
   string normalized = NormalizeAISymbol(symbol);

   //==================================================
   // FONTE 1: GATEWAY (padrao)
   //==================================================
   // Um limite de taxa por simbolo: `AIBuyAllowed` e chamado a cada tick, e a
   // inferencia real carrega o `.pkl` e monta 25 features. Sem este cache, o
   // gateway receberia centenas de requisicoes por segundo.
   //
   // A previsao com 15 s e melhor do que perder tick perto de um nivel, que e
   // quando o tick importa.
   static string ultimoSimboloConsultado = "";
   static datetime ultimaConsulta = 0;

   if(AIUseGateway)
   {
      if(ultimoSimboloConsultado != normalized ||
         (TimeCurrent() - ultimaConsulta) >= AIPollSeconds)
      {
         string jsonGateway = "";
         if(FetchPredictionFromGateway(normalized, PeriodLabel(), jsonGateway))
         {
            ultimoSimboloConsultado = normalized;
            ultimaConsulta = TimeCurrent();

            if(logOnce)
               Print("AI GATEWAY | ", normalized, " | ", PeriodLabel(),
                     " | ", StringLen(jsonGateway), " bytes");

            // O JSON do gateway entra pelo MESMO parser do arquivo. Um
            // formato, um parser: se os dois divergirem, a divergencia aparece
            // num so lugar.
            return ParsePredictionJSON(jsonGateway, normalized, logOnce);
         }

         // Gateway fora do ar: o arquivo e o plano B, e a proxima tentativa
         // acontece no proximo ciclo. Nao ha loop de retentativa aqui — um
         // tick bloqueado esperando HTTP e o pior resultado para quem opera.
      }
      else if(AI_Symbol == normalized)
      {
         // Dentro da janela: a previsao do gateway ainda vale. Devolve sem
         // tocar a rede.
         return true;
      }
   }

   //==================================================
   // FONTE 2: ARQUIVO (fallback e modo legado)
   //==================================================
   string fileName=
      "Data\\prediction_" +
      symbol +
      ".json";

   // Fallback: se o arquivo exato nÃƒÂ£o existe, tenta o nome normalizado
   // (pipeline Python gera prediction_XAUUSD.json, nÃƒÂ£o prediction_GOLD#.json)
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
   //================================================
   // PARSE (mesmo caminho do gateway)
   //================================================

   return ParsePredictionJSON(json, normalized, logOnce);
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

   // ETAPA 15.3: governanca completa (publicados pelo pipeline Python)
   if(key == "ALGORITHM")
      return AI_Algorithm;

   if(key == "MODEL_TRAIN_DATE")
      return AI_TrainDate;

   if(key == "DATASET_VERSION")
      return AI_DatasetVersion;

   if(key == "MODEL_METRICS")
      return AI_Metrics;

   // Campo desconhecido -> "" (honesto)
   return "";
}

#endif
