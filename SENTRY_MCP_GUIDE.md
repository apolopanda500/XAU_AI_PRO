# Sentry MCP - Guia de Integracao com XAU AI Pro

## O que e Sentry MCP?

O **Sentry MCP (Model Context Protocol)** e um servidor que permite que assistentes de IA (Claude, GPT, Cursor, etc.) interajam com o Sentry diretamente.

### Beneficios para XAU AI Pro:

1. **Debugging Inteligente** - IA analisa erros de treinamento/predicao
2. **Investigacao Automatica** - Busca padroes de erro automaticamente
3. **Sugestoes de Solucao** - IA recomenda acoes baseada no historico
4. **Workflow Natural** - Use linguagem natural para investigar issues

## Instalacao

### Opcao 1: CLI Global (Recomendado)

```bash
# Instale
npm install -g @sentry/mcp

# Verifique
sentry-mcp --version
```

### Opcao 2: Servidor Local

```bash
# Clone o repositorio
git clone https://github.com/getsentry/sentry-mcp.git
cd sentry-mcp

# Instale dependencias
pnpm install

# Configure
cp .env.example .env
# Edite .env com SENTRY_DSN e tokens

# Execute
pnpm dev
```

## Configuracao para XAU AI Pro

### 1. Variaveis de Ambiente

```bash
# Adicione ao .env existente
SENTRY_DSN=https://c58d3855cb3d89ff2da34aaefc68106a@o4511837787586560.ingest.de.sentry.io/4511882908074064
SENTRY_ORG=henrique-7n
SENTRY_PROJECT=default
```

### 2. Configure no Claude Desktop

Edite `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sentry": {
      "command": "sentry-mcp",
      "args": ["--stdio"],
      "env": {
        "SENTRY_DSN": "seu_dsn_aqui",
        "SENTRY_ORG": "henrique-7n"
      }
    }
  }
}
```
## Como Usar com XAU AI Pro

### Exemplos de Prompts para IA:

#### 1. Investigar Erros de Treinamento
```
"Quais erros de treinamento aconteceram nas ultimas 24h?"
"Mostre os erros mais frequentes durante treinamento de XAUUSD"
"Analise o erro de gradient explosion na epoch 50"
```

#### 2. Monitorar Predicoes
```
"Quais simbolos tiveram erros de predicao hoje?"
"Mostre a confianca media das predicoes de XAUUSD"
"Quais erros acontecem mais no timeframe M5?"
```

#### 3. Analise de Performance
```
"Qual a accuracy media dos modelos nas ultimas predicoes?"
"Mostre a distribuicao de F1-scores por simbolo"
"Qual o win rate das predicoes com confianca > 80%?"
```

## Comandos uteis do Sentry MCP

### Listar Issues
```bash
sentry-mcp query "list issues -project xau-ai-pro -limit 10"
```

### Buscar Erros Especificos
```bash
sentry-mcp query "search errors -tag asset:XAUUSD -last 24h"
```

### Analise de Stacktrace
```bash
sentry-mcp query "analyze issue ISSUE_ID"
```

## Workflow de Debugging com IA

### Exemplo Pratico:

**Voce**: "O modelo XAUUSD esta com baixa accuracy, investigue no Sentry"

**IA (usando MCP)**:
1. Busca erros de treinamento de XAUUSD
2. Analisa stacktraces dos erros
3. Identifica padrao: "Gradient explosion em LSTM layer 3"
4. Consulta solucoes anteriores
5. Sugere: "Reduzir learning rate para 0.0001"

## Instalacao e Teste

### 1. Instale Sentry MCP
```bash
npm install -g @sentry/mcp
```

### 2. Teste Conexao
```bash
sentry-mcp query "who am I?"
```

### 3. Liste Projetos
```bash
sentry-mcp query "list projects"
```

### 4. Busque Issues do XAU AI Pro
```bash
sentry-mcp query "list issues -tag project:xau_ai_pro -last 24h"
```

## Integracao com IDEs

### Claude Desktop

Edite `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "sentry": {
      "command": "sentry-mcp",
      "args": ["--stdio"],
      "env": {
        "SENTRY_DSN": "seu_dsn_aqui",
        "SENTRY_ORG": "henrique-7n"
      }
    }
  }
}
```

### Cursor/VS Code

Adicione ao `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "sentry": {
      "command": "sentry-mcp",
      "args": ["--stdio"]
    }
  }
}
```

## Recursos

- **GitHub**: https://github.com/getsentry/sentry-mcp
- **Docs**: https://docs.sentry.io/platforms/python/mcp/
- **Dashboard**: https://henrique-7n.sentry.io/

## Proximos Passos

1. Instale: npm install -g @sentry/mcp
2. Configure no Claude Desktop ou Cursor
3. Teste queries basicas
4. Use com XAU AI Pro para debugging inteligente

**Status: GUIA CRIADO - PRONTO PARA INSTALACAO**
