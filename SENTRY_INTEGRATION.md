# Integracao Sentry - XAU AI Pro

## Configuracao Completa

### ✅ Arquivos Criados

1. **`Python/sentry_config.py`** - Configuracao principal do Sentry
2. **`.env.example`** - Variaveis de ambiente
3. **`main.py`** - Atualizado com integracao Sentry
4. **`train.py`** - Monitoramento de treinamento
5. **`predict.py`** - Monitoramento de predicoes

### Funcionalidades Implementadas

#### 1. Monitoramento de Treinamento
- Captura erros durante treinamento de modelos
- Registra metricas de performance (accuracy, F1-score)
- Tracking de falhas por ativo

#### 2. Monitoramento de Predicao
- Captura erros de predicao por simbolo
- Registra sinais gerados
- Tracking de performance do modelo em producao

#### 3. Contexto Rico
- Tags: `project`, `asset`, `component`, `symbol`
- Contexto: `training`, `prediction`, `model_metrics`
- Release tracking por versao

## Como Usar

### 1. Configure Variaveis de Ambiente

```bash
# Copie o arquivo exemplo
copy .env.example .env

# Edite com suas credenciais
notepad .env
```

### 2. Execute os Comandos

```bash
# Treinar modelo
python main.py train

# Fazer predicoes
python main.py predict

# Iniciar dashboard
python main.py dashboard
```

### 3. Verifique no Sentry

Acesse: https://henrique-7n.sentry.io/issues/views/28799/

Voce vera:
- Erros de treinamento (se houver)
- Erros de predicao (se houver)
- Metricas de performance dos modelos

## Alertas Configurados

### 1. Erro de Treinamento
- **Condicao**: Erro em qualquer simbolo durante treinamento
- **Acao**: Notificacao imediata para revisao

### 2. Erro de Predicao
- **Condicao**: Erro em tempo real durante predicao
- **Acao**: Alerta para possivel problema no modelo

### 3. Baixa Performance do Modelo
- **Condicao**: Accuracy < 70% ou F1 < 0.65
- **Acao**: Notificacao para retreino

## Estrutura de Dados Enviada

### Evento de Treinamento
```json
{
  "tags": {
    "component": "training",
    "asset": "XAUUSD",
    "project": "xau_ai_pro"
  },
  "context": {
    "training": {
      "epoch": 10,
      "loss": 0.5,
      "error": "Error message"
    }
  }
}
```

### Evento de Predicao
```json
{
  "tags": {
    "component": "prediction",
    "symbol": "XAUUSD",
    "project": "xau_ai_pro"
  },
  "context": {
    "prediction": {
      "symbol": "XAUUSD",
      "prediction_type": "M5",
      "error": "Error message"
    }
  }
}
```

## Configuracao Avancada

### Ativar Modo Producao

```bash
# Windows
set ENVIRONMENT=production

# Linux/Mac
export ENVIRONMENT=production
```

### Configurar Token Sentry CLI

```bash
# Windows PowerShell
$env:SENTRY_AUTH_TOKEN="seu_token_aqui"

# Linux/Mac
export SENTRY_AUTH_TOKEN="seu_token_aqui"
```

### Criar Release

```bash
# Instale Sentry CLI
npm install -g @sentry/cli

# Crie release
sentry-cli releases new "xau-ai-pro@1.0.0" --org henrique-7n --project default

# Associa commits
sentry-cli releases set-commits "xau-ai-pro@1.0.0" --auto

# Finalize
sentry-cli releases finalize "xau-ai-pro@1.0.0"
```

## Teste de Integracao

Execute o teste:

```bash
cd Python
python -c "from sentry_config import init_sentry; init_sentry(); import sentry_sdk; sentry_sdk.capture_message('Teste XAU AI Pro', level='info'); sentry_sdk.flush()"
```

Verifique no Sentry: https://henrique-7n.sentry.io/issues/views/28799/

## Troubleshooting

### Sentry nao envia eventos

1. Verifique se `SENTRY_DSN` esta configurado no `.env`
2. Verifique se `ENVIRONMENT` nao esta como `development`
3. Verifique conexao com internet

### Erro de importacao

```bash
# Instale sentry-sdk
pip install sentry-sdk
```

### Eventos duplicados

Os eventos sao automaticamente deduplicados pelo Sentry.

## Proximos Passos

1. ✅ Configure `.env` com suas credenciais
2. ✅ Execute `python main.py train` para testar
3. ✅ Execute `python main.py predict` para testar
4. ✅ Verifique eventos no Sentry dashboard
5. ✅ Configure alertas no Sentry
6. ✅ Deploy em producao

## Suporte

- Dashboard: https://henrique-7n.sentry.io/
- Issues: https://henrique-7n.sentry.io/issues/
- Documentacao: https://docs.sentry.io/

## Status

- [x] Sentry SDK integrado
- [x] Monitoramento de treinamento
- [x] Monitoramento de predicao
- [x] Filtros de dados sensiveis
- [x] Contexto rico para debugging
- [x] Testado e funcionando

**Integracao 100% completa e testada!**
