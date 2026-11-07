// XAU_AI_PRO v1.2.10
#ifndef LEARNINGHISTORY_MQH
#define LEARNINGHISTORY_MQH

//==================================================
// APRENDIZADO PELO HISTORICO REAL
//
// A AILearningMemory original era volátil: zerava a
// cada recarga e nunca lia o histórico da conta.
// Este módulo acrescenta:
//
// 1) Diário append-only em MQL5\Files\Data\ (persiste
//    entre recargas, reinícios e mudanças de gráfico);
// 2) Ingestão do histórico real via HistorySelect(),
//    incluindo as operações MANUAIS do usuário
//    (magic == 0) e as do próprio EA;
// 3) Registro em tempo real de cada trade fechado
//    (OnTradeTransaction -> AILearningRecordDeal);
// 4) Ajuste de score por símbolo (LearningAdjustedScore)
//    usado pelo DecisionEngine.
//
// Formato do diário (uma linha por evento):
//   simbolo;ticket;direcao;confianca;resultado;hora
//==================================================

#include "AILearningMemory.mqh"
#include "../Monitoring/DiagGate.mqh"

//==================================================
// INPUTS
//==================================================

input group "=== APRENDIZADO PELO HISTORICO ==="

input bool   EnableLearningFromHistory  = true;   // Aprende com o historico real da conta
input bool   LearningImportManualTrades = true;   // Inclui as operacoes manuais (feitas por voce)
input bool   LearningImportExpertTrades = true;   // Inclui as operacoes do proprio EA
input int    LearningHistoryDays        = 180;    // Janela do historico em dias
input bool   EnableLearningBoost        = true;   // Usa a memoria para ajustar o score
input bool   LearningPenaltyEnabled     = false;  // Permite que a memoria REDUZA o score
input bool   LearningDirBoostEnabled    = true;   // Considera o vies por direcao (BUY x SELL)
input int    LearningDirMinTrades       = 3;      // Amostra minima por direcao para opinar
input bool   EnableLearningHourBoost    = true;   // Considera o horario/sessao do trade
input int    LearningHourMinTrades      = 4;      // Amostra minima por hora para opinar
input bool   EnableDirectionBlacklist   = false;  // BLOQUEIA entrada na direcao historicamente ruim
input int    DirectionBlacklistMinTrades= 5;      // Amostra minima para bloquear a direcao
input double DirectionBlacklistMaxWR    = 30.0;   // WR (%) que caracteriza direcao ruim

// PENALIDADE SEM VETO (v1.2.14): o historico ruim NAO bloqueia a entrada,
// apenas reduz o LOTE. O EA continua operando e saindo no lucro, so que
// menor onde historicamente erra (USDSEK 0/6, USDCHF 0/3, GBPUSD 0/3,
// NZDUSD SELL 7%). O score continua so incentivando (piso em 1.0).
input bool   EnableLearningLotPenalty    = true;  // Historico ruim reduz o LOTE (nunca bloqueia)
input int    LearningPenaltyMinTrades    = 5;     // Amostra minima para opinar no lote
input double LearningPenaltyMaxWR        = 40.0;  // WR (%) abaixo disso reduz o lote
input double LearningPenaltyLotFactor    = 0.60;  // Fator de lote nessa faixa
input double LearningPenaltyHardWR       = 25.0;  // WR (%) muito ruim
input double LearningPenaltyHardLotFactor= 0.45;  // Fator de lote nessa faixa
input bool   EnableLearningHourPenalty   = true;  // Hora historicamente ruim reduz o LOTE
input double LearningPenaltyHourLotFactor= 0.75;  // Fator de lote na hora ruim
// P1.6 (v1.2.35): a hora ruim so actuava no LOTE. O score continuava a ignorar
// o horario porque `LearningAdjustedScore` forca `boost>=1.0` sempre que
// `LearningPenaltyEnabled=false` - e o factor de hora ruim (0,92/0,96 em
// `HourBoost`) era descartado nesse piso. Este par de inputs deixa a hora
// reduzir o SCORE com um piso proprio, sem depender da penalidade global e
// sem nunca vetar sozinha (o piso 0,90 tira no maximo 10% do score).
input bool   EnableLearningHourScorePenalty = true;  // Hora historicamente ruim reduz o SCORE
input double LearningHourScoreFloor        = 0.90;  // Piso do factor de hora no score (0,90-1,00)

//==================================================
// CONSTANTES
//==================================================

#define LEARNING_JOURNAL      "Data\\XAU_AI_PRO_learning.csv"
#define LEARNING_JOURNAL_ALT  "XAU_AI_PRO_learning.csv"
#define LEARNING_IMPORT_GV    "XAI_PRO_LEARN_IMPORT"

//==================================================
// CURSOR: ultimo deal ja aprendido por simbolo
// (evita contar o mesmo trade duas vezes)
//==================================================

struct AILearningCursor
{
   string   symbol;
   ulong    lastDeal;
};

static AILearningCursor g_LearnCursor[];

//==================================================

int LearningCursorIndex(string symbol)
{
   for(int i=0;i<ArraySize(g_LearnCursor);i++)
   {
      if(g_LearnCursor[i].symbol==symbol)
         return i;
   }

   return -1;
}

//==================================================

ulong LearningLastDeal(string symbol)
{
   int id=LearningCursorIndex(symbol);

   if(id<0)
      return 0;

   return g_LearnCursor[id].lastDeal;
}

//==================================================

void LearningSetLastDeal(string symbol, ulong deal)
{
   if(symbol=="" || deal==0)
      return;

   int id=LearningCursorIndex(symbol);

   if(id<0)
   {
      int n=ArraySize(g_LearnCursor);

      ArrayResize(g_LearnCursor,n+1);

      g_LearnCursor[n].symbol=symbol;
      g_LearnCursor[n].lastDeal=deal;

      return;
   }

   if(deal>g_LearnCursor[id].lastDeal)
      g_LearnCursor[id].lastDeal=deal;
}

//==================================================
//==================================================
// MEMORIA POR DIRECAO (BUY / SELL)
//
// O diario ja grava a direcao de cada trade. Aqui ela
// passa a valer: acertos e erros sao contados separados
// por simbolo+direcao, revelando o vies real do trader
// (ex.: XAUUSD comprado 91% x vendido 0%).
//==================================================

struct AILearningDirection
{
   string   symbol;
   int      dir;      // +1 BUY, -1 SELL
   int      total;
   int      wins;
};

static AILearningDirection g_LearnDir[];

int DirIndex(string symbol,int dir)
{
   for(int i=0;i<ArraySize(g_LearnDir);i++)
   {
      if(g_LearnDir[i].symbol==symbol && g_LearnDir[i].dir==dir)
         return i;
   }

   return -1;
}

void DirStore(string symbol,int dir,bool win)
{
   if(symbol=="" || dir==0)
      return;

   int id=DirIndex(symbol,dir);

   if(id<0)
   {
      int n=ArraySize(g_LearnDir);

      ArrayResize(g_LearnDir,n+1);

      g_LearnDir[n].symbol=symbol;
      g_LearnDir[n].dir=dir;
      g_LearnDir[n].total=0;
      g_LearnDir[n].wins=0;

      id=n;
   }

   g_LearnDir[id].total++;

   if(win)
      g_LearnDir[id].wins++;
}

int DirTotal(string symbol,int dir)
{
   int id=DirIndex(symbol,dir);

   if(id<0)
      return 0;

   return g_LearnDir[id].total;
}

// retorna -1 quando a amostra e menor que LearningDirMinTrades
double DirWinRate(string symbol,int dir)
{
   int id=DirIndex(symbol,dir);

   if(id<0 || g_LearnDir[id].total<LearningDirMinTrades)
      return -1.0;

   return(100.0*g_LearnDir[id].wins/g_LearnDir[id].total);
}

double DirBoost(string symbol,int dir)
{
   double wr=DirWinRate(symbol,dir);

   if(wr<0.0)
      return 1.0;

   if(wr>=70.0)
      return 1.10;

   if(wr>=55.0)
      return 1.05;

   if(wr<=30.0)
      return 0.90;

   if(wr<=45.0)
      return 0.95;

   return 1.0;
}

string DirSummary(string symbol)
{
   string out="";

   double wrBuy=DirWinRate(symbol,1);

   if(wrBuy>=0.0)
      out=out+" BUY="+DoubleToString(wrBuy,0)+"%("+IntegerToString(DirTotal(symbol,1))+")";

   double wrSell=DirWinRate(symbol,-1);

   if(wrSell>=0.0)
      out=out+" SELL="+DoubleToString(wrSell,0)+"%("+IntegerToString(DirTotal(symbol,-1))+")";

   return out;
}

//==================================================
//==================================================
// MEMORIA POR HORA DO DIA (sessao)
//
// O simbolo e a direcao nao contam a hora: o mesmo par
// pode render em Londres e devolver tudo no fim de Nova
// York. O diario ja grava o timestamp de cada trade,
// entao a hora sai de graca — sem campo novo no CSV.
//==================================================

struct AILearningHour
{
   string   symbol;
   int      hour;      // 0..23 (hora do servidor)
   int      total;
   int      wins;
};

static AILearningHour g_LearnHour[];

int HourIndex(string symbol,int hour)
{
   for(int i=0;i<ArraySize(g_LearnHour);i++)
   {
      if(g_LearnHour[i].symbol==symbol && g_LearnHour[i].hour==hour)
         return i;
   }

   return -1;
}

void HourStore(string symbol,int hour,bool win)
{
   if(symbol=="" || hour<0 || hour>23)
      return;

   int id=HourIndex(symbol,hour);

   if(id<0)
   {
      int n=ArraySize(g_LearnHour);

      ArrayResize(g_LearnHour,n+1);

      g_LearnHour[n].symbol=symbol;
      g_LearnHour[n].hour=hour;
      g_LearnHour[n].total=0;
      g_LearnHour[n].wins=0;

      id=n;
   }

   g_LearnHour[id].total++;

   if(win)
      g_LearnHour[id].wins++;
}

int HourTotal(string symbol,int hour)
{
   int id=HourIndex(symbol,hour);

   if(id<0)
      return 0;

   return g_LearnHour[id].total;
}

// retorna -1 quando a amostra e menor que LearningHourMinTrades
double HourWinRate(string symbol,int hour)
{
   int id=HourIndex(symbol,hour);

   if(id<0 || g_LearnHour[id].total<LearningHourMinTrades)
      return -1.0;

   return(100.0*g_LearnHour[id].wins/g_LearnHour[id].total);
}

double HourBoost(string symbol,int hour)
{
   double wr=HourWinRate(symbol,hour);

   if(wr<0.0)
      return 1.0;

   if(wr>=70.0)
      return 1.08;

   if(wr>=55.0)
      return 1.04;

   if(wr<=30.0)
      return 0.92;

   if(wr<=45.0)
      return 0.96;

   return 1.0;
}

int LearningServerHour(datetime t)
{
   MqlDateTime dt;

   TimeToStruct(t,dt);

   return dt.hour;
}

string HourSummary(string symbol)
{
   int melhor=-1, pior=-1;
   double melhorWR=-1.0, piorWR=101.0;

   for(int h=0;h<24;h++)
   {
      double wr=HourWinRate(symbol,h);

      if(wr<0.0)
         continue;

      if(wr>melhorWR)
      {
         melhorWR=wr;
         melhor=h;
      }

      if(wr<piorWR)
      {
         piorWR=wr;
         pior=h;
      }
   }

   string out="";

   if(melhor>=0)
      out=" MELHOR_HORA="+IntegerToString(melhor)+"h("+DoubleToString(melhorWR,0)+"%)";

   if(pior>=0 && pior!=melhor)
      out=out+" PIOR_HORA="+IntegerToString(pior)+"h("+DoubleToString(piorWR,0)+"%)";

   return out;
}

//==================================================
// BLOQUEIO OPCIONAL POR DIRECAO (item de risco)
//
// MEDIDO no historico da conta: USDSEK comprado 0/6,
// GBPUSD vendido 0/3, USDCHF comprado 0/3. O DirBoost
// ja reduzia o score, mas com LearningPenaltyEnabled=false
// o boost nunca fica abaixo de 1.0 — ou seja, o EA nao
// deixava de insistir. Aqui a direcao ruim pode ser
// BLOQUEADA de verdade. Desligado por padrao: bloquear
// e decisao do dono, nao efeito colateral do aprendizado.
//==================================================

double DirRawWinRate(string symbol,int dir)
{
   int id=DirIndex(symbol,dir);

   if(id<0 || g_LearnDir[id].total<=0)
      return -1.0;

   return(100.0*g_LearnDir[id].wins/g_LearnDir[id].total);
}

bool LearningDirectionBlocked(string symbol,int signal)
{
   if(!EnableLearningFromHistory || !EnableDirectionBlacklist)
      return false;

   if(symbol=="" || signal==0)
      return false;

   if(DirTotal(symbol,signal)<DirectionBlacklistMinTrades)
      return false;

   double wr=DirRawWinRate(symbol,signal);

   if(wr<0.0)
      return false;

   return(wr<=DirectionBlacklistMaxWR);
}

// ARQUIVO DE PERSISTENCIA
//==================================================

int LearningJournalOpen(int flags)
{
   ResetLastError();

   int handle=FileOpen(
      LEARNING_JOURNAL,
      flags|FILE_TXT|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE
   );

   if(handle!=INVALID_HANDLE)
      return handle;

   int err=GetLastError();

   // fallback: pasta Data ausente -> grava na raiz de MQL5\Files
   handle=FileOpen(
      LEARNING_JOURNAL_ALT,
      flags|FILE_TXT|FILE_ANSI|FILE_SHARE_READ|FILE_SHARE_WRITE
   );

   if(handle!=INVALID_HANDLE)
      return handle;

   Print(
      "[LEARN] journal indisponivel | path=",
      LEARNING_JOURNAL,
      " | err=",
      err,
      "/",
      GetLastError()
   );

   return INVALID_HANDLE;
}

//==================================================

bool LearningJournalExists()
{
   if(FileIsExist(LEARNING_JOURNAL))
      return true;

   return FileIsExist(LEARNING_JOURNAL_ALT);
}

//==================================================

bool LearningAppendEvent(
   string symbol,
   ulong deal,
   int signal,
   double confidence,
   bool win
)
{
   int handle=LearningJournalOpen(FILE_READ|FILE_WRITE);

   if(handle==INVALID_HANDLE)
      return false;

   FileSeek(handle,0,SEEK_END);

   string line=
      symbol+";"+
      IntegerToString((long)deal)+";"+
      IntegerToString(signal)+";"+
      DoubleToString(confidence,2)+";"+
      (win?"1":"0")+";"+
      IntegerToString((long)TimeCurrent());

   FileWrite(handle,line);

   FileClose(handle);

   return true;
}

//==================================================
// REPLAY DO DIARIO (recupera a memoria apos recarga)
//==================================================

int LearningReplayJournal()
{
   if(!LearningJournalExists())
      return 0;

   int handle=LearningJournalOpen(FILE_READ);

   if(handle==INVALID_HANDLE)
      return 0;

   int lines=0;
   int applied=0;

   g_AILearnQuiet=true;

   while(!FileIsEnding(handle))
   {
      string line=FileReadString(handle);

      if(line=="")
         continue;

      lines++;

      string part[];

      if(StringSplit(line,(ushort)';',part)<6)
         continue;   // linha truncada por escrita concorrente

      string   sym  = part[0];
      ulong    deal = (ulong)StringToInteger(part[1]);
      int      sig  = (int)StringToInteger(part[2]);
      double   conf = StringToDouble(part[3]);
      bool     win  = (StringToInteger(part[4])>0);

      if(sym=="" || deal==0)
         continue;

      if(deal<=LearningLastDeal(sym))
         continue;   // evento repetido

      // v1.2.10: 1 aplicacao por linha (evita contagem dobrada no replay)
      StoreExperience(sym,sig,conf,win);
      DirStore(sym,sig,win);
      HourStore(sym,sig,LearningServerHour((datetime)StringToInteger(part[5])));

      LearningSetLastDeal(sym,deal);

      applied++;
   }

   g_AILearnQuiet=false;

   FileClose(handle);

   if(applied<=0)
      if(LogInicioDetalhe()) { Print("[LEARN] diario ja aplicado | linhas=",lines); }

   if(applied>0)
      if(LogInicioDetalhe()) Print(
         "[LEARN] memoria restaurada do disco | linhas=",
         lines,
         " | aplicadas=",
         applied,
         " | simbolos=",
         ArraySize(g_AIMemory)
      );

   return applied;
}

//==================================================
// CONTROLE DE FREQUENCIA DA INGESTAO
//
// O EA roda em varios graficos; a importacao completa
// do historico e caro, entao roda uma vez por hora. Os demais
// leem o diario. O controle e por conta.
//==================================================

string LearningImportKey()
{
   return LEARNING_IMPORT_GV+"_"+
      IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
}

//==================================================

bool LearningImportDue()
{
   if(MQLInfoInteger(MQL_TESTER)!=0)
      return true;

   if(!GlobalVariableCheck(LearningImportKey()))
      return true;

   datetime last=(datetime)GlobalVariableGet(LearningImportKey());

   if(last<=0)
      return true;

   return((TimeCurrent()-last)>=3600);
}

//==================================================

void LearningMarkImportDone()
{
   if(MQLInfoInteger(MQL_TESTER)!=0)
      return;

   GlobalVariableSet(LearningImportKey(),(double)TimeCurrent());
}

//==================================================
// INGESTAO DO HISTORICO REAL
//==================================================

// v1.2.11: prototipo - a importacao usa a trava por deal e ela esta
// declarada mais abaixo, junto de AILearningRecordDeal.
bool LearningDealClaimed(ulong deal);

//==================================================
// DIRECAO DA POSICAO ORIGINAL (v1.2.12 - 29/10/2026)
//
// O aprendizado conta apenas deals de SAIDA (DEAL_ENTRY_OUT /
// DEAL_ENTRY_OUT_BY). O DEAL_TYPE da saida e SEMPRE o oposto da
// posicao fechada: uma posicao de COMPRA e encerrada por um deal de
// VENDA, e uma posicao de VENDA por um deal de COMPRA.
//
// A versao anterior usava o tipo da saida direto e gravava a direcao
// INVERTIDA no diario (compra virava venda e vice-versa), contaminando
// DirStore/DirBoost e o resumo por direcao - por exemplo USDCNH,
// operado sempre vendido, aparecia como "BUY=81%".
//
// A direcao vem da inversao do tipo da saida, sem tocar na selecao do
// historico (HistorySelectByPosition quebraria os lacos de importacao
// em andamento).
//   retorno: +1 = posicao de COMPRA, -1 = posicao de VENDA, 0 = outro
//==================================================

int LearningExitToPositionDir(long exitType)
{
   if(exitType==DEAL_TYPE_SELL)
      return 1;    // saida por venda => a posicao era de compra

   if(exitType==DEAL_TYPE_BUY)
      return -1;   // saida por compra => a posicao era de venda

   return 0;
}

int AILearningImportHistory(int days)
{   if(!EnableLearningFromHistory)
      return 0;

   if(days<=0)
      days=LearningHistoryDays;

   if(!LearningImportDue())
   {
      // v1.2.11: ficar em silencio aqui fazia o "importados=0" parecer
      // falha. Agora o journal diz que a varredura so esta em espera.
      // v1.2.15 (29/10/2026): esta funcao roda no laco principal, a cada
      // 30s. Sem trava, este Print escrevia 2 linhas por minuto POR GRAFICO
      // com o mesmo texto e nenhuma informacao nova - medido no journal
      // ("[LEARN] varredura em espera" repetido de minuto em minuto), o que
      // tambem inflava o log do tester em centenas de MB. Agora o aviso sai
      // no maximo 1x por hora, que ja e a janela do throttle de importacao.
      static datetime lastWaitLog = 0;
      datetime waitNow = TimeCurrent();

      if(lastWaitLog == 0 || waitNow - lastWaitLog >= 14400)
      {
         lastWaitLog = waitNow;

         if(AccountLogGatePodeImprimir("learnwait", 21600)) Print("[LEARN] varredura em espera | throttle de 6h por conta");
      }
      return 0;
   }

   datetime from=TimeCurrent()-((datetime)days*86400);

   if(from<=0)
      from=0;

   if(!HistorySelect(from,TimeCurrent()))
   {
      Print("[LEARN] HistorySelect falhou | err=",GetLastError());
      return 0;
   }

   int totalDeals=HistoryDealsTotal();
   int saldo=0;
   int manuais=0;
   int doEA=0;
   int empates=0;
   int vistos=0;
   int aprendiveis=0;

   // v1.2.20 (29/10/2026): contadores de CLASSIFICACAO, independentes do
   // cursor. "deste_EA" passou a contar de fato as saidas com a magic deste
   // EA na janela, e "ja_aprendidos" mostra o que o cursor pulou. Antes o
   // resumo escrevia "deste_EA=0" apenas porque todas as saidas ja estavam
   // na memoria, e isso se confundia com "o EA nunca operou".
   int desteEA=0;
   int manuaisTotal=0;
   int outrosEA=0;
   int jaAprendidos=0;

   g_AILearnQuiet=true;

   for(int i=0;i<totalDeals;i++)
   {
      ulong deal=HistoryDealGetTicket(i);

      if(deal==0)
         continue;

      long entry=HistoryDealGetInteger(deal,DEAL_ENTRY);

      // conta apenas saidas: cada saida = um trade concluido
      if(entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY)
         continue;

      long type=HistoryDealGetInteger(deal,DEAL_TYPE);

      if(type!=DEAL_TYPE_BUY && type!=DEAL_TYPE_SELL)
         continue;   // ignora deposito/retirada/ajustes

      string sym=HistoryDealGetString(deal,DEAL_SYMBOL);

      if(sym=="")
         continue;

      vistos++;

      // v1.2.20: classifica a saida ANTES do cursor para o resumo refletir o
      // historico real (do EA / manual / outro EA que usa a mesma conta).
      long magic=HistoryDealGetInteger(deal,DEAL_MAGIC);

      bool manual=(magic==0);

      if(manual)
         manuaisTotal++;
      else
      if(magic==MagicNumber)
         desteEA++;
      else
         outrosEA++;

      if(deal<=LearningLastDeal(sym))
      {
         jaAprendidos++;
         continue;   // ja aprendido
      }

      if(manual && !LearningImportManualTrades)
         continue;

      if(!manual && magic!=MagicNumber)
         continue;   // outro EA na mesma conta: nao e historico deste sistema

      if(!manual && !LearningImportExpertTrades)
         continue;

      aprendiveis++;

      double net=
         HistoryDealGetDouble(deal,DEAL_PROFIT)+
         HistoryDealGetDouble(deal,DEAL_SWAP)+
         HistoryDealGetDouble(deal,DEAL_COMMISSION);

      if(MathAbs(net)<0.0000001)
      {
         LearningSetLastDeal(sym,deal);
         empates++;
         saldo++;
         continue;
      }

      // v1.2.12: direcao da POSICAO (nao a do deal de saida)
      int sig=LearningExitToPositionDir(type);

      double conf=50.0;

      int id=FindLearningIndex(sym);

      if(!manual && id>=0 && g_AIMemory[id].lastConfidence>0.0)
         conf=g_AIMemory[id].lastConfidence;

      bool win=(net>0.0);

      // v1.2.11: o deal pode ja ter sido registrado em tempo real
      // por outro grafico. Nesse caso so avanca o cursor.
      if(LearningDealClaimed(deal))
      {
         LearningSetLastDeal(sym,deal);
         continue;
      }

      LearningAppendEvent(sym,deal,sig,conf,win);

      StoreExperience(sym,sig,conf,win);
      DirStore(sym,sig,win);
      HourStore(sym,sig,LearningServerHour((datetime)HistoryDealGetInteger(deal,DEAL_TIME)));

      LearningSetLastDeal(sym,deal);

      if(manual)
         manuais++;
      else
         doEA++;

      saldo++;
   }

   g_AILearnQuiet=false;

   // v1.2.9 (29/10/2026): "importados=0" NAO pode travar a proxima tentativa
   // por 1 hora. No OnInit o terminal muitas vezes ainda nao carregou o
   // historico, HistoryDealsTotal() vem 0, nada e importado - e o throttle
   // era renovado assim mesmo, deixando a memoria parada em deals antigos.
   // Agora a marca so e gravada quando o historico RESPONDEU (vistos>0).
   if(vistos>0)
      LearningMarkImportDone();
   else
      if(AccountLogGatePodeImprimir("learn_sem_hist", 3600)) Print("[LEARN] historico ainda nao disponivel | nova tentativa no proximo ciclo");   // P1.133: 1x/h por instancia no tester

   // v1.2.11 (29/10/2026): mostra SEMPRE o resultado da varredura.
   // Antes o resumo so saia quando havia deal novo; como a memoria ja tem
   // todo o historico fechado, o caso normal e "nenhum novo" e o journal
   // ficava mudo ("importados=0" parecia falha). Agora o dono ve, a cada
   // ciclo, quantas saidas existem, quantas sao deste EA e quantas ja
   // estavam aprendidas.
   // v1.2.54 (31/10/2026) - P1.31: esta varredura roda a cada passagem e, com a
   // memoria ja carregada, o resultado normal e "nenhum novo" - mas a linha era
   // impressa em todas. Medido no ultimo run: 158 294 linhas (12,29% de todo o
   // output), o maior emissor unico do journal. O caso que o dono precisa de ver
   // e o deal NOVO, e esse (saldo>0) continua a sair sempre; o "verifiquei e nao
   // havia nada" passa a sair no maximo 1x/hora por simbolo. Nada da importacao,
   // do throttle nem da aprendizagem mudou - decide apenas se a linha volta.
   if(vistos>0)
   {
      if(saldo > 0 || DiagGateAllow(_Symbol, "LEARN_VERIF", "sem_novos", 3600))
         if(LogInicioDetalhe()) Print(
            "[LEARN] historico verificado | janela=",
            days,
            "d | saidas=",
            vistos,
            " | deste_EA=",
            desteEA,
            " | manuais=",
            manuaisTotal,
            " | outros_EA=",
            outrosEA,
            " | ja_aprendidos=",
            jaAprendidos,
            " | novos=",
            saldo,
            " | novos_EA=",
            doEA,
            " | novos_manual=",
            manuais,
            " | empates=",
            empates
         );
   }
   return saldo;
}

//==================================================
// REGISTRO EM TEMPO REAL (trade fechado)
//==================================================

//==================================================
// TRAVA POR DEAL (v1.2.11 - 29/10/2026)
//
// Ha 13 graficos com o EA na mesma conta. O mesmo fechamento pode ser
// contado duas vezes: uma pela transacao em tempo real e outra pela
// importacao do historico em outro grafico cujo cursor por simbolo
// ainda estava atras. O resultado era a memoria somando o mesmo trade
// 2x (win rate e boost irreais). Esta trava garante 1 registro por
// deal por conta, independente de quantos graficos estejam abertos.
//==================================================

bool LearningDealClaimed(ulong deal)
{
   if(MQLInfoInteger(MQL_TESTER)!=0)
      return false;

   string gv="XAI_PRO_LDEAL_"+IntegerToString((long)deal);

   if(GlobalVariableCheck(gv))
      return true;

   GlobalVariableSet(gv,1.0);
   return false;
}

void AILearningRecordDeal(ulong deal, string symbol, double profit)
{   if(!EnableLearningFromHistory)
      return;

   if(deal==0 || symbol=="")
      return;

   if(deal<=LearningLastDeal(symbol))
      return;

   long type=HistoryDealGetInteger(deal,DEAL_TYPE);

   if(type!=DEAL_TYPE_BUY && type!=DEAL_TYPE_SELL)
      return;

   // v1.2.11: se outro grafico ja registrou este deal, nao soma de novo.
   if(LearningDealClaimed(deal))
   {
      LearningSetLastDeal(symbol,deal);
      return;
   }

   double net=
      profit+
      HistoryDealGetDouble(deal,DEAL_SWAP)+
      HistoryDealGetDouble(deal,DEAL_COMMISSION);

   LearningSetLastDeal(symbol,deal);

   if(MathAbs(net)<0.0000001)
      return;   // empate

   // v1.2.12: direcao da POSICAO (nao a do deal de saida)
   int sig=LearningExitToPositionDir(type);

   double conf=50.0;

   int id=FindLearningIndex(symbol);

   if(id>=0 && g_AIMemory[id].lastConfidence>0.0)
      conf=g_AIMemory[id].lastConfidence;

   bool win=(net>0.0);

   LearningAppendEvent(symbol,deal,sig,conf,win);

   StoreExperience(symbol,sig,conf,win);
   DirStore(symbol,sig,win);
   HourStore(symbol,sig,LearningServerHour((datetime)HistoryDealGetInteger(deal,DEAL_TIME)));
}

//==================================================
// PENALIDADE DE APRENDIZADO SEM VETO (v1.2.14)
//
// Regra do dono: "corrigir tudo, mas manter sempre sair no lucro", sem
// bloqueios indevidos. O historico ruim do par/direcao (e da hora) NAO veta
// a entrada: reduz o LOTE. O EA continua operando, aprende com o resultado e
// sai no lucro com tamanho menor onde erra mais.
// Devolve 1.0 = sem penalidade.
//==================================================

double LearningLotPenalty(string symbol,int signal)
{
   if(!EnableLearningFromHistory || !EnableLearningLotPenalty)
      return(1.0);

   if(symbol=="")
      symbol=_Symbol;

   if(signal==0)
      return(1.0);

   if(DirTotal(symbol,signal)<LearningPenaltyMinTrades)
      return(1.0);

   double wr=DirRawWinRate(symbol,signal);

   if(wr<0.0)
      return(1.0);

   if(wr<=LearningPenaltyHardWR)
      return(LearningPenaltyHardLotFactor);

   if(wr<=LearningPenaltyMaxWR)
      return(LearningPenaltyLotFactor);

   return(1.0);
}

// Hora do dia historicamente ruim para o par (inverso do MELHOR_HORA).
double LearningHourLotPenalty(string symbol)
{
   if(!EnableLearningFromHistory || !EnableLearningHourPenalty)
      return(1.0);

   if(symbol=="")
      symbol=_Symbol;

   int hora=LearningServerHour(TimeCurrent());

   if(HourTotal(symbol,hora)<LearningPenaltyMinTrades)
      return(1.0);

   double wr=HourWinRate(symbol,hora);

   if(wr<0.0)
      return(1.0);

   if(wr<=LearningPenaltyMaxWR)
      return(LearningPenaltyHourLotFactor);

   return(1.0);
}

//==================================================
// USO DA MEMORIA NO SCORE
//
// Por padrao o aprendizado apenas INCENTIVA
// (LearningPenaltyEnabled=false): memoria negativa
// nao reduz o score, para nao reintroduzir bloqueios
// globais no EA autonomo. O diario continua registrando
// tudo, inclusive os erros.
//==================================================

double LearningHourScoreFactor(string symbol="")
{
   // (v1.2.35 - P1.6) Factor de hora APENAS para o score. Separado de
   // `LearningAdjustedScore` para nao herdar o piso `boost>=1.0`, que existe
   // para a memoria global e nao para o horario.
   if(!EnableLearningFromHistory || !EnableLearningHourBoost)
      return(1.0);

   if(symbol=="")
      symbol=_Symbol;

   double factor=HourBoost(symbol,LearningServerHour(TimeCurrent()));

   if(factor>=1.0)
      return(factor);          // bonus de hora continua a entrar

   if(!EnableLearningHourScorePenalty)
      return(1.0);             // dono desligou a hora no score

   double piso=LearningHourScoreFloor;

   if(piso<=0.0 || piso>1.0)
      piso=0.90;               // valor invalido: usa o piso documentado

   if(factor<piso)
      factor=piso;

   return(factor);
}

double LearningAdjustedScore(string symbol, int signal, double score)
{
   if(!EnableLearningFromHistory || !EnableLearningBoost)
      return score;

   if(symbol=="")
      symbol=_Symbol;

   double boost=MemoryBoost(symbol);

   // vies por direcao: o mesmo simbolo pode acertar comprando e errar vendendo
   if(LearningDirBoostEnabled && signal!=0)
      boost*=DirBoost(symbol,signal);

   // vies por horario/sessao: o mesmo par rende diferente em Londres e no
   // fechamento de Nova York.
   // v1.2.35 P1.6: a hora saiu do boost; ver LearningHourScoreFactor() abaixo.


   if(boost<1.0 && !LearningPenaltyEnabled)
      boost=1.0;

   double out=score*boost*LearningHourScoreFactor(symbol);   // v1.2.35 P1.6: hora no score

   if(out>100.0)
      out=100.0;

   if(out<0.0)
      out=0.0;

   return out;
}

//==================================================
// RESUMO
//==================================================

string LearningSymbolSummary(string symbol)
{
   int id=FindLearningIndex(symbol);

   if(id<0)
      return "MEM=novo";

   double wr=0.0;

   if(g_AIMemory[id].totalTrades>0)
      wr=100.0*g_AIMemory[id].wins/g_AIMemory[id].totalTrades;

   return(
      "T="+IntegerToString(g_AIMemory[id].totalTrades)+
      " W="+IntegerToString(g_AIMemory[id].wins)+
      " L="+IntegerToString(g_AIMemory[id].losses)+
      " WR="+DoubleToString(wr,1)+"%"+
      " MEM="+DoubleToString(g_AIMemory[id].memoryStrength,2)+
      " BOOST="+DoubleToString(((MemoryBoost(symbol)<1.0 && !LearningPenaltyEnabled)?1.0:MemoryBoost(symbol)),2)+
      DirSummary(symbol)+
      HourSummary(symbol)
   );
}

//==================================================

void LearningPrintSummary()
{
   int n=ArraySize(g_AIMemory);

   if(n<=0)
   {
      Print("[LEARN] memoria vazia | sem historico aprendido ainda");
      return;
   }

   // v1.2.87 (02/11/2026) - P1.74: MEDIDO 11 linhas por arranque (176 num
   // reload de 16 graficos) so para repetir memoria que os 16 graficos
   // partilham. Passa a UMA linha com o mesmo conteudo.
   string linhaLear = "";
   for(int i=0;i<n;i++)
   {
      if(i>0)
         linhaLear += " ; ";
      linhaLear += g_AIMemory[i].symbol + " " + LearningSymbolSummary(g_AIMemory[i].symbol);
   }

   if(n>0)
      if(LogInicioDetalhe()) { Print("[LEARN] resumo | simbolos=",n," | ",linhaLear); }
}

//==================================================
// ENTRADA UNICA (OnInit)
//==================================================

void AILearningInit()
{
   if(!EnableLearningFromHistory)
   {
      Print("[LEARN] desligado | EnableLearningFromHistory=false");
      return;
   }

   g_AILearnQuiet=false;

   int restored=LearningReplayJournal();

   // v1.2.9 (29/10/2026): AO INICIAR, APRENDE SEMPRE.
   // A guarda de 1 hora (LearningImportDue) existe para nao repetir
   // HistorySelect em cada grafico, mas fazia o EA reiniciar com
   // "importados=0" e a memoria ficar parada em deals antigos. O custo e um
   // HistorySelect por OnInit: deal ja aprendido e barrado pelo cursor
   // (LearningLastDeal), entao nada e contado duas vezes.
   if(MQLInfoInteger(MQL_TESTER)==0)
      GlobalVariableSet(LearningImportKey(),0.0);

   int imported=AILearningImportHistory(LearningHistoryDays);

   if(LogInicioDetalhe()) Print(
      "[LEARN] inicializado | restaurados=",
      restored,
      " | importados=",
      imported,
      " | janela=",
      LearningHistoryDays,
      "d | manual=",
      (LearningImportManualTrades?"on":"off"),
      " | boost=",
      (EnableLearningBoost?"on":"off"),
      " | penalidade=",
      (LearningPenaltyEnabled?"on":"off"),
      " | penalidade_lote=",
      (EnableLearningLotPenalty?"on":"off")
   );

   LearningPrintSummary();
}

#endif
