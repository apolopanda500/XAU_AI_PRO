# Política de Segurança do XAU_AI_PRO

## Divulgação de Vulnerabilidades

A segurança do projeto **XAU_AI_PRO** é nossa prioridade. Se você descobrir uma
vulnerabilidade de segurança, por favor, **não abra uma issue pública**. Em
vez disso, siga os passos abaixo:

### Como Reportar uma Vulnerabilidade

1. **Não compartilhe publicamente** — envie um e-mail privado para
   `apolopanda500@gmail.com` com o assunto:
   `SECURITY: [XAU_AI_PRO] <descrição curta>`.

2. **Inclua os detalhes** da vulnerabilidade:
   - Descrição do problema e impacto potencial
   - Passos para reproduzir
   - Versão do projeto afetada
   - Qualquer PoC (proof of concept) relevante
   - Seu contato (e-mail e/ou Discord)

3. **Tempo de resposta**: aguarde até **48 horas úteis**. Se não receber
   resposta, envie um follow-up.

4. **Validação**: validaremos o relato e, se confirmado, forneceremos uma
   estimativa para correção.

5. **Divulgação coordenada**: coordenaremos a publicação da correção com
   você antes de qualquer divulgação pública.

### Escopo

**Em escopo**:
- Vulnerabilidades em código Python (app/, Python/, src/)
- Vulnerabilidades em código JavaScript/Node.js (backend/)
- Problemas de configuração de segurança (workflows, Docker)
- Credenciais expostas ou secretos hardcoded

**Fora de escopo**:
- Questões de UI/UX estéticas
- Solicitações de features
- Questões de TradingView charts (terceirizadas)

## Medidas de Segurança Implementadas

| Controle | Status | Descrição |
|----------|--------|-----------|
| CodeQL | ✅ Ativo | Escaneamento de código em Python, JS/TS e GitHub Actions |
| Dependabot | ✅ Ativo | Atualizações automáticas de dependências |
| Secret Scanning | ✅ Ativo | Escaneamento nativo + padrões personalizados |
| npm audit | ✅ Ativo | Verificação de vulnerabilidades npm (audit-level=high) |
| .gitignore | ✅ Ativo | Arquivos `.env` não são versionados |
| Pinned dependencies | ✅ Ativo | `requirements-lock.txt` fixado por versão |
| Branch protection | 🛡️ Manual | Proteção da branch `main` via GitHub Settings |
| SECURITY.md | ✅ Este arquivo | Política de divulgação responsável |

## Credenciais Sensíveis

**NUNCA** commite:
- `.env`, `.env.local`, `.env.integrations`
- Arquivos `.pkl`, `.pkg`, modelos treinados
- Arquivos de banco de dados (`trading.db`, `ai_memory.db`)
- Arquivos de log (`*.log`)
- Credenciais de broker (MT5 conta, senha, servidor)

Use **GitHub Secrets** para:
- `DOCKER_PAT`
- `CLINE_API_KEY` / `OPENAI_API_KEY`

> Vercel, Sentry, Slack e Kilo sairam do projeto em 04/10/2026. Os secrets
> `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, `SENTRY_AUTH_TOKEN` e
> `SLACK_WEBHOOK_URL` **nao devem ser recriados**. As regras do `.gitleaks.toml`
> que caçam esses formatos continuam ativas, para pegar um token vazado no
> historico git — mesmo sem serviço consumindo.

## Segurança Operacional

- Use conta **demo** até validar estratégias em backtest e forward test
- Revise limites de lote, stop loss e drawdown antes de operar
- O módulo **Subgraph** é **somente leitura** (não envia ordens)
- O EA MQL5 opera de forma independente dentro do MetaTrader 5

## Contato

- **E-mail segurança**: `apolopanda500@gmail.com`
- **GitHub Security**: [https://github.com/apolopanda500/XAU_AI_PRO/security](https://github.com/apolopanda500/XAU_AI_PRO/security)

Agradecemos a todos que ajudam a manter o XAU_AI_PRO seguro! 🛡️