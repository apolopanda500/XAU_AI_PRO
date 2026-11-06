//+------------------------------------------------------------------+
//| CircuitBreaker.mqh                                               |
//| Circuit Breaker System                                           |
//| XAU_AI_PRO v1.2.9                                                  |
//+------------------------------------------------------------------+

#ifndef CIRCUIT_BREAKER_MQH
#define CIRCUIT_BREAKER_MQH

#include "../Core/Config.mqh"

//==================================================
// ESCOPO DA ANOMALIA DE MERCADO
//==================================================
// MEDIDO em 29/10/2026: ATR do USDBRL em 3.64x a media disparou
// ForceSafeMode("Abnormal market: USDBRL"). O SAFE_MODE e persistido em
// GlobalVariable, entao UM simbolo exotico parava os 13 graficos do EA e
// nenhum ativo abria operacao.
// Default: a anomalia fica restrita ao simbolo (CanTrade(symbol)); o estado
// global NAO e tocado. `true` restaura o comportamento antigo (para tudo).
input bool   CircuitAbnormalMarketBlocksAll = false;
input double CircuitAbnormalATRRatio        = 3.0;   // ATR atual / ATR medio
//==================================================
// HISTERESE DO GATILHO DE BROKER (v1.2.24)
//==================================================
// MEDIDO em 29/10/2026 as 22:29:27 no grafico USDJPY:
//   [CIRCUIT] SAFE MODE activated: Broker connection or trading disabled | Trigger #1
// e, imediatamente depois, no MESMO journal:
//   Status: HEALTHY | Uptime (s): 195 | Checks: 3 | Broker errors: 0
//
// A CAUSA: CheckBrokerError lia TERMINAL_CONNECTED e ACCOUNT_TRADE_ALLOWED
// UMA vez e devolvia falha no primeiro instante em que o terminal ainda nao
// estava conectado (recarga do .ex5 / reconexao do servidor). Sem histerese,
// UM tique ruim virava SAFE_MODE GLOBAL, que e persistido em GlobalVariable
// por 300 s e sobrevive a reinicios - o EA inteiro ficava sem operar.
//
// A CORRECAO: a falha so e aceita como real quando persiste por N leituras
// E por S segundos. Um piscar de conexao nao para o robo.
// CircuitBrokerFailMinCheck=0 && CircuitBrokerFailMinSeconds=0 restaura o
// comportamento antigo (gatilho imediato).
input int    CircuitBrokerFailMinCheck   = 3;    // leituras seguidas com falha
input int    CircuitBrokerFailMinSeconds = 15;   // persistencia minima (s)
input int    CircuitWarmupSeconds        = 30;   // carencia apos OnInit (s)

// Estado da histerese (escopo de arquivo: uma instancia por grafico)
int      g_cbBrokerFails     = 0;
datetime g_cbBrokerFirstFail = 0;
datetime g_cbInitTime        = 0;

//==================================================
// CIRCUIT STATE
//==================================================

enum CircuitState
{
   CIRCUIT_NORMAL=0,
   CIRCUIT_WARNING,
   CIRCUIT_SAFE_MODE,
   CIRCUIT_LOCKED
};


//==================================================
// CIRCUIT BREAKER
//==================================================

class CCircuitBreaker
{
private:

   static CircuitState m_state;

   static bool m_initialized;

   static datetime m_triggered_time;

   static string m_trigger_reason;

   static int m_trigger_count;

   static int m_cooldown_seconds;


   //================================================
   // INTERNAL CHECKS
   //================================================

   static bool CheckSpreadExplosion(
      string symbol
   );

   static bool CheckHighDrawdown();

   static bool CheckBrokerError();

   static bool CheckAIFailure(
      string symbol
   );

   static bool CheckAbnormalMarket(
      string symbol
   );

   static double GetCurrentSpread(
      string symbol
   );

   static double GetATRValue(
      string symbol,
      ENUM_TIMEFRAMES timeframe,
      int shift
   );

   static double GetAverageATR(
      string symbol,
      ENUM_TIMEFRAMES timeframe,
      int startShift,
      int count
   );


public:

   static void Init();

   static void Run();

   static void RunSymbol(
      string symbol
   );

   static CircuitState GetState();

   static string GetStateString();

   static bool IsSafeMode();

   static bool CanTrade();

   static bool CanTrade(
      string symbol
   );

   static void Reset();

   static void ForceSafeMode(
      const string reason
   );

   static datetime GetTriggeredTime();
   static string GetTriggerReason();

   static void LogStatus();
};


//==================================================
// THROTTLE DE DIAGNOSTICO
//
// MEDIDO em 07/10/2026 na conta 391773676 (XMGlobal-MT5 14).
// Ver AGENTS.md Â§7: alterar .mqh exige recompilar no
// MetaEditor e REANEXAR ao grafico â€” compilar nao reanexa.
//
// O QUE ESTAVA ACONTECENDO
// -----------------------
// 12 instancias do EA anexadas no terminal, 3 delas no
// mesmo BTCUSD (M1, M5 e M15). O journal do dia fechou em
// 934.078 linhas / 139,2 MB, das quais:
//
//   57.393  [CIRCUIT] SPREAD EXPLOSION
//   57.393  [CIRCUIT] SPREAD ALTO  (o mesmo tique)
//   38.331  [SAFETY] Free margin low
//   20.067  blocos de "=== RECOVERY STATUS ===" (8 linhas cada)
//
// USDSEK,H1 sozinho responde por 198.079 linhas.
//
// A CALIBRACAO NAO FOI ALTERADA
// -----------------------------
// `CheckSpreadExplosion` continua devolvendo `true` nos
// mesmos tiques, com o mesmo limite. O filtro barra spread
// exatamente como antes. O que mudou e a FREQUENCIA do log â€”
// e o proprio comentario do `RunSymbol` ja dizia que essa
// linha "serve apenas de diagnostico".
//
// Por que o limite de 500 nao Ã© o mesmo para todos: "500
// pontos" vale $5,00 no BTCUSD (point 0,01) e $0,005 no
// EURUSD (point 0,00001). Sao 1000x de diferenca, porque
// `digits` vai de 2 a 5 entre os graficos. E o mapa de
// limites `MaxSpreadBySymbol = "GOLD#:350,BTCUSD#:600,..."`
// nunca acerta, porque os graficos usam os nomes SEM o `#`
// e o `GetMaxSpread` compara com `StringCompare` exato.
// MEDIDO: BTCUSD tem o MENOR spread relativo da conta
// (0,048%) e mesmo assim era o que mais disparava.
//
// --------------------------------------------------
// ESTE DEFECTO FOI CORRIGIDO EM 08/10/2026 (ver Core/Config.mqh)
// --------------------------------------------------
// MEDIDO na conta 391773676 com o EA operando BTCUSD H4: 4 de 12 simbolos
// bloqueados com spread NORMAL â€” BTCUSD, ETHUSD, USDSEK e o OURO, este por
// 57 pontos contra o limite de 50.
//
// A CORRECAO: o limite virou PORCENTAGEM do preco (`MaxSpreadPct`, 0,6%), e o
// `GetMaxSpread` deriva os PONTOS do preco e do `point` daquele simbolo. Os
// seis leitores continuam comparando em pontos e nao mudaram uma linha. O `#`
// saiu do mapa, porque `_Symbol` nunca teve sufixo.
//
// A `emergencySpread = GetMaxSpread(symbol)*10.0` abaixo continua sendo a
// explosao EXTREMA â€” e agora esse 10x e sobre um numero ja convertido, que e o
// que se pretendia.
//==================================================

#define CIRCUIT_LOG_MAX_SIMBOLOS 32
#define CIRCUIT_LOG_INTERVALO_SEG 60

string
   g_circLogSimbolo[CIRCUIT_LOG_MAX_SIMBOLOS];
datetime
   g_circLogQuando[CIRCUIT_LOG_MAX_SIMBOLOS];
int
   g_circLogQuantos=
   0;


//==================================================
// CIRCUIT LOG PODE IMPRIMIR
//==================================================
// Verdadeiro no maximo uma vez por `segundos` por `id`.
// Um id diferente (ex.: "spread" vs "spread_alto") conta
// separado, porque sao duas mensagens distintas.
//==================================================

bool
CircuitLogPodeImprimir(
   string id,
   int segundos
)
{
   if(segundos <= 0)
      return(true);

   datetime agora=
      TimeCurrent();

   for(int i = 0; i < g_circLogQuantos; i++)
   {
      if(g_circLogSimbolo[i] == id)
      {
         if(agora - g_circLogQuando[i] < segundos)
            return(false);

         g_circLogQuando[i]=
            agora;

         return(true);
      }
   }

   if(g_circLogQuantos >= CIRCUIT_LOG_MAX_SIMBOLOS)
      return(false);

   g_circLogSimbolo[g_circLogQuantos]=
      id;
   g_circLogQuando[g_circLogQuantos]=
      agora;
   g_circLogQuantos++;

   return(true);
}


//==================================================
// STATIC DEFINITIONS
//==================================================

CircuitState
CCircuitBreaker::m_state=
   CIRCUIT_NORMAL;


bool
CCircuitBreaker::m_initialized=
   false;


datetime
CCircuitBreaker::m_triggered_time=
   0;


string
CCircuitBreaker::m_trigger_reason=
   "";


int
CCircuitBreaker::m_trigger_count=
   0;


int
CCircuitBreaker::m_cooldown_seconds=
   300;


//==================================================
// INIT
//==================================================

void CCircuitBreaker::Init()
{
   if(g_cbInitTime <= 0)
      g_cbInitTime = TimeCurrent();

   if(m_initialized)
      return;


   m_state=
      CIRCUIT_NORMAL;


   m_triggered_time=
      0;


   m_trigger_reason=
      "";


   m_trigger_count=
      0;


   m_initialized=
      true;


   // v1.3.0 (Etapa 3): SAFE_MODE persiste entre reinicializacoes.
   // Quedas de rede nao liberam mais o circuit breaker por acidente.
   string gvCB="XAI_PRO_CB_SAFE_UNTIL";

   if(MQLInfoInteger(MQL_TESTER)==0 && GlobalVariableCheck(gvCB))
   {
      datetime until=(datetime)GlobalVariableGet(gvCB);

      bool deBroker = false;
      if(GlobalVariableCheck("XAI_PRO_CB_SAFE_BROKER"))
         deBroker = (GlobalVariableGet("XAI_PRO_CB_SAFE_BROKER") > 0.5);

      bool brokerOkAgora = (TerminalInfoInteger(TERMINAL_CONNECTED) != 0
                            && AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) != 0);

      if(TimeCurrent() < until && deBroker && brokerOkAgora)
      {
         // v1.2.24: o motivo do bloqueio desapareceu - manter 300 s de cegueira
         // apos um restart nao protege nada.
         GlobalVariableDel(gvCB);
         GlobalVariableDel("XAI_PRO_CB_SAFE_BROKER");
         Print("[CIRCUIT] SAFE_MODE de broker descartado no start (broker conectado e liberado)");
      }
      else if(TimeCurrent() < until)
      {
         m_state=CIRCUIT_SAFE_MODE;

         m_triggered_time=until - m_cooldown_seconds;

         m_trigger_reason="restaurado apos reinicio";

         Print("[CIRCUIT] SAFE_MODE restaurado apos reinicio ate ",
               TimeToString(until, TIME_DATE|TIME_SECONDS));
      }
      else
      {
         if(MQLInfoInteger(MQL_TESTER)==0)
            { GlobalVariableDel(gvCB); if(GlobalVariableCheck("XAI_PRO_CB_SAFE_BROKER")) GlobalVariableDel("XAI_PRO_CB_SAFE_BROKER"); }
      }
   }


   if(LogInicioDetalhe()) Print(
      "[CIRCUIT] CircuitBreaker initialized"
   );
}


//==================================================
// GET CURRENT SPREAD
//==================================================

double CCircuitBreaker::GetCurrentSpread(
   string symbol
)
{
   if(symbol=="")
      return 0.0;


   double ask=
      SymbolInfoDouble(
         symbol,
         SYMBOL_ASK
      );


   double bid=
      SymbolInfoDouble(
         symbol,
         SYMBOL_BID
      );


   double point=
      SymbolInfoDouble(
         symbol,
         SYMBOL_POINT
      );


   if(
      ask<=0.0 ||
      bid<=0.0 ||
      point<=0.0
   )
   {
      return 0.0;
   }


   return(
      (ask-bid)/point
   );
}


//==================================================
// CHECK SPREAD EXPLOSION
//==================================================

bool CCircuitBreaker::CheckSpreadExplosion(
   string symbol
)
{
   if(symbol=="")
      return false;


   if(!EnableSpreadFilter)
      return false;


   double spread=
      GetCurrentSpread(
         symbol
      );


   if(spread<=0.0)
      return false;


   // Circuit Breaker atua somente em
   // spread extremamente anormal.
   //
   // O filtro normal jÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¡ usa MaxSpread.
   //
   // IMPORTANTE (v1.2.0 - diagnostico):
   // Em backtest, sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­mbolos crypto (BTCUSD#, ETHUSD#)
   // tÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªm spread natural de ~345 pontos, enquanto
   // MaxSpread default = 30. Com fator 3x (=90),
   // o CircuitBreaker dispara ForceSafeMode a cada
   // tick, travando toda a operaÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â£o.
   //
   // SoluÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â£o defensiva:
   //   - O filtro normal (ValidateTrade) jÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¡ barra
   //     spread > MaxSpread por sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­mbolo.
   //   - O CircuitBreaker sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³ deve agir em explosÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â£o
   //     EXTREMA (fator 10x), evitando falso-positivo
   //     em spread normal de crypto/volatilidade alta.

   double emergencySpread=
      GetMaxSpread(symbol)*10.0;


   if(
      spread>
      emergencySpread
   )
   {
      // O retorno e incondicional: a DECISAO nao depende do log.
      // O log e throttle por `CircuitLogPodeImprimir`.
      if(
         CircuitLogPodeImprimir(
            "spread|" + symbol,
            CIRCUIT_LOG_INTERVALO_SEG
         )
      )
      {
         Print(
            "[CIRCUIT] SPREAD EXPLOSION | ",
            symbol,
            " | Spread=",
            DoubleToString(
               spread,
               2
            ),
            " | Limit=",
            DoubleToString(
               emergencySpread,
               2
            )
         );
      }

      return true;
   }


   return false;
}


//==================================================
// CHECK HIGH DRAWDOWN
//==================================================

bool CCircuitBreaker::CheckHighDrawdown()
{
   double balance=
      AccountInfoDouble(
         ACCOUNT_BALANCE
      );


   double equity=
      AccountInfoDouble(
         ACCOUNT_EQUITY
      );


   if(balance<=0.0)
      return false;


   // Drawdown da CONTA (acumulado vs balance) - intencional:
   // RiskHub (GetDrawdownPercent) mede o peak DIARIO.
   double drawdown=
      (
         (balance-equity)
         /
         balance
      )
      *100.0;


   if(
      drawdown>
      MaxDrawdownPercent
   )
   {
      Print(
         "[CIRCUIT] HIGH DRAWDOWN | ",
         DoubleToString(
            drawdown,
            2
         ),
         "%"
      );

      return true;
   }


   return false;
}


//==================================================
// CHECK BROKER
//==================================================

bool CCircuitBreaker::CheckBrokerError()
{
   // v1.2.24: LEITURA PURA do estado do broker
   bool connected    = (TerminalInfoInteger(TERMINAL_CONNECTED) != 0);
   bool tradeAllowed = (AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) != 0);

   if(connected && tradeAllowed)
   {
      // Reconectou antes do gatilho: o episodio nao bloqueia nada.
      if(g_cbBrokerFails > 0)
      {
         // v1.2.85 (02/11/2026) - P1.72: MEDIDO na janela 17:40-18:44 do
         // Logs de 02/11 (872 linhas): 32 linhas [CIRCUIT] BROKER INSTAVEL e
         // 32 [CIRCUIT] BROKER OK - um PAR por leitura transitoria, 64
         // linhas/hora para dizer que nada aconteceu. A linha OK so informa
         // quando houve mesmo uma rajada (3+ leituras ou 60+ s); uma leitura
         // isolada continua a ser contada e continua a nao bloquear nada.
         bool rajadaRelevante = (g_cbBrokerFails >= 3
                                 || (g_cbBrokerFirstFail > 0
                                     && (TimeCurrent() - g_cbBrokerFirstFail) >= 60));

         if(rajadaRelevante && CircuitLogPodeImprimir("broker_transitorio", CIRCUIT_LOG_INTERVALO_SEG))
            PrintFormat("[CIRCUIT] BROKER OK | falha transitoria descartada: %d leituras / %ds",
                        g_cbBrokerFails,
                        (int)(TimeCurrent() - g_cbBrokerFirstFail));
      }

      g_cbBrokerFails     = 0;
      g_cbBrokerFirstFail = 0;

      return(false);
   }

   // Gatilho imediato restaurado a pedido do dono
   if(CircuitBrokerFailMinCheck <= 0 && CircuitBrokerFailMinSeconds <= 0)
      return(true);

   datetime agora = TimeCurrent();

   if(g_cbBrokerFails == 0)
      g_cbBrokerFirstFail = agora;

   g_cbBrokerFails++;

   int duracao = (g_cbBrokerFirstFail > 0) ? (int)(agora - g_cbBrokerFirstFail) : 0;

   bool carencia = (g_cbInitTime > 0 && (agora - g_cbInitTime) < CircuitWarmupSeconds);

   bool confirmado = (!carencia
                      && g_cbBrokerFails >= CircuitBrokerFailMinCheck
                      && duracao >= CircuitBrokerFailMinSeconds);

   if(!confirmado)
   {
      // Diagnostico throttle por `CircuitLogPodeImprimir`: nao pode inundar o journal.
      if(CircuitLogPodeImprimir("broker_instavel", CIRCUIT_LOG_INTERVALO_SEG))
         PrintFormat("[CIRCUIT] BROKER INSTAVEL | leituras=%d | %ds | %s | aguardando confirmacao (nao bloqueia)",
                     g_cbBrokerFails,
                     duracao,
                     (carencia ? "carencia de start" : "histerese"));

      return(false);
   }

   PrintFormat("[CIRCUIT] BROKER CONFIRMADO INDISPONIVEL | leituras=%d | %ds | conectado=%d | trade_allowed=%d",
               g_cbBrokerFails,
               duracao,
               (int)connected,
               (int)tradeAllowed);

   return(true);
}


//==================================================
// CHECK AI (v1.2.0 fix - fallback no tester)
//==================================================

bool CCircuitBreaker::CheckAIFailure(
   string symbol
)
{
   if(!EnableAIFilter)
      return false;


   if(symbol=="")
      return false;


   // FIX v1.2.0: em backtest o pipeline Python nao roda,
   // entao prediction_<SYMBOL>.json nunca existe. Usa o
   // fallback local do AIEngine (nao bloqueia o simbolo).
   // Em modo real, JSON ausente so bloqueia se RequireAIJSON=true.
   if(!RequireAIJSON)
      return false;

   if(MQLInfoInteger(MQL_TESTER)!=0)
      return false;

   string fileName=
      "Data\\prediction_" +
      symbol +
      ".json";


   if(
      !FileIsExist(
         fileName,
         0
      )
   )
   {
      return true;
   }


   return false;
}


//==================================================
// GET ATR
//==================================================

double CCircuitBreaker::GetATRValue(
   string symbol,
   ENUM_TIMEFRAMES timeframe,
   int shift
)
{
   if(symbol=="")
      return 0.0;


   int handle=
      iATR(
         symbol,
         timeframe,
         ATRPeriod
      );


   if(
      handle==
      INVALID_HANDLE
   )
   {
      return 0.0;
   }


   double buffer[];


   ArrayResize(
      buffer,
      1
   );


   ArraySetAsSeries(
      buffer,
      true
   );


   double value=0.0;


   if(
      CopyBuffer(
         handle,
         0,
         shift,
         1,
         buffer
      )>0
   )
   {
      value=
         buffer[0];
   }


   IndicatorRelease(
      handle
   );


   return value;
}


//==================================================
// GET AVERAGE ATR
//==================================================

double CCircuitBreaker::GetAverageATR(
   string symbol,
   ENUM_TIMEFRAMES timeframe,
   int startShift,
   int count
)
{
   if(
      symbol=="" ||
      count<=0
   )
   {
      return 0.0;
   }


   int handle=
      iATR(
         symbol,
         timeframe,
         ATRPeriod
      );


   if(
      handle==
      INVALID_HANDLE
   )
   {
      return 0.0;
   }


   double buffer[];


   ArrayResize(
      buffer,
      count
   );


   ArraySetAsSeries(
      buffer,
      true
   );


   int copied=
      CopyBuffer(
         handle,
         0,
         startShift,
         count,
         buffer
      );


   IndicatorRelease(
      handle
   );


   if(
      copied<=0
   )
   {
      return 0.0;
   }


   double sum=0.0;

   int valid=0;


   for(
      int i=0;
      i<copied;
      i++
   )
   {
      if(
         buffer[i]>0.0
      )
      {
         sum+=
            buffer[i];

         valid++;
      }
   }


   if(valid<=0)
      return 0.0;


   return(
      sum/
      valid
   );
}


//==================================================
// CHECK ABNORMAL MARKET
//==================================================

bool CCircuitBreaker::CheckAbnormalMarket(
   string symbol
)
{
   if(symbol=="")
      return false;


   double currentATR=
      GetATRValue(
         symbol,
         PERIOD_CURRENT,
         1
      );


   if(
      currentATR<=0.0
   )
   {
      return false;
   }


   double averageATR=
      GetAverageATR(
         symbol,
         PERIOD_CURRENT,
         2,
         20
      );


   if(
      averageATR<=0.0
   )
   {
      return false;
   }


   double ratio=
      currentATR/
      averageATR;


   // Volatilidade extrema:
   // ATR atual > 3x mÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©dia recente

   if(
      ratio>=CircuitAbnormalATRRatio
   )
   {
      Print(
         "[CIRCUIT] ABNORMAL MARKET | ",
         symbol,
         " | ATR=",
         DoubleToString(
            currentATR,
            6
         ),
         " | AvgATR=",
         DoubleToString(
            averageATR,
            6
         ),
         " | Ratio=",
         DoubleToString(
            ratio,
            2
         )
      );

      return true;
   }


   return false;
}


//==================================================
// RUN ALL
//==================================================

void CCircuitBreaker::Run()
{
   if(!m_initialized)
      Init();


   if(
      m_state==
      CIRCUIT_LOCKED
   )
   {
      return;
   }


   //===============================================
   // BROKER / ACCOUNT
   //===============================================

   if(
      CheckBrokerError()
   )
   {
      ForceSafeMode(
         "Broker connection or trading disabled"
      );

      return;
   }


   //===============================================
   // DRAWDOWN
   //===============================================

   if(
      CheckHighDrawdown()
   )
   {
      ForceSafeMode(
         "High drawdown detected"
      );

      return;
   }


   //===============================================
   // CURRENT SYMBOL
   //===============================================

   RunSymbol(
      _Symbol
   );


   //===============================================
   // AUTO RECOVERY
   //===============================================

   if(
      m_state==
      CIRCUIT_SAFE_MODE
   )
   {
      if(
         TimeCurrent()-
         m_triggered_time
         >=
         m_cooldown_seconds
      )
      {
         m_state=
            CIRCUIT_NORMAL;

         m_trigger_reason=
            "";

         Print(
            "[CIRCUIT] Recovered to NORMAL mode"
         );

          // v1.3.0 (Etapa 3): limpa a persistencia do SAFE_MODE
          string gvCB="XAI_PRO_CB_SAFE_UNTIL";

          if(MQLInfoInteger(MQL_TESTER)==0 && GlobalVariableCheck(gvCB))
            { GlobalVariableDel(gvCB); if(GlobalVariableCheck("XAI_PRO_CB_SAFE_BROKER")) GlobalVariableDel("XAI_PRO_CB_SAFE_BROKER"); }
      }
   }
}


//==================================================
// RUN SYMBOL
//==================================================

void CCircuitBreaker::RunSymbol(
   string symbol
)
{
   if(
      symbol==""
   )
   {
      return;
   }


   if(
      CheckSpreadExplosion(
         symbol
      )
   )
   {
      //================================================
      // SPREAD
      //
      // NÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â£o bloquear o sistema inteiro por causa do
      // spread de um ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âºnico sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­mbolo.
      //
      // O filtro por sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­mbolo (ValidateTrade | SPREAD)
      // ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© o responsÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¡vel por barrar spread > MaxSpread,
      // sem travar as demais operaÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âµes.
      //
      // Em backtest, sÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­mbolos crypto (BTCUSD#, ETHUSD#)
      // tÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªm spread natural muito alto (ex: 2250 pontos),
      // o que fazia o CircuitBreaker travar TUDO a cada
      // tick (Trigger #99k).
      //
      // Este log serve apenas de diagnÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³stico.
      //================================================

      if(
         CircuitLogPodeImprimir(
            "spread_alto|" + symbol,
            CIRCUIT_LOG_INTERVALO_SEG
         )
      )
      {
         Print(
            "[CIRCUIT] SPREAD ALTO | ",
            symbol,
            " | Bloqueio delegado ao ValidateTrade"
         );
      }
   }


   if(
      CheckAIFailure(
         symbol
      )
   )
   {
      //================================================
      // AI
      //
      // NÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â£o bloquear o sistema inteiro apenas porque
      // prediction_<symbol>.json nÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â£o estÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¡ disponÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­vel.
      //
      // O AIEngine possui fallback local.
      //
      // O AITradeAllowed() serÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¡ responsÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¡vel pela
      // decisÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â£o final da IA.
      //================================================

      Print(
         "[CIRCUIT] AI JSON AUSENTE | ",
         symbol,
         " | Usando fallback do AIEngine"
      );
   }


   if(
      CheckAbnormalMarket(
         symbol
      )
   )
   {
      // Default (CircuitAbnormalMarketBlocksAll=false): a anomalia fica
      // restrita ao simbolo, avaliada em CanTrade(symbol). O SAFE_MODE
      // global NAO e tocado - um ativo exotico nao para os demais.
      if(CircuitAbnormalMarketBlocksAll)
      {
         ForceSafeMode(
            "Abnormal market: "
            +
            symbol
         );

         return;
      }

      static datetime lastAbnormalLog = 0;
      datetime abnormalNow = TimeCurrent();

      if(abnormalNow - lastAbnormalLog >= 300)
      {
         lastAbnormalLog = abnormalNow;
         Print(
            "[CIRCUIT] ABNORMAL MARKET restrito ao simbolo | ",
            symbol,
            " | demais ativos seguem liberados"
         );
      }
   }
}


//==================================================
// GET STATE
//==================================================

CircuitState
CCircuitBreaker::GetState()
{
   return m_state;
}


//==================================================
// GET STATE STRING
//==================================================

string CCircuitBreaker::GetStateString()
{
   switch(
      m_state
   )
   {
      case CIRCUIT_NORMAL:
         return "NORMAL";

      case CIRCUIT_WARNING:
         return "WARNING";

      case CIRCUIT_SAFE_MODE:
         return "SAFE_MODE";

      case CIRCUIT_LOCKED:
         return "LOCKED";
   }


   return "UNKNOWN";
}


//==================================================
// SAFE MODE
//==================================================

bool CCircuitBreaker::IsSafeMode()
{
   return(
      m_state==
      CIRCUIT_SAFE_MODE
      ||
      m_state==
      CIRCUIT_LOCKED
   );
}


//==================================================
// CAN TRADE
//==================================================

bool CCircuitBreaker::CanTrade()
{
   return(
      m_state==
      CIRCUIT_NORMAL
      ||
      m_state==
      CIRCUIT_WARNING
   );
}


//==================================================
// CAN TRADE SYMBOL
//==================================================

bool CCircuitBreaker::CanTrade(
   string symbol
)
{
   if(
      !CanTrade()
   )
   {
      return false;
   }


   if(
      symbol==""
   )
   {
      return false;
   }


   if(
      CheckSpreadExplosion(
         symbol
      )
   )
   {
      return false;
   }


   if(
      CheckAbnormalMarket(
         symbol
      )
   )
   {
      return false;
   }


   if(
      CheckAIFailure(
         symbol
      )
   )
   {
      return false;
   }


   return true;
}


//==================================================
// RESET
//==================================================

void CCircuitBreaker::Reset()
{
   g_cbBrokerFails     = 0;
   g_cbBrokerFirstFail = 0;

   m_state=
      CIRCUIT_NORMAL;


   m_triggered_time=
      0;


   m_trigger_reason=
      "";


   Print(
      "[CIRCUIT] CircuitBreaker reset to NORMAL"
   );
}


//==================================================
// FORCE SAFE MODE
//==================================================

void CCircuitBreaker::ForceSafeMode(
   const string reason
)
{
   if(
      m_state==
      CIRCUIT_LOCKED
   )
   {
      return;
   }


   m_state=
      CIRCUIT_SAFE_MODE;


   m_triggered_time=
      TimeCurrent();


   m_trigger_reason=
      reason;


      m_trigger_count++;
   // v1.3.0 (Etapa 3): persiste SAFE_MODE pelo cooldown (sobrevive a reinits)
   if(MQLInfoInteger(MQL_TESTER)==0)
   {
      GlobalVariableSet("XAI_PRO_CB_SAFE_UNTIL", TimeCurrent() + m_cooldown_seconds);

      // v1.2.24: o SAFE_MODE de BROKER nao deve sobreviver a um restart em que
      // o broker ja voltou. A marca permite descartar so esse caso.
      string motivo = reason;
      StringToLower(motivo);

      bool deBroker = (StringFind(motivo, "broker") >= 0);

      if(deBroker)
      {
         if(!GlobalVariableCheck("XAI_PRO_CB_SAFE_BROKER"))
            GlobalVariableSet("XAI_PRO_CB_SAFE_BROKER", 1.0);
      }
      else
      {
         if(GlobalVariableCheck("XAI_PRO_CB_SAFE_BROKER"))
            GlobalVariableDel("XAI_PRO_CB_SAFE_BROKER");
      }
   }

   PrintFormat(
      "[CIRCUIT] SAFE MODE activated: %s | Trigger #%d",
      reason,
      m_trigger_count
   );
}


//==================================================
// TRIGGER REASON
//==================================================

datetime CCircuitBreaker::GetTriggeredTime()
{
   return m_triggered_time;
}

string CCircuitBreaker::GetTriggerReason()
{
   return m_trigger_reason;
}


//==================================================
// LOG STATUS
//==================================================

void CCircuitBreaker::LogStatus()
{
   PrintFormat(
      "[CIRCUIT] State=%s | Reason=%s | Triggers=%d",
      GetStateString(),
      m_trigger_reason,
      m_trigger_count
   );
}


//==================================================
// FAILSAFE COMPAT (v1.4.0 - Etapa 5)
//==================================================
// O modulo orfao Monitoring/FailSafe.mqh foi fundido
// aqui. O CircuitBreaker ja era o dono real do
// SAFE_MODE (cooldown 300s, persistencia em
// GlobalVariable, recovery automatico). Esta secao
// preserva a API publica do FailSafe e adiciona os
// contadores de erro com histerese.
//
// NOTA Etapa 6: o health check do antigo FailSafe
// dependia de HealthMonitor/WatchDog (orfao). Sera
// integrado na Etapa 6 junto com esses modulos.
//==================================================

enum ENUM_ROBOT_MODE
{
   ROBOT_MODE_AUTO = 0,
   ROBOT_MODE_SAFE = 1
};

// Duracao minima do SAFE_MODE (compat FailSafe)
int g_failSafeDuration = 300;

// Limites de histerese (compat FailSafe)
int g_failSafeMaxAIErrors = 5;
int g_failSafeMaxBrokerErrors = 10;

// Contadores acumulados (sobrevivem enquanto o EA roda)
int g_failSafeAIErrorCount = 0;
int g_failSafeBrokerErrorCount = 0;

//==================================================
// ACTIVATE (compat)
//==================================================

void FailSafeActivate(string reason)
{
   CCircuitBreaker::ForceSafeMode(reason);
}

//==================================================
// CAN TRADE (compat)
//==================================================

bool FailSafeCanTrade()
{
   return CCircuitBreaker::CanTrade();
}

//==================================================
// GET MODE (compat)
//==================================================

ENUM_ROBOT_MODE FailSafeGetMode()
{
   return(CCircuitBreaker::IsSafeMode() ? ROBOT_MODE_SAFE : ROBOT_MODE_AUTO);
}

//==================================================
// GET MODE STRING (compat)
//==================================================

string FailSafeGetModeString()
{
   return CCircuitBreaker::GetStateString();
}

//==================================================
// GET REASON (compat)
//==================================================

string FailSafeGetReason()
{
   return CCircuitBreaker::GetTriggerReason();
}

//==================================================
// GET ELAPSED (compat)
//==================================================

int FailSafeGetElapsed()
{
   if(!CCircuitBreaker::IsSafeMode())
      return 0;
   return(int)(TimeCurrent() - CCircuitBreaker::GetTriggeredTime());
}

//==================================================
// GET REMAINING (compat)
//==================================================

int FailSafeGetRemaining()
{
   if(!CCircuitBreaker::IsSafeMode())
      return 0;
   int remaining = g_failSafeDuration - FailSafeGetElapsed();
   if(remaining < 0)
      remaining = 0;
   return remaining;
}

//==================================================
// SET MODE (compat) - modo manual
//==================================================

void FailSafeSetMode(ENUM_ROBOT_MODE mode)
{
   if(mode == ROBOT_MODE_SAFE)
   {
      CCircuitBreaker::ForceSafeMode("MANUAL_SAFE_MODE");
      return;
   }
   CCircuitBreaker::Reset();
}

//==================================================
// RESET (compat)
//==================================================

void FailSafeReset()
{
   CCircuitBreaker::Reset();
   g_failSafeAIErrorCount = 0;
   g_failSafeBrokerErrorCount = 0;
}

//==================================================
// SUMMARY (compat)
//==================================================

string FailSafeSummary()
{
   string summary = "=== FAILSAFE ===\n";
   summary += "Mode: " + FailSafeGetModeString() + "\n";
   summary += "CanTrade: " + (FailSafeCanTrade() ? "YES" : "NO") + "\n";
   summary += "Reason: " + CCircuitBreaker::GetTriggerReason() + "\n";
   if(CCircuitBreaker::IsSafeMode())
   {
      summary += "Elapsed: " + IntegerToString(FailSafeGetElapsed()) + "s\n";
      summary += "Remaining: " + IntegerToString(FailSafeGetRemaining()) + "s\n";
   }
   summary += "AI Errors: " + IntegerToString(g_failSafeAIErrorCount) + "/" + IntegerToString(g_failSafeMaxAIErrors) + "\n";
   summary += "Broker Errors: " + IntegerToString(g_failSafeBrokerErrorCount) + "/" + IntegerToString(g_failSafeMaxBrokerErrors) + "\n";
   return summary;
}

//==================================================
// SHUTDOWN (compat)
//==================================================

void FailSafeShutdown()
{
   Print("[FAILSAFE] Finalizado");
}

//==================================================
// ERROR COUNTERS (v1.4.0 - Etapa 5)
// Chamados pelo CCircuitBreaker::Run() para dar
// histerese aos gatilhos de IA/broker.
//==================================================

void FailSafeRegisterAIError()
{
   g_failSafeAIErrorCount++;
   if(g_failSafeAIErrorCount >= g_failSafeMaxAIErrors)
   {
      FailSafeActivate("AI_ERRORS");
      g_failSafeAIErrorCount = 0;
   }
}

void FailSafeRegisterBrokerError()
{
   g_failSafeBrokerErrorCount++;
   if(g_failSafeBrokerErrorCount >= g_failSafeMaxBrokerErrors)
   {
      FailSafeActivate("BROKER_ERRORS");
      g_failSafeBrokerErrorCount = 0;
   }
}

//==================================================
// END
//==================================================

#endif  f