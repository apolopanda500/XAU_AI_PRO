# XAU AI PRO — registro de trabalho de 15/09/2026

## Escopo e regras preservadas

- Foco no app desktop React + Vite + Tauri, versão 1.2.0.
- EA MT5 mantido intocável.
- Sem dados simulados em produção.
- Sem saques, transferências ou comandos de ordem habilitados pelo app.
- MT5 permanece como fonte real de conta, posições, histórico e cotações.
- Conexão do MT5 não é iniciada automaticamente pelo app.

## Correções e melhorias consolidadas

1. Remoção do calendário da navegação principal para reduzir peso e manter foco operacional.
2. Gateway MT5 somente leitura, com estado real e erros explícitos.
3. Correção do endpoint de cotações do Painel.
4. Descoberta de símbolos reais via `/api/symbols`, sem inventar ativos.
5. Telemetria real da máquina: CPU, memória, disco, temperatura quando disponível e GPU opcional.
6. PowerShell oculto na telemetria para impedir janelas azuis ao iniciar.
7. Aba Robô reorganizada, com conexão, estado da conta e mini-terminal somente leitura.
8. Proteção contra deslocamento automático do scroll durante atualizações.
9. Configurações persistentes para autoatualização do Painel, Mercado e Histórico.
10. Intervalos de atualização configuráveis pelo usuário, com limites mínimos e máximos.
11. Histórico automático desligado por padrão para evitar consultas desnecessárias.
12. Mini gráfico real na aba Mercado, usando somente as últimas leituras recebidas do MT5.
13. Mini gráfico sem candles ou preços inventados; mostra mensagem enquanto não houver duas leituras reais.
14. Remoção do indicador global “FONTE DE MERCADO / MT5 aguardando conexão” que aparecia em todas as abas.
15. Otimização de renderização: componentes visuais memoizados, isolamento `contain: layout paint`, scroll contido e canvas com pausa fora da área visível.
16. Limite do gráfico local a 60 leituras para evitar crescimento de memória.

## Validações realizadas

- TypeScript: aprovado com `npx tsc --noEmit`.
- Build Vite de produção: aprovado.
- Build Tauri release: aprovado.
- Pacotes gerados:
  - `frontend/src-tauri/target/release/bundle/msi/XAU AI PRO_1.2.0_x64_en-US.msi`
  - `frontend/src-tauri/target/release/bundle/nsis/XAU AI PRO_1.2.0_x64-setup.exe`

## Observação de produção

O build foi concluído com sucesso. A validação final de cotações depende de o MT5 estar aberto, autorizado e com os símbolos disponíveis. Quando a fonte não estiver conectada, o app deve mostrar estado indisponível, nunca preencher dados fictícios.

## Próximo checklist após instalação

- Abrir uma única instância do XAU AI PRO.
- Confirmar que não há janela azul do PowerShell.
- Confirmar que o app não abre o MT5 sozinho.
- Abrir Mercado e verificar cotações reais.
- Abrir Robô e verificar estado de conexão.
- Confirmar mini gráfico após duas leituras reais.
- Confirmar Painel, Histórico e Sistema sem travas ou saltos de scroll.
