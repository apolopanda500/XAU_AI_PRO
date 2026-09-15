# XAU AI PRO — Handoff da sessão

## Estado final

- Versão mantida: 1.2.0.
- EA/MQL5 preservado; não foi alterado nesta entrega final.
- Instalação antiga removida pelo desinstalador oficial.
- Novo instalador NSIS gerado e instalado.
- Aplicação aberta após a instalação.
- Smoke test final: 1 UI, 1 `xau-ai-pro-core.exe` e 1 `mt5-gateway.exe`.
- Core e bridge iniciam sem janela de console.

## Correções principais do app

- Painel, Mercado, Robô, Histórico, Calendário, Estratégia e Configuração receberam melhorias de dados reais, estados de erro e operação manual.
- Histórico passou a consultar deals reais do MT5 e exportar CSV.
- Calendário bloqueia dados simulados, normaliza eventos reais e possui copiloto de análise sem ordens.
- Estratégia identifica manifesto de modelos e não exibe backtest fictício.
- Configuração possui teste MT5, PIN, perfis locais de contas sem senhas, botão de sair/bloquear e permissões operacionais explícitas.
- Robô mostra conta MT5, recursos locais, temperatura CPU quando o Windows expõe sensor e GPU opcional apenas para monitoramento.
- Campos visuais seguem o tema e não exibem fundos brancos indevidos.
- Rodapé incorreto `v0.1.0 • Rust Core + Tauri` foi substituído por `XAU AI PRO · Operação manual segura`.

## Segurança operacional

- O app não implementa saque ou transferência.
- O app não envia ordens automáticas nesta interface.
- O EA continua sendo autoridade operacional no MT5.
- Chaves de IA permanecem no backend; não são gravadas no frontend.
- Perfis de contas guardam apenas nome, login e servidor localmente.

## Build e instalação

- Frontend Vite compilado durante o build Tauri.
- Rust release compilado.
- Instaladores gerados:
  - `frontend/src-tauri/target/release/bundle/nsis/XAU AI PRO_1.2.0_x64-setup.exe`
  - `frontend/src-tauri/target/release/bundle/msi/XAU AI PRO_1.2.0_x64_en-US.msi`
- Corrigida a idempotência do Core: se as portas 9002/9003 já estiverem ativas, o bootstrap não cria outro Core.

## Limites honestos

- FPS de 60–120 depende do hardware e ainda precisa de medição específica no computador do usuário.
- Temperatura pode aparecer como indisponível quando o driver/sensor WMI não expõe o valor.
- O endpoint remoto de IA pode ficar indisponível; nesse caso a interface não inventa resposta.
- O Strategy Tester oficial continua sendo o MT5 até existir um endpoint de backtest integrado e validado.
