# MODEL GOVERNANCE POLICY - XAU_AI_PRO v1.2.0-RC1
## ETAPA 15.3 - Governanca de IA

**Data:** 24/08/2026 | **Status:** ATIVA

---

## 1. MODELO: RandomForestClassifier

- n_estimators=200, max_depth=8 (pipeline.py)
- NORMALIZACAO: Nao aplicada. RandomForest e um modelo por arvores de decisao,
  invariante a escala/monotonicidade. Aplicar scaler seria reundante (sem ganho)
  e adicionaria um componente extra de fragilidade.
- O Pipeline NAO produz scaler.pkl (correto para este algoritmo).

## 2. FEATURES
- Lista unica: 25 features (ai/feature_engineering.py FEATURES)
- Treino e inferencia usam a MESMA lista, na mesma ordem.
- prepare_features() rejeita features ausentes (ValueError) - nunca preenche 0.

## 3. CONTRATO DE PREDICAO (prediction_XY.json)
- model_version: heredado do .meta.json (fallback APP_VERSION 1.2.0)
- algorithm: type(model).__name__ (RandomForestClassifier)
- train_date: ISO UTC do treino
- dataset_version: hash SHA-256 parcial do dataset (len + ultima close + TF + features)
- feature_count: len(FEATURES) = 25
- metrics: accuracy/f1_score/train_samples/test_samples

## 4. MODELGOVERNANCE (MQL5)
- AIConnector parse dos novos campos -> GetAIMetaString:
  ALGORITHM / MODEL_TRAIN_DATE / DATASET_VERSION / MODEL_METRICS
- ModelGovernanceRefresh: g_modelGoverned = (id != "" && version != "")
- ModelProductionReady: STAATUS "production" quando informado

## 5. QUALIDADE / FALLBACK
- AI NUNCA cria sinal: apenas BLOQUEIA / CONFIRMA.
- IA indisponivel (signal UNAVAILABLE) -> fallback local (indicadores) ou
  bloqueio, conforme RequireAIJSON.
- Timeout de previsao: tratado pelo stale check do AIConnector (MaxPredictionAgeSec).

---
*Documento oficial - ETAPA 15.3*
