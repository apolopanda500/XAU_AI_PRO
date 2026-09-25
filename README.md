# XAU AI PRO v1.2.3

Plataforma desktop para acompanhamento do MetaTrader 5, análise de mercado e treinamento local de modelos. A interface atual usa **Python/Tkinter** e o robô opera no **MetaTrader 5** por meio do EA MQL5 distribuído com o projeto.

> Trading envolve risco. Valide qualquer estratégia primeiro em backtest e conta demo. O módulo **Subgraph** é somente leitura e não envia ordens.

## Recursos

- Painel para mercado, posições, robô, treino e configurações.
- Conexão opcional com MetaTrader 5 oficial.
- EA MQL5, arquivos `.mq5`, `.mqh` e presets `.set` incluídos no instalador.
- Subgraph de mercado: indicadores, correlação de retornos e classificação de regime.
- Integrações configuráveis: GitHub, Sentry, Slack, CDN de modelos e MCP.
- Planos locais Free, Pro e Business com entitlements e ativação sem cobrança.
- Social Paper para compartilhar estratégias somente em paper/demo.
- Atualizações via GitHub Releases e instalador Inno Setup.

## Desenvolvimento local

```powershell
Set-Location "C:\caminho\para\XAU_AI_PRO"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe app\main.py
```

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests
```

## CrewAI AMP / A2A

The CrewAI deployment exposes the analyst as an A2A server agent. After
redeploying, use the following URLs in AMP or another A2A client:

- Agent Card: `https://<deployment-host>/.well-known/agent-card.json`
- JSON-RPC endpoint: `https://<deployment-host>/a2a`

The reproducible Python environment is defined by `requirements-lock.txt`; redeploy from the repository and configure deployment environment variables in the host platform. Do not commit provider keys or tokens.

## Instalador

O arquivo `installer\installer.iss` detecta a pasta de dados do MT5 e instala em `MQL5\Files\XAU_AI_PRO`, sem privilégios de administrador.

```powershell
Set-Location "C:\caminho\para\XAU_AI_PRO\installer"
.\build_installer.cmd
```

O resultado do fluxo PyInstaller/Inno é `dist\XAU_AI_PRO_Setup_<versao>.exe`.

> Para builds atuais, o spec `launcher.spec` usa **onedir**: o executavel fica em
> `dist\XAU_AI_PRO\XAU_AI_PRO.exe`, com dependencias na mesma pasta. O Inno
> produz `dist\XAU_AI_PRO_Setup_<versao>.exe`. O instalador Tauri (NSIS/MSI)
> e um fluxo separado, com gateway Python e Core Rust; nao confundir os dois
> artefatos nem concluir que um scan do primeiro valida o segundo.
> Nenhum build esta aprovado para operar dinheiro real ou para distribuicao
> publica sem testes DEMO, verificacao de assinatura, hashes e scan por artefato.

## Segurança operacional

- Não versione tokens, senhas ou DSNs.

---

## Nova Stack 2026 (em migração)

O projeto está sendo modernizado para a stack 2026:

- **Core Backend**: Rust (axum/tokio) — performance extrema
- **Frontend**: React + TypeScript + Tauri — nativo, leve
- **Execução**: MQL5 EA (mantido como executor real)

Veja `docs/ARCHITECTURE.md` para detalhes.

- Use conta demo até haver histórico suficiente de backtest e forward test.
- Revise limites de lote, spread, perda diária e drawdown antes de habilitar o robô.