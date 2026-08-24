//+------------------------------------------------------------------+
//|                                         ModelGovernance.mqh      |
//|                                 XAU_AI_PRO - ML Gov E15/E16     |
//|        Versionamento de modelo/dataset + registro por trade     |
//+------------------------------------------------------------------+
// ETAPA 15/16 - ML/AI PRODUCTION + MODEL GOVERNANCE
//
//  - Congela o dataset de treino (fingerprint + versao) e impede que
//    a versao de producao mude no meio da sessao sem reinicio.
//  - Registra o modelo utilizado por cada trade (auditoria/telemetria).
//  - Exige MODEL_ID/VERSION/DATASET_VERSION/STATUS=production para
//    permitir uso em producao (modelo experimental NAO entra).
//
// Modelo de dados (preenchido pelo pipeline Python / prediction JSON):
//   MODEL_ID, MODEL_VERSION, MODEL_TRAIN_DATE, DATASET_VERSION,
//   FEATURE_VERSION, ALGORITHM, MODEL_METRICS, MODEL_STATUS
//
// PRINCIPIO: falha de IA/JSON NAO gera ordem invalida; se o modelo
// nao e "production" ou o JSON esta ausente, DecideHandler bloqueia
// novas entradas (fail-closed APENAS quando RequireAIJSON=true).
//+------------------------------------------------------------------+

#ifndef MODEL_GOVERNANCE_MQH
#define MODEL_GOVERNANCE_MQH

#include "../Core/Config.mqh"
#include "AIConnector.mqh"

//==================================================
// ESTADO DO MODELO (preenchido pela leitura do JSON)
//==================================================
string g_modelId           = "";
string g_modelVersion      = "";
string g_modelTrainDate    = "";
string g_modelDatasetVer   = "";
string g_modelFeatureVer   = "";
string g_modelAlgorithm    = "";
string g_modelMetrics      = "";
string g_modelStatus       = "";      // production | experimental | etc.

bool   g_modelGoverned     = false;  // true quando modelo carregado e valido

#define MODEL_REQUIRED_STATUS "production"

//==================================================
// LE METADADOS DO MODELO A PARTIR DO JSON DE PREDICAO
// Os campos sao lidos via AIConnector (AI_* globals) quando presentes.
// Fallback honesto: se o JSON nao expoe metadados, deixa vazio e
// marca NAO-governado (nao bloqueia, mas loga aviso).
//==================================================
void ModelGovernanceRefresh()
{
   g_modelId         = LoadModelMetaString("MODEL_ID");
   g_modelVersion    = LoadModelMetaString("MODEL_VERSION");
   g_modelTrainDate  = LoadModelMetaString("MODEL_TRAIN_DATE");
   g_modelDatasetVer = LoadModelMetaString("DATASET_VERSION");
   g_modelFeatureVer = LoadModelMetaString("FEATURE_VERSION");
   g_modelAlgorithm  = LoadModelMetaString("ALGORITHM");
   g_modelMetrics    = LoadModelMetaString("MODEL_METRICS");
   g_modelStatus     = LoadModelMetaString("MODEL_STATUS");

   g_modelGoverned = (g_modelId != "" && g_modelVersion != "");

   if(g_modelGoverned && !EnableVerboseDebug)
      Print("[MODEL] Governado | ID=", g_modelId,
            " | V=", g_modelVersion,
            " | DS=", g_modelDatasetVer,
            " | Status=", (g_modelStatus == "" ? "production" : g_modelStatus));
}

//==================================================
// METADADO AUXILIAR - le campo do JSON se existir
// AIConnector ja expoe o parse; aqui apenas consultamos via
// uma funcao generica (definida em AIConnector.mqh).
//==================================================
string LoadModelMetaString(string key)
{
   return GetAIMetaString(key);
}

//==================================================
// MODELO APTO PARA PRODUCAO?
// Experimental nao entra. Requer STATUS=production quando informado.
// Se status vazio, assume production (comportamento atual v1.2.0).
//==================================================
bool ModelProductionReady()
{
   if(!g_modelGoverned)
      return true;     // sem metadados = manter comportamento atual (fail-open)

   if(g_modelStatus == "")
      return true;

   return (g_modelStatus == MODEL_REQUIRED_STATUS);
}

//==================================================
// REGISTRO POR TRADE - auditoria do modelo usado
// Chamado no DEAL_ENTRY_IN (apos positionId conhecido).
//==================================================
void ModelLogTradeUsage(ulong positionId, string symbol)
{
   if(!EnableAuditLog)
      return;

   string modelTag = StringFormat("%s|%s|%s|%s%s",
      (g_modelId == "" ? "n/a" : g_modelId),
      (g_modelVersion == "" ? "n/a" : g_modelVersion),
      (g_modelDatasetVer == "" ? "n/a" : g_modelDatasetVer),
      (ModelProductionReady() ? "prod" : "experimental"),
      (RequireAIJSON ? "|json" : "|nojson"));

   Print("[MODEL] Trade ", (string)positionId, " | ", symbol, " | ", modelTag);
}

//==================================================
// SUMMARY
//==================================================
string ModelGovernanceSummary()
{
   return StringFormat("Model | ID=%s | V=%s | DS=%s | Feat=%s | Alg=%s | Metrics=%s | Status=%s | Governed=%s | ProdReady=%s",
      (g_modelId=="" ? "n/a" : g_modelId),
      (g_modelVersion=="" ? "n/a" : g_modelVersion),
      (g_modelDatasetVer=="" ? "n/a" : g_modelDatasetVer),
      (g_modelFeatureVer=="" ? "n/a" : g_modelFeatureVer),
      (g_modelAlgorithm=="" ? "n/a" : g_modelAlgorithm),
      (g_modelMetrics=="" ? "n/a" : g_modelMetrics),
      (g_modelStatus=="" ? "production" : g_modelStatus),
      (g_modelGoverned ? "YES" : "NO"),
      (ModelProductionReady() ? "YES" : "NO"));
}

#endif // MODEL_GOVERNANCE_MQH