# Handoff — XAU AI PRO

Data da última atualização: 2026-09-23
Projeto: `C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO`

## Objetivo e limites

- Preparar o app XAU AI PRO para estudo, paper/demo e operação assistida.
- Expert Advisors e arquivos MQL5 são intocáveis.
- Não criar, editar, mover, excluir, formatar, gerar ou sobrescrever `.mq4`, `.mq5`, `.mqh`, `.set` ou `MQL5/Experts`.
- Não ativar dinheiro real, saques, transferências ou credenciais.
- Manter `XAU_MCP_TRADING=0` e `XAU_ENABLE_EMERGENCY_RESUME=0`.
- Não copiar código proprietário; usar apenas APIs, documentação e implementações originais.

## Pesquisa realizada

Foram consultadas referências oficiais de:

- MetaTrader 5 Strategy Tester: backtesting, otimização, múltiplos ativos, spread e margem.
- TradingView: alertas, Pine Script, webhooks e análise visual.
- NinjaTrader: ordem flow, trade management, OCO, Strategy Analyzer e backtesting.
- Sierra Chart: simulação, replay, risco e conectividade de dados.
- QuantConnect/LEAN: pipeline pesquisa → backtest → paper/live, custos e métricas.
- Stripe Billing: planos, assinaturas, webhooks e Entitlements.

Padrões identificados foram traduzidos para módulos originais do XAU AI PRO. Nenhuma implementação proprietária foi copiada.

## Trabalho concluído

### OpenCode e Windows

- OpenCode validado na versão `1.18.32`.
- Plugin `@opencode-ai/plugin` alinhado na versão `1.18.32`.
- GitKraken CLI portable `v3.1.75` instalado em `C:\Users\Micro\AppData\Local\GitKrakenCLI\gk.exe` com SHA-256 validado.
- Caminho global do MCP GitKraken corrigido para `gk.exe`.
- GitKraken MCP permanece desabilitado até autenticação e teste.
- Hook automático do GitKraken foi neutralizado após ser detectado um processo storm de `gk ai hook run`; deve permanecer desabilitado até uma revisão explícita.
- Configuração nativa do projeto criada em `opencode.json`.
- Regras de segurança e validação criadas em `AGENTS.md`.
- Watcher ignora `.venv`, `node_modules`, builds, releases, experiments, `.env` e arquivos MQL5 protegidos.
- Permissões de edição bloqueiam `.mq4`, `.mq5`, `.mqh`, `.set` e `MQL5/Experts`.

### Assinaturas locais e Social Paper

- Planos locais `Free`, `Pro` e `Business` criados em `app/subscriptions.py`.
- Entitlements locais cobrem paper, analytics, IA, calendário, múltiplas contas, dados e Social Paper.
- Ativação é local e não configura cobrança, pagamentos ou execução real.
- Estratégias paper-only criadas em `app/social_paper.py`.
- Endpoints locais criados no FastAPI para planos e social.
- Painel React criado em `frontend/src/components/SubscriptionPanel.tsx`.
- Aba Tkinter de configurações recebeu ativador de planos.

### Backtest e paper

- Backtester original criado em `backend/backtest.py`.
- Consome candles reais fornecidos pelo MT5; não gera dados sintéticos.
- Calcula sinais RSI/MACD, stop, alvo, PnL, saldo final, win rate, profit factor, curva de equity e drawdown.
- Retorna `mode=historical_paper` e `live_execution=false`.
- Endpoint criado em `backend/fastapi_gateway.py`: `POST /api/backtest/run`.
- Botão “Executar paper” conectado no Strategy Tester React.
- Botão “Backtest paper” conectado no Strategy Tester Tkinter.
- O backtest nunca envia ordens.

### Risco, MCP e segurança

- `backend/risk_gate.py` agora limita drawdown, operações diárias, spread e notional quando informados.
- `emergency_resume` exige flags explícitas no MCP, FastAPI e gateway stdlib.
- `app/mcp_bridge.py` não reporta sucesso falso quando servidores MCP não estão habilitados.
- `XAU_ENABLE_EMERGENCY_RESUME=0` é o padrão operacional.
- `XAU_MCP_TRADING=0` é o padrão operacional.
- O gateway continua bloqueando saques e execução universal real.

### Estrutura e build

- `requirements-lock.txt` foi regenerado em formato pip válido.
- `pyproject.toml` foi alinhado às dependências principais.
- `Dockerfile` corrigido para copiar `rust-toolchain.toml` da raiz.
- `release_production.cmd` corrigido para o layout ONEDIR `dist\\XAU_AI_PRO\\XAU_AI_PRO.exe`.
- `README.md` foi atualizado para a versão e o fluxo de dependências atuais.
- Nenhum arquivo de EA aparece no diff do Git.

## Validações Executadas

- Python: `202 passed`.
- Testes direcionados de backtest, planos, social, MCP, gateway e capabilities: `52 passed` em uma etapa.
- Frontend Vitest: `24 passed`.
- TypeScript: `npx tsc --noEmit` passou.
- Frontend build: `npm run build` passou.
- Backend lint: `npm run lint` passou.
- Backend build: `npm run build` passou.
- Pylint direcionado: `10.00/10`.
- `opencode debug config` aceitou o schema.
- `opencode mcp list` mostrou `xau-trading` conectado e MCPs opcionais desabilitados.
- Gateway novo na porta `9001` foi iniciado após o encerramento do app antigo.
- `/api/health`, `/api/subscriptions/plans`, `/api/subscriptions/me`, `/api/social/strategies` e `/api/capabilities` responderam corretamente.
- Conta demo do MT5 e heartbeat do EA foram detectados pelo gateway; não foram enviadas ordens.

## Pendências

### Backtest

- `POST /api/backtest/run` ainda retorna `503` porque `gw._mt5_candles` falha neste processo.
- A conta/EA estão conectados, portanto o próximo passo é capturar a exceção original de `MetaTrader5.copy_rates` e corrigir a inicialização ou o timeframe.
- Depois do ajuste, executar novamente o backtest e validar que `source=mt5_gateway`, `mode=historical_paper` e `live_execution=false`.

### OpenCode e GitKraken

- Reiniciar o OpenCode para carregar definitivamente `opencode.json` e o plugin neutralizado.
- Confirmar que `Get-Process gk` permanece em zero.
- Executar `gk auth login` somente quando o usuário quiser ativar a integração GitKraken.
- Não reativar o hook automático até testar `gk ai hook run` isoladamente.
- Manter GitKraken MCP desabilitado até autenticação e teste de conexão.

### Paper/demo

- Fazer backtest com XAUUSD e timeframe M15 usando a conta demo.
- Executar forward test em paper/demo.
- Testar ordens Demo, stop/target, trailing, break-even, fechamento parcial e rejeições.
- Testar kill switch, emergency stop, auditoria, idempotência e reconciliação.
- Revisar volume, spread, perda diária, drawdown e número de posições.
- Não ativar `XAU_MCP_TRADING=1` nem ordens reais durante essa fase.

### Produto e assinatura

- A assinatura atual é local; Stripe Checkout, webhooks e cobrança real ainda não foram instalados.
- Se for necessário cobrar usuários, implementar servidor de backend, autenticação, Customer/Price IDs, webhooks idempotentes e Entitlements.
- Trading social/copy-trading está limitado a Social Paper; não existe copy trading real.
- Separar claramente estratégia, sinal, permissões e execução antes de qualquer distribuição social.

### Infraestrutura restante da auditoria

- CI ainda usa Node 20 em alguns workflows, enquanto dependências atuais exigem Node mais recente.
- O build de release e os gates de CI precisam ser alinhados antes de distribuição.
- `docker-compose.yml` referencia `core/config.json` que ainda precisa ser definido ou removido.
- Revisar o lock raiz sem `package.json` e o build Tauri separadamente do fluxo PyInstaller/Inno.
- Preservar as alterações existentes do working tree; não executar reset, checkout ou commit automático.

## Estado Git

- Não houve commit.
- O working tree já continha muitas alterações do usuário; elas foram preservadas.
- Novos arquivos principais: `AGENTS.md`, `opencode.json`, `app/subscriptions.py`, `app/social_paper.py`, `backend/backtest.py`, `frontend/src/components/SubscriptionPanel.tsx` e testes correspondentes.
- Confirmado: nenhum `.mq4`, `.mq5`, `.mqh` ou `MQL5/Experts` foi editado.

## Instrução para a próxima conversa

Leia este arquivo primeiro. Continue somente no app XAU AI PRO, mantenha os Expert Advisors intocáveis, opere em paper/demo, não habilite dinheiro real sem uma etapa posterior explícita e não copie código proprietário.
