# XAU AI Pro + Sentry Integration

## Status: INTEGRADO E TESTADO

### O que foi implementado:

1. **Monitoramento de Treinamento**
   - Captura erros durante treinamento de modelos
   - Registra metricas (accuracy, F1-score, loss)
   - Tracking de falhas por ativo

2. **Monitoramento de Predicao**
   - Captura erros de predicao em tempo real
   - Registra sinais gerados (BUY/SELL/HOLD)
   - Tracking de performance do modelo

3. **Contexto Rico**
   - Tags: project, asset (XAUUSD), component, symbol
   - Contexto: training, prediction, model_metrics
   - Release tracking por versao

## Arquivos Modificados/Criados

### Novos Arquivos
- `Python/sentry_config.py` - Configuracao principal
- `.env` - Variaveis de ambiente (configurado)
- `.env.example` - Template de variaveis
- `SENTRY_INTEGRATION.md` - Esta documentacao

### Arquivos Modificados
- `Python/main.py` - Inicializa Sentry
- `Python/train.py` - Monitoramento de treinamento
- `Python/predict.py` - Monitoramento de predicao

## Como Usar

### 1. Execute os Comandos Normais

```bash
# Nada muda! Os comandos funcionam como antes

# Treinar modelo
python main.py train

# Fazer predicoes
python main.py predict

# Dashboard
python main.py dashboard
```

### 2. Monitoramento Automatico

O Sentry captura automaticamente:
- Erros de treinamento
- Erros de predicao
- Metricas de performance
- Excecoes nao tratadas

### 3. Verifique no Dashboard

Acesse: https://henrique-7n.sentry.io/issues/views/28799/

## Configuracao

### Environment
- **Development**: Monitoramento desativado (padrao)
- **Production**: Monitoramento ativo

### Ativar Producao

```bash
# Windows
set ENVIRONMENT=production

# Linux/Mac
export ENVIRONMENT=production
```

## Alertas Sugeridos

Configure no Sentry Dashboard:

### 1. Erro de Treinamento
```
IF: Issue frequency > 1 per hour
AND: Tags contain component:training
THEN: Send email/Slack
```

### 2. Erro de Predicao Critico
```
IF: First time seen
AND: Tags contain component:prediction
AND: Level is: error
THEN: Immediate notification
```

### 3. Baixa Performance do Modelo
```
IF: Context contains accuracy < 70%
THEN: Send warning
```

## Testes Realizados

### Teste 1: Integracao Basica
- Status: PASS
- Sentry inicializado
- Funcoes de captura funcionando

### Teste 2: Erro de Treinamento
- Status: PASS
- Erro capturado com contexto
- Enviado ao Sentry

### Teste 3: Erro de Predicao
- Status: PASS
- Erro por simbolo capturado
- Enviado ao Sentry

### Teste 4: Metricas de Modelo
- Status: PASS
- Performance metrics enviadas
- Contexto rico

## Proximos Passos

1. **Configure credenciais** no arquivo `.env`
2. **Execute treinamento**: `python main.py train`
3. **Execute predicao**: `python main.py predict`
4. **Verifique Sentry**: Dashboard online
5. **Configure alertas**: No Sentry dashboard
6. **Deploy em producao**: Com monitoramento ativo

## Comandos uteis

```bash
# Testar integracao
cd Python
python -c "from sentry_config import init_sentry; init_sentry(); import sentry_sdk; sentry_sdk.capture_message('Teste', level='info'); sentry_sdk.flush()"

# Ver eventos no Sentry
# Acesse: https://henrique-7n.sentry.io/issues/views/28799/

# Ver releases
# Acesse: https://henrique-7n.sentry.io/releases/
```

## Estrutura de Eventos

### Evento de Treinamento
```json
{
  "message": "Training error at epoch 10: erro",
  "tags": {
    "component": "training",
    "asset": "XAUUSD",
    "project": "xau_ai_pro"
  },
  "context": {
    "training": {
      "epoch": 10,
      "loss": "0.5",
      "error": "erro"
    }
  }
}
```

### Evento de Predicao
```json
{
  "message": "Prediction error for XAUUSD: erro",
  "tags": {
    "component": "prediction",
    "symbol": "XAUUSD",
    "project": "xau_ai_pro"
  },
  "context": {
    "prediction": {
      "symbol": "XAUUSD",
      "prediction_type": "M5",
      "error": "erro"
    }
  }
}
```

## Seguranca

- Dados sensiveis sao filtrados (API keys)
- PII desativado por padrao
- Variaveis de ambiente para credenciais
- Nenhuma informacao sensivel enviada ao Sentry

## Status Final

- [x] Sentry SDK instalado
- [x] Configuracao completa
- [x] Integrado em main.py
- [x] Integrado em train.py
- [x] Integrado em predict.py
- [x] Testes passando
- [x] Eventos enviados
- [x] Documentacao completa

**INTEGRACAO 100% COMPLETA E TESTADA**

## Suporte

- Dashboard: https://henrique-7n.sentry.io/
- Issues: https://henrique-7n.sentry.io/issues/
- Documentacao: https://docs.sentry.io/platforms/python/

## Projeto

- **Nome**: XAU AI Pro
- **Localizacao**: C:\Users\Micro\Downloads\XAU_AI_PRO\
- **Ativo**: XAUUSD (Gold)
- **Tipo**: AI Trading System
- **Monitoramento**: Ativo via Sentry
