# Relatório de UI/UX e notas de produto — XAU AI PRO

Data: **2026-09-25**
Base: `develop` @ `777fc12` + 107 arquivos alterados não commitados
Método: **análise estática do código**. Nenhuma avaliação visual por usuário, nenhum teste de usabilidade, nenhum screenshot. Abaixo, "achado" significa algo verificável no repositório, não opinião sobre estética.

## 1. Achados com evidência

### 1.1 — 28 componentes `.tsx` não são importados por lugar nenhum

Verificado enumerando os 96 `.tsx` de `frontend/src/components` e procurando o nome do arquivo em **todos** os `.ts`/`.tsx` do projeto, excluindo a própria definição. Resultado: **28 órfãos confirmados**.

```
AccountAuthorizationPanel      AccountSwitcher          MiniMarketPanel
AccountConnectionManager       AdvancedSettingsPanel   MiningRig
AppIdentity                    AssetSelectionPanel     RealAccessPanel
BrokerConnectionGuide          BrokerOnboardingPanel   RealCommandPanel
MiniInfoWidget                 RecentTradesPanel       RobotTableCommandsUniversal
SettingsActionsPanel           SettingsConnectivityActions
SystemActionsPanel             UniversalAccountSwitcher UniversalLiveTerminalSafe
charts/QuantumChart            tabs/DashboardHomeClean  tabs/DashboardTab
tabs/DashboardUniversalTab     tabs/RobotWorkspaceTab   tabs/SystemMonitorTab
trading/AutoButton             trading/CommandPanel
```

Por que importa: código morto que continua sendo corrigido, revisado e pode reintroduzir bugs de segurança sem estar em produção. `RealAccessPanel` e `RealCommandPanel` são o caso mais delicado — pelos nomes, tocam em acesso real e comandos; manter código morto nessa área é exatamente o tipo de superfície que deveria ser eliminada primeiro.

**Não removi nada.** Excluir 28 arquivos exige confirmar que não há import dinâmico, uso em teste ou referência por string. É trabalho de meio dia e precisa de decisão de produto.

### 1.2 — Famílias de componentes paralelos sem variante canônica

Existem tríos e quads do mesmo conceito:

| Conceito | Variantes |
| --- | --- |
| Terminal universal | `UniversalLiveTerminal`, `UniversalLiveTerminalLatest`, `UniversalLiveTerminalSafe` |
| Portfolio home | `PortfolioHomeClean`, `PortfolioHomeSafe`, `PortfolioTab` |
| Dashboard | `DashboardTab`, `DashboardUniversalTab`, `DashboardHomeClean` |
| Monitor do sistema | `SystemMonitorTab`, `SystemMonitorUniversalTab`, `SystemHealthOnly` |
| Conectividade | `UniversalConnectivityPanel`, `UniversalConnectivityPanelLight` |

Os sufixos `Latest`, `Clean` e `Safe` sugerem substituições incrementais onde a anterior ficou para trás. Sem um marcador de "canônico", qualquer correção pode ser aplicada na variante errada e não aparecer no produto.

### 1.3 — Estilo por camadas de override, não por design system

`frontend/src/theme` tem **25 arquivos CSS, 138,8 KB**, dos quais **22 são carregados em `main.tsx`**. Os nomes revelam o método:

```
robot-terminal-compact.css   robot-terminal-clean.css   robot-terminal-dedup.css
robot-no-warnings.css        robot-clean-messages.css   dashboard-clean.css
history-compact.css          portfolio-balance.css
```

Cinco folhas existem só para apagar/compactar algo que uma folha anterior deixou. `global.css` tem 70,7 KB e concentra a maior parte das regras. Isso é CSS como remendo, não como sistema: aumenta o custo de qualquer mudança visual e torna regressões difíceis de rastrear.

### 1.4 — Não há teste de componente para a maior parte da UI

`vitest` roda **35 testes em 5 arquivos**. Só dois são de componente: `MarketTab.test.tsx` (6 testes) e testes de `lib/` (`api`, `marketApi`, `riskCalculations`, `performanceMetrics`). As 28 abas e 60+ componentes de UI **não têm cobertura de renderização**. O crate Rust do Tauri também não tem testes unitários — `cargo test --locked` roda 0 casos.

Consequência: a suíte verde de 267 + 35 + 38 testes **não protege a interface**. Uma tab pode quebrar silenciosamente.

### 1.5 — Camadas de boot e autenticação sem fonte única

`auth/Splash`, `auth/LockScreen`, `auth/Onboarding`, `AuthGate`, `SystemStartupSync`, `AppIdentity` e o bootstrap em `useCoreBootstrap` formam uma cadeia de inicialização distribuída. O log de runtime mostra que o gateway é autenticado **antes** do Core subir, o que é a ordem correta. Mas a ordem estar certa hoje é resultado de teste manual, não de teste automatizado.

### 1.6 — Log de runtime escreve fora do diretório instalado

O app instalado em `%LOCALAPPDATA%\XAU_AI_PRO_TAURI_TEST` escreveu em `%LOCALAPPDATA%\XAU_AI_PRO\logs\core_bootstrap.log`. O caminho do log não acompanha o diretório de instalação. Com duas instalações simultâneas, os logs se misturam — o que prejudica justamente o diagnóstico forense que o produto promete.

## 2. Pontos positivos verificados

- **Estados de erro e vazio** tratados na aba Mercado (`MarketTab` tem teste dedicado).
- **Distinção visual entre paper, demo e real bloqueado** implementada, coerente com a trava de risco.
- **Encerramento gracioso funciona**: `processos filhos encerrados com a UI` no log, sem processo órfão e sem porta presa.
- **Autenticação do gateway é exigida de fato**: `/health`, `/api/boot` e o Core responderam **401** sem token.
- **IPC autenticado** entre UI, gateway e Core com token por sessão.

## 3. Recomendações em ordem de retorno

| # | Ação | Esforço | Risco se não feito |
| --- | --- | --- | --- |
| 1 | Eliminar os 28 componentes órfãos, começando por `RealAccessPanel` e `RealCommandPanel` | médio | superfície de código morto em área sensível |
| 2 | Declarar uma variante canônica por família da 1.2 e apagar as outras | baixo | correções aplicadas na variante errada |
| 3 | Consolidar as 5 folhas de "apagar" em `global.css` e reduzir o número de imports | médio | custo crescente de manutenção visual |
| 4 | Adicionar teste de renderização para cada tab | alto | regressão de UI sem detecção |
| 5 | Fazer o caminho do log derivar do diretório de instalação | baixo | diagnóstico impossible com 2 instalações |
| 6 | Guardar o token Android fora do APK | médio | credencial exposta no pacote |

Nenhuma dessas ações foi executada. Este relatório é diagnóstico.

## 4. Notas de produto

**Posicionamento defensável.** Terminal de execução com governança de risco para metal e múltiplas corretoras, com paper/demo e dinheiro real travado por design. É um nicho real e o `risk_gate` + `intent_log` + `reconciliation` + `audit_log` formam um conjunto que os concorrentes de gráfico não vendem.

**Posicionamento não defensável.** "Mercado 10/10", "o melhor app de trading", qualquer comparação direta com TradingView, NinjaTrader ou Sierra Chart em gráfico, backtest ou community. O detalhamento está em `Docs/BENCHMARK_TRADING_APPS_2026.md`.

**Decisões que o produto ainda precisa tomar**

1. **Preço.** Nenhum plano foi definido apesar de `SubscriptionPanel.tsx` existir. Assinatura, compra única ou open source? Isso bloqueia qualquer plano de distribuição.
2. **Distribuição Android.** O APK é `aarch64` e assinado com certificado de teste. Google Play exige assinatura de release guardada com segurança e política de privacidade. Nada disso existe.
3. **Público-alvo.** O foco em XAU/metals aparece na configuração, mas a matriz de capabilities é multiativo. Aprovar um ou o outro evita construir os dois pela metade.
4. **Conta de corretora.** O produto fala em MT5 e em 4 exchanges cripto. Verificar qual é o caminho principal evita suporte duplicado.
5. **Token Android.** É o bloqueador técnico número um do Android e não tem desenho de solução ainda.

**Ordem sugerida de produto**

1. Fechar o token Android — sem isso o APK não é produto.
2. Remover código morto e fixar variantes canônicas — reduz superfície e custo de mudança.
3. Assinatura de release Android + política de privacidade.
4. Definir preço e decidir open source.
5. Só então ampliar data de mercado e backtest.
