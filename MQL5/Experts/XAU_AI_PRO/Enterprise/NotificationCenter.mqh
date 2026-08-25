//+------------------------------------------------------------------+
//|                                           NotificationCenter.mqh |
//|                                  Notification Center             |
//|                                            XAU_AI_PRO v1.2.0      |
//|                                            ETAPA 9 - v2.0         |
//+------------------------------------------------------------------+
// Central de notificacoes do EA: camada de OBSERVABILIDADE.
//
// PRINCIPIO FUNDAMENTAL: notificacao NUNCA e ponto unico de falha.
// - Todas as funcoes retornam bool e nunca bloqueiam o fluxo do EA.
// - WebRequest e protegido por cooldown/dedup/rate-limit.
// - Falha de envio apenas conta e registra; trading segue normal.
//
// Canais:
//  - Push nativo do MT5 (SendNotification) - sempre disponivel
//  - Telegram via WebRequest (api.telegram.org) - opcional
//
// Anti-spam (ETAPA 9):
//  - Cooldown por categoria (NCAT_*)
//  - Deduplicacao: mesma mensagem dentro da janela e ignorada
//  - Rate limit global por minuto
//
// v2.0 (ETAPA 9): implementacao real de Telegram, anti-spam,
// tratamento de erro, integracao com AuditLog e log proprio.
//+------------------------------------------------------------------+

#ifndef NOTIFICATION_CENTER_MQH
#define NOTIFICATION_CENTER_MQH

#include "../Monitoring/AuditLog.mqh" // self-contained: AuditLogSimple

#define NOTIFY_MAX_PER_MINUTE_DEF 10
#define NOTIFY_DEDUP_SEC_DEF      60

enum NotifyChannel { NOTIFY_TELEGRAM, NOTIFY_PUSH };
enum NotifyPriority { NOTIFY_LOW, NOTIFY_NORMAL, NOTIFY_HIGH, NOTIFY_CRITICAL };

// Categorias de evento (cooldown/dedup por categoria)
enum NotifyCategory
{
   NCAT_SYSTEM,        // alertas de sistema / encerramento
   NCAT_TRADE_OPEN,    // abertura de operacao
   NCAT_TRADE_CLOSE,   // fechamento de operacao
   NCAT_ERROR,         // erros
   NCAT_DRAWDOWN,      // drawdown / risco
   NCAT_HEALTH,        // HealthMonitor
   NCAT_CIRCUIT,       // Circuit Breaker / SAFE
   NCAT_EXECUTION,     // falhas de execucao
   NCAT_REPORT,        // relatorios periodicos
   NCAT_COUNT
};

class CNotificationCenter
{
private:
   static bool     m_initialized;
   static bool     m_push_enabled;
   static string   m_telegram_token;
   static string   m_telegram_chat_id;
   static int      m_sent_count;
   static int      m_failed_count;
   static int      m_last_minute;
   static int      m_minute_count;
   static int      m_max_per_minute;
   static int      m_cooldown_sec[NCAT_COUNT];
   static datetime m_last_send[NCAT_COUNT];
   static string   m_last_message[NCAT_COUNT];
   static bool     m_dedup_enabled;
   static int      m_dedup_sec;
   static string   NCUrlEncode(string s);
   static bool     SendTelegram(string message);
   static bool     SendPush(string message);
   static void     RegisterLog(string status, string detail);
   static void     RegisterAudit(string detail, bool ok);
public:
   static void Init();
   static void SetPushEnabled(bool enabled);
   static void SetTelegram(string token, string chat_id);
   static void SetCooldown(NotifyCategory cat, int seconds);
   static void SetMaxPerMinute(int max);
   static void SetDedup(bool enabled, int seconds);
   static bool Send(string message, NotifyPriority priority, NotifyCategory cat);
   static bool SendTradeOpen(string symbol, double volume, double price, string type);
   static bool SendTradeClose(string symbol, double profit, string comment);
   static bool SendError(string module, string error);
   static bool SendExecutionFailure(string symbol, string error);
   static bool SendDrawdown(double dd_percent);
   static bool SendHealthAlert(string detail);
   static bool SendCircuitBreaker(string state, string reason);
   static bool SendDailyReport(double profit, int trades, double win_rate);
   static bool SendSystemAlert(string alert);
   static int  GetSentCount();
   static int  GetFailedCount();
   static string GetStatus();
   static void LogStatus();
};

//--------------------------------------------------
// DEFINICOES ESTATICAS
//--------------------------------------------------

bool     CNotificationCenter::m_initialized = false;
bool     CNotificationCenter::m_push_enabled = true;
string   CNotificationCenter::m_telegram_token = "";
string   CNotificationCenter::m_telegram_chat_id = "";
int      CNotificationCenter::m_sent_count = 0;
int      CNotificationCenter::m_failed_count = 0;
int      CNotificationCenter::m_last_minute = 0;
int      CNotificationCenter::m_minute_count = 0;
int      CNotificationCenter::m_max_per_minute = NOTIFY_MAX_PER_MINUTE_DEF;
int      CNotificationCenter::m_cooldown_sec[NCAT_COUNT];
datetime CNotificationCenter::m_last_send[NCAT_COUNT];
string   CNotificationCenter::m_last_message[NCAT_COUNT];
bool     CNotificationCenter::m_dedup_enabled = true;
int      CNotificationCenter::m_dedup_sec = NOTIFY_DEDUP_SEC_DEF;

//--------------------------------------------------
// INIT
//--------------------------------------------------

void CNotificationCenter::Init()
{
   if(m_initialized)
      return;

   m_initialized = true;

   // Cooldowns default por categoria (segundos)
   for(int i = 0; i < NCAT_COUNT; i++)
      m_cooldown_sec[i] = 300;

   m_cooldown_sec[NCAT_TRADE_OPEN]  = 30;
   m_cooldown_sec[NCAT_TRADE_CLOSE] = 30;
   m_cooldown_sec[NCAT_HEALTH]      = 600;
   m_cooldown_sec[NCAT_DRAWDOWN]    = 600;
   m_cooldown_sec[NCAT_REPORT]      = 3600;

   for(int i = 0; i < NCAT_COUNT; i++)
   {
      m_last_send[i]    = 0;
      m_last_message[i] = "";
   }

   Print("[NOTIFY] NotificationCenter inicializado");
}

//--------------------------------------------------
// CONFIGURACAO
//--------------------------------------------------

void CNotificationCenter::SetPushEnabled(bool enabled)
{
   m_push_enabled = enabled;
}

void CNotificationCenter::SetTelegram(string token, string chat_id)
{
   m_telegram_token   = token;
   m_telegram_chat_id = chat_id;
}

void CNotificationCenter::SetCooldown(NotifyCategory cat, int seconds)
{
   if(cat >= 0 && cat < NCAT_COUNT && seconds >= 0)
      m_cooldown_sec[(int)cat] = seconds;
}

void CNotificationCenter::SetMaxPerMinute(int max)
{
   if(max > 0)
      m_max_per_minute = max;
}

void CNotificationCenter::SetDedup(bool enabled, int seconds)
{
   m_dedup_enabled = enabled;
   if(seconds > 0)
      m_dedup_sec = seconds;
}

//--------------------------------------------------
// URL ENCODE (UTF-8 byte a byte)
//--------------------------------------------------

string CNotificationCenter::NCUrlEncode(string s)
{
   uchar bytes[];
   int len = StringToCharArray(s, bytes, 0, WHOLE_ARRAY, CP_UTF8) - 1;
   if(len <= 0)
      return "";

   string out = "";
   for(int i = 0; i < len; i++)
   {
      uchar b = bytes[i];
      if((b >= '0' && b <= '9') ||
         (b >= 'A' && b <= 'Z') ||
         (b >= 'a' && b <= 'z') ||
         b == '-' || b == '_' || b == '.' || b == '~')
         out += CharToString(b);
      else
         out += StringFormat("%%%02X", (int)b);
   }
   return out;
}

//--------------------------------------------------
// SEND TELEGRAM (WebRequest)
//--------------------------------------------------

bool CNotificationCenter::SendTelegram(string message)
{
   if(m_telegram_token == "" || m_telegram_chat_id == "")
      return false;

   string url = "https://api.telegram.org/bot" + m_telegram_token + "/sendMessage";
   string post = "chat_id=" + m_telegram_chat_id + "&text=" + NCUrlEncode(message);

   uchar post_data[];
   uchar result_data[];
   string result_headers;

   int plen = StringToCharArray(post, post_data, 0, WHOLE_ARRAY, CP_UTF8) - 1;
   if(plen <= 0)
      return false;

   ResetLastError();
   int res = WebRequest("POST", url, "", 5000, post_data, result_data, result_headers);

   if(res == -1)
   {
      Print("[NOTIFY] Telegram WebRequest falhou | Erro=", GetLastError(),
         " | Adicione https://api.telegram.org em Ferramentas > Opcoes > Expert Advisors (URLs permitidas)");
      return false;
   }

   return (res >= 200 && res < 300);
}

//--------------------------------------------------
// SEND PUSH (nativo MT5)
//--------------------------------------------------

bool CNotificationCenter::SendPush(string message)
{
   ResetLastError();
   bool ok = SendNotification(message);
   if(!ok)
   {
      Print("[NOTIFY] SendNotification falhou | Erro=", GetLastError(),
         " | Configure Push em Ferramentas > Opcoes > Notificacoes");
   }
   return ok;
}

//--------------------------------------------------
// CAN SEND (anti-spam: cooldown + dedup + rate limit)
//--------------------------------------------------

bool CNotificationCenter::Send(string message, NotifyPriority priority, NotifyCategory cat)
{
   if(!m_initialized)
      Init();

   if(cat < 0 || cat >= NCAT_COUNT)
      cat = NCAT_SYSTEM;

   datetime now = TimeCurrent();

   // Rate limit global por minuto
   int minute = (int)(now / 60);
   if(minute != m_last_minute)
   {
      m_last_minute = minute;
      m_minute_count = 0;
   }
   if(m_minute_count >= m_max_per_minute)
   {
      Print("[NOTIFY] Rate limit atingido (", m_max_per_minute, "/min) - mensagem ignorada: ", message);
      return false;
   }

   // Cooldown por categoria
   if(now - m_last_send[(int)cat] < m_cooldown_sec[(int)cat])
      return false;

   // Deduplicacao (mesma mensagem dentro da janela)
   if(m_dedup_enabled && message == m_last_message[(int)cat] &&
      (now - m_last_send[(int)cat]) < m_dedup_sec)
      return false;

   // Reserva o slot
   m_minute_count++;
   m_last_send[(int)cat]    = now;
   m_last_message[(int)cat] = message;

   bool anySent = false;

   if(m_push_enabled)
   {
      if(SendPush(message))
         anySent = true;
      else
         m_failed_count++;
   }

   if(m_telegram_token != "" && m_telegram_chat_id != "")
   {
      if(SendTelegram(message))
         anySent = true;
      else
         m_failed_count++;
   }

   if(anySent)
      m_sent_count++;
   else
      m_failed_count++;

   // Observabilidade: log proprio + auditoria
   RegisterLog(anySent ? "SENT" : "FAIL", message);
   RegisterAudit(message, anySent);

   return anySent;
}

//--------------------------------------------------
// LOG PROPRIO (FILE_COMMON, append)
//--------------------------------------------------

void CNotificationCenter::RegisterLog(string status, string detail)
{
   int h = FileOpen("Notifications.log", FILE_COMMON | FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE)
      return;

   FileSeek(h, 0, SEEK_END);
   FileWrite(h, TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS), status, detail);
   FileClose(h);
}

//--------------------------------------------------
// AUDITORIA (integracao com AuditLog)
//--------------------------------------------------

void CNotificationCenter::RegisterAudit(string detail, bool ok)
{
   // AuditLogSimple(symbol, direction, result, score) - registra evento simples
   AuditLogSimple(_Symbol, "NOTIFY", (ok ? "OK" : "FAIL") + "|" + detail, 0.0);
}

//--------------------------------------------------
// EVENTOS ESPECIFICOS
//--------------------------------------------------

bool CNotificationCenter::SendTradeOpen(string symbol, double volume, double price, string type)
{
   string msg = "[ABERTURA] " + type + " " + symbol + " | lote=" + DoubleToString(volume, 2) +
      " | preco=" + DoubleToString(price, _Digits);
   return Send(msg, NOTIFY_NORMAL, NCAT_TRADE_OPEN);
}

bool CNotificationCenter::SendTradeClose(string symbol, double profit, string comment)
{
   string msg = "[FECHAMENTO] " + symbol + " | P/L=" + DoubleToString(profit, 2) +
      " | " + comment;
   return Send(msg, NOTIFY_NORMAL, NCAT_TRADE_CLOSE);
}

bool CNotificationCenter::SendError(string module, string error)
{
   string msg = "[ERRO] " + module + ": " + error;
   return Send(msg, NOTIFY_HIGH, NCAT_ERROR);
}

bool CNotificationCenter::SendExecutionFailure(string symbol, string error)
{
   string msg = "[FALHA EXECUCAO] " + symbol + ": " + error;
   return Send(msg, NOTIFY_HIGH, NCAT_EXECUTION);
}

bool CNotificationCenter::SendDrawdown(double dd_percent)
{
   string msg = "[RISCO] Drawdown atual: " + DoubleToString(dd_percent, 2) + "%";
   return Send(msg, NOTIFY_HIGH, NCAT_DRAWDOWN);
}

bool CNotificationCenter::SendHealthAlert(string detail)
{
   string msg = "[SAUDE] Falha detectada: " + detail;
   return Send(msg, NOTIFY_CRITICAL, NCAT_HEALTH);
}

bool CNotificationCenter::SendCircuitBreaker(string state, string reason)
{
   string msg = "[CIRCUIT BREAKER] State=" + state + " | Reason=" + reason;
   return Send(msg, NOTIFY_CRITICAL, NCAT_CIRCUIT);
}

bool CNotificationCenter::SendDailyReport(double profit, int trades, double win_rate)
{
   string msg = "[RELATORIO] Profit=" + DoubleToString(profit, 2) +
      " | Trades=" + IntegerToString(trades) +
      " | WinRate=" + DoubleToString(win_rate, 2) + "%";
   return Send(msg, NOTIFY_LOW, NCAT_REPORT);
}

bool CNotificationCenter::SendSystemAlert(string alert)
{
   string msg = "[SISTEMA] " + alert;
   return Send(msg, NOTIFY_CRITICAL, NCAT_SYSTEM);
}

//--------------------------------------------------
// GETTERS / STATUS
//--------------------------------------------------

int CNotificationCenter::GetSentCount()
{
   return m_sent_count;
}

int CNotificationCenter::GetFailedCount()
{
   return m_failed_count;
}

string CNotificationCenter::GetStatus()
{
   return StringFormat("Sent=%d | Failed=%d | Push=%s | Telegram=%s | MaxMin=%d",
      m_sent_count, m_failed_count,
      m_push_enabled ? "ON" : "OFF",
      (m_telegram_token != "" && m_telegram_chat_id != "") ? "ON" : "OFF",
      m_max_per_minute);
}

void CNotificationCenter::LogStatus()
{
   Print("[NOTIFY] " + GetStatus());
}

#endif // NOTIFICATION_CENTER_MQH
