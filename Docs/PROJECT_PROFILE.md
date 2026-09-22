# XAU AI PRO — Perfil do projeto

## Identificação

- Desenvolvedor e proprietário: Henrique de Carvalho
- Contato: +55 (21) 98315-8911
- E-mail: rickjax123@gmail.com
- Aplicativo: XAU AI PRO
- Versão de trabalho: 1.2.0

## Arquitetura

1. **EA MT5** — executa a estratégia dentro do MetaTrader 5.
2. **Gateway local** — lê conta, modo DEMO/REAL, cotações, posições, ordens, histórico, Journal e heartbeat.
3. **Aplicativo Quantum** — painel, Robô, inventário, testador, configurações e monitoramento.

## Segurança operacional

- Conta DEMO e conta REAL são classificadas pelo `trade_mode` real do MT5.
- Ordens DEMO exigem confirmação do Gateway e AutoTrading permitido.
- Ordens REAL permanecem bloqueadas por padrão.
- O aplicativo não armazena senha, PIN ou chave de API.
- Valores exibidos devem vir do MT5, Gateway, EA ou sensores reais; sem dados simulados.

## Requisitos

- MetaTrader 5 aberto e conectado.
- EA compilado sem erros ou avisos.
- Gateway local ativo na porta 9001.
- Conta identificada pelo MT5.
- AutoTrading ativado somente durante testes DEMO autorizados.
- Para produção: validação fora da amostra, auditoria, logs e aprovação explícita.
