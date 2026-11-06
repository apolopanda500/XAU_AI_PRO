// XAU_AI_PRO v1.2.53
#ifndef TRADEPIPELINE_MQH
#define TRADEPIPELINE_MQH

#include "../Core/SymbolManager.mqh"
#include "../Core/MarketScanner.mqh"
#include "../Indicators/MarketPulse.mqh"   // VIA RAPIDA (29/10/2026)
// v1.2.52 (P1.28): DiagGate para abafar a linha da via rapida.
#include "../Monitoring/DiagGate.mqh"
// P1.83 (v1.2.95): a permissao do proprio programa (MQL_TRADE_ALLOWED) passou
// a decidir quem pode ser dono do pipeline - ver PipelineIsMaster().
#include "../Core/TradeGate.mqh"

//==================================================
// TRADE PIPELINE
// XAU_AI_PRO
// MULTI SYMBOL + DIAGNOSTIC
//==================================================

#define PIPELINE_MASTER_TTL_SEC 180

// Sem este guarda, cada grafico com o EA anexado varre TODOS os simbolos.
// Alem do custo (13 x 11 = 143 pipelines por tick), o latch por vela usa
// PERIOD_CURRENT: o grafico M1 libera nova entrada a cada minuto e o H1 a
// cada hora para o MESMO simbolo, porque a chave do latch inclui o tempo da
// vela do grafico. Uma unica instancia dona resolve os dois problemas.
bool PipelineIsMaster()
{
   if(!EnablePipelineMasterGuard)
      return(true);

   string   key     = "XAI_PRO_PIPE_MASTER_" + IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
   string   keyBeat = key + "_T";
   double   me      = (double)ChartID();
   datetime agora   = TimeLocal();

   // P1.83 (v1.2.95) - MEDIDO em 02/11/2026 21:50:33: o dono do pipeline era
   // o grafico USDCHF recem-recarregado, com MQL_TRADE_ALLOWED=0. O OnTick do
   // dono sai no portao de negociacao ANTES de chegar ao pipeline, logo NAO
   // varria o mercado; as outras 14 instancias viam um dono vivo e ficavam em
   // STANDBY. Resultado medido: 5 minutos sem uma unica linha [SCANNER],
   // [CENARIO] ou [SIGNAL] e zero operacoes possiveis, embora os 15 graficos
   // estivessem ligados. Um grafico sem permissao de programa nao pode ser
   // dono: devolve o bastao (apaga as duas chaves) e deixa assumir quem
   // consegue realmente negociar. Nao muda nenhuma regra de entrada, risco ou
   // execucao - decide apenas QUEM corre o pipeline.
   if(!CTradeGate::Mql())
     {
      if(GlobalVariableCheck(key) && (ulong)GlobalVariableGet(key) == (ulong)me)
        {
         GlobalVariableDel(key);
         GlobalVariableDel(keyBeat);
        }

      static datetime avisoSemPermissao = 0;

      if((avisoSemPermissao == 0 || (agora - avisoSemPermissao) >= 3600) && LogSessaoPodeImprimir("pipeline_sem_permissao"))
        {
         avisoSemPermissao = agora;

         Print("[PIPELINE] SEM PERMISSAO | esta instancia nao pode ser dona do pipeline | MQL_TRADE_ALLOWED=0 | bastao libertado para uma instancia com permissao | esta=", (long)me);
        }

      return(false);
     }

   if(GlobalVariableCheck(key) && GlobalVariableCheck(keyBeat))
   {
      double   dono   = GlobalVariableGet(key);
      datetime ultimo = (datetime)GlobalVariableGet(keyBeat);

      // Outra instancia viva: fica em standby (nao negocia, nao gerencia).
      if(dono != me && (agora - ultimo) < PIPELINE_MASTER_TTL_SEC)
         return(false);
   }

   GlobalVariableSet(key, me);
   GlobalVariableSet(keyBeat, (double)agora);

   return(true);
}

// P1.47 (v1.2.64): quem NAO e o dono precisa de saber quem e. O id do dono
// ja vivia no GlobalVariable acima; faltava expo-lo. Sem isto, o diagnostico
// de standby imprimia o proprio ChartID() logo a seguir a dizer que outra
// instancia era a dona - apontava para si proprio. MEDIDO em 01/11/2026:
// GBPUSD (chart 35819305996467) escrevia chart=35819305996467 enquanto o
// dono real era o USDCZK (chart 35819164653256), ausente de todas as linhas
// de standby do dia. Devolve 0 quando nao ha mestre publicado.
ulong PipelineMasterChart()
{
   if(!EnablePipelineMasterGuard)
      return(0);

   string key = "XAI_PRO_PIPE_MASTER_" + IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));

   if(!GlobalVariableCheck(key))
      return(0);

   return((ulong)GlobalVariableGet(key));
}

//+------------------------------------------------------------------+
//| P2.14 (03/11/2026)                                               |
//| A dona publicada pode ja estar MORTA: o id fica na GlobalVariable |
//| quando o grafico dono e fechado a mao, e o batimento (_T) envelhece|
//| em 180 s. O [STOP] do OnDeinit cala-se por "so a dona imprime",    |
//| portanto precisa de saber se a dona ainda respira - com a dona     |
//| morta ninguem imprimiria. true = ha dona E batimento fresco;       |
//| false = o chamador volta ao portao por conta, como antes.          |
//+------------------------------------------------------------------+
bool PipelineMasterFresh()
{
   if(!EnablePipelineMasterGuard)
      return(false);

   string key     = "XAI_PRO_PIPE_MASTER_" + IntegerToString((long)AccountInfoInteger(ACCOUNT_LOGIN));
   string keyBeat = key + "_T";

   if(!GlobalVariableCheck(key) || !GlobalVariableCheck(keyBeat))
      return(false);

   datetime ultimo = (datetime)GlobalVariableGet(keyBeat);
   datetime agora  = TimeLocal();

   return((agora - ultimo) < PIPELINE_MASTER_TTL_SEC);
}

void RunTradePipeline()
{
   // Log de diagnostico 1x por minuto (evita spam a cada tick)
   static datetime lastLogTime = 0;
   datetime now = TimeCurrent();
   bool logOnce = (now - lastLogTime >= 60);
   if(logOnce)
      lastLogTime = now;

   // Uma unica instancia por conta executa o pipeline (ver PipelineIsMaster).
   if(!PipelineIsMaster())
   {
      // v1.2.27 (30/10/2026) - P1.3: 15 das 16 instancias ficam em STANDBY e
      // imprimiam esta linha 1x/minuto cada (~900 linhas por hora de ruido).
      static datetime lastStandbyLog = 0;

      // P2.00 (03/11/2026): o static sozinho e por INSTANCIA, portanto 13
      // graficos davam 13 linhas/hora a dizer o mesmo (150 no dia 03/11).
      // Passa a exigir tambem a janela por CONTA (AccountLogGate.mqh).
      if(now - lastStandbyLog >= 3600)
      {
         // P2.13 (03/11/2026): o carimbo avancava SO quando a linha era
         // impressa. Enquanto o portao por conta dizia "outra instancia ja
         // escreveu", a condicao ficava verdadeira para sempre e o FileOpen do
         // portao corria a cada tick - 14 instancias a abrir o mesmo ficheiro
         // comum sem necessidade. O carimbo passa a avancar em TODA tentativa;
         // quem imprime continua a ser decidido pelo portao por conta.
         lastStandbyLog = now;

         if(AccountLogGatePodeImprimir("pipe_standby", 3600))
            Print(
               "[PIPELINE] STANDBY | esta instancia nao e a dona do pipeline | esta=",
               ChartID(),
               " | dono=",
               PipelineMasterChart()
            );
      }

      return;
   }

   int total=
      TotalSymbols();

   // v1.2.53 (31/10/2026) - P1.30: linha de "estou vivo" a 1 por minuto.
   // MEDIDO no ultimo run (1 252 528 linhas de journal): INICIO 26 979 e
   // FINALIZADO 26 979, ou seja 53 958 linhas, 4,31 por cento de todo o
   // output, sempre com o mesmo desfecho (Symbols=11). O PROCESSANDO ja tinha
   // sido baixado a 1 por hora no P1.3; estas duas ficaram a 1 por minuto.
   // Passam a usar o mesmo portao de diagnostico das outras linhas: 1 por hora
   // por desfecho. O heartbeat continua a existir, so deixa de gastar uma
   // linha por minuto.
   if(logOnce && DiagGateAllow(_Symbol, "PIPELINE_INICIO", IntegerToString(total), 3600))
      Print(
         "[PIPELINE] INICIO | Symbols=",
         total
      );

   if(total<=0)
   {
      if(logOnce)
         Print(
            "[PIPELINE] BLOQUEADO | Nenhum símbolo configurado"
         );

      return;
   }


   // v1.2.33 (30/10/2026) - P1.3 rodada 5: "[PIPELINE] PROCESSANDO" e progresso
   // puro e saia 1x/minuto POR SIMBOLO. Medido em 17:30-17:35 da v1.2.32: 160
   // linhas em 5 min no grafico master (~1 900/hora com as linhas do scanner).
   // Passa a 1x/hora para o ciclo inteiro: continua provando que o pipeline
   // esta vivo, sem uma linha por simbolo por minuto.
   static datetime pipelineInfoTime = 0;
   bool pipelineInfo = (TimeCurrent() - pipelineInfoTime >= 3600);

   if(pipelineInfo)
      pipelineInfoTime = TimeCurrent();

   for(int i=0; i<total; i++)
   {
      string symbol=
         GetTradeSymbol(i);

      if(symbol=="")
      {
         if(logOnce)
            Print(
               "[PIPELINE] Symbol vazio | Index=",
               i
            );

         continue;
      }


      // P2.00: o ciclo imprimia uma linha por simbolo (11); o progresso e o
      // mesmo de hora em hora, por isso passa a 1 por CONTA e por hora.
      if(pipelineInfo && AccountLogGatePodeImprimir("pipe_proc", 3600))
         Print(
            "[PIPELINE] PROCESSANDO | Index=",
            i,
            " | Symbol=",
            symbol
         );


      if(!SymbolSelect(symbol,true))
      {
         if(logOnce)
            Print(
               "[PIPELINE] BLOQUEADO | SymbolSelect | ",
               symbol,
               " | Error=",
               GetLastError()
            );

         continue;
      }


      // ETAPA 11 - NEWS FILTER (bloqueia novas entradas, nao mata o EA)
      if(NewsModuleActive() && !CanTradeNews(symbol))
         continue;

      ProcessSymbol(symbol);
   }


   if(logOnce && DiagGateAllow(_Symbol, "PIPELINE_FIM", "FINALIZADO", 3600))
      Print(
         "[PIPELINE] FINALIZADO"
      );
}


//==================================================
// PROCESS SINGLE SYMBOL
//==================================================

bool RunTradePipelineSymbol(
   string symbol
)
{
   if(symbol=="")
      return false;


   if(!SymbolSelect(symbol,true))
   {
      Print(
         "[PIPELINE] SymbolSelect falhou | ",
         symbol,
         " | Error=",
         GetLastError()
      );

      return false;
   }


   ProcessSymbol(symbol);

   return true;
}

//==================================================
// VIA RAPIDA - VOLUME ALTO + PRECO CORRENDO (29/10/2026)
//==================================================
// Com volume alto, esperar o ciclo do scheduler (60s) e perder o movimento.
// Esta rotina roda no OnTick, com throttle proprio, e chama o pipeline SO para
// os simbolos em disparada. O latch "1 operacao por vela" continua valendo,
// logo ela NAO duplica entrada no mesmo candle.
void MarketPulseFastLane()
{
   if(!EnableMarketPulse)
      return;

   static datetime ultimo = 0;

   datetime agora  = TimeCurrent();
   int      janela = (PulseFastLaneSec > 0) ? PulseFastLaneSec : 5;

   if(ultimo > 0 && (agora - ultimo) < janela)
      return;

   ultimo = agora;

   int total = TotalSymbols();

   for(int i = 0; i < total; i++)
   {
      string symbol = GetTradeSymbol(i);

      if(symbol == "")
         continue;

      double pulseVol = 0.0;
      double pulseVel = 0.0;
      ENUM_PULSE_REGIME regime = GetMarketPulse(symbol, pulseVol, pulseVel);

      if(regime == PULSE_NORMAL)
         continue;

      if(NewsModuleActive() && !CanTradeNews(symbol))
         continue;

      // v1.2.52 (P1.28): medido em 31/10/2026 no run actual do backtest
      // (1 234 648 linhas): 131 227 linhas desta mensagem = 10,63% do
      // journal, sem portao nenhum, uma por simbolo a cada 5 s de tempo de
      // modelo. A chave do desfecho e o REGIME - o volume e a velocidade
      // variam a cada tick e nao podem servir de chave. A chamada ao
      // pipeline fica FORA do portao: nenhuma operacao muda.
      if(DiagGateAllow(symbol, "VIA_RAPIDA", PulseRegimeName(regime), 3600))
         Print("[VIA RAPIDA] ", symbol,
               " | Regime=", PulseRegimeName(regime),
               " | Volume x", DoubleToString(pulseVol, 2),
               " | Velocidade ", DoubleToString(pulseVel, 2), " ATR");

      RunTradePipelineSymbol(symbol);
   }
}

#endif
