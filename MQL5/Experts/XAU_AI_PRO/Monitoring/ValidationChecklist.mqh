//+------------------------------------------------------------------+
//| ValidationChecklist.mqh                                         |
//| XAU_AI_PRO - Validacao real READY/WARNING/BLOCKED (ETAPA 10)    |
//| BLOCKED  = impede operacao segura (critico)                     |
//| WARNING  = degradado, nao bloqueia                              |
//| READY    = operacional                                          |
//+------------------------------------------------------------------+
#property copyright "XAU_AI_PRO"
#property version   "1.290"   // 1.2.9 no formato xxx.yyy exigido pelo compilador

#ifndef VALIDATIONCHECKLIST_MQH
#define VALIDATIONCHECKLIST_MQH

#include "../Core/Config.mqh"
// P1.61 (v1.2.75): fonte unica de verdade das permissoes de negociacao.
#include "../Core/TradeGate.mqh"

//==================================================
// STATUS
//==================================================

enum VCheckStatus
{
   VC_READY   = 0,
   VC_WARNING = 1,
   VC_BLOCKED = 2
};

//==================================================
// ESTADO GLOBAL (arrays paralelos - seguro em MQL5)
//==================================================

string g_vcheck_names[15];
VCheckStatus g_vcheck_status[15];
string g_vcheck_msg[15];
int    g_vcheck_count = 15;
bool   g_validationPassed = false;
datetime g_vcheck_time = 0;    // P1.44: hora do snapshot (o veredicto nao e reavaliado)

string g_vcheck_name(int i)
{
   switch(i)
   {
      case 0:  return "ATR";
      case 1:  return "ADX";
      case 2:  return "RSI";
      case 3:  return "EMA";
      case 4:  return "AI";
      case 5:  return "JSON";
      case 6:  return "Dataset";
      case 7:  return "Python";
      case 8:  return "Broker";
      case 9:  return "Spread";
      case 10: return "Session";
      case 11: return "Symbol Manager";
      case 12: return "Position Manager";
      case 13: return "Trade Manager";
      case 14: return "Dashboard";
   }
   return "?";
}

string g_vcheck_status_str(VCheckStatus s)
{
   switch(s)
   {
      case VC_READY:   return "READY";
      case VC_WARNING: return "WARNING";
      case VC_BLOCKED: return "BLOCKED";
   }
   return "?";
}

void g_vcheck_set(int i, VCheckStatus s, string msg)
{
   if(i < 0 || i >= g_vcheck_count)
      return;
   g_vcheck_status[i] = s;
   g_vcheck_msg[i]    = msg;
}

//==================================================
// EXECUTA CHECKLIST
//==================================================

bool ValidationChecklistRun()
{
   g_validationPassed = true;
   g_vcheck_time = TimeCurrent();

   if(LogInicioDetalhe()) { Print("[VALIDATION] Iniciando checklist READY/WARNING/BLOCKED..."); }

   // 0. ATR
   int hATR = iATR(_Symbol, PERIOD_CURRENT, ATRPeriod);
   bool atrOK = (hATR != INVALID_HANDLE);
   if(hATR != INVALID_HANDLE)
      IndicatorRelease(hATR);
   g_vcheck_set(0, atrOK ? VC_READY : VC_WARNING, atrOK ? "ATR OK" : "ATR indisponivel (degradado)");

   // 1. ADX
   int hADX = iADX(_Symbol, PERIOD_CURRENT, ADXPeriod);
   bool adxOK = (hADX != INVALID_HANDLE);
   if(hADX != INVALID_HANDLE)
      IndicatorRelease(hADX);
   g_vcheck_set(1, adxOK ? VC_READY : VC_WARNING, adxOK ? "ADX OK" : "ADX indisponivel (degradado)");

   // 2. RSI
   int hRSI = iRSI(_Symbol, PERIOD_CURRENT, RSIPeriod, PRICE_CLOSE);
   bool rsiOK = (hRSI != INVALID_HANDLE);
   if(hRSI != INVALID_HANDLE)
      IndicatorRelease(hRSI);
   g_vcheck_set(2, rsiOK ? VC_READY : VC_WARNING, rsiOK ? "RSI OK" : "RSI indisponivel (degradado)");

   // 3. EMA (tendencia)
   int hEMA = iMA(_Symbol, PERIOD_CURRENT, FastEMA, 0, MODE_EMA, PRICE_CLOSE);
   bool emaOK = (hEMA != INVALID_HANDLE);
   if(hEMA != INVALID_HANDLE)
      IndicatorRelease(hEMA);
   g_vcheck_set(3, emaOK ? VC_READY : VC_WARNING, emaOK ? "EMA OK" : "EMA indisponivel (degradado)");

   // 4. AI
   string predFile = "Data\\prediction_" + _Symbol + ".json";
   // P1.54 (v1.2.68): sandbox do terminal, como o AIConnector le. Com
   // FILE_COMMON esta linha procurava em Common\Files\Data, onde o EA nunca
   // escreve, e respondia "prediction ausente" mesmo quando o ficheiro
   // existia (7 dos 16 simbolos as 05:18 de 02/11/2026).
   bool hasPred = FileIsExist(predFile);

   // P1.60 (v1.2.74): a idade da previsao passa a contar para o veredicto,
   // com o mesmo limiar do motor (AI\AIConnector.mqh:420, MaxPredictionAgeSec
   // = 900 s). Antes o item dizia READY so por o ficheiro existir, com o
   // ficheiro a 600 h rejeitado pelo motor no mesmo arranque.
   double predIdadeS = -1.0;

   if(hasPred)
   {
      long modPred = FileGetInteger(predFile, FILE_MODIFY_DATE, false);
      if(modPred > 0)
      {
         double sLocal = (double)((long)TimeLocal() - (long)modPred);
         double sGmt   = (double)((long)TimeGMT()   - (long)modPred);
         predIdadeS = MathMin(sLocal, sGmt);
         if(predIdadeS < 0.0)
            predIdadeS = 0.0;
      }
   }

   bool predVelha = hasPred && (MaxPredictionAgeSec > 0) &&
                    (predIdadeS < 0.0 || predIdadeS > (double)MaxPredictionAgeSec);

   if(!EnableAIFilter)
      g_vcheck_set(4, VC_READY, "Filtro IA desativado (nao requerido)");
   else if(hasPred && !predVelha)
      g_vcheck_set(4, VC_READY, "Prediction JSON usavel pelo motor | idade="
                    + DoubleToString(predIdadeS, 0) + "s (max="
                    + IntegerToString(MaxPredictionAgeSec) + "s)");
   else if(predVelha && RequireAIJSON)
      g_vcheck_set(4, VC_BLOCKED, "Prediction STALE e IA requerida: idade="
                    + DoubleToString(predIdadeS, 0) + "s > max="
                    + IntegerToString(MaxPredictionAgeSec) + "s");
   else if(predVelha)
      g_vcheck_set(4, VC_WARNING, "Prediction STALE: idade="
                    + DoubleToString(predIdadeS, 0) + "s > MaxPredictionAgeSec="
                    + IntegerToString(MaxPredictionAgeSec) + "s | motor ignora, fallback tecnico (nao bloqueia)");
   else if(RequireAIJSON)
      g_vcheck_set(4, VC_BLOCKED, "IA requerida mas prediction ausente");
   else
      g_vcheck_set(4, VC_WARNING, "IA sem prediction (fallback tecnico)");

   // 5. JSON
   bool jsonOK = false;
   if(FileIsExist(predFile))
   {
      int jh = FileOpen(predFile, FILE_READ | FILE_BIN | FILE_SHARE_READ | FILE_SHARE_WRITE);
      if(jh != INVALID_HANDLE)
      {
         jsonOK = (FileSize(jh) > 0);
         FileClose(jh);
      }
   }

   if(!EnableAIFilter || !RequireAIJSON)
      g_vcheck_set(5, jsonOK ? VC_READY : VC_WARNING, jsonOK ? "JSON OK" : "JSON ausente/vazio (opcional)");
   else
      g_vcheck_set(5, jsonOK ? VC_READY : VC_BLOCKED, jsonOK ? "JSON OK" : "JSON ausente/vazio (requerido)");

   // 6. Dataset
   string dsFile = "Data\\dataset.csv";
   bool dsOK = false;
   // P1.54 (v1.2.68): o dataset esta na sandbox (MQL5\Files\Data), aberto
   // pelo DataLogger.mqh:180 sem FILE_COMMON; com FILE_COMMON esta linha
   // olhava para Common\Files\Data e nunca o encontrava. FILE_SHARE_* e
   // necessario porque o DataLogger mantem o CSV aberto enquanto o EA corre.
   if(FileIsExist(dsFile))
   {
      int dh = FileOpen(dsFile, FILE_READ | FILE_BIN | FILE_SHARE_READ | FILE_SHARE_WRITE);
      if(dh != INVALID_HANDLE)
      {
         dsOK = (FileSize(dh) > 0);
         FileClose(dh);
      }
   }

   // P1.53 (v1.2.67): MEDIDO no arranque de 02/11/2026 05:14 - a
   // ProductionChecklist escrevia "[OPTIONAL] Dataset: FAIL - Dataset ausente
   // ou vazio" (nao critico, nao trava) e esta checklist escrevia BLOCKED
   // para o MESMO input e o MESMO ficheiro. O cabecalho define BLOCKED como
   // "impede operacao segura (critico)" e nada o consulta desde o P1.44: era
   // um alarme falso com nome de portao. Dataset ausente e degradacao, nao
   // bloqueio - passa a WARNING, igual ao FAIL nao critico da Production.
   if(!EnableDataset)
      g_vcheck_set(6, VC_READY, "Dataset desativado");
   else
      g_vcheck_set(6, dsOK ? VC_READY : VC_WARNING, dsOK ? "Dataset OK" : "Dataset ausente/vazio (opcional, nao bloqueia)");

   // 7. Python
   bool pyOK = hasPred && dsOK;
   g_vcheck_set(7, pyOK ? VC_READY : VC_WARNING, pyOK ? "Pipeline Python OK" : "Pipeline Python incompleto (opcional)");

   // 8. Broker
   // P1.64: le a fonte unica (Core/TradeGate.mqh) em vez do bit cru
   bool brokerOK = CTradeGate::Connected();
   g_vcheck_set(8, brokerOK ? VC_READY : VC_BLOCKED, brokerOK ? "Terminal conectado" : CTradeGate::Cause(TG_DISCONNECTED));

   // 9. Spread
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   bool spreadOK = true;
   string spreadMsg = "Spread OK";

   if(ask > 0.0 && bid > 0.0 && point > 0.0)
   {
      double spreadPoints = (ask - bid) / point;
      // `GetMaxSpread()`, e nao o input cru `MaxSpread`: ver
      // `Monitoring/ProductionChecklist.mqh` no mesmo ponto. O input virou
      // porcentagem; quem converte para PONTOS e o getter.
      double maxSpreadPts = GetMaxSpread();
      if(spreadPoints > maxSpreadPts)
      {
         spreadOK = false;
         spreadMsg = "Spread " + DoubleToString(spreadPoints, 1) + " > max " + DoubleToString(maxSpreadPts, 1);
      }
   }

   if(!spreadOK && EnableSpreadFilter)
      g_vcheck_set(9, VC_BLOCKED, spreadMsg + " (bloqueia)");
   else if(!spreadOK)
      g_vcheck_set(9, VC_WARNING, spreadMsg + " (filtro desativado)");
   else
      g_vcheck_set(9, VC_READY, spreadMsg);

   // 10. Session
   int hourNow = (int)(TimeCurrent() / 3600) % 24;
   bool inSession = (hourNow >= TradeStartHour && hourNow < TradeEndHour);

   if(!EnableSessionFilter)
      g_vcheck_set(10, VC_READY, "Filtro de sessao desativado");
   else if(inSession)
      g_vcheck_set(10, VC_READY, "Dentro da sessao de trading");
   else
      g_vcheck_set(10, VC_WARNING, "Fora da sessao de trading (nao bloqueia)");

   // 11. Symbol Manager
   // P1.57 (v1.2.71): a ProductionChecklist exige cotacao (bid>0 e ask>0) para
   // o item Symbols e esta lista aceitava o simbolo so por SymbolSelect: um
   // simbolo selecionavel mas sem bid/ask dava "READY - Symbol disponivel" aqui e
   // "FAIL - Symbol sem cotacao" la. Sem cotacao nao ha execucao possivel, por
   // isso o criterio mais estrito passa a ser o unico: bid/ask medidos acima.
   bool symOK = SymbolSelect(_Symbol, true) && bid > 0.0 && ask > 0.0;
   g_vcheck_set(11, symOK ? VC_READY : VC_BLOCKED, symOK ? ("Symbol OK: " + _Symbol) : "Symbol sem cotacao (bloqueia)");

   // 12. Position Manager (health geral de posicoes)
   // Sem dependencia externa: valida que o gerenciamento de posicoes
   // esta acessivel (historico selecionavel).
   bool posOK = HistorySelect(0, TimeCurrent());
   g_vcheck_set(12, posOK ? VC_READY : VC_WARNING, posOK ? "Historico de posicoes acessivel" : "Historico indisponivel (degradado)");

   // 13. Trade Manager
   // P1.61 (v1.2.75): mesma fonte de verdade do portao de OnTick e do item 2
   // da ProductionChecklist. Antes este item exigia EA+TERMINAL e ignorava a
   // conta, enquanto a Production exigia TERMINAL+CONTA e ignorava o EA: em
   // 02/11 as 08:09 o mesmo instante dava PASS la e BLOCKED aqui.
   // P1.88 (v1.2.98): veredicto da SUITE, nao desta instancia. A execucao e
   // delegada (PipelineIsMaster): um grafico sem MQL_TRADE_ALLOWED nao impede
   // a suite de negociar e nao deve marcar BLOCKED quando ha mestre com o bit.
   ETradeGate tradeGate = CTradeGate::EvaluateSuite();

   if(tradeGate == TG_OK)
      g_vcheck_set(13, VC_READY, CTradeGate::DescribeSuite(tradeGate));
   else
      g_vcheck_set(13, VC_BLOCKED, CTradeGate::Describe(tradeGate));

   // 14. Dashboard
   // P1.53 (v1.2.67): a ProductionChecklist da sempre PASS ao Dashboard
   // (opcional, P1.46) e esta dava WARNING para o mesmo input. Desligado
   // continua a ser uma opcao, nao uma degradacao: READY dos dois lados.
   g_vcheck_set(14, VC_READY, EnableDashboard ? "Dashboard ativo" : "Dashboard desativado (opcional)");

   //==================================================
   // RESULTADO FINAL: BLOCKED impede operacao
   //==================================================

   int blocked = 0;
   int warning = 0;

   for(int i = 0; i < g_vcheck_count; i++)
   {
      if(g_vcheck_status[i] == VC_BLOCKED)
         blocked++;
      if(g_vcheck_status[i] == VC_WARNING)
         warning++;
   }

   g_validationPassed = (blocked == 0);

   if(LogInicioDetalhe()) Print("[VALIDATION] Resultado: READY=", IntegerToString(g_vcheck_count - blocked - warning),
         " WARNING=", IntegerToString(warning),
         " BLOCKED=", IntegerToString(blocked));

   // P1.44: a versao anterior dizia operacao permitida, o que sugeria um portao
   // que nao existe. Medido: ninguem consulta ValidationChecklistPassed().
   if(g_validationPassed)
      { if(LogInicioDetalhe()) Print("[VALIDATION] SEM BLOCKED (diagnostico de init, nao e portao)"); }   // P1.99: chavetas devolvem o else ao if exterior
   else
      // v1.2.130 - P2.22: saia em TODOS os graficos a cada reload (15 linhas por
      // reload, medido as 23:49:43). O resultado e de init e nao muda entre
      // instancias; a contagem real continua a sair 1x por sessao e por CONTA.
      if(LogSessaoPodeImprimir("val_blocked")) Print("[VALIDATION] ", IntegerToString(blocked),
            " BLOCKED (diagnostico de init, nao impede execucao - spread e filtrado por tick)");

   // P1.44: FILE_WRITE sozinho apaga o conteudo na abertura.
   // Com FILE_READ | FILE_WRITE, FileSeek(0) e sem truncar, um resumo mais
   // curto que o anterior deixava o rabo do anterior no disco - defeito
   // medido no proprio ficheiro em 01/11/2026.
   int h = FileOpen("XAU_AI_PRO\\ValidationChecklist.txt", FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h != INVALID_HANDLE)
     {
      FileSeek(h, 0, SEEK_SET);
      FileWriteString(h, ValidationChecklistSummary());
      FileClose(h);
     }

   return g_validationPassed;
}

//==================================================
// STATUS
//==================================================

// P1.44: MEDIDO - nenhum caminho de execucao chama esta funcao.
// Mantida para uso futuro explicito; hoje o veredicto e so diagnostico.
bool ValidationChecklistPassed()
{
   return g_validationPassed;
}

//==================================================
// SUMMARY
//==================================================

string ValidationChecklistSummary()
{
   string summary = "=== VALIDATION CHECKLIST (READY/WARNING/BLOCKED) ===\n";

   int blocked = 0;
   int warning = 0;

   for(int i = 0; i < g_vcheck_count; i++)
   {
      summary += g_vcheck_name(i) + ": " + g_vcheck_status_str(g_vcheck_status[i]) + " - " + g_vcheck_msg[i] + "\n";

      if(g_vcheck_status[i] == VC_BLOCKED)
         blocked++;
      if(g_vcheck_status[i] == VC_WARNING)
         warning++;
   }

   summary += "\nREADY=" + IntegerToString(g_vcheck_count - blocked - warning) +
              " | WARNING=" + IntegerToString(warning) +
              " | BLOCKED=" + IntegerToString(blocked);

   summary += "\nResultado: " + (g_validationPassed ? "SEM BLOCKED" : "COM BLOCKED");
   summary += "\nsnapshot de init: " + TimeToString(g_vcheck_time, TIME_DATE|TIME_MINUTES) + " (nao reavaliado)";
   summary += "\nNOTA: diagnostico do arranque, nao e portao de execucao.";

   return summary;
}

#endif
