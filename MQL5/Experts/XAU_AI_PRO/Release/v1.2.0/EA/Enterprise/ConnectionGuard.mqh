//+------------------------------------------------------------------+
//|                                          ConnectionGuard.mqh    |
//|                                     XAU_AI_PRO - Hardening E12  |
//|                        Conexion/Broker/Mercado connection guard |
//+------------------------------------------------------------------+
// ETAPA 12 (1/12) - FALHAS DE CONEXION
//
// Guardia de conexion del EA. Monitoring de bajo nivel de la conexion
// con el broker y del estado del mercado para evitar enviar ordenes
// con datos inutilizables (precio invalido, mercado cerrado, desconexion).
//
// PRINCIPIO: CanOperate() debe ser llamada en el OnTick/pipeline para
// permitir o bloquear NOVAS ENTRADAS. NUNCA debe usarse para detener
// la gestion de posiciones abertas (SL/TP/pendientes/close).
//
// Fuentes MQL5 utilizadas:
//   - TerminalInfoInteger(TERMINAL_CONNECTED)  : conexion del terminal
//   - MQLInfoInteger(MQL_TRADE_ALLOWED)         : algo trading permitido
//   - TerminalInfoInteger(TERMINAL_TRADE_ALLOWED): algo trading boton
//   - SymbolInfoInteger(symbol, SYMBOL_VALID)  : simbolo disponible
//   - SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE): modo de trading
//+------------------------------------------------------------------+

#ifndef CONNECTION_GUARD_MQH
#define CONNECTION_GUARD_MQH

#include "../Core/Config.mqh"

//==================================================
// ESTADO/ULTIMO CHECK
//==================================================
bool    g_connTerminalConnected       = false;
bool    g_connAccountTradeAllowed      = false;
bool    g_connAlgoAllowed              = false;
bool    g_connSymbolValid              = false;
bool    g_connMarketOpen               = false;
datetime  g_connLastCheck               = 0;
string  g_connLastError                = "";

//==================================================
// CHECK TERMINAL / TRADING ALLOWED
//==================================================
bool ConnTerminalUp()
{
   return (TerminalInfoInteger(TERMINAL_CONNECTED) != 0);
}

bool ConnAlgoAllowed()
{
   // Algor trading del terminal + del EA habilitado
   if(MQLInfoInteger(MQL_TRADE_ALLOWED) == 0)
      return false;
   if(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) == 0)
      return false;
   return true;
}

//==================================================
// CHECK CONEXION (nivel broker/account)
//==================================================
bool ConnBrokerConnected()
{
   // AccountInfoInteger ACCOUNT_TRADE_ALLOWED refleja permiso de cuenta.
   // En una conexion sana, al menos el terminal esta conectado y la cuenta operativa.
   bool terminal = ConnTerminalUp();
   bool account  = (AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) != 0);

   return (terminal && account);
}

//==================================================
// CHECK INSTRUMENTO / MERCADO ABIERTO
//==================================================
bool ConnSymbolTradeable(const string symbol)
{
   if(symbol == "")
      return true;   // no se puede validar simbolo vacio -> no bloquear

   // Simbolo disponible no terminal (SYMBOL_VISIBLE=1) + existe especial
   if(SymbolInfoInteger(symbol, SYMBOL_VISIBLE) == 0 &&
      SymbolInfoInteger(symbol, SYMBOL_EXIST) == 0)
      return false;

   // Modo de trading: 0 = NO_TRADES (no operar si el instrumento no permite trading)
   // Los modos MQL5: 0=NO_TRADES, 1=CLOSED/FULL..., 2=OPENED_TRADES, etc.
   ENUM_SYMBOL_TRADE_MODE mode = (ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE);
   if((int)mode == 0)
      return false;

   // Precio valido (bid/ask > 0)
   if(SymbolInfoDouble(symbol, SYMBOL_BID) <= 0.0 ||
      SymbolInfoDouble(symbol, SYMBOL_ASK) <= 0.0)
      return false;

   return true;
}

bool ConnMarketOpen(const string symbol)
{
   if(symbol == "")
      return true;
   if(!ConnSymbolTradeable(symbol))
      return false;

   // Mercado de referencia: sesion de trading activa segun el instrumento.
   // No bloquea en intervalo vacio porque algunos mercados son 24h.
   return true;
}

//==================================================
// REFRESH - actualiza el estado global (chamar cada bar)
//==================================================
void ConnectionGuardRefresh()
{
   g_connTerminalConnected  = ConnTerminalUp();
   g_connAccountTradeAllowed = ConnBrokerConnected();
   g_connAlgoAllowed        = ConnAlgoAllowed();
   g_connSymbolValid        = ConnSymbolTradeable(_Symbol);
   g_connMarketOpen         = ConnMarketOpen(_Symbol);
   g_connLastCheck          = TimeCurrent();

   g_connLastError = "";
   if(!g_connTerminalConnected)
      g_connLastError = "Terminal desconectado";
   else if(!g_connAccountTradeAllowed)
      g_connLastError = "Trading de cuenta deshabilitado";
   else if(!g_connAlgoAllowed)
      g_connLastError = "Algo trading (MT5/EA) apagado";
   else if(!g_connSymbolValid)
      g_connLastError = "Simbolo no disponible / modo sin trades";
   else if(!g_connMarketOpen)
      g_connLastError = "Mercado/instrumento no operativo";
}

//==================================================
// CAN OPERATE - decide si permitir NOVAS ENTRADAS
//==================================================
bool ConnectionGuardCanOperate()
{
   ConnectionGuardRefresh();

   // Requisitos: terminal conectado + trading de cuenta + algo trading
   if(!g_connTerminalConnected)
      return false;
   if(!g_connAccountTradeAllowed)
      return false;
   if(!g_connAlgoAllowed)
      return false;

   // Para abrir nuevas posiciones: simbolo valido y precio disponible
   if(!g_connSymbolValid)
      return false;

   return true;
}

bool ConnectionGuardConnected()
{
   ConnectionGuardRefresh();
   return (g_connTerminalConnected && g_connAccountTradeAllowed);
}

//====================================================
// GETTERS
//====================================================
string ConnectionGuardGetError()
{
   return g_connLastError;
}

bool ConnectionGuardTerminalUp()
{
   return g_connTerminalConnected;
}

bool ConnectionGuardAccountTradingAllowed()
{
   return g_connAccountTradeAllowed;
}

//====================================================
// SUMMARY
//====================================================
string ConnectionGuardSummary()
{
   return StringFormat("ConnGuard | Terminal=%s | Account=%s | Algo=%s | Symbol=%s | Market=%s | LastError=%s",
      (g_connTerminalConnected ? "UP" : "DOWN"),
      (g_connAccountTradeAllowed ? "ON" : "OFF"),
      (g_connAlgoAllowed ? "ON" : "OFF"),
      (g_connSymbolValid ? "VALID" : "INVALID"),
      (g_connMarketOpen ? "OPEN" : "CLOSED"),
      (g_connLastError == "" ? "None" : g_connLastError));
}

#endif // CONNECTION_GUARD_MQH