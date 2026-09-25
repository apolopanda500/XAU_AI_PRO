# Decisões de produto e arquitetura — 2026-09-25

Data: **2026-09-25**
Estado: decididas pelo usuário. Este documento é a fonte da verdade para as escolhas abaixo.

## Decisões

| ID | Tema | Decisão |
| --- | --- | --- |
| A1 | Modelo de negócio | **Assinatura** (produto proprietário) |
| A2 | Escopo de ativos | **Totalmente multiativo, global** |
| A3 | Corretoras | **As top corretoras**: forex, índices, commodities, cripto e afins |
| A4 | Posicionamento | **Governança de execução com IA** (escolhido por recomendação, ver justificativa) |
| B1 | Token no Android | **Login por usuários** |
| B2 | Assinatura Android | **Grátis** |
| B3 | Assinatura Windows | **Grátis** |
| B4 | Código morto | **Limpeza segura**, mantendo o espaço limpo |
| B5 | CSS | **Consolidar** as folhas de override |
| C1 | Procedência dos 23.820 ticks | **São dados de teste** (confirmado pelo usuário) |
| C2 | Dependências vulneráveis | **Corrigir**, mantendo o projeto seguro |
| C3 | Repo Git órfão do Cline | **Apagar** |
| C4 | Vazamento de processos no pytest | **Corrigir** |
| C5 | Guarda de segredos | **Forma segura** (DPAPI) |
| D1 | Submódulos de `experiments/` | **Remover** |
| D2 | GitLab | **Melhor opção** a definir |

## Justificativa da recomendação de A4

Escolhi **governança de execução com IA** em vez de tentar competir em charting.

Motivo: a comparação com TradingView, NinjaTrader e Sierra Chart mostrou que competir em graphing é uma aposta perdida. TradingView tem 150.000+ scripts da comunidade, 100+ corretoras e mais de 20 anos de catálogo de dados. NinjaTrader e Sierra Chart têm backtesting de múltiplos anos em dados de tick. O XAU AI PRO não tem footprint, não tem order flow, não tem ecossistema de scripts públicos e o backtest ainda é paper-only.

Já **governança de risco auditável** é um espaço que nenhum dos quatro ocupa como produto: eles tratam controle de risco como responsabilidade do usuário. O XAU AI PRO já tem `risk_gate` com fail-closed, `kill switch`, `intent_log` idempotente, `reconciliation` e `audit_log`. Com A2/A3 (multiativo e global) aplicado a metal, isso vira "terminal de execução com governança auditável para operar capital em múltiplas contas e corretoras".

A alegação de "Mercado 10/10" não se sustenta e não deve ser usada em material de venda.

## Conflitos entre as decisões — precisam ser resolvidos

### Conflito 1: A1 (assinatura) vs B3 (assinatura Windows grátis)

**São mutuamente exclusivos.** A SignPath Foundation, único caminho viável para Authenticode gratuito, atende **somente projetos open source**. Não existe certificado Authenticode gratuito para produto proprietário.

Opções reais:

| Opção | Custo | Consequência |
| --- | --- | --- |
| A. Abrir o código sob licença OSS para acessar a SignPath | US$ 0 | Concede o código-fonte; conflita com A1 |
| B. Certificado de CA comercial | US$ 70–400/ano | Mantém proprietary, custo recorrente |
| C. Publicar sem assinar | US$ 0 | SmartScreen alerta o usuário; má reputação de download |

### Conflito 2: B2 (Android grátis) tem custo escondido

A **assinatura do APK é grátis** — o keystore é gerado localmente com `keytool`. O que custa é a **conta de desenvolvedor do Google Play: US$ 25 unique**. Sideload direto por APK é 100% grátis, sem conta, mas exige instalar "fontes desconhecidas" no aparelho e não chega a usuários de loja.

### Incoerência 3: A3 está majoritariamente coberto já

"Top corretoras globais" é essencialmente o que o **MT5** já entrega: qualquer corretora que suporte MT5 passa a estar acessível, com forex, índices, commodities e cripto. Somando os 4 adaptadores de exchange já existentes (Binance, Bybit, MEXC, OKX), falta pouco em cobertura.

O que falta não é adapter novo, é a **matriz de capabilities por corretora e por ativo** — declaring explicitamente o que cada uma suporta, em vez de prometer "todas as corretoras".

## Execução já realizada

| ID | Status | Resultado |
| --- | --- | --- |
| C3 | **Concluído** | 6,04 GB liberados; `C:\Users\Micro\.git` removido. Sem remote, sem worktree, árvore HEAD vazia. Disco foi de 0,75 GB para 8,97 GB. |
| D1 | **Concluído** | 3 submódulos removidos de `experiments/isolated` (mcp-servers, opentelemetry-js, tanstack-query). Eram gitlinks sem `.gitmodules`, impossíveis de inicializar. Diretórios preservados em disco e blindados no `.gitignore`. |
| C4 | **Concluído** | Vazamento reproduzido (4 processos, porta 9001 travada) e corrigido em três pontos: teardown do fixture `app`, handle do `Popen` em `app/mt5_gateway.py`, e fixture `autouse` de sessão em `tests/conftest.py`. Verificado: 267 passed, 0 órfãos, porta livre. |
| C2 | **Parcial** | `npm audit` de 6 (1 alta + 5 moderadas) para **0** no `develop`. Removido `react-router-dom` (dependência de produção sem nenhum import). Upgrade de vite 5→8, vitest 3→5, plugin-react 4→6. `manualChunks` migrado para a forma de função (Rolldown rejeita a forma de objeto). tsc limpo, 35 testes, build OK. **O alerta do Dependabot NÃO foi encerrado** — ver seção "Por que o alerta do Dependabot continua aberto". |
| C1 | **Parcial** | Procedência registrada como dado de teste no docstring de `app/market_store.py` e no handoff. **Lacuna aberta:** `market_ticks` não tem coluna de procedência e o fallback do gráfico não rotula a origem. |
| C5 | **Concluído** | `scripts/segredos_windows.ps1` criado. Senhas cifradas com DPAPI, ACL restrita a usuário/SYSTEM/Administradores, nada mais em `Temp`. Round-trip verificado: a senha recuperada reassinou o APK com digest de certificado idêntico. |

## O que A2 e A3 implicam em trabalho

Nenhuma das duas está implementada como "multiativo global" completo. O que existe hoje:

- 5 adaptadores (MT5 + Binance, Bybit, MEXC, OKX), com cliente e execução separados.
- 105 rotas no gateway, catálogo universal de quotes, candles, depth e trades.
- Matriz de capabilities já presente, mas sem a documentação pública por corretora/ativo.

Trabalho que A2/A3 exigem, ainda não feito:

1. Publicar a matriz de capabilities por corretora e por classe de ativo.
2. Garantir que cada ativo do catálogo tem depth, candles e trades reais, ou declara `unavailable` honestamente.
3. Decidir o que fazer com símbolos que a corretora não expõe — falhar explícito, nunca fallback silencioso.

## Por que o alerta do Dependabot continua aberto

O push para o GitHub continua respondendo "1 vulnerability on the default branch (1 moderate)", mesmo com `npm audit` em zero no `develop`.

Diagnóstico:

1. **O branch default do repositório é `main`, não `develop`.** Confirmado com `git remote show origin` → `HEAD branch: main`. Todos os commits desta sessão foram para `develop`.
2. `main` está **70 commits atrás** de `develop` e não tem nenhum commit exclusivo (`git rev-list --left-right --count main...develop` → `0 70`).
3. O `.github/dependabot.yml` monitora **seis ecossistemas**: `pip` (raiz), `npm` (`/backend`), `npm` (`/frontend`), `cargo` (`/core`), `cargo` (`/frontend/src-tauri`) e `github-actions`. O alerta pode estar em qualquer um deles, não necessariamente em npm.

O que **não** consegui verificar:

- O conteúdo do alerta #74. A URL retorna **404** sem autenticação e o token do `gh` CLI está inválido (`The token in default is invalid`). Precisa de `gh auth login -h github.com`.
- Os ecossistemas `pip`, `cargo` e `github-actions` não foram auditados. `cargo-audit` não está instalado e `pip list --outdated` não retornou dados confiáveis nesta sessão.

O que **foi** verificado: `npm audit` no `frontend` e no `backend`, ambos contra o advisory DB do GitHub. `backend` já estava em 0. `frontend` foi de 6 para 0, com typecheck, os 35 testes e o build verificados.

Encerrar o alerta exige saber qual ecossistema é. Sem `gh auth login` não dá para distinguir.

## Ordem sugerida

1. **B1 — login por usuários** no Android. Sem isso o APK não é produto. É o bloqueador número um. O backend (`backend/remote_auth.py`) já está pronto e agora tem 18 testes; falta expor as rotas e a tela de login.
2. Resolver o conflito A1/B3, porque a resposta muda a estratégia de distribuição no Windows.
3. Fazer `gh auth login` e auditar `pip`, `cargo` e `github-actions`, para fechar o alerta do Dependabot.
4. Publicar a matriz de capabilities (A3).
5. Corrigir a lacuna de procedência do gráfico (C1).
6. Decidir o papel de `main` e do GitLab (D2).
