// XAU_AI_PRO v1.2.9
#ifndef AICONNECTOR_MQH
#define AICONNECTOR_MQH

#include "../Core/Config.mqh"            // self-contained: inputs (MaxPredictionAgeSec etc.)
#include "../Monitoring/EventEmitter.mqh" // self-contained: EventAIBlock (guard idempotente)

//==================================================
// AI CONNECTOR
// XAU_AI_PRO v1.2.9
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
// ESTADO DE IA POR SIMBOLO (P1.102)
//==================================================
// AI_Symbol/AI_Signal/AI_Confidence sao um slot UNICO por instancia, e o
// pipeline do grafico master percorre os 11 simbolos dentro da mesma volta.
// MEDIDO no journal de 04/11 as 21:27:55: a instancia (USDJPY,H1) escreveu
// "[AI] PYTHON | XAUUSD | SELL | CONF=76.80%" e, cinco segundos depois, o
// [RESUMO] da MESMA instancia publicou "IA=UNAVAILABLE 0.0%" - porque as
// visitas seguintes a EURUSD...USDCNH passaram pelo ramo de recusa, que faz
// ResetAIState(). O resumo lia o estado do ULTIMO simbolo visitado (USDCNH),
// nao o do par que o grafico negoceia, e o dono concluiu "a IA caiu" com a
// previsao do XAUUSD fresca na linha de cima.
//
// Esta cache e SO DE LEITURA para o resumo: nao entra em decisao, nao altera
// AI_Signal nem qualquer portao. Guarda os ultimos 32 simbolos visitados.
#define AI_STATE_CACHE_MAX 32

string   g_aiStateSymbol[AI_STATE_CACHE_MAX];
string   g_aiStateSignal[AI_STATE_CACHE_MAX];
double   g_aiStateConf[AI_STATE_CACHE_MAX];
datetime g_aiStateWhen[AI_STATE_CACHE_MAX];

// v1.2.167 (05/11/2026) - P1.131: prototipo antes do primeiro uso.
// AIClockRelogio() esta definido mais abaixo, junto do FetchPredictionFromGateway,
// e passou a ser a unica fonte de tempo deste ficheiro: TimeLocal em producao
// (avanca com o broker em baixo) e TimeCurrent no tester (tempo modelado).
datetime AIClockRelogio();

void AIRecordState(string symbol, string signal, double conf)
{
   if(symbol=="" || signal=="")
      return;

   int slot=-1;

   for(int i=0; i<AI_STATE_CACHE_MAX; i++)
   {
      if(g_aiStateSymbol[i]==symbol)
      {
         slot=i;
         break;
      }

      if(slot<0 && g_aiStateSymbol[i]=="")
         slot=i;
   }

   // Cache cheia: reutiliza o slot 0. Sao 32 simbolos para 15 graficos; o
   // pior caso e uma linha de resumo a mostrar um estado antigo, nunca uma
   // decisao de trade.
   if(slot<0)
      slot=0;

   g_aiStateSymbol[slot]=symbol;
   g_aiStateSignal[slot]=signal;
   g_aiStateConf[slot]=conf;
   g_aiStateWhen[slot]=AIClockRelogio();   // v1.2.167 P1.131: relogio unico
}

bool AIStateForSymbol(string symbol, string &signal, double &conf, datetime &when)
{
   signal="";
   conf=0.0;
   when=0;

   if(symbol=="")
      return false;

   for(int i=0; i<AI_STATE_CACHE_MAX; i++)
   {
      if(g_aiStateSymbol[i]==symbol)
      {
         signal=g_aiStateSignal[i];
         conf=g_aiStateConf[i];
         when=g_aiStateWhen[i];
         return true;
      }
   }

   return false;
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
   //
   // v1.2.95 (02/11/2026) - P1.83b: StringFind removia o sufixo em QUALQUER
   // posicao. MEDIDO no journal desta sessao: USDCHF, USDCAD, USDCNH, USDCZK,
   // USDCLP e USDCOP viravam "USD" porque o "C" do prefixo USD era o primeiro
   // encontrado. O gateway pedia symbol=USD e o parser recusava o arquivo
   // correto com "SIMBOLO DIFERENTE" - 6 dos 15 graficos ficavam sem IA mesmo
   // com Data\prediction_<SIMBOLO>.json valido. Agora so remove quando o
   // sufixo esta no FIM do nome.
   string suffixes[] = {"#", "C", "M", ".PRO", "_I", "."};
   for(int i=0; i<ArraySize(suffixes); i++)
   {
      int lenSuf=StringLen(suffixes[i]);
      int lenUp=StringLen(up);
      if(lenUp>lenSuf && StringSubstr(up, lenUp-lenSuf)==suffixes[i])
      {
         up=StringSubstr(up, 0, lenUp-lenSuf);
         break;
      }
   }

   // Mapeamento de aliases -> nome base do Python
   //
   // v1.2.167 (05/11/2026) - P1.130: "GOLD" e AMBIGUO nesta corretora.
   // MEDIDO no Market Watch as 21:30 de 05/11: existe GOLD (Barrick Gold
   // Corporation, XNYS, stock, contract_size=1, exemode=EXCHANGE, bid 37.40)
   // e existe XAUUSD (metal, contract_size=100, exemode=MARKET, bid 4106.66).
   // O alias mandava as DUAS para XAUUSD, portanto um grafico do stock GOLD
   // pedia ao gateway a previsao do METAL e recebia um numero que nao era
   // dele - a mesma troca de serie que o P1.113/P1.115 corrigiram do lado
   // dos indicadores. O alias passa a valer so para instrumento que NAO
   // seja de bolsa (o metal que a corretora chame GOLD).
   bool deBolsa = false;

   if(SymbolSelect(symbol, true))
      deBolsa = (SymbolInfoInteger(symbol, SYMBOL_TRADE_EXEMODE) == SYMBOL_TRADE_EXECUTION_EXCHANGE);

   if((up=="GOLD" || up=="XAU") && !deBolsa)
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

   // v1.2.95 (02/11/2026) - P1.83: o parser lia a chave "esperado", que
   // NAO existe em nenhum prediction_*.json. Resultado medido no journal de
   // 02/11: 55 linhas "[AI] JSON INVALIDO | SYMBOL=..." para arquivos que
   // existiam e eram validos, e a IA ficava offline mesmo com o arquivo
   // presente. O contrato publicado pelo pipeline usa "symbol"; e essa a
   // chave que este parser passa a ler. Nenhuma decisao muda: antes a
   // funcao devolvia false SEMPRE que o arquivo era lido.
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


   // v1.2.141 (P1.98): o gateway recusa responder quando o walk-forward nao
   // aprova o ativo e devolve, nesse caso,
   //   {"ok":true,"available":false,"reason":"...","signal":"NEUTRAL",
   //    "confidence":0.0,"price":0.0,...}
   // Este parser nao lia "available" e aceitava a recusa como se fosse uma
   // previsao valida. MEDIDO no journal as 20:31:39 de 04/11, grafico USDCNH
   // H1: "[AI] PYTHON | USDCNH | NEUTRAL | PRICE=0.00000 | BUY=0.00% |
   // SELL=0.00% | SCORE=0.00 | CONF=0.00%" - um preco zero publicado como se
   // fosse cotacao e uma IA "neutra" que nao existe. O mesmo acontece em
   // todos os simbolos sem modelo publicado (14 dos 15 graficos). Os campos
   // passam a ser lidos aqui e a recusa e tratada antes de qualquer escrita
   // no estado global.
   string jsonAvailable=
      ExtractJSON(
         json,
         "available"
      );

   string jsonReason=
      ExtractJSON(
         json,
         "reason"
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
            "[AI] JSON INVALIDO | SYMBOL=",
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
            "[AI] JSON INVALIDO | SIGNAL=",
            esperado
         );

      return false;
   }


   //================================================
   //================================================
   // DISPONIBILIDADE (P1.98)
   // available=false = o gateway RESPONDEU e recusou: nao ha previsao.
   // Tratar isto como previsao neutra com preco zero era fail-open: o
   // portao de IA avancado (AIEngine.mqh:512) so bloqueia quando
   // LoadAIPrediction devolve false ou o sinal e UNAVAILABLE/ERROR, logo a
   // recusa passava como "IA presente e neutra". Com AllowTradeWithoutAI
   // = false a IA ausente tem de ser ausencia, nao neutralidade.
   // A comparacao e textual de proposito: ExtractJSON devolve o valor cru,
   // e "false"/"0" cobrem as duas formas de o gateway escrever a recusa.
   // Sem a chave (ficheiro prediction_*.json local) nada muda.
   //================================================

   if(jsonAvailable!="")
   {
      string av=jsonAvailable;
      StringToLower(av);

      if(av=="false" || av=="0")
      {
         ResetAIState();

         AI_Symbol="";
         AI_Signal="UNAVAILABLE";

         // P1.102: a recusa fica registada por simbolo para o [RESUMO] poder
         // distinguir "o MEU par nao tem modelo" de "outro par da volta nao tem".
         AIRecordState(esperado, "UNAVAILABLE", 0.0);

         // Uma linha por simbolo por hora: 15 graficos a repetir a mesma
         // recusa em cada ciclo de polling enchia o journal sem informacao
         // nova - a razao do gateway ja diz o que falta.
         if(AccountLogGatePodeImprimir("ai_unavail_" + esperado, 3600))
            Print(
               "[AI] INDISPONIVEL | ",
               esperado,
               " | MOTIVO=",
               (jsonReason=="" ? "gateway recusou sem motivo" : jsonReason)
            );

         return false;
      }
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
            "[AI] SIMBOLO DIFERENTE | REQUEST=",
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

   // v1.2.95 (02/11/2026) - P1.83: o pipeline publica "timestamp" (ISO) e
   // este parser procurava apenas "timestamp_utc". Sem o fallback, um JSON
   // real ficava sem data e a verja de frescura nao tinha como reprovar.
   if(jsonTimestampUTC=="")
      jsonTimestampUTC=ExtractJSON(json,"timestamp");

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

               // P2.00: 129 linhas no dia a repetir "VENCIDA" com idades
               // diferentes; passa a 1x/h por CONTA e por simbolo.
               // P2.03: a chave levava o simbolo, logo os 15 graficos emitiam
               // ate 15 linhas por hora (15 simbolos x 1/h) para a MESMA
               // causa - a IA sem preco, que e uma so para a conta inteira.
               // A chave passa a ser da CONTA e a linha continua a nomear o
               // simbolo: nenhuma informacao de decisao se perde, so deixa de
               // ser repetida uma vez por simbolo.
               // P1.101 (05/11/2026): a leitura VENCIDA de OUTRO simbolo nao pode
               // apagar o estado de IA do simbolo que esta bom. MEDIDO no journal de
               // 04/11, instancia XAU_AI_PRO (USDJPY,H1): as 9 linhas PREDICAO VENCIDA
               // da sessao sairam TODAS desta instancia, nomeando XAUUSD (AGE 4666 s e a
               // subir), AUDUSD (152199 s) e USDJPY (153013 s) - ficheiros locais
               // obsoletos - e cada uma chamava ResetAIState(), que e um slot UNICO.
               // Resultado na mesma janela: [AI] GATEWAY | XAUUSD | 1122 bytes e
               // [AI] PYTHON | XAUUSD | SELL seguidos de IA=UNAVAILABLE 0.0% no
               // [RESUMO], porque a previsao fresca era apagada pela leitura velha de
               // outro par. O estado so e limpo quando o slot e do proprio simbolo
               // pedido (ou esta vazio); o primeiro aviso continua a sair com o mesmo
               // texto, logo o facto nunca fica escondido. O valor devolvido para o
               // simbolo pedido nao muda: continua false.
               bool estadoEhDoSimbolo =
                  (AI_Symbol=="" || AI_Symbol==esperado);

               if(estadoEhDoSimbolo)
               {
                  if(AccountLogGatePodeImprimir("ai_stale", 3600))
                  Print(
                     "[AI] PREDICAO VENCIDA | ",
                     esperado,
                     " | AGE=",
                     (string)age,
                     "s > LIMIT=",
                     IntegerToString(MaxPredictionAgeSec),
                     "s"
                  );

                  ResetAIState();
               }

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
         "[AI] PYTHON | ",
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


   // P1.102: guarda o estado por simbolo para o [RESUMO] da instancia.
   AIRecordState(esperado, AI_Signal, AI_Confidence);

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
//
// v1.2.133 (04/11/2026) - P-01b: o token do gateway deixa de depender de colar
// 64 caracteres em cada grafico.
// MEDIDO em 04/11/2026: os graficos levavam 17 caracteres em AIGatewayToken
// enquanto MQL5\Files\XAU_AI_PRO\.env tem XAU_GATEWAY_TOKEN com 64, e o
// gateway respondia 401 - havia dois valores para o mesmo nome e nenhum sitio
// no EA onde a divergencia aparecesse. Passa a existir UMA fonte: o input
// quando tem tamanho plausivel (>= 32 caracteres), senao o .env da sandbox -
// a mesma raiz que este modulo ja usa para a previsao, sem FILE_COMMON. O
// valor lido nunca vai para o journal: quem o publica e a linha de erro, e so
// o NUMERO de caracteres enviados.
string AIGatewayTokenEfetivo()
{
   if(StringLen(AIGatewayToken) >= 32)
      return(AIGatewayToken);

   int h = FileOpen("XAU_AI_PRO\\.env",
                    FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE)
      return(AIGatewayToken);

   string achado = "";
   while(!FileIsEnding(h))
     {
      string linha = FileReadString(h);
      if(StringFind(linha, "XAU_GATEWAY_TOKEN") != 0)
         continue;

      int eq = StringFind(linha, "=");
      if(eq < 0)
         continue;

      achado = StringSubstr(linha, eq + 1);
      StringTrimLeft(achado);
      StringTrimRight(achado);
      StringReplace(achado, "\"", "");
      // aspas simples nao aparecem no .env gerado; so as duplas sao removidas
      break;
     }
   FileClose(h);

   // .env ilegivel, chave ausente ou valor curto: mantem o input exactamente
   // como antes, para que esta funcao nunca piore um caso que ja funcionava.
   return(StringLen(achado) >= 32 ? achado : AIGatewayToken);
}

// v1.2.134 (04/11/2026) - P-01d: a porta do gateway tambem passa a vir do .env.
// MEDIDO em 04/11/2026 com list_open_charts: as 13 janelas do perfil
// XAI_P216_LIVE estao anexadas com AIGatewayUrl em 127.0.0.1:9001 - o servidor
// MCP embutido do terminal, nao o gateway - e com AIGatewayToken contendo o
// NOME da variavel (17 caracteres), que e a origem exacta da divergencia 17 vs
// 64. O MT5 guarda as ENTRADAS com que o grafico foi anexado e elas ganham a
// omissao do codigo, portanto mudar a omissao nao corrige grafico aberto. Em
// vez de reescrever 13 graficos e arriscar todas as entradas, o .env passa a
// ser a unica fonte do ENDERECO, como ja e do token: se XAU_GATEWAY_PORT
// existir e for so digitos, a porta da entrada e substituida; sem a chave,
// nada muda.
string AIGatewayPortaEnv()
{
   static bool   lido  = false;
   static string porta = "";

   if(!lido)
     {
      lido = true;

      int h = FileOpen("XAU_AI_PRO\\.env",
                       FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
      if(h != INVALID_HANDLE)
        {
         while(!FileIsEnding(h))
           {
            string linha = FileReadString(h);
            if(StringFind(linha, "XAU_GATEWAY_PORT") != 0)
               continue;

            int eq = StringFind(linha, "=");
            if(eq < 0)
               continue;

            string v = StringSubstr(linha, eq + 1);
            StringTrimLeft(v);
            StringTrimRight(v);
            StringReplace(v, "\"", "");

            int n = StringLen(v);
            bool soDigitos = (n > 0);
            for(int i = 0; i < n && soDigitos; i++)
              {
               ushort c = StringGetCharacter(v, i);
               if(c < '0' || c > '9')
                  soDigitos = false;
              }

            if(soDigitos)
               porta = v;

            break;
           }
         FileClose(h);
        }
     }

   return porta;
}

// Troca APENAS a porta da autoridade da URL: esquema, host, rota e placeholders
// ficam intactos. URL sem "://" ou sem porta declarada nao e reescrita.
string AIGatewayUrlEfetiva()
{
   string alvo = AIGatewayUrl;
   if(StringLen(alvo) == 0)
      return alvo;

   string porta = AIGatewayPortaEnv();
   if(StringLen(porta) == 0)
      return alvo;

   int esquema = StringFind(alvo, "://");
   if(esquema < 0)
      return alvo;

   int inicio = esquema + 3;
   int fim    = StringFind(alvo, "/", inicio);
   if(fim < 0)
      fim = StringLen(alvo);

   string autoridade = StringSubstr(alvo, inicio, fim - inicio);
   int doisPontos = StringFind(autoridade, ":");
   if(doisPontos >= 0)
      autoridade = StringSubstr(autoridade, 0, doisPontos);

   return StringSubstr(alvo, 0, inicio) + autoridade + ":" + porta + StringSubstr(alvo, fim);
}

// v1.2.164 (05/11/2026) - P1.127: relogio que NAO congela quando o broker cai.
// MEDIDO nesta sessao (05/11, 20:05-20:11): o TimeCurrent() e tempo do SERVIDOR
// e so avanca quando chegam ticks. Com a ligacao ao broker em baixo ele fica
// parado, e isso partiu tres coisas ao mesmo tempo:
//   (a) o poll do gateway deixava de disparar - o EA ficava cego exactamente
//       durante a avaria, que e quando mais precisa de sondar;
//   (b) "TimeCurrent() - lastWrErrLog" dava 0 para sempre, logo a linha
//       "[AI] GATEWAY falhou" NUNCA era publicada (foi por isso que a queda
//       do gateway nao deixou rasto nenhum no journal);
//   (c) o "cego=Ns" da linha de recuperacao media tempo que nao tinha passado.
// TimeLocal() e o relogio do computador: avanca sempre, com ou sem ticks.
// No Strategy Tester devolve TimeCurrent() para o backtest continuar a medir
// tempo MODELADO, exactamente como antes - nada muda dentro do tester.
datetime AIClockRelogio()
{
   if(MQLInfoInteger(MQL_TESTER))
      return(TimeCurrent());

   return(TimeLocal());
}


bool FetchPredictionFromGateway(
   string symbol,
   string timeframe,
   string &json
)
{
   string url = AIGatewayUrlEfetiva();
   if(StringLen(url) == 0)
      return false;

   // v1.2.30 (30/10/2026) - P1.3/P-01: backoff de transporte. MEDIDO na
   // v1.2.29, janela 17:05:00-17:08:30: 51 linhas "AI GATEWAY | WebRequest
   // falhou | erro 4014" em 3,5 min (~900/hora nos 16 graficos), porque cada
   // grafico chama o gateway 1x/min e o WebRequest esta DESABILITADO no
   // terminal (P-01, decisao do dono). 4014/4060/5200/5202 sao erro de
   // CONFIGURACAO: nao se curam sozinhos durante a sessao, e insistir so gasta
   // requisicao e journal. Depois de 3 falhas duras seguidas o conector para de
   // tentar por AI_GW_COOLDOWN_SEC (o temporizador VOLTA a tentar, para o EA
   // retomar sozinho quando o dono habilitar o WebRequest). O arquivo local
   // Data\prediction_<SIMBOLO>.json continua a ser a fonte de fallback.
   static datetime s_gwCooldownUntil = 0;
   static int      s_gwHardFails     = 0;
   const int       AI_GW_COOLDOWN_SEC = 1800;

   // v1.2.130 (03/11/2026) - P2.21: 401/403 e erro de CREDENCIAL, nao de
   // rede. MEDIDO no journal do expert entre 23:37:09 e 23:46:19 de 03/11,
   // com a v1.2.128 nos 15 graficos: a linha "[AI] GATEWAY | HTTP 401"
   // saia 1x/min por GRAFICO (15/min, cerca de 900/h) porque a unica janela
   // era um static de 60 s POR INSTANCIA, e token recusado nao se cura
   // sozinho durante a sessao. O transporte ja tinha backoff (4014/4060);
   // a credencial nao tinha nenhum. Agora 3 recusas seguidas armam o MESMO
   // tipo de cooldown de 1800 s: o conector para de bater a porta e volta a
   // tentar 30 min depois, sozinho, quando o operador corrigir o token.
   // O fallback fica identico: FetchPredictionFromGateway devolve false e
   // LoadAIPrediction cai em Data\prediction_<SIMBOLO>.json, exactamente o
   // mesmo caminho de quando o 401 acontecia a cada 30 s.
   static datetime s_gwAuthCooldownUntil = 0;
   static int      s_gwAuthFails         = 0;
   // v1.2.163: o cooldown FIXO de 1800 s da credencial deu lugar a escadaGw.

   // v1.2.163 (05/11/2026) - P1.126: RECONEXAO AUTONOMA DO GATEWAY.
   // MEDIDO nesta sessao, com o gateway Python em 127.0.0.1:9011: com o
   // processo no ar o EA recebia 200 e inferencia real; ao parar o processo o
   // journal passou a "resposta NAO-HTTP" (1001/1003) e voltou a 200 assim que
   // o processo subiu, sem ninguem tocar no grafico. Nesse caminho nenhum
   // cooldown armava, portanto essa metade ja se curava sozinha no ciclo
   // seguinte (AIPollSeconds = 15 s). O que NAO se curava era o resto, e sao
   // esses tres pontos que mudam aqui:
   //   (1) 5202 (TIMEOUT) estava na lista dos erros de CONFIGURACAO e armava
   //       1800 s de cegueira ao terceiro timeout seguido. Um backend que
   //       engasga (inferencia pesada, disco, primeira chamada a frio) produz
   //       TIMEOUTS, nao recusas de ligacao: um unico engasgo custava 30 min
   //       sem IA mesmo depois de o servidor voltar. Passa a ser TRANSITORIO,
   //       com escada propria que volta a tentar.
   //   (2) A credencial (401/403) esperava 1800 s fixos. Se o dono corrigir o
   //       token, o EA tem de o apanhar em minutos, nao em meia hora. Passa a
   //       usar a mesma escada.
   //   (3) Um HTTP 200 nao limpava o estado de forma explicita e nao deixava
   //       rasto nenhum de que a sessao tinha recuperado sozinha. Passa a
   //       limpar tudo e a publicar [AI] GATEWAY RECUPERADO com o numero de
   //       falhas e o tempo em que ficou cego.
   // 4014/4060/5200 continuam nos 1800 s de proposito: sao configuracao do
   // terminal (Ferramentas > Opcoes > Expert Advisors) e so o operador as
   // cura. 5201/5203 continuam SEM cooldown: e o que um gateway MORTO devolve,
   // e o EA tem de o apanhar no ciclo seguinte, nao dentro de meia hora.
   static int      s_gwTransFails     = 0;   // timeouts seguidos (5202)
   static datetime s_gwBlindSince     = 0;   // inicio da cegueira actual
   static int      s_gwBlindFails     = 0;   // falhas desde o ultimo 200

   int escadaGw[5] = {60, 120, 300, 600, 900};   // espera em segundos

   if(AIClockRelogio() < s_gwAuthCooldownUntil)
      return false;

   // Cooldowns: configuracao (AI_GW_COOLDOWN_SEC, 4014/4060/5200), credencial
   // (401/403, escadaGw) e transitorio (5202, escadaGw). Os tres EXPIRAM
   // sozinhos: o temporizador e a sonda. Nenhum deles exige que o operador
   // reanexe o EA ou reinicie o terminal.

   if(AIClockRelogio() < s_gwCooldownUntil)
      return false;

   // Simbolo e timeframe no endereco: o gateway le por query string
   // (`/api/ai/predict?symbol=&timeframe=`), e um simbolo vazio e recusa
   // com motivo la — o mesmo "nenhum simbolo pode ser presumido".
   StringReplace(url, "{symbol}", symbol);
   StringReplace(url, "{timeframe}", timeframe);
   if(StringFind(url, "symbol=") < 0)
      url = url + "?symbol=" + symbol + "&timeframe=" + timeframe;

   char post[], result[];
   string result_headers = "";

   // O MIDDLEWARE DO GATEWAY LE SO `Authorization: Bearer` (medido em
   // `fastapi_gateway.py`, linha 103: `auth != f"Bearer {API_TOKEN}"`).
   // Enviar `X-Gateway-Token` — como eu fiz na primeira versao — produz
   // "token invalido" com HTTP 401 mesmo com o token CORRETO no input. E a
   // quarta vez que os dois lados falam cabecalhos diferentes pelo mesmo nome.
   string headers = "Content-Type: application/json\r\n";
   string tokenGW = AIGatewayTokenEfetivo();
   if(StringLen(tokenGW) > 0)
      headers = headers + "Authorization: Bearer " + tokenGW + "\r\n";

   // v1.2.132 (04/11/2026) - P-01: o EA fazia POST numa rota que o gateway
   // declara como GET (`backend\fastapi_gateway.py`, `@app.get("/api/ai/predict")`).
   // MEDIDO em 04/11/2026: um POST nessa rota recebe 405 Method Not Allowed, e
   // como o middleware de autenticacao corre ANTES do routing o sintoma visivel
   // era 401 - o defeito de metodo ficava escondido atras de um falso problema
   // de credencial. A rota e de leitura e o contrato e GET com corpo vazio; os
   // parametros continuam na query string (?symbol=&timeframe=), que e onde o
   // servidor os le.
   ResetLastError();
   int status = WebRequest(
      "GET",
      url,
      headers,
      AIRequestTimeoutMs,
      post,
      result,
      result_headers
   );

   // v1.2.163 (05/11/2026) - P1.126: relogio da cegueira. TODO resultado
   // diferente de 200 conta como falha; a primeira arma o instante de inicio.
   // Serve apenas para a linha de recuperacao poder publicar quantas falhas
   // houve e por quanto tempo o EA esteve sem IA - sem esse numero, "voltou
   // sozinho" e uma afirmacao nao verificavel.
   if(status != 200)
     {
      if(s_gwBlindSince == 0)
         s_gwBlindSince = AIClockRelogio();
      s_gwBlindFails++;
     }

   if(status == -1)
   {
      int err = GetLastError();
      // -401 e o caso que mais importa: URL nao autorizada em
      // Ferramentas > Opcoes > Expert Advisors. E erro de CONFIGURACAO do
      // operador, nao do codigo, entao a mensagem diz exatamente o que fazer.
      // v1.2.18 (29/10/2026): a falha do WebRequest era MUDA quando o erro
      // nao era 401/406 (ex.: 4014/4060 = WebRequest desabilitado nas opcoes
      // do terminal). O journal so mostrava "AI LOAD" e "AI INVALID JSON",
      // escondendo a causa real. Agora o codigo do erro aparece 1x por minuto.
      static datetime lastWrErrLog = 0;

      // v1.2.30: 4014/4060/5200/5202 = configuracao do terminal. Aviso 1x/30 min
      // (era 1x/min) e contador de falhas duras que arma o cooldown do topo.
      // v1.2.163 (05/11/2026) - P1.126: 5202 saiu da lista de CONFIGURACAO.
      // 5202 e TIMEOUT (o servidor existe, nao respondeu no prazo), nao lista
      // de URLs nem permissao: cura-se sozinho quando o backend desengasga,
      // logo esperar 1800 s e tempo perdido. 4014/4060/5200 continuam a ser
      // configuracao do terminal e mantem a espera longa. 5201 (ligacao
      // recusada) e 5203 (pedido falhou) continuam SEM cooldown: e
      // exactamente o que um gateway morto devolve.
      bool hardErr   = (err == 4014 || err == 4060 || err == 5200);
      bool transErr  = (err == 5202);
      int  errLogSec = (hardErr ? 14400 : 300);

      // v1.2.164 (05/11/2026) - P1.127: o portao por CONTA era 21600 (1x/6h)
      // para TODOS os codigos. MEDIDO nesta sessao: com o gateway parado, o
      // 5201 ja tinha sido publicado antes e ficou mudo 6 horas, portanto a
      // queda e a recuperacao passaram SEM UMA UNICA LINHA no journal. Erro de
      // configuracao (4014/4060/5200) nao se cura sozinho e continua em 6 h,
      // para nao fazer spam; erro de transporte (5201/5202/5203) passa a
      // 300 s, para cada tentativa de reconexao deixar rasto verificavel.
      int  gateErrSec = (hardErr ? 21600 : 300);

      if(hardErr)
        {
         s_gwHardFails++;
         if(s_gwHardFails >= 3)
            s_gwCooldownUntil = AIClockRelogio() + AI_GW_COOLDOWN_SEC;
        }
      else if(transErr)
        {
         // Escada transitoria: o 1o e o 2o timeout continuam a tentar no ciclo
         // normal (o poll de 15 s ja e barato); do 3o em diante espera
         // 60/120/300/600/900 s. O tecto de 900 s e a diferenca pratica para
         // os 1800 s anteriores: um gateway que volte e apanhado em 15 min no
         // pior caso, sem ninguem tocar em nada.
         s_gwTransFails++;
         int idxEsc = s_gwTransFails - 3;
         if(idxEsc >= 0)
           {
            if(idxEsc > 4)
               idxEsc = 4;
            s_gwCooldownUntil = AIClockRelogio() + escadaGw[idxEsc];
           }
        }

      if(AIClockRelogio() - lastWrErrLog >= errLogSec && AccountLogGatePodeImprimir("aigw_" + IntegerToString(err), gateErrSec))   // P1.90: por CONTA e por codigo
        {
         lastWrErrLog = AIClockRelogio();
         // v1.2.88 (02/11/2026) - P1.75: tag [AI] e texto curto. 4014/4060
         // continuam a ser WebRequest desabilitado em Opcoes > Expert Advisors;
         // 5200/5202 = URL nao autorizada.
         // v1.2.129 (03/11/2026) - P2.20: 4014 tem DUAS causas (URL fora da
         // lista OU checkbox "Allow WebRequest" desligado) e publicar so a
         // primeira mandava o operador ao lugar errado. E a mesma doenca que o
         // P2.19 corrigiu no script de diagnostico. 4060 e dominio ausente;
         // 5200/5202 sao rede/URL. O codigo continua a ser impresso.
         string motivoWr = "erro nao classificado";
         if(err == 4014)
            motivoWr = "NAO PERMITIDO (URL fora da lista, ou checkbox 'Allow WebRequest' desligado)";
         else if(err == 4060)
            motivoWr = "URL nao adicionada a lista (dominio ausente)";
         else if(err == 5200)
            motivoWr = "URL invalida para o WebRequest";
         else if(err == 5202)
           {
            // v1.2.163 - P1.126: 5202 e TIMEOUT, nao lista. 5201/5203 sao o
            // que um gateway PARADO devolve - sem os nomear, a simulacao de
            // queda aparecia no journal como "erro nao classificado".
            motivoWr = "TIMEOUT (o servidor nao respondeu no prazo; transitorio, o EA volta a tentar sozinho)";
           }
         else if(err == 5201)
            motivoWr = "LIGACAO RECUSADA (ninguem a escutar nessa porta - gateway parado?)";
         else if(err == 5203)
            motivoWr = "PEDIDO FALHOU (a ligacao caiu a meio)";
         Print("[AI] GATEWAY falhou | erro=", err, " | ", url, " | ", motivoWr);
        }

      if(err == 401)
         Print("[AI] GATEWAY | URL nao autorizada (-401) | ", url,
               " | Autorize em Ferramentas > Opcoes > Expert Advisors");
      else if(err == 406)
         Print("[AI] GATEWAY | URL nao permitida (-406) | ", url);
      return false;
   }

   // HTTP DE ERRO NAO E PREVISAO (29/10/2026)
   // MEDIDO NESTA MAQUINA: sem `AIGatewayToken` o gateway responde 401 com
   // corpo JSON de erro. Esse corpo tem mais de 10 bytes, entao passava no
   // teste de tamanho abaixo, o parser falhava, o conector caia no arquivo
   // antigo e o journal mostrava apenas "IA indisponivel" — nunca o 401. A
   // causa real (token vazio) ficava invisivel para o operador.
   if(status != 200)
   {
      // v1.2.30: o transporte respondeu (HTTP != 200), logo o WebRequest esta
      // habilitado: zera o backoff de transporte para nao punir token/rota.
      s_gwHardFails     = 0;
      s_gwCooldownUntil = 0;
      s_gwTransFails    = 0;   // P1.126: resposta HTTP = transporte vivo

      // P2.21: credencial recusada (401/403) nao se cura sozinha durante a
      // sessao. Tres recusas seguidas armam o cooldown de credencial; o
      // temporizador volta a tentar, como no backoff de transporte.
      if(status == 401 || status == 403)
        {
         s_gwAuthFails++;
         if(s_gwAuthFails >= 3)
           {
            // v1.2.163 - P1.126: mesma escada da perna transitoria. Com o
            // token errado isto vale 60/120/300/600/900 s entre sondas: se o
            // dono corrigir o .env, o EA apanha-o em 15 min no pior caso, em
            // vez dos 30 min fixos de antes.
            int idxAuth = s_gwAuthFails - 3;
            if(idxAuth > 4)
               idxAuth = 4;
            s_gwAuthCooldownUntil = AIClockRelogio() + escadaGw[idxAuth];
           }
        }
      else
         s_gwAuthFails = 0;

      static datetime lastStatusLog = 0;
      datetime statusNow = AIClockRelogio();

      // v1.2.130 (03/11/2026) - P2.21: o aviso de HTTP != 200 tinha janela de 60 s
// POR PROGRAMA. MEDIDO: 13 graficos x 1 linha/min = ~780 linhas/hora no journal
// com um unico 401 de configuracao, que nao muda de minuto para minuto. O gate
// agora e por CONTA (arquivo em Common, igual ao AccountLogGate dos outros
// avisos): a mesma combinacao tag+status imprime 1x/30 min, venha de quantos
// graficos vier. A janela local sobe para 300 s como segunda barreira.
      if(statusNow - lastStatusLog >= 300 &&
         AccountLogGatePodeImprimir("aigw_http_" + IntegerToString(status), (status > 599 ? 300 : 1800)))
      {
         lastStatusLog = statusNow;
         // v1.2.129 (03/11/2026) - P2.20: o transporte respondeu, logo o
         // WebRequest esta LIGADO e a URL esta na lista. Culpar sempre o token
         // (texto fixo "401/403 = token ausente ou invalido") escondia duas
         // causas distintas: token VAZIO e token RECUSADO. Agora a mensagem
         // separa por EVIDENCIA - comprimento do token enviado, codigo HTTP e
         // tamanho do corpo. O VALOR do token nunca e impresso.
         int    nTok   = StringLen(AIGatewayTokenEfetivo());
         string corpoR = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
         int    nCorpo = StringLen(corpoR);
         string motivo = "erro nao classificado";
         if(status == 401 || status == 403)
           {
            if(nTok == 0)
               motivo = "token AUSENTE (input AIGatewayToken vazio)";
            else
               motivo = "token RECUSADO (" + IntegerToString(nTok) +
                        " caracteres enviados; o gateway espera o XAU_GATEWAY_TOKEN do .env)";
           }
         else if(status == 404)
            motivo = "rota inexistente nesse servidor - confira AIGatewayUrl e se algo serve /api/ai/predict nessa porta";
         else if(status == 422)
            motivo = "requisicao recusada pelo servidor (parametros de symbol/timeframe)";
         else if(status > 599)
            motivo = "resposta NAO-HTTP (codigo devolvido pelo transporte, nao pelo servidor; um codigo HTTP valido termina em 599)";
         else if(status >= 500)
            motivo = "backend fora do ar";
         Print("[AI] GATEWAY | HTTP ", status, " | ", url, " | ", motivo,
               " | WebRequest=LIGADO (a chamada SAIU) | corpo=", nCorpo, "B");
         if(nCorpo > 0)
            Print("[AI] GATEWAY | resposta: ", StringSubstr(corpoR, 0, 200));
      }

      return false;
   }

   string corpo = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
   // v1.2.163 - P1.126: a limpeza do estado e a linha de recuperacao passaram
   // para DEPOIS do teste de corpo, para so existirem quando ha mesmo uma
   // previsao utilizavel (ver abaixo).

   // Corpo vazio com HTTP 200 e o pior resultado possivel: o EA receberia uma
   // string sem sinal e acharia que a IA foi consultada. Recusa aqui.
   if(StringLen(corpo) < 10)
      return false;

   // v1.2.163 (05/11/2026) - P1.126: HTTP 200 com corpo util e a PROVA de que
   // o caminho esta bom, logo zera TODO o estado de falha de uma vez, em vez
   // de depender de o ramo anterior ter limpado por efeito colateral. A linha
   // [AI] GATEWAY RECUPERADO sai uma vez por recuperacao (portao por CONTA,
   // 1800 s) com o numero de falhas e o tempo em que a instancia esteve cega:
   // e a evidencia medivel no journal de que o EA voltou sozinho, sem
   // reanexar, sem reiniciar o terminal e sem tocar no grafico.
   if(s_gwBlindSince > 0)
     {
      int segCego = (int)(AIClockRelogio() - s_gwBlindSince);
      if(segCego < 0)
         segCego = 0;   // relogio do servidor recuou (mudanca de sessao)
      // v1.2.164 - P1.127: 1800 s -> 300 s. A linha sai uma vez por recuperacao
      // e o portao e por CONTA (13 graficos partilham o mesmo ficheiro), logo
      // 300 s continua a ser uma linha de cada vez; so deixa de esconder uma
      // segunda queda dentro da mesma meia hora, que era o caso ao testar.
      if(AccountLogGatePodeImprimir("aigw_recuperado", 300))
         Print("[AI] GATEWAY RECUPERADO | ", symbol, " | ", timeframe,
               " | falhas=", s_gwBlindFails, " | cego=", segCego,
               "s | resposta=", StringLen(corpo), "B | sem intervencao");
     }

   s_gwAuthFails         = 0;   // P2.21: credencial aceite
   s_gwHardFails         = 0;
   s_gwTransFails        = 0;
   s_gwCooldownUntil     = 0;
   s_gwAuthCooldownUntil = 0;
   s_gwBlindSince        = 0;
   s_gwBlindFails        = 0;

   json = corpo;
   return true;
}


//==================================================
// LOAD AI PREDICTION
//==================================================

bool LoadAIPrediction(string symbol="")
{
   // Log de diagnostico (evita spam a cada tick)
   //
   // v1.2.33 (30/10/2026) - P1.3 rodada 5: era 1x/minuto e, com o gateway
   // inalcancavel (erro 4014) e sem os arquivos Data\prediction_*.json, as
   // tres linhas de diagnostico ("AI LOAD", "AI FILE NOT FOUND",
   // "AI INVALID JSON") somavam ~700 linhas/hora nos 16 graficos - medido em
   // 17:42-17:46 da v1.2.32. O estado que elas descrevem nao muda de minuto
   // para minuto: o arquivo continua ausente ou o JSON continua invalido.
   // Agora 1x/30 min. `logOnce` aqui gateia SOMENTE impressao (as decisoes
   // usam o retorno de ParsePredictionJSON), entao o comportamento de sinal
   // nao muda: so a frequencia do aviso.
   static datetime lastLogTime = 0;
   datetime logNow = AIClockRelogio();   // v1.2.167 P1.131: portao de log nao pode congelar
   bool logOnce = (logNow - lastLogTime >= 1800);
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
         (AIClockRelogio() - ultimaConsulta) >= AIPollSeconds)
      {
         string jsonGateway = "";
         if(FetchPredictionFromGateway(normalized, PeriodLabel(), jsonGateway))
         {
            ultimoSimboloConsultado = normalized;
            ultimaConsulta = AIClockRelogio();

            if(logOnce)
            {
               // P1.105: o journal mostrava so o tamanho da resposta. MEDIDO
               // em 04/11: 55 linhas "[AI] GATEWAY | <simbolo> | H1 | 357
               // bytes" sem nada que dissesse que 357 B era uma RECUSA do
               // walk-forward e nao uma avaria; o motivo so saia 1x/hora na
               // linha INDISPONIVEL. Aqui vai o estado, sem repetir o motivo.
               string avLog = ExtractJSON(jsonGateway, "available");
               StringToLower(avLog);

               string estadoG = (avLog == "false" || avLog == "0")
                                ? "disponivel=false"
                                : "disponivel=true";

               Print("[AI] GATEWAY | ", normalized, " | ", PeriodLabel(),
                     " | ", StringLen(jsonGateway), " bytes | ", estadoG);
            }

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
   // P1.103 (05/11/2026): uma falha de TRANSPORTE do gateway nao pode trocar
   // uma previsao fresca em memoria por um ficheiro local obsoleto. MEDIDO no
   // journal de 04/11: 21:21:29.101 [AI] PREDICAO VENCIDA | XAUUSD | AGE=6787s
   // seguida de 21:21:44.446 [RESUMO] com IA=UNAVAILABLE 0.0%, enquanto a sonda
   // ao MESMO endpoint devolvia available=true (XAUUSD SELL conf 81.0). O
   // ficheiro Data/prediction_XAUUSD.json esta parado desde ~19:28 - quem o
   // escreve e o pipeline Python, nao o EA - por isso cada consulta falhada ao
   // gateway virava "IA indisponivel" e bloqueava a entrada ate ao poll seguinte.
   // Se o gateway JA respondeu para ESTE simbolo e a previsao em memoria ainda
   // esta dentro de MaxPredictionAgeSec, devolve-se essa previsao e nao se le o
   // ficheiro. O ficheiro continua a ser o plano B quando nao ha nada em memoria
   // (arranque, modo legado, tester). Nenhuma regra de trading muda: sem
   // previsao fresca o retorno continua false e a entrada continua bloqueada
   // com AllowTradeWithoutAI=false.
   if(AIUseGateway &&
      AI_Symbol == normalized &&
      AI_Price > 0.0 &&
      ultimaConsulta > 0 &&
      MaxPredictionAgeSec > 0 &&
      (long)(AIClockRelogio() - ultimaConsulta) <= (long)MaxPredictionAgeSec)
      return true;
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


   // v1.2.111 (03/11/2026) - P1.99: MEDIDO no journal de 03/11 -
   // 250 linhas [AI] LOAD (15 instancias x 2/hora) a repetir o MESMO
   // caminho de ficheiro. A janela passa a ser por CONTA e por simbolo,
   // como ja acontece no [SCANNER]: o texto identico sai 1x/hora no total.
   // P2.00: o caminho do ficheiro nao muda entre leituras - 1x/dia por CONTA
   // e por simbolo em vez de 1x/hora.
   // v1.2.137 (04/11/2026) - P1.92: a previsao passa a ser procurada tambem
   // em FILE_COMMON. MEDIDO no log do tester de 04/11 (run das 18:08, XAUUSD
   // H1, XAI_BASE_v131.ini): "[AI] FILE EM FALTA |
   // Data\prediction_XAUUSD.json" repetido durante a simulacao. Dentro do
   // Strategy Tester o sandbox e Tester\Agent-<ip>-<porta>\MQL5\Files\ e o
   // pipeline Python escreve em <terminal>\MQL5\Files\, logo o backtest nao
   // via o ficheiro que a producao ve. O ficheiro existia (mtime 04/11
   // 22:28) e era invisivel - o backtest media um EA SEM IA, exactamente o
   // mesmo tipo de defeito do P1.91 (ADX nunca lido). FILE_COMMON resolve
   // para a pasta comum verdadeira tambem dentro do tester (medido na
   // v1.2.45), por isso a leitura tenta a raiz LOCAL primeiro e a COMMON
   // depois: em producao, onde o local existe, nada muda.
   int fileRoot=0;

   if(!FileIsExist(fileName) && fileRoot==0)
   {
      if(FileIsExist(fileName, FILE_COMMON))
      {
         fileRoot=FILE_COMMON;
      }
      else if(normalized!=symbol)
      {
         string altCommon=
            "Data\\prediction_" +
            normalized +
            ".json";

         if(FileIsExist(altCommon, FILE_COMMON))
         {
            fileName=altCommon;
            fileRoot=FILE_COMMON;
         }
      }
   }


   if(logOnce && AccountLogGatePodeImprimir("ai_load_" + symbol, 86400))
   // v1.2.142 (P1.100): o segundo if(logOnce) que aqui estava era redundante -
   // o portao por conta ja so e consultado quando logOnce e verdadeiro. A
   // condicao fica so na linha de cima, para nao se ler como um salto.
      Print(
         "[AI] LOAD | SYMBOL=",
         symbol,
         " | ROOT=", fileRoot==FILE_COMMON ? "COMMON" : "LOCAL", " | FILE=",
         fileName
      );


   ResetLastError();


   //================================================
   // FILE EXISTS
   //================================================

   if(!FileIsExist(fileName) && fileRoot==0)
   {
      if(logOnce)
         Print(
            "[AI] FILE EM FALTA | ",
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
         FILE_ANSI |
         FILE_SHARE_READ | FILE_SHARE_WRITE |
         fileRoot
      );


   if(file==INVALID_HANDLE)
   {
      if(logOnce)
         Print(
            "[AI] FILE ERRO | ",
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
            "[AI] JSON VAZIO | ",
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
         "[AI] BLOCK | Estado nao executa vel: ",
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
         "[AI] BLOCK | Estado nao executa vel: ",
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
