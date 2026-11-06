// XAU_AI_PRO v1.2.48
#ifndef TRADELOGGER_MQH
#define TRADELOGGER_MQH

#include "../Indicators/VolatilityFilter.mqh"
#include "../Indicators/ADX.mqh"
#include "../Indicators/RSI.mqh"
#include "EventLock.mqh"   // v1.2.41 - P1.16: lock global de escrita (F4)

//==================================================
// TRADE LOGGER ENGINE
//==================================================
// P1.16 (v1.2.41) - HISTORICO DO DEFEITO
//
// Este modulo mantinha UM handle persistente por instancia (FILE_SHARE_READ
// | FILE_SHARE_WRITE) e fazia FileSeek(SEEK_END) + FileWrite a cada trade.
// Com 15 instancias a escrever no MESMO Common\Files\trade_history.csv
// somavam-se dois defeitos independentes:
//
//   1) INTERLEAVE: dois FileWrite concorrentes no mesmo ficheiro, sem
//      serializacao nenhuma.
//   2) POSICAO OBSOLETA: o handle guarda a posicao onde fez o seek. Se a
//      instancia A fez seek ao EOF quando o ficheiro tinha N bytes e a
//      instancia B escreveu entretanto, o write de A comeca em N e grava
//      POR CIMA do que B escreveu (o modo nao e append atomico).
//
// MEDIDO em 31/10/2026 sobre 99 560 registos validos de trade_history.csv:
// 371 linhas partidas (campos a mais, simbolo cortado, "0.00" sozinho) e
// 369 reinicios de ordem temporal. O ficheiro de onde o EA aprende estava
// corrompido na origem - qualquer agregacao por banda de ADX feita sobre
// ele agrupa lixo.
//
// CORRECAO (padrao F4, o mesmo do Monitoring/EventEmitter.mqh e do
// BackupManager): ABRIR -> LOCK -> SEEK(END) -> WRITE -> FLUSH -> FECHAR,
// tudo dentro do lock global EventLock. Sem handle persistente nao existe
// EOF em cache; sem lock nao existe interleave. O header tambem passa a ser
// criado sob lock: as instancias arrancam no mesmo segundo e antes podiam
// grava-lo varias vezes.
//
// PRINCIPIO: nunca bloqueia a execucao. Um trade nao gravado e um DROP
// contado e impresso; nunca uma linha partida no ficheiro.

#define TL_FILE        "trade_history.csv"
#define TL_FILE_TESTER "trade_history_backtest.csv"
#define TL_FILE_LEGACY        "trade_history_legacy_v1.csv"
#define TL_FILE_TESTER_LEGACY "trade_history_backtest_legacy_v1.csv"

// P1.20 (v1.2.45) - O TESTER NAO PODE ESCREVER NO FICHEIRO DE PRODUCAO
//
// MEDIDO em 31/10/2026 as 17:02: o backtest de 3 meses (run
// 7702924108834513378) estava a anexar ao Common\Files\trade_history.csv
// linhas SIMULADAS com data 2026.07.29 e ATR/ADX/RSI/AI a 0.00 - o mtime do
// ficheiro acompanhava o relogio do teste. FILE_COMMON resolve, tambem no
// Strategy Tester, para a pasta comum verdadeira, logo o isolamento nao pode
// ser herdado do modo de ficheiro: tem de ser explicito aqui.
//
// O ficheiro contaminado e precisamente aquele de onde sairam as bandas de
// ADX (80 065 registos), as horas (99 560 registos) e o historico de
// aprendizagem. Uma linha simulada por cada trade de backtest muda a
// distribuicao que serve de base a essas medicoes.
//
// Nada da logica de trading muda: so o nome do ficheiro de destino.
string TradeLoggerFileName()
{
   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_VISUAL_MODE))
      return TL_FILE_TESTER;

   return TL_FILE;
}

// P1.21 (v1.2.46) - NOME DO FICHEIRO DE MIGRACAO DO SCHEMA
//
// O ficheiro de producao e o do tester tem o mesmo problema: foram criados
// com 10 colunas (Time..AI) e o schema novo tem 13. Em vez de misturar
// registos de 10 e 13 campos no mesmo ficheiro - exactamente o defeito que o
// P1.16 mediu em 371 linhas partidas - o ficheiro antigo e RODADO inteiro
// para *_legacy_v1.csv e o novo comeca limpo. Nada e apagado.
string TradeLoggerLegacyName()
{
   if(TradeLoggerFileName() == TL_FILE_TESTER)
      return TL_FILE_TESTER_LEGACY;

   return TL_FILE_LEGACY;
}

// P1.21 - ORIGEM DO TRADE
//
// Regra 7 estava em aberto desde 30/10: o trade_history.csv nao tinha como
// distinguir uma operacao manual de uma operacao do EA, porque o ficheiro so
// guardava preco/lucro/indicadores. A origem passa a ser derivada do magic do
// deal - e o unico campo do historico do broker que a distingue de forma
// causal, e nao por inferencia:
//   MagicNumber do EA -> "EA"
//   0                 -> "MANUAL" (ordem enviada a mao ou por EA sem magic)
//   qualquer outro    -> "OTHER"  (outro EA com magic diferente)
string TradeLoggerOrigin(long dealMagic)
{
   if(dealMagic == MagicNumber)
      return "EA";

   if(dealMagic == 0)
      return "MANUAL";

   return "OTHER";
}

bool g_tradeLoggerOn = false;   // P1.16: substitui o handle persistente
int  g_tl_written    = 0;       // linhas gravadas (esta instancia)
int  g_tl_skipped    = 0;       // P1.23: deals de OUTRO simbolo (nao gravados)
int  g_tl_dropped    = 0;       // linhas nao gravadas (lock ou abertura)


//==================================================
// ABRE PARA ESCRITA - sempre um handle novo
//==================================================

int TradeLoggerOpen()
{
   ResetLastError();

   return FileOpen(
      TradeLoggerFileName(),
      FILE_COMMON |
      FILE_CSV |
      FILE_READ |
      FILE_WRITE |
      FILE_ANSI |
      FILE_SHARE_READ |
      FILE_SHARE_WRITE,
      ','
   );
}


// P1.21 (v1.2.46) - GARANTIA DO SCHEMA (13 colunas)
//
// Corre SOB LOCK, uma vez por instancia, no arranque. Tres casos:
//   1) ficheiro vazio            -> escreve o cabecalho novo (13 colunas);
//   2) cabecalho com "Origin"    -> nada a fazer;
//   3) cabecalho antigo (10 col) -> roda o ficheiro para *_legacy_v1.csv e
//                                   comeca um novo com 13 colunas.
// No caso 3, se a rotacao falhar, a escrita e DESLIGADA em vez de continuar:
// misturar linhas de 10 e 13 campos no mesmo ficheiro e precisamente o tipo
// de corrupcao que o P1.16 mediu (371 linhas partidas em 99 560).
bool TradeLoggerEnsureSchema()
{
   if(!EventLockAcquire())
   {
      Print("TradeLogger WARN | schema sem lock (concorrencia) | append continuara");
      return true;
   }

   int h = TradeLoggerOpen();

   if(h == INVALID_HANDLE)
   {
      EventLockRelease();

      Print("TradeLogger ERR | schema: falha ao abrir | Err=", GetLastError());

      return false;
   }

   bool temDados  = (FileSize(h) > 0);
   bool temOrigin = false;

   if(temDados)
   {
      FileSeek(h, 0, SEEK_SET);

      // O ficheiro esta aberto em FILE_CSV: FileReadString devolve UM campo.
      // Basta varrer os campos do primeiro registo (o cabecalho).
      for(int i = 0; i < 13; i++)
      {
         string campo = FileReadString(h);

         if(StringFind(campo, "Origin") >= 0)
         {
            temOrigin = true;
            break;
         }

         if(FileIsEnding(h))
            break;
      }
   }

   if(temDados && !temOrigin)
   {
      FileClose(h);

      // v1.2.59 (P1.39): a rotacao procurava a origem na pasta LOCAL.
      //
      // MEDIDO no run 7703149588273005599 (v1.2.58): o journal registou
      // "TradeLogger ERR | rotacao do schema falhou | Err=5019" seguido de
      // "TradeLogger OFF", o trade_history_backtest.csv ficou com 10 colunas
      // e ZERO linhas novas, e 9 188 registos foram descartados.
      //
      // A causa esta na assinatura do FileMove, confirmada na documentacao
      // oficial (File Functions / FileMove):
      //   common_flag = 0            -> pasta LOCAL  (MQL5\Files)
      //   common_flag = FILE_COMMON  -> pasta COMUM  (Terminal\Common\Files)
      // O ficheiro e criado e lido com FILE_COMMON, mas a rotacao pedia a
      // ORIGEM com 0 - logo o FileMove ia buscar um ficheiro que nao existe
      // nessa pasta. O codigo 5019 e ERR_FILE_NOT_EXIST ("File does not
      // exist") na tabela oficial de erros MQL5, o que confirma o diagnostico:
      // nao era permissao nem bloqueio, era o caminho errado.
      //
      // Segunda guarda: a documentacao diz tambem que, sem FILE_REWRITE, um
      // destino que ja exista faz a funcao devolver false. Para a rotacao ser
      // IDEMPOTENTE - pode ser tentada a cada arranque, em 17 instancias e em
      // cada run do tester - o destino e o primeiro nome livre com sufixo
      // numerico, em vez de sobrescrever o legado anterior. Nada e apagado.
      string legado = TradeLoggerLegacyName();
      string raiz   = legado;
      int    ponto  = StringFind(raiz, ".csv");

      if(ponto > 0)
         raiz = StringSubstr(raiz, 0, ponto);

      string alvo = legado;
      int    seq  = 1;

      while(FileIsExist(alvo, FILE_COMMON) && seq < 100)
      {
         seq++;
         alvo = raiz + "_" + IntegerToString(seq) + ".csv";
      }

      ResetLastError();

      if(!FileMove(TradeLoggerFileName(), FILE_COMMON, alvo, FILE_COMMON))
      {
         EventLockRelease();

         Print("TradeLogger ERR | rotacao do schema falhou | Err=", GetLastError(),
               " | origem='", TradeLoggerFileName(), "' destino='", alvo,
               "' (ambos em Common\\Files) | escrita DESLIGADA para nao misturar 10 e 13 colunas");

         return false;
      }

      Print("TradeLogger MIGRACAO | ficheiro sem coluna Origin rodado para '", alvo,
            "' (integralmente preservado); novo '", TradeLoggerFileName(),
            "' com 13 colunas");

      h = TradeLoggerOpen();

      if(h == INVALID_HANDLE)
      {
         EventLockRelease();

         Print("TradeLogger ERR | reabrir apos rotacao | Err=", GetLastError());

         return false;
      }

      temDados = false;
   }

   if(!temDados)
   {
      FileWrite(
         h,
         "Time",
         "Symbol",
         "Type",
         "Entry",
         "Exit",
         "Profit",
         "ATR",
         "ADX",
         "RSI",
         "AI",
         "Ticket",
         "Magic",
         "Origin"
      );

      FileFlush(h);
   }

   FileClose(h);
   EventLockRelease();

   return true;
}


//==================================================
// INIT
//==================================================

bool InitTradeLogger()
{
   // Evita reabrir a cada chamada (OnInit de cada instancia)
   if(g_tradeLoggerOn)
      return true;

   int h = TradeLoggerOpen();

   if(h == INVALID_HANDLE)
   {
      Print(
         "Erro TradeLogger: ",
         GetLastError()
      );

      return false;
   }

   FileClose(h);

   // P1.21: o cabecalho passou a ter 13 colunas. Toda a logica de schema vive
   // em TradeLoggerEnsureSchema(), que deteta o cabecalho antigo e roda o
   // ficheiro para *_legacy_v1.csv em vez de misturar 10 e 13 colunas.
   if(!TradeLoggerEnsureSchema())
   {
      Print("TradeLogger OFF | schema do ficheiro incompativel; escrita desligada");
      return false;
   }

   g_tradeLoggerOn = true;

   // v1.2.88 (02/11/2026) - P1.75: tag [TRADELOG] para a linha casar com as vizinhas.
   if(LogInicioDetalhe()) Print("[TRADELOG] inicializado (abre-lock-seek-write-flush-fecha)");

   return true;
}


//==================================================
// LOG TRADE
//==================================================

//--------------------------------------------------
// P1.45 (v1.2.63) - SEMANTICA DAS COLUNAS
//--------------------------------------------------
//
// Time        : hora do evento de fecho (TimeCurrent no momento do registo)
// Symbol      : DEAL_SYMBOL do deal de fecho (P1.22), nao o simbolo do grafico
// Type        : BUY ou SELL = direcao da POSICAO (deal DEAL_ENTRY_IN).
//               Antes do P1.45 vinha de DEAL_TYPE do deal de FECHO, pelo que
//               uma compra fechada por venda era gravada como SELL.
// Entry       : preco de ABERTURA da posicao (DEAL_PRICE do DEAL_ENTRY_IN).
//               Antes do P1.45 vinha de DEAL_PRICE do deal de fecho, isto e,
//               era o preco de SAIDA.
// Exit        : preco de FECHO executado (DEAL_PRICE do deal do evento).
//               Antes do P1.45 vinha de SymbolInfoDouble(SYMBOL_BID) lido no
//               instante do registo - retrato posterior ao fecho, nao o preco
//               executado.
// Profit      : DEAL_PROFIT do deal de fecho, na moeda da conta
// ATR/ADX/RSI : valores dos indicadores no momento do registo
// AI          : AIScore do EA no momento do registo (0.00 no Strategy Tester
//               enquanto o pipeline Python estiver offline)
// Ticket      : DEAL_POSITION_ID (P1.21) - liga a linha ao historico do broker
// Magic       : DEAL_MAGIC (P1.21) - 2026001 = este EA, 0 = manual
// Origin      : EA ou MANUAL, derivado do Magic
//
// INVARIANTE verificavel: para BUY com Profit maior que zero espera-se
// Exit maior que Entry; para SELL com Profit maior que zero espera-se
// Exit menor que Entry. Uma linha que viole isto esta errada, nao e um
// caso de borda.

void LogTradeCSV(
   string symbol,           // P1.22: simbolo do DEAL (nao o do grafico)
   bool isBuy,
   double entry,
   double exit,
   double profit,
   double aiScore,
   ulong positionId = 0,     // P1.21: ticket da posicao (DEAL_POSITION_ID)
   long  dealMagic  = -1     // P1.21: magic do deal (DEAL_MAGIC)
)
{
   if(!g_tradeLoggerOn)
      return;

   //--------------------------------------------------
   // P1.23 (v1.2.48) - UMA LINHA POR DEAL, NAO UMA POR GRAFICO
   //--------------------------------------------------
   //
   // MEDIDO em 31/10/2026 sobre 100 151 linhas validas do trade_history.csv:
   // colapsando por (segundo, tipo, lucro) sobram 42 850 assinaturas - 57 301
   // linhas sao repeticao. A distribuicao de multiplicidade tem picos em 2, 10
   // e 17, que e o numero de graficos a receber o mesmo OnTradeTransaction.
   // Cada instancia gravava TODOS os deals da conta: o ficheiro que serve de base
   // as bandas de ADX e as horas estava inflado 2,3x (valor subestimado, porque
   // duas operacoes distintas podem cair no mesmo segundo com o mesmo lucro).
   //
   // Aqui cada grafico passa a gravar apenas os deals do seu _Symbol. O simbolo
   // do DEAL (DEAL_SYMBOL) continua a ser o que vai para a coluna Symbol desde o
   // P1.22; esta guarda decide QUEM escreve, nao o que e escrito.
   //
   // No Strategy Tester a guarda fica desligada de proposito: ha uma so instancia,
   // logo nao ha duplicacao a evitar, e o teste de XAUUSD tambem negoceia outros
   // simbolos (ver PENDENCIAS 27.8) - descarta-los la seria perder informacao.
   //
   // Efeito colateral assumido: um deal cujo simbolo nao tenha grafico aberto
   // deixa de ser gravado N vezes de forma errada e passa a nao ser gravado. E o
   // preco de o ficheiro dizer a verdade uma vez em vez de mentir 17.
   string tlSymbol = (symbol == "") ? _Symbol : symbol;
   int    tlDigits = (int)SymbolInfoInteger(tlSymbol, SYMBOL_DIGITS);

   if(tlDigits <= 0)
      tlDigits = _Digits;

   if(!MQLInfoInteger(MQL_TESTER) && tlSymbol != _Symbol)
   {
      g_tl_skipped++;
      return;
   }

   //--------------------------------------------------
   // F4: 1 produtor por vez no ficheiro
   //--------------------------------------------------

   if(!EventLockAcquire())
   {
      g_tl_dropped++;

      Print(
         "[TRADELOGGER] DROP | lock indisponivel | total_dropped=",
         g_tl_dropped,
         " | timeouts=",
         g_ev_lock_timeouts
      );

      return;
   }

   int h = TradeLoggerOpen();

   if(h == INVALID_HANDLE)
   {
      int err = GetLastError();

      EventLockRelease();

      g_tl_dropped++;

      Print(
         "[TRADELOGGER] DROP | falha ao abrir | Err=",
         err,
         " | total_dropped=",
         g_tl_dropped
      );

      return;
   }

   // Handle novo => posicao no EOF de AGORA, nao a de quando esta instancia
   // arrancou. E o que impede a gravacao por cima de outra instancia.
   if(!FileSeek(h, 0, SEEK_END))
   {
      int errSeek = GetLastError();

      FileClose(h);
      EventLockRelease();

      g_tl_dropped++;

      Print(
         "[TRADELOGGER] DROP | FileSeek: ",
         errSeek,
         " | total_dropped=",
         g_tl_dropped
      );

      return;
   }

   string tradeType = "SELL";

   if(isBuy)
      tradeType = "BUY";

   // P1.22 (v1.2.47) - O SIMBOLO E O DO DEAL, NAO O DO GRAFICO
   //
   // MEDIDO em 31/10/2026 sobre as 100 228 linhas do trade_history.csv:
   // 63 simbolos, e em 10 916 linhas com symbol XAUUSD o preco gravado era
   // 0.81, 1.32, 6.77 ou 163.74 - valores que o ouro nunca teve. A mesma
   // operacao aparecia repetida no mesmo segundo em varios simbolos, com o
   // MESMO lucro e o mesmo preco em escalas diferentes (1.32 no grafico
   // XAUUSD, 1.324 no USDJPY, 1.32429 no GBPUSD). Causa: cada instancia
   // regista todos os deals e escrevia _Symbol na coluna Symbol e _Digits na
   // formatacao, logo a coluna mentia e o ADX/ATR/RSI eram os do grafico.
   //
   // Aqui o simbolo vem de DEAL_SYMBOL (passado pelo chamador). Vazio (nunca
   // acontece com um deal valido) cai para o comportamento antigo.
   // P1.23: as declaracoes de tlSymbol/tlDigits subiram para o inicio da funcao,
   // para o descarte por simbolo ser decidido antes de qualquer I/O.
   double atr = GetATR(tlSymbol);
   double adx = GetADX(tlSymbol);
   double rsi = GetRSI(tlSymbol);

   FileWrite(
      h,

      TimeToString(
         TimeCurrent(),
         TIME_DATE | TIME_SECONDS
      ),

      tlSymbol,

      tradeType,

      DoubleToString(
         entry,
         tlDigits
      ),

      DoubleToString(
         exit,
         tlDigits
      ),

      DoubleToString(
         profit,
         2
      ),

      DoubleToString(
         atr,
         tlDigits
      ),

      DoubleToString(
         adx,
         2
      ),

      DoubleToString(
         rsi,
         2
      ),

      DoubleToString(
         aiScore,
         2
      ),

      // P1.21: identidade e origem. O ticket liga esta linha ao historico do
      // broker; a origem sai do magic (EA / MANUAL / OTHER) e nao de uma
      // inferencia sobre o simbolo ou o horario.
      (string)positionId,

      (string)dealMagic,

      TradeLoggerOrigin(dealMagic)
   );

   FileFlush(h);
   FileClose(h);

   EventLockRelease();

   g_tl_written++;
}


//==================================================
// ESTADO / RESUMO
//==================================================

// P1.16: o .mq5 perguntava por `tradeLoggerHandle != INVALID_HANDLE`.
// Deixa de existir handle persistente; o estado passa a ser explicito.
bool TradeLoggerReady()
{
   return g_tradeLoggerOn;
}

string TradeLoggerSummary()
{
   return StringFormat(
             "TradeLogger | File=%s | State=%s | Written=%d | Dropped=%d | OutroSimbolo=%d | %s",
             TradeLoggerFileName(),   // P1.23: diz o ficheiro REAL (tester -> backtest)
             (g_tradeLoggerOn ? "ON" : "OFF"),
             g_tl_written,
             g_tl_dropped,
             g_tl_skipped,
             EventLockStats()
          );
}


//==================================================
// CLOSE
//==================================================

void CloseTradeLogger()
{
   // Sem handle persistente nao ha o que fechar; libera o lock se esta
   // instancia o deteve e volta a deixar o modulo inactivo.
   EventLockRelease();

   g_tradeLoggerOn = false;
}

#endif
