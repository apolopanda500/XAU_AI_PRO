//+------------------------------------------------------------------+
//|                                              DatabaseManager.mqh |
//|                                  SQLite Database Manager         |
//|                                            XAU_AI_PRO v1.2.0       |
//+------------------------------------------------------------------+

#ifndef DATABASE_MANAGER_MQH
#define DATABASE_MANAGER_MQH

#import "sqlite3.dll"
   int sqlite3_open(string filename, int &db);
   int sqlite3_close(int db);
   int sqlite3_exec(int db, string sql, int callback, int param, string &errmsg);
   string sqlite3_errmsg(int db);
#import

class CDatabaseManager
{
private:
   static int    m_db;
   static bool   m_initialized;
   static string m_db_path;
   static bool ExecuteQuery(const string sql);
public:
   static void Init();
   static bool Connect();
   static void Disconnect();
   static bool IsConnected();
   static bool InsertTrade(ulong ticket, string symbol, int type, double volume, double price, datetime time, string comment);
   static bool UpdateTrade(ulong ticket, double close_price, datetime close_time, double profit, double commission, double swap);
   static bool InsertTick(string symbol, datetime time, double bid, double ask, double volume);
   static bool InsertDecision(datetime time, string symbol, string signal, double confidence, double score, string reason);
   static bool InsertError(datetime time, string module, string error_msg, int error_code);
   static double GetTotalProfit();
   static int GetTotalTrades();
   static double GetWinRate();
   static bool Backup(const string backup_path);
   static bool Restore(const string backup_path);
   static string GetStatus();
   static void LogStatus();
};

int CDatabaseManager::m_db = 0;
bool CDatabaseManager::m_initialized = false;
string CDatabaseManager::m_db_path = "";

void CDatabaseManager::Init()
{
   if(m_initialized) return;
   m_db_path = TerminalInfoString(TERMINAL_PATH) + "\\MQL5\\Experts\\XAU_AI_PRO\\Enterprise\\Data\\xau_ai_pro.db";
   m_initialized = true;
   Print("[DATABASE] DatabaseManager initialized");
}

bool CDatabaseManager::Connect()
{
   if(m_db != 0) return true;
   // v1.2.0 fix: em backtest o sqlite3.dll nao esta no agente do tester
   if(MQLInfoInteger(MQL_TESTER)!=0)
      return false;
   int result = sqlite3_open(m_db_path, m_db);
   if(result != 0) { PrintFormat("[DATABASE] Failed: %s", sqlite3_errmsg(m_db)); return false; }
   ExecuteQuery("CREATE TABLE IF NOT EXISTS trades (ticket INTEGER PRIMARY KEY, symbol TEXT, type INTEGER, volume REAL, open_price REAL, open_time INTEGER, close_price REAL, close_time INTEGER, profit REAL, commission REAL, swap REAL, comment TEXT)");
   ExecuteQuery("CREATE TABLE IF NOT EXISTS ticks (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, time INTEGER, bid REAL, ask REAL, volume REAL)");
   ExecuteQuery("CREATE TABLE IF NOT EXISTS decisions (id INTEGER PRIMARY KEY AUTOINCREMENT, time INTEGER, symbol TEXT, signal TEXT, confidence REAL, score REAL, reason TEXT)");
   ExecuteQuery("CREATE TABLE IF NOT EXISTS errors (id INTEGER PRIMARY KEY AUTOINCREMENT, time INTEGER, module TEXT, error_msg TEXT, error_code INTEGER)");
   Print("[DATABASE] Connected: " + m_db_path);
   return true;
}

void CDatabaseManager::Disconnect() { if(m_db != 0) { sqlite3_close(m_db); m_db = 0; Print("[DATABASE] Disconnected"); } }
bool CDatabaseManager::IsConnected() { return (m_db != 0); }

bool CDatabaseManager::ExecuteQuery(const string sql)
{
   if(m_db == 0) return false;
   string errmsg;
   int result = sqlite3_exec(m_db, sql, 0, 0, errmsg);
   if(result != 0) { PrintFormat("[DATABASE] SQL error: %s", errmsg); return false; }
   return true;
}

bool CDatabaseManager::InsertTrade(ulong ticket, string symbol, int type, double volume, double price, datetime time, string comment)
{
   if(m_db == 0) return false;
   string sql = StringFormat("INSERT OR REPLACE INTO trades VALUES (%llu,'%s',%d,%.2f,%.5f,%d,0,0,0,0,0,'%s')", ticket, symbol, type, volume, price, (int)time, comment);
   return ExecuteQuery(sql);
}

bool CDatabaseManager::UpdateTrade(ulong ticket, double close_price, datetime close_time, double profit, double commission, double swap)
{
   if(m_db == 0) return false;
   string sql = StringFormat("UPDATE trades SET close_price=%.5f, close_time=%d, profit=%.2f, commission=%.2f, swap=%.2f WHERE ticket=%llu", close_price, (int)close_time, profit, commission, swap, ticket);
   return ExecuteQuery(sql);
}

bool CDatabaseManager::InsertTick(string symbol, datetime time, double bid, double ask, double volume)
{
   if(m_db == 0) return false;
   string sql = StringFormat("INSERT INTO ticks (symbol, time, bid, ask, volume) VALUES ('%s',%d,%.5f,%.5f,%.2f)", symbol, (int)time, bid, ask, volume);
   return ExecuteQuery(sql);
}

bool CDatabaseManager::InsertDecision(datetime time, string symbol, string signal, double confidence, double score, string reason)
{
   if(m_db == 0) return false;
   string sql = StringFormat("INSERT INTO decisions (time, symbol, signal, confidence, score, reason) VALUES (%d,'%s','%s',%.2f,%.2f,'%s')", (int)time, symbol, signal, confidence, score, reason);
   return ExecuteQuery(sql);
}

bool CDatabaseManager::InsertError(datetime time, string module, string error_msg, int error_code)
{
   if(m_db == 0) return false;
   string sql = StringFormat("INSERT INTO errors (time, module, error_msg, error_code) VALUES (%d,'%s','%s',%d)", (int)time, module, error_msg, error_code);
   return ExecuteQuery(sql);
}

double CDatabaseManager::GetTotalProfit() { return 0; }
int CDatabaseManager::GetTotalTrades() { return 0; }
double CDatabaseManager::GetWinRate() { return 0; }

bool CDatabaseManager::Backup(const string backup_path) { if(m_db == 0) return false; Disconnect(); bool ok = FileCopy(backup_path, 0, m_db_path, 0); Connect(); return ok; }
bool CDatabaseManager::Restore(const string backup_path) { return Backup(backup_path); }

string CDatabaseManager::GetStatus() { return StringFormat("DB: %s | Connected: %s", m_db_path, IsConnected() ? "Yes" : "No"); }
void CDatabaseManager::LogStatus() { Print("[DATABASE] " + GetStatus()); }

#endif // DATABASE_MANAGER_MQH
