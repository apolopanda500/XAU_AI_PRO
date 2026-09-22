# XAU AI PRO — Estado do projeto e caminho para produção

Data: 15/09/2026
Versão: 1.2.0

## Estado atual

O projeto desktop usa React 18 + Vite + Tauri, com Core Rust separado e gateway local MT5 em Python/PyInstaller.

O EA MT5 foi preservado intocado. O app não realiza saques, transferências ou operações reais.

## Concluído

- App desktop Tauri v1.2.0 compilado.
- Instaladores MSI e NSIS gerados.
- Instalação antiga removida e nova instalação executada.
- Core Rust iniciado.
- Gateway MT5 iniciado.
- WebSocket Core nas portas 9002/9003.
- Gateway MT5 na porta 9001.
- Health local respondeu HTTP 200.
- Dados simulados permanecem bloqueados.
- Painel, Mercado, Robô, Histórico, Sistema, Estratégia e Configurações organizados.
- Mini gráfico real na aba Mercado usando cotações recebidas.
- Auto-refresh configurável pelo usuário.
- Proteção contra requisições sobrepostas no Painel e Mercado.
- Cotações WebSocket agrupadas por frame para evitar excesso de repaints.
- Canvas visual memoizado e renderização isolada.
- Scroll preservado durante atualizações.
- Barras de rolagem adaptadas ao tema escuro.
- Indicador global “Fonte de mercado / MT5 aguardando conexão” removido.
- Telemetria de CPU, RAM, disco, temperatura e GPU opcional.
- PowerShell da telemetria oculto.

## Testes aprovados

- `npx tsc --noEmit`: aprovado.
- `npm run build`: aprovado.
- `npm run tauri:build`: aprovado.
- `python -m py_compile backend/mt5_gateway.py`: aprovado.
- App instalado e iniciado sem janela azul observada.
- Core e gateway foram iniciados pelo app.

## Bloqueio atual encontrado

Foi criada uma rota protegida para execução demo em `/api/demo/order`, com intenção de exigir:

- variável local explícita de habilitação;
- confirmação demo;
- rejeição de conta real;
- volume máximo de 0,10;
- SL e TP obrigatórios;
- `order_check` antes de `order_send`.

Entretanto, após a instalação, o endpoint ainda respondeu o comportamento antigo `{"ok":true,"gateway":"post_aceito"}`. Isso indica que o processo iniciado pelo instalador ainda está usando o gateway antigo ou outro processo na porta 9001.

Nenhuma ordem foi enviada.

## Trabalho obrigatório antes de produção

1. Identificar exatamente qual executável/processo está ocupando a porta 9001.
2. Confirmar o caminho real do gateway iniciado pelo Tauri.
3. Garantir que o instalador inclua o gateway compilado com a rota demo correta.
4. Reiniciar sem processos antigos e testar `/api/demo/order` esperando rejeição segura quando desabilitado.
5. Validar conta MT5 com `trade_mode` DEMO.
6. Testar `order_check` com conta demo sem enviar ordem.
7. Criar tela de execução demo com confirmação manual e limites configuráveis.
8. Testar uma ordem mínima apenas depois da confirmação explícita do usuário.
9. Confirmar que conta REAL sempre retorna bloqueio.
10. Adicionar kill switch, limite de perda diária, limite de posições e auditoria.
11. Rodar endurance por horas/dias observando CPU, RAM, FPS, reconexão e logs.
12. Gerar novo instalador final após a correção do gateway.

## Critério de produção

O app só deve ser considerado produção quando o gateway instalado estiver comprovadamente sincronizado com o código, a conta real estiver recusada pela camada demo, o fluxo MT5 estiver auditado e o teste instalado não apresentar travamentos, processos duplicados ou dados simulados.

## Arquivos relevantes

- `backend/mt5_gateway.py`
- `mt5-gateway.spec`
- `frontend/src/hooks/useMarketWebSocket.ts`
- `frontend/src/components/tabs/MarketTab.tsx`
- `frontend/src/components/tabs/DashboardTab.tsx`
- `frontend/src/components/tabs/RobotTab.tsx`
- `frontend/src/hooks/useAppStore.ts`
- `frontend/src/theme/global.css`
- `frontend/src-tauri/src/main.rs`

## Regra de segurança mantida

Não alterar o EA. Não liberar conta real. Não enviar ordem enquanto a divergência entre o gateway compilado e o gateway instalado não estiver resolvida e validada.
