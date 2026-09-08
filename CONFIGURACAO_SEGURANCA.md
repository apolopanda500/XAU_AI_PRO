# Guia de Configuracao de Seguranca - XAU_AI_PRO

> Versão: 1.2.0
> Ultima atualizacao: Setembro 2026

Este documento descreve todas as medidas de seguranca configuradas no
repositorio GitHub apolopanda500/XAU_AI_PRO.

---

## 1. Visao Geral das Protecoes

| Controle | Arquivo | Ativo |
|---|---|---|
| CodeQL | .github/workflows/codeql.yml + .github/codeql.yml | Sim |
| Dependabot | .github/dependabot.yml | Sim |
| Secret Scanning | .github/secret-scanning.yml | Sim |
| Gitleaks | .gitleaks.toml + security.yml | Sim |
| pip-audit | .github/workflows/security.yml | Sim |
| npm audit | .github/workflows/maintenance.yml | Sim |
| SECURITY.md | .github/SECURITY.md | Sim |
| Env files check | .github/workflows/security.yml | Sim |
| Docker scan | .github/workflows/security.yml | Sim |
| Code patterns | .github/workflows/security.yml | Sim |

---

## 2. CodeQL

Workflow: .github/workflows/codeql.yml
Configuracao: .github/codeql.yml
Agendamento: quarta-feira 15:00 UTC
Linguagens: actions, javascript-typescript, python
Queries: security-extended, security-and-quality

---

## 3. Dependabot

Arquivo: .github/dependabot.yml
Frequencia: semanal (Segunda, 06:00 UTC-3)
Ecosystems: pip, npm, github-actions

---

## 4. Secret Scanning

GitHub native + padroes personalizados (.github/secret-scanning.yml)
Configuracao: .gitleaks.toml
Detecta: Sentry DSN, GitHub PAT, Slack webhook, API keys, Vercel tokens

---

## 5. Workflow de Seguranca

Arquivo: .github/workflows/security.yml
Jobs: dependency-audit, secret-scanning, env-files-check,
      actions-permissions-check, code-patterns-check, docker-scan
Triggers: push, pull_request, schedule (Monday 07:00 UTC)

---

## 6. Correcoes Aplicadas

- .env.example: DSN real do Sentry substituido por placeholder vazio
- config_manager.py: admin/admin substituido por senha aleatoria
  (secrets.token_urlsafe(16))

---

## 7. Configuracoes Recomendadas (Manual)

- Branch Protection: main (status checks obrigatorios)
- Secrets: DOCKER_PAT, VERCEL_TOKEN, SENTRY_AUTH_TOKEN, SLACK_WEBHOOK_URL
- Variables: API_URL, DOCKER_USER

---

## 8. Proximos Passos

1. Commit das mudancas de seguranca
2. Configure branch protection via GitHub Settings
3. Adicione .github/CODEOWNERS
4. Revise os alerts do CodeQL existentes
5. Execute workflow Security Checks (workflow_dispatch)
