# Sentry CLI - Configuracao para XAU AI Pro

## Status: INSTALADO E PRONTO PARA USO

### Versao Instalada
- **Sentry CLI**: 3.6.2
- **Localizacao**: C:\Program Files\nodejs\
- **Status**: Funcionando

## Configuracao Inicial

### 1. Autenticacao

#### Opcao A: Login Interativo
```bash
sentry-cli login
```

#### Opcao B: Token Manual
```bash
$env:SENTRY_AUTH_TOKEN="seu_token_aqui"
```

### 2. Como Obter o Token

1. Acesse: https://henrique-7n.sentry.io/settings/auth-tokens/
2. Crie novo token
3. Selecione escopos: project:releases, org:read, project:read
4. Copie o token

## Comandos Uteis

### Verificar Autenticacao
```bash
sentry-cli info
```

### Listar Projetos
```bash
sentry-cli projects list --org henrique-7n
```

### Criar Release
```bash
sentry-cli releases new "xau-ai-pro@1.0.0" --org henrique-7n --project default
```

### Associar Commits
```bash
sentry-cli releases set-commits "xau-ai-pro@1.0.0" --auto
```

### Notificar Deploy
```bash
sentry-cli releases deploys "xau-ai-pro@1.0.0" new -e production
```

### Finalizar Release
```bash
sentry-cli releases finalize "xau-ai-pro@1.0.0"
```
