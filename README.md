# XAU AI PRO v1.2.0

Plataforma desktop para acompanhamento do MetaTrader 5, análise de mercado e treinamento local de modelos. A interface atual usa **Python/Tkinter** e o robô opera no **MetaTrader 5** por meio do EA MQL5 distribuído com o projeto.

> Trading envolve risco. Valide qualquer estratégia primeiro em backtest e conta demo. O módulo **Subgraph** é somente leitura e não envia ordens.

## Recursos

- Painel para mercado, posições, robô, treino e configurações.
- Conexão opcional com MetaTrader 5 oficial.
- EA MQL5, arquivos `.mq5`, `.mqh` e presets `.set` incluídos no instalador.
- Subgraph de mercado: indicadores, correlação de retornos e classificação de regime.
- Integrações configuráveis: GitHub, Sentry, Slack, CDN de modelos e MCP.
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

## Instalador

O arquivo `installer\installer.iss` detecta a pasta de dados do MT5 e instala em `MQL5\Files\XAU_AI_PRO`, sem privilégios de administrador.

```powershell
Set-Location "C:\caminho\para\XAU_AI_PRO\installer"
.\build_installer.cmd
```

O resultado é `installer\XAU_AI_PRO_Setup.exe`.

## Segurança operacional

- Não versione tokens, senhas ou DSNs.
- Use conta demo até haver histórico suficiente de backtest e forward test.
- Revise limites de lote, spread, perda diária e drawdown antes de habilitar o robô.