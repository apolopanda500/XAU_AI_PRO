//+------------------------------------------------------------------+
//|                                 TradeLoggerSQLite.mqh            |
//| XAU_AI_PRO v1.2.121 - TradeLogger com SQLite NATIVO do MQL5      |
//| Historico de trades em banco estruturado, sem CSV colado.        |
//+------------------------------------------------------------------+
// ESTADO: ATIVO e a compilar 0 errors / 0 warnings no EA e no script
// de prova Scripts/XAI_SqliteLoggerProbe.mq5.
//
// CORRECAO P2.11 (03/11/2026) - o ficheiro NAO COMPILAVA e quebrava o
// EA inteiro com 23 erros. Defeitos medidos:
//   (1) `#include <Database.mqh>` - esse ficheiro NAO EXISTE no MQL5.
//       `dir /b /s Database.mqh` no terminal devolve vazio e nao ha
//       Database.mqh na pasta Include. O SQLite e NATIVO da linguagem
//       (DatabaseOpen, DatabasePrepare, DatabaseBind, DatabaseRead,
//       DatabaseFinalize, ...), nao precisa de include nenhum. Por isso
//       este modulo NAO fica atras de um #ifdef: nao ha dependencia
//       externa para desligar.
//   (2) `CDatabase` e os metodos `db.Attach/Prepare/BindInteger/Step/
//       ColumnInteger` tambem nao existem: eram de uma biblioteca
//       imaginaria. As funcoes reais sao livres e recebem o handle.
//   (3) Assinaturas reais medidas por compilacao de sonda
//       (Files/Temp/db_probe.mq5): DatabaseClose e DatabaseFinalize
//       devolvem void; DatabaseColumnText/Integer/Double devolvem bool e
//       escrevem o valor por REFERENCIA; DatabaseColumnInteger so aceita
//       int& (nao ha overload long&), por isso ticket e time (64 bits)
//       sao lidos como texto e convertidos com StringToInteger.
//   (4) O INSERT por prepared statement EXECUTA no DatabaseRead() e nao
//       devolve linha. Medido em runtime: o DatabaseRead de um INSERT
//       bem sucedido deixa 5126 ("sem mais dados"). A primeira versao
//       tratava 5126 como erro e dizia "falha" em gravacoes que tinham
//       sido gravadas. 5126 passou a ser resultado normal.
// A API publica ficou identica (STradeRecord, CTradeLoggerSQLite,
// g_trade_logger_sqlite, TradeLoggerSQLiteInit/Log/Shutdown), portanto
// XAU_AI_PRO.mq5 nao precisou de mudar uma linha.
// Isto grava historico; nao abre, fecha nem altera nenhuma posicao.
//+------------------------------------------------------------------+
#ifndef TRADE_LOGGER_SQLITE_MQH
#define TRADE_LOGGER_SQLITE_MQH

// Codigo de erro devolvido por DatabaseRead quando o statement nao tem
// linha de resultado (caso do INSERT). Nao e falha.
#define XAI_DB_NO_MORE_DATA 5126

// Nome do banco por omissao (ficheiro criado em MQL5\Files pelo sandbox).
#define XAI_TRADE_DB_NAME "trade_history.db"

//+------------------------------------------------------------------+
//| Estrutura de registro de trade (13 colunas)                      |
//+------------------------------------------------------------------+
struct STradeRecord
{
   ulong    ticket;
   long     magic;
   string   origin;          // "EA", "MANUAL", "COPY", "MCP"
   datetime time;
   string   symbol;
   long     type;            // POSITION_TYPE_BUY / POSITION_TYPE_SELL
   double   volume;
   double   price_open;
   double   sl;
   double   tp;
   double   price_close;
   double   profit;
   string   details;
};

//+------------------------------------------------------------------+
//| Classe TradeLoggerSQLite                                         |
//+------------------------------------------------------------------+
class CTradeLoggerSQLite
{
private:
   int      m_db_handle;
   bool     m_connected;
   string   m_db_path;

public:
   CTradeLoggerSQLite();
   ~CTradeLoggerSQLite();

   bool  Connect(const string db_name = XAI_TRADE_DB_NAME);
   void  Disconnect();

   bool  InsertTrade(const STradeRecord &rec);
   bool  CreateTableIfNotExists();

   //--- Consulta por ticket
   bool  GetTradeByTicket(ulong ticket, STradeRecord &rec);

   //--- Estatisticas
   int   GetTotalTrades();
   double GetTotalProfit();

   //--- Diagnostico
   bool  IsConnected() const { return(m_connected); }
   string DatabasePath() const { return(m_db_path); }
};

//+------------------------------------------------------------------+
CTradeLoggerSQLite::CTradeLoggerSQLite()
{
   m_db_handle = INVALID_HANDLE;
   m_connected = false;
   m_db_path   = "";
}

//+------------------------------------------------------------------+
CTradeLoggerSQLite::~CTradeLoggerSQLite()
{
   Disconnect();
}

//+------------------------------------------------------------------+
//| Abre (ou cria) o banco e garante a tabela.                       |
//| Idempotente: o chamador abre e fecha a cada trade fechado.       |
//+------------------------------------------------------------------+
bool CTradeLoggerSQLite::Connect(const string db_name)
{
   if(m_connected)
      Disconnect();

   m_db_path = (db_name == "" ? (string)XAI_TRADE_DB_NAME : db_name);

   ResetLastError();
   m_db_handle = DatabaseOpen(m_db_path, DATABASE_OPEN_READWRITE | DATABASE_OPEN_CREATE);
   if(m_db_handle == INVALID_HANDLE)
   {
      Print("[SQLITE] Falha ao abrir banco: ", m_db_path, " erro=", GetLastError());
      m_connected = false;
      return(false);
   }

   m_connected = true;

   if(!CreateTableIfNotExists())
   {
      Print("[SQLITE] Falha ao criar tabela em ", m_db_path);
      Disconnect();
      return(false);
   }

   return(true);
}

//+------------------------------------------------------------------+
void CTradeLoggerSQLite::Disconnect()
{
   if(m_db_handle != INVALID_HANDLE)
   {
      DatabaseClose(m_db_handle);   // retorna void
      m_db_handle = INVALID_HANDLE;
   }
   m_connected = false;
}

//+------------------------------------------------------------------+
bool CTradeLoggerSQLite::CreateTableIfNotExists()
{
   if(!m_connected || m_db_handle == INVALID_HANDLE)
      return(false);

   string sql =
      "CREATE TABLE IF NOT EXISTS trades ("
      "  ticket      INTEGER PRIMARY KEY,"
      "  magic       INTEGER NOT NULL,"
      "  origin      TEXT    NOT NULL,"
      "  time        INTEGER NOT NULL,"
      "  symbol      TEXT    NOT NULL,"
      "  type        INTEGER NOT NULL,"
      "  volume      REAL    NOT NULL,"
      "  price_open  REAL    NOT NULL,"
      "  sl          REAL    NOT NULL,"
      "  tp          REAL    NOT NULL,"
      "  price_close REAL    DEFAULT 0,"
      "  profit      REAL    DEFAULT 0,"
      "  details     TEXT"
      ");";

   ResetLastError();
   if(!DatabaseExecute(m_db_handle, sql))
   {
      Print("[SQLITE] Erro CREATE TABLE: erro=", GetLastError());
      return(false);
   }

   // Indices para consulta por simbolo e por data (falha nao e fatal).
   DatabaseExecute(m_db_handle, "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);");
   DatabaseExecute(m_db_handle, "CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(time);");

   return(true);
}

//+------------------------------------------------------------------+
//| INSERT OR REPLACE parametrizado (sem concatenar strings).        |
//+------------------------------------------------------------------+
bool CTradeLoggerSQLite::InsertTrade(const STradeRecord &rec)
{
   if(!m_connected || m_db_handle == INVALID_HANDLE)
      return(false);

   ResetLastError();
   int req = DatabasePrepare(m_db_handle,
      "INSERT OR REPLACE INTO trades ("
      "  ticket, magic, origin, time, symbol, type, volume, "
      "  price_open, sl, tp, price_close, profit, details"
      ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?);");

   if(req == INVALID_HANDLE)
   {
      Print("[SQLITE] Erro PREPARE INSERT: erro=", GetLastError());
      return(false);
   }

   bool bound = true;
   bound = DatabaseBind(req,  0, (long)rec.ticket)  && bound;
   bound = DatabaseBind(req,  1, rec.magic)         && bound;
   bound = DatabaseBind(req,  2, rec.origin)        && bound;
   bound = DatabaseBind(req,  3, (long)rec.time)    && bound;
   bound = DatabaseBind(req,  4, rec.symbol)        && bound;
   bound = DatabaseBind(req,  5, rec.type)          && bound;
   bound = DatabaseBind(req,  6, rec.volume)        && bound;
   bound = DatabaseBind(req,  7, rec.price_open)    && bound;
   bound = DatabaseBind(req,  8, rec.sl)            && bound;
   bound = DatabaseBind(req,  9, rec.tp)            && bound;
   bound = DatabaseBind(req, 10, rec.price_close)   && bound;
   bound = DatabaseBind(req, 11, rec.profit)        && bound;
   bound = DatabaseBind(req, 12, rec.details)       && bound;

   if(!bound)
   {
      Print("[SQLITE] Erro BIND INSERT: erro=", GetLastError());
      DatabaseFinalize(req);
      return(false);
   }

   // Um INSERT executa aqui e NAO devolve linha. Medido em runtime: o
   // DatabaseRead de um INSERT bem sucedido deixa 5126 (sem mais dados),
   // logo so uma falha REAL conta como falha.
   ResetLastError();
   DatabaseRead(req);
   int err = GetLastError();
   DatabaseFinalize(req);

   if(err != 0 && err != XAI_DB_NO_MORE_DATA)
   {
      Print("[SQLITE] Erro STEP INSERT: erro=", err);
      return(false);
   }

   return(true);
}

//+------------------------------------------------------------------+
//| Le um trade pelo ticket. Devolve false se o ticket nao existir.  |
//+------------------------------------------------------------------+
bool CTradeLoggerSQLite::GetTradeByTicket(ulong ticket, STradeRecord &rec)
{
   if(!m_connected || m_db_handle == INVALID_HANDLE)
      return(false);

   ResetLastError();
   int req = DatabasePrepare(m_db_handle, "SELECT * FROM trades WHERE ticket = ?;");
   if(req == INVALID_HANDLE)
   {
      Print("[SQLITE] Erro PREPARE SELECT: erro=", GetLastError());
      return(false);
   }

   if(!DatabaseBind(req, 0, (long)ticket))
   {
      DatabaseFinalize(req);
      return(false);
   }

   if(!DatabaseRead(req))
   {
      DatabaseFinalize(req);
      return(false);
   }

   // Colunas por referencia. ticket/time tem 64 bits e nao ha overload
   // long& em DatabaseColumnInteger, logo vao por texto.
   int    iv = 0;
   string st = "";

   if(DatabaseColumnText(req, 0, st))
      rec.ticket = (ulong)StringToInteger(st);
   if(DatabaseColumnInteger(req, 1, iv))
      rec.magic = (long)iv;

   DatabaseColumnText(req, 2, rec.origin);

   st = "";
   if(DatabaseColumnText(req, 3, st))
      rec.time = (datetime)StringToInteger(st);

   DatabaseColumnText(req, 4, rec.symbol);

   if(DatabaseColumnInteger(req, 5, iv))
      rec.type = (long)iv;

   DatabaseColumnDouble(req,  6, rec.volume);
   DatabaseColumnDouble(req,  7, rec.price_open);
   DatabaseColumnDouble(req,  8, rec.sl);
   DatabaseColumnDouble(req,  9, rec.tp);
   DatabaseColumnDouble(req, 10, rec.price_close);
   DatabaseColumnDouble(req, 11, rec.profit);
   DatabaseColumnText(req,   12, rec.details);

   DatabaseFinalize(req);

   return(true);
}

//+------------------------------------------------------------------+
int CTradeLoggerSQLite::GetTotalTrades()
{
   if(!m_connected || m_db_handle == INVALID_HANDLE)
      return(0);

   ResetLastError();
   int req = DatabasePrepare(m_db_handle, "SELECT COUNT(*) FROM trades;");
   if(req == INVALID_HANDLE)
      return(0);

   int total = 0;
   if(DatabaseRead(req))
      DatabaseColumnInteger(req, 0, total);

   DatabaseFinalize(req);
   return(total);
}

//+------------------------------------------------------------------+
double CTradeLoggerSQLite::GetTotalProfit()
{
   if(!m_connected || m_db_handle == INVALID_HANDLE)
      return(0.0);

   ResetLastError();
   int req = DatabasePrepare(m_db_handle, "SELECT COALESCE(SUM(profit),0) FROM trades;");
   if(req == INVALID_HANDLE)
      return(0.0);

   double total = 0.0;
   if(DatabaseRead(req))
      DatabaseColumnDouble(req, 0, total);

   DatabaseFinalize(req);
   return(total);
}

//+------------------------------------------------------------------+
//| Instancia global                                                 |
//+------------------------------------------------------------------+
CTradeLoggerSQLite g_trade_logger_sqlite;

//+------------------------------------------------------------------+
//| Funcoes de conveniencia (contrato usado por XAU_AI_PRO.mq5)       |
//+------------------------------------------------------------------+
bool TradeLoggerSQLiteInit(const string db_name = XAI_TRADE_DB_NAME)
{
   return(g_trade_logger_sqlite.Connect(db_name));
}

void TradeLoggerSQLiteShutdown()
{
   g_trade_logger_sqlite.Disconnect();
}

bool TradeLoggerSQLiteLog(const STradeRecord &rec)
{
   return(g_trade_logger_sqlite.InsertTrade(rec));
}

#endif
//+------------------------------------------------------------------+
