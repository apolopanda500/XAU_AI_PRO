# XAU AI PRO

[![CI](https://github.com/apolopanda500/XAU_AI_PRO/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/apolopanda500/XAU_AI_PRO/actions/workflows/ci.yml)
[![Security Checks](https://github.com/apolopanda500/XAU_AI_PRO/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/apolopanda500/XAU_AI_PRO/actions/workflows/security.yml)
[![Pylint](https://github.com/apolopanda500/XAU_AI_PRO/actions/workflows/pylint.yml/badge.svg?branch=main)](https://github.com/apolopanda500/XAU_AI_PRO/actions/workflows/pylint.yml)
[![Rust](https://github.com/apolopanda500/XAU_AI_PRO/actions/workflows/rust.yml/badge.svg?branch=main)](https://github.com/apolopanda500/XAU_AI_PRO/actions/workflows/rust.yml)
[![Validação e Empacotamento](https://github.com/apolopanda500/XAU_AI_PRO/actions/workflows/deploy.yml/badge.svg?branch=main)](https://github.com/apolopanda500/XAU_AI_PRO/actions/workflows/deploy.yml)

**Versão:** `1.2.9` · **Página:** <https://apolopanda500.github.io/XAU_AI_PRO/> · **Plataforma:** Windows

Plataforma de operação para MetaTrader 5 e múltiplas corretoras: gateway local em
Python, interface desktop em React/TypeScript (Tauri), núcleo em Rust, aplicação
legada em Tkinter e Expert Advisor em MQL5.

> **Aviso de risco.** Trading envolve risco de perda. Nada aqui é promessa de
> lucro. Valide qualquer estratégia primeiro em backtest e conta demo. O módulo
> *Subgraph* é somente leitura e não envia ordens.

---

## O que é

Três caminhos independentes operam a mesma conta. O dono escolhe qual usar.

```
MOTOR -> IA -> decide ativo, timeframe e limites -> opera   (backend Python)
EA    -> IA -> decide sinal                             -> opera   (MT5)
MESA  -> você -> monta a ordem                          -> opera   (gráfico)
```

Não existe confirmação por ordem. A decisão é da IA ou do dono, conforme o
caminho escolhido; a responsabilidade de operar é sempre do dono.

## Componentes

| Pasta | Responsabilidade |
|---|---|
| `backend/` | gateway local, adaptadores de corretora, risco, auditoria, fila, MCP de trading |
| `frontend/` | interface React/TypeScript empacotada por Tauri |
| `core/` | componentes Rust |
| `MQL5/Experts/XAU_AI_PRO/` | Expert Advisor, compilado no MetaEditor |
| `app/` | interface Tkinter legada, memória e configuração |
| `tests/` | suíte Python do gateway e da lógica de aplicação |
| `scripts/` | build, instalador, preflight, auditorias e ferramentas de prova |
| `Docs/` | decisões, levantamentos e o estado medido de cada ciclo |
| `mcp/` | catálogo interno de servidores MCP |

O mapa detalhado está em [`Docs/ARCHITECTURE.md`](Docs/ARCHITECTURE.md) e o índice
completo de documentos em [`Docs/INDICE.md`](Docs/INDICE.md).

## Requisitos

| Item | Versão |
|---|---|
| Windows | 10/11 (x64) |
| Python | 3.11 |
| Node.js | 22 |
| Rust | stable (`rust-toolchain.toml`) |
| MetaTrader 5 | terminal oficial, para o EA e para os dados de mercado |

## Começar

```powershell
git clone https://github.com/apolopanda500/XAU_AI_PRO.git
Set-Location XAU_AI_PRO

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt

# interface desktop legada (Tkinter)
.\.venv\Scripts\python.exe app\main.py
```

Aplicação empacotada: `XAU_AI_PRO.cmd` ou `Run_XAU_AI_PRO.bat`. O instalador é
gerado por `installer\build_installer.cmd` e produz `installer\XAU_AI_PRO_Setup.exe`,
instalando em `MQL5\Files\XAU_AI_PRO` sem privilégios de administrador.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ci.txt
.\.venv\Scripts\python.exe -m pytest -q tests
```

O CI executa, em cada push para `main`/`develop` e em cada pull request:

| Workflow | O que faz |
|---|---|
| [`ci.yml`](.github/workflows/ci.yml) | varredura de segredos (gitleaks), Rust (`fmt`/`check`/`test`/`clippy`), build do frontend |
| [`security.yml`](.github/workflows/security.yml) | análise de segurança e CodeQL |
| [`pylint.yml`](.github/workflows/pylint.yml) | lint de Python |
| [`rust.yml`](.github/workflows/rust.yml) | verificação do núcleo Rust |
| [`deploy.yml`](.github/workflows/deploy.yml) | suíte Python e empacotamento do bundle |

## Expert Advisor

O EA vive em `MQL5/Experts/XAU_AI_PRO/`. A compilação é manual, no MetaEditor,
sobre `XAU_AI_PRO.mqproj`; o binário `.ex5` não é versionado. O contrato entre o
EA e o gateway está em [`Docs/EA_APP_CONTRACT.md`](Docs/EA_APP_CONTRACT.md).

Regras de operação real, nesta ordem: validação completa em **demo**, forward
test aprovado, endurance test e autorização explícita do dono. Toda ordem exige
`confirm=true` e `request_id` idempotente, e passa por `risk_gate`, `intent_log`
e `audit_log`.

## Segurança

- Nenhum saque, transferência ou movimentação de fundos para fora da corretora —
  em nenhum adaptador, rota, cliente ou tela. Há teste que reprova se aparecer.
- O gateway é *fail-closed*: sem token de sessão, recusa tudo com `401`.
- Tokens, senhas e DSNs não são versionados; use `.env` local e os segredos do
  repositório/CI.
- Para reportar uma vulnerabilidade, siga [`SECURITY.md`](SECURITY.md).
- Termos de uso em [`EULA.txt`](EULA.txt) e privacidade em
  [`PRIVACIDADE.txt`](PRIVACIDADE.txt).

## Publicações

O projeto é local-first. Não existe deploy hospedado do produto: os jobs de
Vercel/Nitro foram removidos em 04/10/2026. Os deployments `dev` que aparecem no
histórico do GitHub são anteriores a essa remoção e **permanecem como registro
histórico** — eles não representam o estado atual.

As únicas publicações automáticas hoje são os artefatos de CI e o site desta
página, em GitHub Pages.

## Documentação

| Documento | Conteúdo |
|---|---|
| [`Docs/README.md`](Docs/README.md) | visão geral e desenvolvimento local |
| [`Docs/INDICE.md`](Docs/INDICE.md) | índice de todos os ciclos e decisões |
| [`Docs/ARCHITECTURE.md`](Docs/ARCHITECTURE.md) | arquitetura e fronteiras entre módulos |
| [`Docs/STATUS_ATUAL.md`](Docs/STATUS_ATUAL.md) | estado medido mais recente |
| [`Docs/MATRIZ_CAPABILIDADES.md`](Docs/MATRIZ_CAPABILIDADES.md) | capacidades por camada |
| [`AGENTS.md`](AGENTS.md) | regras de trabalho para agentes e contribuidores |
| [`CHANGELOG.md`](CHANGELOG.md) | histórico de versões |

## Licença

Copyright 2026, APOLOPANDA500. Todos os direitos reservados. O uso é regido por
[`EULA.txt`](EULA.txt); este repositório não é software de código aberto.
