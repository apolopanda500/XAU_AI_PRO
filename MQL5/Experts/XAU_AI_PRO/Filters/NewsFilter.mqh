// XAU_AI_PRO v1.2.51 - NEWS FILTER PROFESSIONAL (Etapa 6 + calendario MT5 nativo)
#ifndef NEWSFILTER_MQH
#define NEWSFILTER_MQH

#include "../Core/Config.mqh"
#include "../Monitoring/AuditLog.mqh"     // self-contained: AuditLogSimple
#include "../Monitoring/EventEmitter.mqh" // self-contained: EventNewsBlock
// v1.2.51 (P1.26): DiagGate para abafar o erro de calendario do tester.
#include "../Monitoring/DiagGate.mqh"

//==================================================
// ESTADOS EXPLICITOS DO FILTRO
//==================================================

enum ENUM_NEWS_STATE
{
   NEWS_CLEAR   = 0,   // nenhum evento relevante na janela ampliada
   NEWS_WARNING = 1,   // evento se aproximando (janela estendida)
   NEWS_BLOCK   = 2,   // dentro da janela ANTES do evento
   NEWS_ACTIVE  = 3    // dentro da janela DEPOIS do evento
};

#define NEWS_REFRESH_SEC     60   // intervalo minimo entre consultas ao calendario
#define NEWS_WARNING_FACTOR  2    // janela de warning = fator x janela de bloqueio

//==================================================
// CACHE / ESTADO
//==================================================

datetime        g_newsLastCheck      = 0;
ENUM_NEWS_STATE g_newsState          = NEWS_CLEAR;
datetime        g_newsNextEventTime  = 0;
string          g_newsNextEventName  = "";
int             g_newsEventsInWindow = 0;
int             g_newsLastError      = 0;
string          g_newsBlockReason    = "";   // ETAPA 11: motivo do bloqueo (audit)
datetime        g_newsBlockLogAt     = 0;    // ETAPA 11: cooldown de log do bloqueo
int             g_newsNextImportance = 0;

//---- estado de OPERAR NOTICIA (29/10/2026)
int    g_newsCurImportance = 0;   // importancia do evento que abriu a janela

// O modulo de noticias passa a existir se o FILTRO estiver ligado OU se o modo
// de OPERAR noticia estiver ligado. Sem isto, um EA anexado com
// EnableNewsFilter=false (estado atual do grafico) ignoraria a noticia por
// completo, inclusive para operar.
bool NewsModuleActive()
{
   return(EnableNewsFilter || EnableNewsTrading);
}    // ETAPA 11: impacto do próximo evento (1-3)

//==================================================
// MOEDAS FX RECONHECIDAS NA AUTO-DERIVACAO
// XAUUSD -> descarta XAU (metal), fica USD
// EURUSD -> EUR + USD
//==================================================

bool IsFxCurrency(const string c)
{
   static const string fx[] =
   {
      "USD","EUR","GBP","JPY","CHF","AUD","NZD","CAD",
      "CNY","SEK","NOK","DKK","MXN","BRL","ZAR","TRY",
      "PLN","HUF","CZK","SGD","HKD","KRW","INR","ILS"
   };

   for(int i=0; i<ArraySize(fx); i++)
   {
      if(c == fx[i])
         return true;
   }

   return false;
}

//==================================================
// SPLIT CSV -> ARRAY MAIUSCULO SEM VAZIOS
//==================================================

void NewsSplitCsv(string csv, string &out[])
{
   ArrayFree(out);

   string parts[];
   int n = StringSplit(csv, ',', parts);

   for(int i=0; i<n; i++)
   {
      string c = parts[i];
      StringTrimLeft(c);
      StringTrimRight(c);
      StringToUpper(c);

      if(c == "")
         continue;

      int sz = ArraySize(out);
      ArrayResize(out, sz+1);
      out[sz] = c;
   }
}

//==================================================
// DERIVA MOEDAS RELEVANTES DO SIMBOLO
// XAUUSD -> USD | EURUSD -> EUR+USD | US30 -> USD
//==================================================

void SymbolNewsCurrencies(string symbol, string &out[])
{
   ArrayFree(out);

   if(symbol == "")
      return;

   string s = symbol;

   StringReplace(s, "#", "");
   StringReplace(s, ".pro", "");
   StringReplace(s, "micro", "");
   StringReplace(s, "_i", "");
   StringReplace(s, ".r", "");
   StringReplace(s, ".cash", "");
   StringTrimLeft(s);
   StringTrimRight(s);

   string tmp[];

   if(StringLen(s) >= 6)
   {
      string c1 = StringSubstr(s, 0, 3);
      string c2 = StringSubstr(s, StringLen(s)-3, 3);

      if(IsFxCurrency(c1))
      {
         int sz = ArraySize(tmp);
         ArrayResize(tmp, sz+1);
         tmp[sz] = c1;
      }

      if(IsFxCurrency(c2))
      {
         int sz = ArraySize(tmp);
         ArrayResize(tmp, sz+1);
         tmp[sz] = c2;
      }
   }

   if(ArraySize(tmp) == 0)
   {
      ArrayResize(tmp, 1);
      tmp[0] = "USD";
   }

   ArrayCopy(out, tmp);
}

//==================================================
// MOEDA DO EVENTO E MONITORADA?
// Lista vazia = todas (comportamento antigo)
//==================================================

bool NewsCurrencyAllowed(const string cur, const string &allowed[])
{
   int n = ArraySize(allowed);

   if(n == 0)
      return true;

   for(int i=0; i<n; i++)
   {
      if(allowed[i] == cur)
         return true;
   }

   return false;
}

//==================================================
// NUCLEO - REFRESH DA JANELA DE EVENTOS
// Throttle: calendario consultado no maximo 1x a cada
// NEWS_REFRESH_SEC. Entre consultas usa o cache.
//==================================================

bool NewsRefreshWindow()
{
   datetime now = TimeTradeServer();
   if(now <= 0)
      now = TimeCurrent();

   if(!NewsModuleActive())
   {
      g_newsState     = NEWS_CLEAR;
      g_newsLastCheck = now;
      return true;
   }

   if(g_newsLastCheck > 0 && (now - g_newsLastCheck) < NEWS_REFRESH_SEC)
      return true;

   g_newsLastCheck = now;

   int beforeSec = NewsMinutesBefore * 60;
   int afterSec  = NewsMinutesAfter  * 60;
   int warnB     = beforeSec * NEWS_WARNING_FACTOR;
   int warnA     = afterSec  * NEWS_WARNING_FACTOR;

   datetime from = now - warnA;
   datetime to   = now + warnB;

   MqlCalendarValue values[];

   ResetLastError();

   int total = CalendarValueHistory(values, from, to);

   if(total < 0)
   {
      g_newsLastError = GetLastError();

      // v1.2.51 (P1.26): medido em 31/10/2026 no journal do tester: 121 076
      // linhas "[NEWS] Calendar error | Error=4014" num unico run, 2,89% de
      // todo o output. O codigo 4014 e ERR_FUNCTION_NOT_ALLOWED na tabela
      // oficial de erros MQL5 - a chamada ao calendario nao e permitida
      // dentro do Strategy Tester. E uma condicao PERMANENTE do teste e nao
      // uma falha, por isso imprime-se uma vez e cala-se. Fora do tester
      // qualquer outro erro continua visivel, abafado a 1 linha por 4 h.
      if(g_newsLastError == 4014)
      {
         static bool avisou4014 = false;

         if(!avisou4014)
         {
            avisou4014 = true;
            Print("[NEWS] Calendario indisponivel no Strategy Tester (erro 4014 ERR_FUNCTION_NOT_ALLOWED) - filtro de noticias em fail-open");
         }
      }
      else if(DiagGateAllow(_Symbol, "NEWS_CAL",
                            IntegerToString(g_newsLastError), 14400))
         Print("[NEWS] Calendar error | Error=", g_newsLastError);

      // Falha de calendario NAO bloqueia o EA (fail-open)
      g_newsState = NEWS_CLEAR;
      return false;
   }

   string allowed[];
   NewsSplitCsv(NewsCurrencies, allowed);

   ENUM_NEWS_STATE newState = NEWS_CLEAR;
   datetime        nextTime = 0;
   string          nextName = "";
   int             inWindow = 0;
   int             curImp   = 0;

   for(int i=0; i<total; i++)
   {
      MqlCalendarEvent ev;

      if(!CalendarEventById(values[i].event_id, ev))
         continue;

      // IMPORTANCIA REAL via CalendarEventById.
      // (codigo antigo usava values[i].impact_type com cast
      // incorreto: impact=POSITIVE/NEGATIVE, nao LOW/HIGH)
      if((int)ev.importance < NewsImpactThreshold)
         continue;

      MqlCalendarCountry cn;

      if(!CalendarCountryById(ev.country_id, cn))
         continue;

      if(!NewsCurrencyAllowed(cn.currency, allowed))
         continue;

      inWindow++;

      datetime t = values[i].time;

      bool inBlock   = (now >= t - beforeSec) && (now <= t + afterSec);
      bool inWarning = (now >= t - warnB)     && (now <= t + warnA);

      if(inBlock)
      {
         if(newState != NEWS_BLOCK)
            newState = (now > t) ? NEWS_ACTIVE : NEWS_BLOCK;

         // Importancia do evento que ABRIU a janela: e ela que decide se a
         // noticia merece modo especial ou se e ruido de calendario.
         if((int)ev.importance > curImp)
            curImp = (int)ev.importance;
      }
      else
      if(inWarning && newState == NEWS_CLEAR)
      {
         newState = NEWS_WARNING;
      }

      if(t > now && (nextTime == 0 || t < nextTime))
      {
         nextTime = t;
         nextName = ev.name;
         g_newsNextImportance = (int)ev.importance;
      }
   }

   g_newsState          = newState;
   g_newsNextEventTime  = nextTime;
   g_newsNextEventName  = nextName;
   
   g_newsEventsInWindow = inWindow;

   g_newsCurImportance  = curImp;

   return true;
}

//==================================================
// ETAPA 11 - NOTIFICAÇÃO / AUDIT DO BLOQUEO
// Registra o motivo do bloqueo no AuditLog (anti-spam).
//==================================================

// Tiempo minimo entre logs repetidos do mesmo bloqueo (segundos)
#define NEWS_AUDIT_COOLDOWN_SEC 300

string GetNewsBlockReason()
{
   if(g_newsState == NEWS_CLEAR || g_newsState == NEWS_WARNING)
      return "";

   return ("NEWS_" + EnumToString(g_newsState));
}

string GetNewsBlockDetail(string symbol)
{
   string reason = "NEWS | Symbol=" + (symbol == "" ? _Symbol : symbol) +
                   " | State=" + EnumToString(g_newsState);

   if(g_newsNextEventTime > 0)
   {
      // Classificação de impacto: 1=BAJO, 2=MEDIO, 3=ALTO
      string impact = (g_newsNextImportance >= 3 ? "ALTO"
                      : (g_newsNextImportance >= 2 ? "MEDIO" : "BAJO"));

      reason += " | Impacto=" + impact +
                " | Next=" + TimeToString(g_newsNextEventTime, TIME_DATE | TIME_MINUTES) +
                " " + g_newsNextEventName;
   }

   return reason;
}

// Registra o motivo do bloqueo de noticias no AuditLog.
// Cooldown anti-spam: mesmo motivo logado no máx 1x a cada NEWS_AUDIT_COOLDOWN_SEC.
void NewsLogBlock()
{
   if(!EnableAuditLog)
   {
      // Resetea para que, ao re-ativar o audit, o próximo bloqueo seja logado.
      g_newsBlockLogAt = 0;
      return;
   }

   datetime now = TimeTradeServer();
   if(now <= 0)
      now = TimeCurrent();

   if(g_newsBlockLogAt > 0 && (now - g_newsBlockLogAt) < NEWS_AUDIT_COOLDOWN_SEC)
      return;

   g_newsBlockLogAt = now;

   // AuditLogSimple(symbol, direction, result, score)
   AuditLogSimple(_Symbol, "NEWS", "BLOCK|" + GetNewsBlockDetail(_Symbol), 0.0);
}

ENUM_NEWS_STATE GetNewsState()
{
   NewsRefreshWindow();
   return g_newsState;
}

bool IsNewsTime()
{
   NewsRefreshWindow();
   return (g_newsState == NEWS_BLOCK || g_newsState == NEWS_ACTIVE);
}

bool NewsFilterActive()
{
   if(!EnableNewsFilter)
      return false;

   return IsNewsTime();
}

//==================================================
// DECISAO UNICA DE NOTICIA (29/10/2026)
//==================================================
// false -> entrada BARRADA (NewsTradeMode=BLOCK ou modo BLOCK)
// true  -> pode entrar, com os multiplicadores preenchidos:
//   lotFactor  multiplica o LOTE
//   riskMult   alarga a distancia de REFERENCIA (stop e orcamento do dia)
//   tpMult     alarga o ALVO
// Sem noticia, tudo fica em 1.0 e a entrada segue a regra normal.
bool NewsTradeAllow(const string symbol, double &lotFactor, double &riskMult,
                    double &tpMult, string &reason)
{
   lotFactor = 1.0;
   riskMult  = 1.0;
   tpMult    = 1.0;
   reason    = "";

   if(!NewsModuleActive())
      return(true);

   NewsRefreshWindow();

   if(g_newsState != NEWS_BLOCK && g_newsState != NEWS_ACTIVE)
      return(true);

   string detail = GetNewsBlockDetail(symbol);

   // Bloqueio explicito: modo BLOCK, ou "operar noticia" desligado.
   if(!EnableNewsTrading || NewsTradeMode == NEWS_TRADE_BLOCK)
   {
      reason = detail;
      return(false);
   }

   // Evento abaixo do impacto minimo: nao merece tratamento especial.
   if(g_newsCurImportance > 0 && g_newsCurImportance < NewsTradeMinImpact)
      return(true);

   if(NewsTradeMode == NEWS_TRADE_FULL)
   {
      reason = detail;
      return(true);
   }

   lotFactor = (NewsTradeLotFactor > 0.0) ? NewsTradeLotFactor : 1.0;
   riskMult  = (NewsTradeRiskMult  > 0.0) ? NewsTradeRiskMult  : 1.0;
   tpMult    = (NewsTradeTPMult    > 0.0) ? NewsTradeTPMult    : 1.0;
   reason    = detail;

   return(true);
}

bool CanTradeNews(const string symbol)
{
   double lotFactor = 1.0;
   double riskMult  = 1.0;
   double tpMult    = 1.0;
   string why       = "";

   if(NewsTradeAllow(symbol, lotFactor, riskMult, tpMult, why))
      return(true);

   g_newsBlockReason = why;

   Print("[NEWS] TRADE BLOCKED | ", symbol,
         " | State=", EnumToString(g_newsState),
         " | Reason=", why);

   NewsLogBlock();
   EventNewsBlock(symbol, why);  // ETAPA 15.6

   return(false);
}

bool CanTradeNews()
{
   return(CanTradeNews(_Symbol));
}

bool IsNewsBlocked()
{
   double lotFactor = 1.0;
   double riskMult  = 1.0;
   double tpMult    = 1.0;
   string why       = "";

   return(!NewsTradeAllow(_Symbol, lotFactor, riskMult, tpMult, why));
}

void PrintNewsStatus()
{
   NewsRefreshWindow();

   Print("[NEWS] ", _Symbol,
         " | State=", EnumToString(g_newsState),
         " | Filter=", (EnableNewsFilter ? "ON" : "OFF"),
         " | Impact>=", NewsImpactThreshold,
         " | Window=", NewsMinutesBefore, "m/", NewsMinutesAfter, "m",
         " | Currencies=", NewsCurrencies,
         " | Trading=", (EnableNewsTrading ? "ON" : "OFF"),
         " | Mode=", EnumToString(NewsTradeMode),
         " | ImpactNow=", g_newsCurImportance,
         " | Events=", g_newsEventsInWindow,
         (g_newsNextEventTime > 0
            ? " | Next=" + TimeToString(g_newsNextEventTime, TIME_DATE|TIME_MINUTES) + " " + g_newsNextEventName
            : ""));
}

#endif
