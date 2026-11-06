//+------------------------------------------------------------------+
//| ProductionChecklist.mqh                                         |
//| XAU_AI_PRO - Production Readiness Checklist (ETAPA 10 v2.0)     |
//| Checagens reais de config, indicadores, IA/Python, dataset,     |
//| execucao, risco, notificacoes, auditoria e ambiente.            |
//+------------------------------------------------------------------+
#property copyright "XAU_AI_PRO"
#property version   "1.290"   // 1.2.9 no formato xxx.yyy exigido pelo compilador

#ifndef PRODUCTION_CHECKLIST_MQH
#define PRODUCTION_CHECKLIST_MQH

// P1.56 (v1.2.70): teto de idade do ficheiro de previsao, o mesmo que o
// registo de modelos usa para o estado READY (MAX_AGE_READY_SEC = 5 dias).
#define AIChecklistMaxAgeHours 120.0

#include "../Core/Config.mqh"
// P1.61 (v1.2.75): fonte unica de verdade das permissoes de negociacao.
#include "../Core/TradeGate.mqh"

//==================================================
// CLASSE (arrays paralelos - seguro em MQL5)
//==================================================

class CProductionChecklist
{
private:

   static string m_names[];
   static bool   m_passed[];
   static string m_messages[];
   static bool   m_critical[];
   static int    m_item_count;
   static bool   m_initialized;
   static bool   m_all_passed;
   // P1.44: hora em que o checklist correu, para que um veredicto antigo
   // nao possa ser lido como se fosse o estado actual do EA.
   static datetime m_snapshot_time;

   static void SetResult(int idx, bool passed, string message);

   static double PredictionAgeHours(const string file);

   static double PredictionAgeSeconds(const string file);

public:

   static void Init();

   static bool Run();

   static bool IsReady();

   static string GetSummary();

   static void LogResults();

   static int GetPassedCount();

   static int GetFailedCount();

   static int GetCriticalFailedCount();

   static void CheckBroker();

   static void CheckAccount();

   static void CheckPermissions();

   static void CheckSymbols();

   static void CheckIndicators();

   static void CheckAI();

   static void CheckPython();

   static void CheckDataset();

   static void CheckJSON();

   static void CheckLogs();

   static void CheckRisk();

   static void CheckExecution();

   static void CheckNotifications();

   static void CheckAudit();

   static void CheckDashboard();

   static void CheckScanner();

   static void CheckPerformance();
};

//==================================================
// VARIAVEIS ESTATICAS
//==================================================

string CProductionChecklist::m_names[];
bool   CProductionChecklist::m_passed[];
string CProductionChecklist::m_messages[];
bool   CProductionChecklist::m_critical[];
int    CProductionChecklist::m_item_count = 0;
bool   CProductionChecklist::m_initialized = false;
bool   CProductionChecklist::m_all_passed = false;
datetime CProductionChecklist::m_snapshot_time = 0;

//==================================================
// HELPERS
//==================================================

void CProductionChecklist::SetResult(int idx, bool passed, string message)
{
   if(idx < 0 || idx >= m_item_count)
      return;
   m_passed[idx]   = passed;
   m_messages[idx] = message;
}

//==================================================
// P1.56: idade de um ficheiro em horas, lida da data de
// modificacao sem abrir o ficheiro.
// Devolve -1.0 quando a data nao pode ser lida.
//==================================================

double CProductionChecklist::PredictionAgeHours(const string file)
{
   long mod = FileGetInteger(file, FILE_MODIFY_DATE, false);

   if(mod <= 0)
      return -1.0;

   // FILE_MODIFY_DATE e a data local do sistema de ficheiros, o mesmo relogio
   // de TimeLocal(). TimeGMT() entra como rede de seguranca para o caso de a
   // maquina e o servidor estarem em fusos diferentes, e o menor dos dois e o
   // escolhido para que a idade nunca seja declarada por engano.
   double hLocal = (double)((long)TimeLocal() - (long)mod) / 3600.0;
   double hGmt   = (double)((long)TimeGMT()   - (long)mod) / 3600.0;
   double horas  = MathMin(hLocal, hGmt);

   if(horas < 0.0)
      horas = 0.0;

   return horas;
}

//==================================================
// P1.60 (v1.2.74): a mesma idade, em segundos. A regra que o motor aplica
// (AI\AIConnector.mqh:420) e em segundos contra MaxPredictionAgeSec; converter
// horas em segundos aqui evita um segundo criterio sobre o mesmo ficheiro.
//==================================================

double CProductionChecklist::PredictionAgeSeconds(const string file)
{
   double horas = PredictionAgeHours(file);

   if(horas < 0.0)
      return -1.0;

   return horas * 3600.0;
}

//==================================================
// INIT
//==================================================

void CProductionChecklist::Init()
{
   if(m_initialized)
      return;

   ArrayResize(m_names, 17);
   ArrayResize(m_passed, 17);
   ArrayResize(m_messages, 17);
   ArrayResize(m_critical, 17);

   m_item_count = 17;

   // CRITICOS
   m_names[0]  = "Broker";          m_critical[0] = true;
   m_names[1]  = "Account";         m_critical[1] = true;
   m_names[2]  = "Permissions";     m_critical[2] = true;
   m_names[3]  = "Symbols";         m_critical[3] = true;
   m_names[4]  = "Indicators";      m_critical[4] = true;

   // NAO CRITICOS
   m_names[5]  = "AI";              m_critical[5] = false;
   m_names[6]  = "Python";          m_critical[6] = false;
   m_names[7]  = "Dataset";         m_critical[7] = false;
   m_names[8]  = "JSON";            m_critical[8] = false;
   m_names[9]  = "Logs";            m_critical[9] = false;

   // CRITICOS
   m_names[10] = "Risk";            m_critical[10] = true;
   m_names[11] = "Execution";       m_critical[11] = true;

   // NAO CRITICOS
   m_names[12] = "Notifications";   m_critical[12] = false;
   m_names[13] = "Audit";           m_critical[13] = false;
   m_names[14] = "Dashboard";       m_critical[14] = false;
   m_names[15] = "Scanner";         m_critical[15] = false;
   m_names[16] = "Performance";     m_critical[16] = false;

   for(int i = 0; i < m_item_count; i++)
   {
      m_passed[i]   = false;
      m_messages[i] = "pendente";
   }

   m_initialized = true;

   if(LogInicioDetalhe()) { Print("[CHECKLIST] ProductionChecklist inicializado (17 itens)"); }
}

//==================================================
// RUN
//==================================================

bool CProductionChecklist::Run()
{
   if(!m_initialized)
      Init();

   CheckBroker();
   CheckAccount();
   CheckPermissions();
   CheckSymbols();
   CheckIndicators();

   CheckAI();
   CheckPython();
   CheckDataset();
   CheckJSON();
   CheckLogs();

   CheckRisk();
   CheckExecution();

   CheckNotifications();
   CheckAudit();
   CheckDashboard();
   CheckScanner();
   CheckPerformance();

   m_all_passed = true;

   for(int i = 0; i < m_item_count; i++)
   {
      if(!m_passed[i] && m_critical[i])
      {
         m_all_passed = false;
         break;
      }
   }

   // P1.44: o relatorio e um retrato do arranque; a hora tem de viajar com ele.
   m_snapshot_time = TimeCurrent();
   LogResults();

   return m_all_passed;
}

//==================================================
// READY
//==================================================

// P1.44: MEDIDO - nenhum caminho de execucao chama esta funcao.
// O resultado do checklist e informativo: nao trava nem liberta trading,
// porque o portao de spread e por tick (Filters/SpreadFilter.mqh).
bool CProductionChecklist::IsReady()
{
   return m_all_passed;
}

//==================================================
// BROKER
//==================================================

void CProductionChecklist::CheckBroker()
{
   // P1.64: le a fonte unica (Core/TradeGate.mqh) em vez do bit cru
   bool ok = CTradeGate::Connected();

   SetResult(0, ok, ok ? "Terminal conectado" : CTradeGate::Cause(TG_DISCONNECTED));
}

//==================================================
// ACCOUNT
//==================================================

void CProductionChecklist::CheckAccount()
{
   long login = AccountInfoInteger(ACCOUNT_LOGIN);

   bool ok = (login > 0);

   SetResult(1, ok, ok ? ("Conta OK: " + IntegerToString(login)) : "Conta nao identificada");
}

//==================================================
// PERMISSIONS
//==================================================

void CProductionChecklist::CheckPermissions()
{
   // P1.61 (v1.2.75): o criterio era TERMINAL && CONTA e ignorava o EA, por
   // isso dava PASS enquanto o portao de OnTick barrava as 16 ordens com
   // MQL_TRADE_ALLOWED=0. Passa a ler a fonte unica (Core/TradeGate.mqh).
   // P1.88 (v1.2.98): veredicto da SUITE. A execucao e delegada a uma instancia
   // (PipelineIsMaster), por isso um grafico sem o bit proprio nao impede a suite
   // de negociar. O item so deve reprovar quando NENHUMA instancia pode negociar.
   ETradeGate tradeGate = CTradeGate::EvaluateSuite();

   bool ok = (tradeGate == TG_OK);

   SetResult(2, ok, CTradeGate::Describe(tradeGate));
}

//==================================================
// SYMBOL
//==================================================

void CProductionChecklist::CheckSymbols()
{
   string symbol = _Symbol;

   bool selected = SymbolSelect(symbol, true);

   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);

   bool ok = selected && bid > 0.0 && ask > 0.0;

   SetResult(3, ok, ok ? ("Symbol OK: " + symbol) : "Symbol sem cotacao");
}

//==================================================
// INDICATORS (ATR + ADX + RSI reais)
//==================================================

void CProductionChecklist::CheckIndicators()
{
   int hATR = iATR(_Symbol, PERIOD_CURRENT, ATRPeriod);
   int hADX = iADX(_Symbol, PERIOD_CURRENT, ADXPeriod);
   int hRSI = iRSI(_Symbol, PERIOD_CURRENT, RSIPeriod, PRICE_CLOSE);

   bool ok = (hATR != INVALID_HANDLE) && (hADX != INVALID_HANDLE) && (hRSI != INVALID_HANDLE);

   if(hATR != INVALID_HANDLE) IndicatorRelease(hATR);
   if(hADX != INVALID_HANDLE) IndicatorRelease(hADX);
   if(hRSI != INVALID_HANDLE) IndicatorRelease(hRSI);

   SetResult(4, ok, ok ? "ATR+ADX+RSI handles OK" : "Falha ao criar handles de indicadores");
}

//==================================================
// AI (prediction JSON do simbolo)
//==================================================

void CProductionChecklist::CheckAI()
{
   // P1.54 (v1.2.68): MEDIDO em 02/11/2026 05:18 - este ficheiro vive em
   // MQL5\Files\Data\prediction_<SIMBOLO>.json, a sandbox do terminal, que e
   // onde o AIConnector o le (AIConnector.mqh:791 e :836 usam FileIsExist e
   // FileOpen SEM FILE_COMMON) e onde o Core\PathManager.mqh o declara
   // (PredictionPath = Files\Data\prediction.json). Com FILE_COMMON a
   // verificacao olhava para Common\Files\Data, pasta onde o EA nunca
   // escreve: 16 de 16 graficos diziam "IA offline" as 05:18, com 7 dos 16
   // ficheiros presentes no disco (XAUUSD, USDJPY, USDCAD, AUDUSD, NZDUSD,
   // GBPUSD, EURUSD).
   //
   // P1.56 (v1.2.70): MEDIDO em 02/11/2026 05:51 - o ficheiro existia mas tinha
   // 25 dias. Data\prediction_XAUUSD.json tem "timestamp":
   // "2026-10-08T22:00:33.296743", que coincide ao segundo com a data de
   // modificacao do ficheiro no disco, e o item imprimia apenas
   // "Prediction JSON encontrado". Um PASS sem idade escondia uma previsao de
   // 08/10, mais velha do que o dataset que o EA escreve a cada vela.
   // O VEREDICTO NAO MUDA: o item continua [OPTIONAL] e continua PASS enquanto
   // o ficheiro existir, para nao criar um segundo veredicto sobre o mesmo dado
   // (regra do P1.53). O que passa a existir e a idade no texto e a marca STALE
   // acima do mesmo teto que o registo de modelos usa para o estado READY
   // (MAX_AGE_READY_SEC = 5 dias). Nenhum return, limite, risco ou regra de
   // trading foi tocado: muda o que a mensagem diz.
   // P1.57 (v1.2.71): MEDIDO em 02/11/2026 05:58 - as duas checklists
   // davam vereditos DIFERENTES para o mesmo ficheiro e os mesmos inputs.
   // Exemplo medido no codigo: com EnableAIFilter=false e nenhuma previsao no
   // disco, esta lista escrevia "[OPTIONAL] AI: FAIL - Prediction JSON nao
   // encontrado (IA offline)" e a ValidationChecklist escrevia, no mesmo
   // arranque, "AI: READY - Filtro IA desativado (nao requerido)". E com
   // RequireAIJSON=true e nenhuma previsao, esta lista ficava em FAIL NAO
   // CRITICO enquanto a Validation escrevia BLOCKED. Passa a haver uma so
   // tabela de decisao: filtro desligado = READY/PASS; previsao presente =
   // READY/PASS; ausente e nao requerida = WARNING/FAIL nao critico; ausente e
   // requerida = BLOCKED/FAIL critico. Nenhum limite, risco ou regra de trading
   // foi tocado: muda o veredicto do item de diagnostico.
   string file = "Data\\prediction_" + _Symbol + ".json";

   bool existe = FileIsExist(file);

   if(!EnableAIFilter)
   {
      m_critical[5] = false;
      SetResult(5, true, "Filtro IA desativado (nao requerido)");
      return;
   }

   // BLOCKED na ValidationChecklist so acontece com RequireAIJSON=true: para o
   // mesmo dado, este item tem de ser critico exatamente no mesmo caso.
   m_critical[5] = RequireAIJSON;

   // P1.60 (v1.2.74): MEDIDO em 02/11/2026 06:19 - o item dizia PASS para
   // a previsao do simbolo so por o ficheiro existir, enquanto o motor
   // descartava o MESMO ficheiro por idade: AI\AIConnector.mqh:420 faz
   // `MaxPredictionAgeSec>0 && age>(long)MaxPredictionAgeSec` e o input vale
   // 900 s. O teto usado aqui era 120 h (AIChecklistMaxAgeHours), que nao e o
   // do motor e nunca decidia nada. Resultado medido: PASS/READY com
   // idade=600 h e o motor em fallback. Passa a haver um so criterio, o do
   // motor, lido do proprio input. O item continua [OPTIONAL]; so vira
   // critico quando RequireAIJSON=true, exatamente como na ValidationChecklist.
   double idadeS = PredictionAgeSeconds(file);

   bool velho = (MaxPredictionAgeSec > 0) && (idadeS < 0.0 || idadeS > (double)MaxPredictionAgeSec);

   bool ok = existe && !velho;

   string msg = "";

   if(!existe)
   {
      msg = "Prediction JSON nao encontrado (IA offline)";
   }
   else if(!velho)
   {
      msg = "Prediction JSON usavel pelo motor | idade=" + DoubleToString(idadeS, 0)
          + "s (max=" + IntegerToString(MaxPredictionAgeSec) + "s)";
   }
   else
   {
      msg = "Prediction STALE: idade=" + DoubleToString(idadeS, 0)
          + "s > MaxPredictionAgeSec=" + IntegerToString(MaxPredictionAgeSec)
          + "s | motor ignora, fallback tecnico (nao bloqueia)";
   }

   if(!ok && RequireAIJSON)
      msg += " | BLOQUEIA (RequireAIJSON=true)";

   SetResult(5, ok, msg);
}

//==================================================
// PYTHON (pipeline: prediction + dataset)
//==================================================

void CProductionChecklist::CheckPython()
{
   // P1.54 (v1.2.68): mesma pasta que o CheckAI e o resto do EA usam -
   // predicao e dataset ficam os dois na sandbox do terminal.
   string pred = "Data\\prediction_" + _Symbol + ".json";
   string ds   = "Data\\dataset.csv";

   bool ok = FileIsExist(pred) && FileIsExist(ds);

   SetResult(6, ok, ok ? "Pipeline Python: prediction + dataset OK" : "Pipeline Python incompleto");
}

//==================================================
// DATASET
//==================================================

void CProductionChecklist::CheckDataset()
{
   // P1.46 (v1.2.64): desligar o dataset e uma opcao, nao uma avaria.
   // MEDIDO em 01/11/2026: com EnableDataset=true e nenhum dataset no disco o
   // relatorio dizia "[OPTIONAL] Dataset: FAIL - Dataset ausente ou vazio",
   // enquanto a ValidationChecklist dizia, no mesmo arranque,
   // "Dataset: READY - Dataset desativado". Uma respeitava a definicao, a
   // outra contava a escolha como falha.
   if(!EnableDataset)
   {
      SetResult(7, true, "Dataset desativado (opcional)");
      return;
   }

   // P1.54 (v1.2.68): MEDIDO em 02/11/2026 05:18:05 - o dataset existe e
   // esta a ser escrito, em MQL5\Files\Data\dataset.csv (3.537.420 bytes,
   // escrita de 1 em 1 vela pelo DataLogger.mqh:180, que abre o ficheiro
   // SEM FILE_COMMON). O relatorio dizia "Dataset ausente ou vazio" porque
   // esta funcao procurava em Common\Files\Data, onde nao existe dataset
   // nenhum. O Diagnostics.mqh:382 le o mesmo ficheiro na sandbox e ja
   // documentava a segunda metade do problema: sem FILE_SHARE_* o CSV aberto
   // pelo DataLogger aparece como "nao encontrado" - por isso o FILE_SHARE_
   // READ/WRITE entra aqui tambem.
   string file = "Data\\dataset.csv";

   bool ok = false;

   if(FileIsExist(file))
   {
      int h = FileOpen(file, FILE_READ | FILE_BIN | FILE_SHARE_READ | FILE_SHARE_WRITE);

      if(h != INVALID_HANDLE)
      {
         ok = (FileSize(h) > 0);
         FileClose(h);
      }
   }

   SetResult(7, ok, ok ? "Dataset OK" : "Dataset ausente ou vazio");
}

//==================================================
// JSON
//==================================================

void CProductionChecklist::CheckJSON()
{
   // P1.54 (v1.2.68): mesma pasta e mesmas flags do CheckDataset (a
   // previsao do simbolo esta na sandbox, ao lado do dataset).
   string file = "Data\\prediction_" + _Symbol + ".json";

   bool ok = false;

   if(FileIsExist(file))
   {
      int h = FileOpen(file, FILE_READ | FILE_BIN | FILE_SHARE_READ | FILE_SHARE_WRITE);

      if(h != INVALID_HANDLE)
      {
         ok = (FileSize(h) > 0);
         FileClose(h);
      }
   }

   // P1.57 (v1.2.71): mesma tabela do item JSon da ValidationChecklist.
   // Antes, com RequireAIJSON=true e o ficheiro vazio, esta lista escrevia
   // "FAIL nao critico" e a Validation escrevia "BLOCKED" para o mesmo ficheiro.
   m_critical[8] = (EnableAIFilter && RequireAIJSON);

   SetResult(8, ok, ok ? ("JSON acessivel" + (RequireAIJSON ? " (requerido)" : " (opcional)")) : (RequireAIJSON && EnableAIFilter ? "JSON ausente ou vazio | BLOQUEIA (RequireAIJSON=true)" : "JSON ausente ou vazio (opcional, nao bloqueia)"));
}

//==================================================
// LOGS
//==================================================

void CProductionChecklist::CheckLogs()
{
   bool ok = EnableLogs;

   SetResult(9, ok, ok ? "Sistema de logs habilitado" : "Logs desabilitados no input");
}

//==================================================
// RISK (margem + parametros de risco validos)
//==================================================

void CProductionChecklist::CheckRisk()
{
   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);

   bool paramsOK =
      RiskPercent > 0.0 &&
      MaxDailyLossPercent > 0.0 &&
      MaxDrawdownPercent > 0.0 &&
      MaxTradesPerDay > 0 &&
      MaxOpenPositions > 0;

   bool ok = paramsOK && freeMargin >= MinFreeMargin;

   string msg = "";

   if(!paramsOK)
      msg = "Parametros de risco invalidos (RiskPercent/MaxDailyLoss/MaxDrawdown/MaxTrades/MaxOpen)";
   else if(freeMargin < MinFreeMargin)
      msg = "Margem livre insuficiente: " + DoubleToString(freeMargin, 2);
   else
      msg = "Risco OK | margem livre=" + DoubleToString(freeMargin, 2);

   SetResult(10, ok, msg);
}

//==================================================
// EXECUTION (bid/ask + spread)
//==================================================

void CProductionChecklist::CheckExecution()
{
   double bid   = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask   = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   bool ok = (bid > 0.0 && ask > 0.0);

   string msg = ok ? "Bid/Ask disponiveis" : "Preco indisponivel";

   if(ok && point > 0.0)
   {
      double spreadPoints = (ask - bid) / point;

      // `GetMaxSpread()`, e nao o input cru `MaxSpread`: o limite virou
      // porcentagem do preco (08/10/2026) e quem converte para PONTOS e o
      // getter. Ler o input aqui comparava um numero em pontos crus com um
      // spread em pontos, e dava o mesmo resultado para BTCUSD e EURUSD —
      // o mesmo defeito que travava o motor, agora no checklist.
      double maxSpreadPts = GetMaxSpread();
      if(spreadPoints > maxSpreadPts)
      {
         ok = false;
         msg = "Spread acima do maximo: " + DoubleToString(spreadPoints, 1) + " pts (max=" + DoubleToString(maxSpreadPts, 1) + ")";
      }
   }

   SetResult(11, ok, msg);
}

//==================================================
// NOTIFICATIONS
//==================================================

void CProductionChecklist::CheckNotifications()
{
   // P1.46 (v1.2.64): desligar notificacoes e uma opcao, nao uma avaria.
   if(!EnableNotifications)
   {
      SetResult(12, true, "Notificacoes desativadas (opcional)");
      return;
   }

   string msg = "Central de notificacoes habilitada";

   if(NotifyTelegramToken != "" && NotifyTelegramChatID == "")
      msg = "Telegram configurado sem ChatID (apenas Push)";

   SetResult(12, true, msg);
}

//==================================================
// AUDIT
//==================================================

void CProductionChecklist::CheckAudit()
{
   // P1.46 (v1.2.64): auditoria desligada e opcao, nao falha.
   SetResult(13, true, EnableAuditLog ? "Auditoria habilitada" : "Auditoria desativada (opcional)");
}

//==================================================
// DASHBOARD
//==================================================

void CProductionChecklist::CheckDashboard()
{
   // P1.46 (v1.2.64): dashboard desligado e opcao, nao falha.
   SetResult(14, true, EnableDashboard ? "Dashboard habilitado" : "Dashboard desativado (opcional)");
}

//==================================================
// SCANNER
//==================================================

void CProductionChecklist::CheckScanner()
{
   bool ok = EnableMultiSymbol;

   SetResult(15, ok, ok ? "Multi-symbol habilitado" : "Scanner multi-symbol desabilitado");
}

//==================================================
// PERFORMANCE (analise/benchmark ativos)
//==================================================

void CProductionChecklist::CheckPerformance()
{
   bool ok = EnableBacktestAnalyzer || EnableBenchmark;

   SetResult(16, ok, ok ? "Metricas de performance ativas" : "Analise de performance desabilitada");
}

//==================================================
// SUMMARY
//==================================================

string CProductionChecklist::GetSummary()
{
   string summary = "=== PRODUCTION CHECKLIST ===\n";

   int passed = 0;
   int failed = 0;
   int criticalFailed = 0;

   for(int i = 0; i < m_item_count; i++)
   {
      string status = m_passed[i] ? "PASS" : "FAIL";
      string critical = m_critical[i] ? "[CRITICAL]" : "[OPTIONAL]";

      summary += critical + " " + m_names[i] + ": " + status + " - " + m_messages[i] + "\n";

      if(m_passed[i])
         passed++;
      else
      {
         failed++;
         if(m_critical[i])
            criticalFailed++;
      }
   }

   summary += "\nResult: " + IntegerToString(passed) + "/" + IntegerToString(m_item_count) + " passed";
   summary += " | " + IntegerToString(failed) + " failed";
   summary += " | " + IntegerToString(criticalFailed) + " critical failed";
   summary += "\nREADY: " + (m_all_passed ? "YES" : "NO");
   summary += " | snapshot de init: " + TimeToString(m_snapshot_time, TIME_DATE|TIME_MINUTES);
   summary += "\nNOTA: relatorio do arranque - nao e reavaliado enquanto o EA corre,"
            + " nao e portao de execucao (nada consulta IsReady()) e o bloqueio"
            + " real de spread e por tick em Filters/SpreadFilter.mqh.";

   return summary;
}

//==================================================
// LOG RESULTS
//==================================================

void CProductionChecklist::LogResults()
{
   string summary = GetSummary();

   // v1.2.87 (02/11/2026) - P1.74: MEDIDO 23 linhas por arranque (368 num
   // reload de 16 graficos) para dizer 13/17. O relatorio completo continua
   // a ir inteiro para Common\Files\XAU_AI_PRO\ProductionChecklist.txt; o
   // journal passa a receber UMA linha com as falhas, o unico facto accionavel.
   int    passou = 0;
   string falhas = "";

   for(int i = 0; i < m_item_count; i++)
     {
      if(m_passed[i])
        {
         passou++;
         continue;
        }

      if(falhas != "")
         falhas += ",";

      falhas += m_names[i] + (m_critical[i] ? "(critico)" : "(opcional)");
     }

   if(LogInicioDetalhe()) Print("[CHECKLIST] ", passou, "/", m_item_count, " passed",
         (falhas == "" ? " | sem falhas" : (" | falhas: " + falhas)),
         " | READY=", (m_all_passed ? "SIM" : "NAO"),
         " | relatorio completo: Common\\Files\\XAU_AI_PRO\\ProductionChecklist.txt");

   // P1.44: FILE_WRITE sozinho apaga o conteudo na abertura.
   // Com FILE_READ | FILE_WRITE, FileSeek(0) e sem truncar, um resumo mais
   // curto deixava o rabo do anterior no disco (medido: READY: YEStical failed).
   int h = FileOpen("XAU_AI_PRO\\ProductionChecklist.txt", FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h != INVALID_HANDLE)
     {
      FileSeek(h, 0, SEEK_SET);
      FileWriteString(h, summary);
      FileClose(h);
     }
}

//==================================================
// COUNTERS
//==================================================

int CProductionChecklist::GetPassedCount()
{
   int count = 0;

   for(int i = 0; i < m_item_count; i++)
   {
      if(m_passed[i])
         count++;
   }

   return count;
}

//==================================================

int CProductionChecklist::GetFailedCount()
{
   int count = 0;

   for(int i = 0; i < m_item_count; i++)
   {
      if(!m_passed[i])
         count++;
   }

   return count;
}

//==================================================

int CProductionChecklist::GetCriticalFailedCount()
{
   int count = 0;

   for(int i = 0; i < m_item_count; i++)
   {
      if(!m_passed[i] && m_critical[i])
         count++;
   }

   return count;
}

#endif
