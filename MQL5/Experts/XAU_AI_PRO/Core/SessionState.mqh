// XAU_AI_PRO v1.2.10
#ifndef SESSIONSTATE_MQH
#define SESSIONSTATE_MQH

//==================================================
// PERSISTENCIA DO ESTADO DA SESSAO
//
// `TradesToday`, `ConsecutiveWins/Losses` e `PeakEquity`
// viviam so na memoria do programa. Medido em 29/10/2026:
// cada recarga (recompilar, trocar de grafico, reiniciar
// o MT5) zerava PeakEquity para o equity atual — e o
// drawdown, que e medido contra o pico, recomecava de
// zero. O freio de drawdown ficava mais frouxo a cada
// recarga, sem nenhum aviso.
//
// Aqui esses contadores vao para MQL5\Files\Data\ e
// voltam no OnInit, com dois limites explicitos:
//   - o estado e POR CONTA (login) e POR DIA: pico de
//     equity e contagem de trades sao intradiarios;
//   - dia diferente = estado novo (nao herda nada).
//
// Formato (uma linha):
//   login;data(dia);trades;wins;losses;pico;saved
//==================================================

#define SESSION_STATE_FILE      "Data\\XAU_AI_PRO_session.csv"
#define SESSION_STATE_FILE_ALT  "XAU_AI_PRO_session.csv"

input bool EnableSessionStatePersistence = true;   // Mantem contadores/pico ao recarregar o EA

struct EASessionState
{
   long     login;
   string   day;              // "YYYY.MM.DD" no horario do servidor
   int      tradesToday;
   int      consecWins;
   int      consecLosses;
   double   peakEquity;
   datetime savedAt;
};

//--------------------------------------------------

string SessionStateToday()
{
   return(TimeToString(TimeCurrent(),TIME_DATE));
}

//--------------------------------------------------

int SessionStateOpen(int flags)
{
   ResetLastError();

   int handle=FileOpen(
      SESSION_STATE_FILE,
      flags|FILE_TXT|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE
   );

   if(handle!=INVALID_HANDLE)
      return handle;

   handle=FileOpen(
      SESSION_STATE_FILE_ALT,
      flags|FILE_TXT|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE
   );

   return handle;
}

//--------------------------------------------------

bool SessionStateExists()
{
   if(FileIsExist(SESSION_STATE_FILE))
      return true;

   return FileIsExist(SESSION_STATE_FILE_ALT);
}

//--------------------------------------------------

bool SessionStateSave(EASessionState &st)
{
   if(!EnableSessionStatePersistence)
      return false;

   int handle=SessionStateOpen(FILE_WRITE);

   if(handle==INVALID_HANDLE)
      return false;

   st.login   = (long)AccountInfoInteger(ACCOUNT_LOGIN);
   st.day     = SessionStateToday();
   st.savedAt = TimeCurrent();

   string line=
      IntegerToString(st.login)+";"+
      st.day+";"+
      IntegerToString(st.tradesToday)+";"+
      IntegerToString(st.consecWins)+";"+
      IntegerToString(st.consecLosses)+";"+
      DoubleToString(st.peakEquity,2)+";"+
      IntegerToString((long)st.savedAt);

   FileWrite(handle,line);

   FileClose(handle);

   return true;
}

//--------------------------------------------------
// Le o estado. Devolve false quando nao ha nada
// aproveitavel: arquivo ausente, outra conta, outro dia
// ou linha corrompida. Nunca "chuta" valores.
//--------------------------------------------------

bool SessionStateLoad(EASessionState &st)
{
   if(!EnableSessionStatePersistence)
      return false;

   if(!SessionStateExists())
      return false;

   int handle=SessionStateOpen(FILE_READ);

   if(handle==INVALID_HANDLE)
      return false;

   string hoje=SessionStateToday();
   bool   ok=false;
   string motivo="sem linha valida";

   while(!FileIsEnding(handle))
   {
      string line=FileReadString(handle);

      StringTrimLeft(line);
      StringTrimRight(line);

      if(line=="")
         continue;

      string part[];

      int n=StringSplit(line,(ushort)';',part);

      if(n<6)
      {
         motivo="linha com "+IntegerToString(n)+" campos";
         continue;
      }

      long login=(long)StringToInteger(part[0]);

      if(login!=(long)AccountInfoInteger(ACCOUNT_LOGIN))
      {
         motivo="outra conta ("+part[0]+")";
         continue;
      }

      if(part[1]!=hoje)
      {
         motivo="outro dia ("+part[1]+", hoje="+hoje+")";
         continue;
      }

      st.login          = login;
      st.day            = part[1];
      st.tradesToday    = (int)StringToInteger(part[2]);
      st.consecWins     = (int)StringToInteger(part[3]);
      st.consecLosses   = (int)StringToInteger(part[4]);
      st.peakEquity     = StringToDouble(part[5]);
      st.savedAt        = (n>=7 ? (datetime)StringToInteger(part[6]) : 0);

      ok=true;

      break;
   }

   FileClose(handle);

   if(!ok)
      Print("[SESSION] nada a restaurar | motivo=",motivo);

   return ok;
}

//--------------------------------------------------

string SessionStateSummary(EASessionState &st)
{
   return(
      "conta="+IntegerToString(st.login)+
      " | dia="+st.day+
      " | trades="+IntegerToString(st.tradesToday)+
      " | W="+IntegerToString(st.consecWins)+
      " | L="+IntegerToString(st.consecLosses)+
      " | pico="+DoubleToString(st.peakEquity,2)
   );
}

#endif
