//+------------------------------------------------------------------+
//|                                                  MarketIntelligence.mqh |
//| XAU_AI_PRO - Market Intelligence System v1.1                       |
//| Sessoes globais, calendario economico, fechamento de mercado,      |
//| score de inteligencia e integracao com IA.                         |
//+------------------------------------------------------------------+
#ifndef MARKETINTELLIGENCE_MQH
#define MARKETINTELLIGENCE_MQH

#include "../Core/Config.mqh"
#include "../Filters/SessionFilter.mqh"
#include "../Filters/NewsFilter.mqh"
#include "../Filters/MarketRegime.mqh"
#include "../Filters/CostGate.mqh"

//======================================================================
// ENUMS E CONSTANTES
//
// v1.2.138 (P1.93): todos os enumeradores levam prefixo MS_ .
// MEDIDO em 04/11/2026: `Filters/GlobalScenario.mqh(61,4) : error 282:
// identifier 'SESSION_CLOSED' already used` - este modulo declarava
// SESSION_CLOSED/SESSION_TOKIO/... e GlobalScenario.mqh ja declarava
// SESSION_CLOSED dentro de ENUM_SESSION_BUCKET. Os dois enums vivem no
// mesmo escopo global do EA, logo os nomes NAO podem coincidir.
// O prefixo resolve a colisao sem tocar em GlobalScenario.mqh, que e
// mais antigo e usado por mais modulos.
//======================================================================
enum MarketSessionType
{
   MS_CLOSED    = 0,   // fora de sessao (reserva)
   MS_SYDNEY    = 1,   // 22:00-01:00 GMT
   MS_TOKIO     = 2,   // 01:00-09:00 GMT
   MS_LONDRES   = 3,   // 08:00-13:00 GMT
   MS_NOVA_YORK = 4,   // 13:00-22:00 GMT
   MS_OVERLAP   = 5    // 13:00-17:00 GMT (Londres + NY)
};

enum MarketDayType
{
   MS_DAY_NORMAL        = 0,
   MS_DAY_LOW_LIQUIDITY = 1,
   MS_DAY_HOLIDAY       = 2,
   MS_DAY_HALF_DAY      = 3
};

enum IntelligenceLevel
{
   MS_INTEL_LOW    = 0,
   MS_INTEL_MEDIUM = 1,
   MS_INTEL_HIGH   = 2,
   MS_INTEL_EXPERT = 3
};

//======================================================================
// ESTRUTURAS DE DADOS
//======================================================================
struct MarketContext
{
   datetime      serverTime;
   datetime      gmtTime;
   int           dayOfWeek;
   int           dayOfMonth;
   int           month;
   int           year;

   MarketSessionType session;
   MarketDayType     dayType;
   int           sessionStart;
   int           sessionEnd;
   int           minutesToClose;
   int           minutesToMarketClose;

   bool          isWeekend;
   bool          isHoliday;
   bool          isHalfDay;
   bool          isLowLiquidity;

   double        intelligenceScore;
   IntelligenceLevel intelLevel;

   string        nextEventName;
   datetime      nextEventTime;
   int           nextEventImpact;
   int           minutesToEvent;

   bool          canTrade;
   string        tradeBlockReason;
};

struct EconomicEvent
{
   datetime   time;
   string     currency;
   string     name;
   int        impact;
   string     actual;
   string     forecast;
   string     previous;
};

//======================================================================
// VARIÁVEIS GLOBAIS DE ESTADO
//======================================================================
datetime        g_marketLastCheck      = 0;
MarketContext   g_marketCtx;
EconomicEvent   g_nextEvents[20];
int             g_nextEventsCount      = 0;
datetime        g_econLastCheck        = 0;
int             g_econErrorCount       = 0;

//======================================================================
// FERIADOS E DIAS ESPECIAIS
//======================================================================
bool IsHolidayDate(int year, int month, int day)
{
   if(month==1 && day==1) return true;
   if(month==5 && day==1) return true;
   if(month==12 && day==25) return true;
   if(month==12 && day==31) return true;
   if(month==7 && day==4) return true;
   if(month==11 && day>=22 && day<=28)
   {
      MqlDateTime tm;
      tm.year=year; tm.mon=month; tm.day=day;
      tm.hour=12; tm.min=0; tm.sec=0;
      datetime dt = StructToTime(tm);
      TimeToStruct(dt, tm);
      if(tm.day_of_week==4) return true;
   }
   return false;
}

int GetDayType(int year, int month, int day, int dayOfWeek)
{
   if(dayOfWeek==0 || dayOfWeek==6) return MS_DAY_HOLIDAY;
   if(IsHolidayDate(year, month, day)) return MS_DAY_HOLIDAY;
   if(dayOfWeek==5) return MS_DAY_LOW_LIQUIDITY;
   if(IsHolidayDate(year, month, day+1)) return MS_DAY_HALF_DAY;
   if(month==12 && day==31) return MS_DAY_HALF_DAY;
   return MS_DAY_NORMAL;
}

//======================================================================
// SESSÕES DE MERCADO (em GMT)
//======================================================================
MarketSessionType GetMarketSession(int hourGMT)
{
   int h = hourGMT;

   if(h >= 22 || h < 1)   return MS_SYDNEY;
   if(h >= 13 && h < 17)  return MS_OVERLAP;
   if(h >= 13 && h < 22)  return MS_NOVA_YORK;
   if(h >= 8  && h < 13)  return MS_LONDRES;
   if(h >= 1  && h < 9)   return MS_TOKIO;

   return MS_CLOSED;
}

int GetSessionStartHour(MarketSessionType sess)
{
   switch(sess)
   {
      case MS_SYDNEY:    return 22;
      case MS_TOKIO:     return 1;
      case MS_LONDRES:   return 8;
      case MS_NOVA_YORK: return 13;
      case MS_OVERLAP:   return 13;
      default:           return 0;
   }
}

int GetSessionEndHour(MarketSessionType sess)
{
   switch(sess)
   {
      case MS_SYDNEY:    return 1;
      case MS_TOKIO:     return 9;
      case MS_LONDRES:   return 13;
      case MS_NOVA_YORK: return 22;
      case MS_OVERLAP:   return 17;
      default:           return 0;
   }
}

int MinutesToSessionClose(int hourGMT, int minuteGMT, MarketSessionType sess)
{
   int endH   = GetSessionEndHour(sess);
   int startH = GetSessionStartHour(sess);

   if(endH <= startH) endH += 24;

   int current = hourGMT * 60 + minuteGMT;
   int endMin  = endH * 60;
   int diff    = endMin - current;

   if(diff < 0) diff += 24 * 60;

   return diff;
}

int MinutesToWeekendClose(int hourGMT, int minuteGMT, int dayOfWeek)
{
   if(dayOfWeek < 5)
   {
      int daysToFri   = 5 - dayOfWeek;
      int targetMin   = daysToFri * 24 * 60 + 22 * 60;
      int currentMin  = hourGMT * 60 + minuteGMT;
      return targetMin - currentMin;
   }

   if(dayOfWeek == 5)
   {
      int targetMin  = 22 * 60;
      int currentMin = hourGMT * 60 + minuteGMT;
      return targetMin - currentMin;
   }

   return 0;
}

//======================================================================
// CALENDÁRIO ECONÔMICO (MT5 nativo)
//
// v1.2.138 (P1.93): a versao anterior chamava
// `CalendarValueLast(changeId, values, NULL, NULL)` e depois lia
// `values[i].currency`, `.event_name`, `.impact`, `.actual`,
// `.forecast`, `.previous` - campos que NAO existem em MqlCalendarValue.
// Resultado medido na compilacao de 04/11/2026: 6 erros 256
// "undeclared identifier". A leitura correcta (a mesma que o
// NewsFilter.mqh ja usa e que compila) e:
//    CalendarValueHistory -> MqlCalendarValue[]
//    CalendarEventById    -> name, importance, country_id
//    CalendarCountryById  -> currency
//======================================================================
string CalendarNumToText(const long v)
{
   // MqlCalendarValue guarda valores como long escalado por 1e6.
   // LONG_MIN significa "sem valor publicado".
   if(v == LONG_MIN) return "";

   return DoubleToString((double)v / 1000000.0, 2);
}

// v1.2.138 (P1.95): o filtro de moeda era aplicado DEPOIS de encher um
// array de 20 lugares, e o scan parava nos 20 primeiros valores do
// calendario. MEDIDO a 04/11/2026: o journal publicava
// "Proximo evento:  (impacto=0)" apesar de o calendario do terminal ter
// dezenas de releases nos 7 dias seguintes - as 20 vagas enchiam-se com
// eventos de moedas irrelevantes para o simbolo antes de chegar aos
// relevantes. O filtro passa para dentro do scan, como no NewsFilter.mqh,
// e o array deixa de truncar a amostra antes de filtrar.
bool IntelCurrencyRelevant(const string currency, const string &currencies[])
{
   for(int c = 0; c < ArraySize(currencies); c++)
   {
      if(currency == currencies[c])
         return true;
   }

   return false;
}

void IntelSymbolCurrencies(const string symbol, string &currencies[])
{
   // v1.2.140 (P1.97): NewsSplitCsv divide CSV por virgula - aplicada a
   // "USDCAD" devolvia um unico elemento "USDCAD", que nunca iguala a moeda
   // de um evento ("USD" ou "CAD"). O filtro descartava a lista inteira e o
   // journal publicava "Proximo evento:  (impacto=0)" em todos os graficos.
   // MEDIDO a 04/11/2026 20:28 no build v1.2.139, depois de reposta a
   // resolucao do pais: o bloco continuava vazio. SymbolNewsCurrencies ja
   // existe no NewsFilter.mqh e faz a derivacao correcta.
   SymbolNewsCurrencies(symbol, currencies);
}

void RefreshEconomicCalendar(const string symbol="")
{
   datetime now = TimeCurrent();

   if(now - g_econLastCheck < 300) return;

   g_econLastCheck   = now;
   g_nextEventsCount = 0;

   string relevant[];
   IntelSymbolCurrencies(symbol, relevant);

   MqlCalendarValue values[];
   datetime from = now;
   datetime to   = now + 7 * 86400;

   int count = CalendarValueHistory(values, from, to);

   if(count <= 0)
   {
      // 4014 = ERR_FUNCTION_NOT_ALLOWED: o calendario nao existe dentro
      // do Strategy Tester. E condicao permanente do teste, nao falha.
      g_econErrorCount++;

      if(GetLastError() != 4014 && DiagGateAllow(_Symbol, "INTEL_CAL",
                                                IntegerToString(GetLastError()), 14400))
         Print("[INTEL] Calendario indisponivel | Error=", GetLastError());

      return;
   }

   g_econErrorCount = 0;

   for(int i = 0; i < count && g_nextEventsCount < 20; i++)
   {
      datetime eventTime = (datetime)values[i].time;

      if(eventTime < now || eventTime > to) continue;

      MqlCalendarEvent ev;

      if(!CalendarEventById(values[i].event_id, ev)) continue;

      MqlCalendarCountry cn;

      // v1.2.139 (P1.96): sem este CalendarCountryById o campo cn.currency
      // fica vazio e IntelCurrencyRelevant("") devolve false para TODOS os
      // eventos - o filtro descartava a lista inteira e o journal publicava
      // "Proximo evento:  (impacto=0)". MEDIDO a 04/11/2026 20:24.
      if(!CalendarCountryById(ev.country_id, cn)) continue;

      if(ArraySize(relevant) > 0 && !IntelCurrencyRelevant(cn.currency, relevant)) continue;

      EconomicEvent e;
      e.time     = eventTime;
      e.currency = cn.currency;
      e.name     = ev.name;
      e.impact   = (int)ev.importance;
      e.actual   = CalendarNumToText(values[i].actual_value);
      e.forecast = CalendarNumToText(values[i].forecast_value);
      e.previous = CalendarNumToText(values[i].prev_value);

      g_nextEvents[g_nextEventsCount++] = e;
   }

   for(int i = 0; i < g_nextEventsCount - 1; i++)
   {
      for(int j = i + 1; j < g_nextEventsCount; j++)
      {
         if(g_nextEvents[j].time < g_nextEvents[i].time)
         {
            EconomicEvent tmp = g_nextEvents[i];
            g_nextEvents[i]   = g_nextEvents[j];
            g_nextEvents[j]   = tmp;
         }
      }
   }
}

EconomicEvent GetNextEventForSymbol(string symbol)
{
   RefreshEconomicCalendar(symbol);

   string currencies[];
   IntelSymbolCurrencies(symbol, currencies);

   for(int i = 0; i < g_nextEventsCount; i++)
   {
      for(int c = 0; c < ArraySize(currencies); c++)
      {
         if(g_nextEvents[i].currency == currencies[c])
            return g_nextEvents[i];
      }
   }

   EconomicEvent empty;
   empty.time   = 0;
   empty.impact = 0;

   return empty;
}

//======================================================================
// SCORE DE INTELIGÊNCIA DE MERCADO
//======================================================================
double CalculateMarketIntelligence(string symbol="")
{
   if(symbol=="") symbol=_Symbol;

   double score = 50.0;

   switch(g_marketCtx.session)
   {
      case MS_OVERLAP:   score += 25; break;
      case MS_LONDRES:   score += 20; break;
      case MS_NOVA_YORK: score += 20; break;
      case MS_TOKIO:     score += 10; break;
      case MS_SYDNEY:    score += 10; break;
      case MS_CLOSED:    score -= 30; break;
   }

   switch(g_marketCtx.dayType)
   {
      case MS_DAY_NORMAL:        score += 20; break;
      case MS_DAY_LOW_LIQUIDITY: score += 5;  break;
      case MS_DAY_HALF_DAY:      score += 10; break;
      case MS_DAY_HOLIDAY:       score -= 40; break;
   }

   if(g_marketCtx.nextEventTime > 0)
   {
      int mins = (int)((g_marketCtx.nextEventTime - TimeCurrent()) / 60);

      if(mins > 0 && mins < 60)
      {
         if(g_marketCtx.nextEventImpact >= 3)      score -= 15;
         else if(g_marketCtx.nextEventImpact == 2) score -= 8;
         else                                      score -= 3;
      }
      else if(mins >= 60 && mins < 240)
      {
         if(g_marketCtx.nextEventImpact >= 3)      score -= 8;
         else if(g_marketCtx.nextEventImpact == 2) score -= 4;
      }
   }

   MarketRegimeType regime = GetMarketRegime(symbol);

   if(regime == REGIME_TREND_UP || regime == REGIME_TREND_DOWN)
      score += 15;
   else
      score += 5;

   if(IsHealthyVolatility(symbol))
      score += 10;
   else
      score -= 10;

   if(g_marketCtx.minutesToMarketClose > 0)
   {
      if(g_marketCtx.minutesToMarketClose < 120)      score -= 10;
      else if(g_marketCtx.minutesToMarketClose < 240) score -= 5;
   }

   if(g_marketCtx.minutesToClose < 60) score -= 5;

   if(score < 0)   score = 0;
   if(score > 100) score = 100;

   return score;
}

IntelligenceLevel GetIntelligenceLevel(double score)
{
   if(score >= 80) return MS_INTEL_EXPERT;
   if(score >= 60) return MS_INTEL_HIGH;
   if(score >= 40) return MS_INTEL_MEDIUM;

   return MS_INTEL_LOW;
}

//======================================================================
// CONTEXTO COMPLETO DE MERCADO
//======================================================================
void UpdateMarketContext()
{
   datetime now = TimeCurrent();

   if(now - g_marketLastCheck < 30) return;

   g_marketLastCheck = now;

   MqlDateTime tm;
   TimeToStruct(now, tm);

   // v1.2.138 (P1.94): as janelas de sessao sao GMT - e o cabecalho de
   // GetMarketSession di-lo - mas a hora usada era tm.hour de TimeCurrent(),
   // que e a hora do SERVIDOR. MEDIDO a 04/11/2026 20:20 local (23:20 UTC):
   // o journal publicou "Sessao: Toquio" quando a janela correcta era Sydney
   // (22:00-01:00 GMT), porque o servidor MetaQuotes-Demo estava em UTC+3.
   // TimeGMT() nao muda com o horario de verao do broker; a hora do servidor
   // continua publicada em serverTime, mas o CALCULO passa a ser GMT.
   datetime    gmtNow = TimeGMT();
   MqlDateTime gm;
   TimeToStruct(gmtNow, gm);

   g_marketCtx.serverTime = now;
   g_marketCtx.gmtTime    = gmtNow;
   g_marketCtx.dayOfWeek  = gm.day_of_week;
   g_marketCtx.dayOfMonth = gm.day;
   g_marketCtx.month      = gm.mon;
   g_marketCtx.year       = gm.year;

   g_marketCtx.isWeekend = (gm.day_of_week==0 || gm.day_of_week==6);
   g_marketCtx.isHoliday = IsHolidayDate(gm.year, gm.mon, gm.day);
   g_marketCtx.isHalfDay = (gm.mon==12 && gm.day==31);

   g_marketCtx.dayType = (MarketDayType)GetDayType(gm.year, gm.mon, gm.day, gm.day_of_week);

   g_marketCtx.isLowLiquidity = (g_marketCtx.dayType == MS_DAY_LOW_LIQUIDITY ||
                                 g_marketCtx.dayType == MS_DAY_HOLIDAY ||
                                 g_marketCtx.isWeekend);

   g_marketCtx.session      = GetMarketSession(gm.hour);
   g_marketCtx.sessionStart = GetSessionStartHour(g_marketCtx.session);
   g_marketCtx.sessionEnd   = GetSessionEndHour(g_marketCtx.session);

   g_marketCtx.minutesToClose       = MinutesToSessionClose(tm.hour, tm.min, g_marketCtx.session);
   g_marketCtx.minutesToMarketClose = MinutesToWeekendClose(gm.hour, gm.min, gm.day_of_week);

   EconomicEvent ev = GetNextEventForSymbol(_Symbol);

   g_marketCtx.nextEventName   = ev.name;
   g_marketCtx.nextEventTime   = ev.time;
   g_marketCtx.nextEventImpact = ev.impact;
   g_marketCtx.minutesToEvent  = (ev.time > 0) ? (int)((ev.time - now) / 60) : -1;

   g_marketCtx.intelligenceScore = CalculateMarketIntelligence(_Symbol);
   g_marketCtx.intelLevel        = GetIntelligenceLevel(g_marketCtx.intelligenceScore);

   bool canTrade = true;
   string reason = "";

   if(g_marketCtx.isWeekend || g_marketCtx.isHoliday)
   {
      canTrade = false;
      reason   = "Mercado fechado (fim de semana/feriado)";
   }
   else if(g_marketCtx.session == MS_CLOSED)
   {
      canTrade = false;
      reason   = "Fora do horario de sessao";
   }
   else if(g_marketCtx.minutesToClose < 15 && g_marketCtx.session != MS_OVERLAP)
   {
      canTrade = false;
      reason   = "Proximo do fechamento da sessao";
   }
   else if(g_marketCtx.minutesToEvent > 0 && g_marketCtx.minutesToEvent < 15 &&
           g_marketCtx.nextEventImpact >= 3)
   {
      canTrade = false;
      reason   = "Evento de alto impacto em menos de 15min";
   }

   g_marketCtx.canTrade         = canTrade;
   g_marketCtx.tradeBlockReason = reason;
}

//======================================================================
// GETTERS PÚBLICOS
//======================================================================
MarketContext GetMarketContext()
{
   UpdateMarketContext();
   return g_marketCtx;
}

bool IsMarketOpenForTrading(string &reason)
{
   if(!EnableMarketIntelligence)
   {
      reason = "inteligencia desligada";
      return true;
   }

   MarketContext ctx = GetMarketContext();
   reason = ctx.tradeBlockReason;

   // Bloqueio por score minimo de inteligencia
   if(MinIntelligenceScore > 0.0 && ctx.intelligenceScore < MinIntelligenceScore)
   {
      reason = StringFormat("inteligencia baixa %.1f < min %.1f", ctx.intelligenceScore, MinIntelligenceScore);
      return false;
   }

   // Bloqueio proximo do fechamento da sessao
   if(BlockPreCloseMinutes > 0 &&
      ctx.minutesToClose > 0 &&
      ctx.minutesToClose < BlockPreCloseMinutes &&
      ctx.session != MS_OVERLAP)
   {
      reason = StringFormat("fechamento da sessao em %d min", ctx.minutesToClose);
      return false;
   }

   // Bloqueio proximo de evento de alto impacto
   if(BlockHighImpactNewsMin > 0 &&
      ctx.minutesToEvent > 0 &&
      ctx.minutesToEvent < BlockHighImpactNewsMin &&
      ctx.nextEventImpact >= 3)
   {
      reason = StringFormat("evento alto impacto em %d min", ctx.minutesToEvent);
      return false;
   }

   return ctx.canTrade;
}

//======================================================================
// AJUSTE DE LOTE POR INTELIGÊNCIA DE MERCADO
//======================================================================
double GetIntelligenceLotFactor()
{
   if(!EnableMarketIntelligence)
      return 1.0;

   UpdateMarketContext();

   double score = g_marketCtx.intelligenceScore;

   if(score >= 70)
      return 1.0;                     // inteligencia alta - lote normal
   else if(score >= 60)
      return 0.75;                    // inteligencia media - reduz 25%
   else if(score >= 50)
      return LowIntelLotFactor;       // inteligencia baixa - fator configuravel
   else
      return LowIntelLotFactor * 0.5; // inteligencia muito baixa - reduz mais
}

double GetMarketIntelligenceScore(string symbol="")
{
   if(symbol=="") symbol=_Symbol;

   UpdateMarketContext();

   return g_marketCtx.intelligenceScore;
}

IntelligenceLevel GetMarketIntelligenceLevel()
{
   UpdateMarketContext();
   return g_marketCtx.intelLevel;
}

bool IsMarketCloseSoon(int minMinutes=60)
{
   UpdateMarketContext();

   return (g_marketCtx.minutesToMarketClose > 0 &&
           g_marketCtx.minutesToMarketClose < minMinutes);
}

string GetSessionName(MarketSessionType sess)
{
   switch(sess)
   {
      case MS_SYDNEY:    return "Sydney";
      case MS_TOKIO:     return "Toquio";
      case MS_LONDRES:   return "Londres";
      case MS_NOVA_YORK: return "Nova York";
      case MS_OVERLAP:   return "Sobreposicao (Londres+NY)";
      default:           return "Fechado";
   }
}

void PrintMarketIntelligence()
{
   MarketContext ctx = GetMarketContext();

   Print("=== [MARKET INTELLIGENCE] ===");
   Print("Simbolo: ", _Symbol);
   Print("Sessao: ", GetSessionName(ctx.session));
   Print("Dia: ", EnumToString(ctx.dayType), " | Semana: ", ctx.isWeekend?"FIM":"OK");
   Print("Feriado: ", ctx.isHoliday?"SIM":"NAO");
   Print("Min para fechar sessao: ", ctx.minutesToClose);
   Print("Min para fechar mercado: ", ctx.minutesToMarketClose);
   Print("Proximo evento: ", ctx.nextEventName, " (impacto=", ctx.nextEventImpact, ")");
   Print("Min para evento: ", ctx.minutesToEvent);
   Print("Score Inteligencia: ", DoubleToString(ctx.intelligenceScore, 1), "/100");
   Print("Nivel: ", EnumToString(ctx.intelLevel));
   Print("Pode negociar: ", ctx.canTrade?"SIM":"NAO", " | ", ctx.tradeBlockReason);
   Print("============================");
}

#endif
//+------------------------------------------------------------------+
