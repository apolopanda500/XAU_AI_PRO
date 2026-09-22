# XAU AI PRO — Acompanhamento Oficial da Versão PC

**Data:** 21/09/2026  
**Versão de trabalho:** `1.2.3`  
**Fase atual:** validação técnica da versão PC/Windows  
**Regra permanente:** o diretório e o EA em `Experts` permanecem intocáveis.

---

## 1. Objetivo do produto

O **XAU AI PRO** é uma plataforma de trading e monitoramento em tempo real. Apesar do nome, não é exclusiva para ouro/XAU nem para uma única corretora.

Objetivo de produto:

- aplicação **multiativos**;
- aplicação **multicorretora**;
- integração principal atual via MetaTrader 5;
- conectores universais para mercados e corretoras homologadas;
- operação, monitoramento, auditoria, risco e suporte assistidos por IA;
- versão PC/Windows aprovada primeiro;
- versão Android somente após a aprovação operacional da versão PC.

A XM Global é o ambiente DEMO atualmente usado para validação, mas não define nem limita a compatibilidade do produto.

---

## 2. Princípios operacionais

1. **EA MT5 intocável:** o EA dentro de `Experts` é autoridade operacional e não deve ser editado neste ciclo.
2. **Sem ativo exclusivo:** os ativos disponíveis dependem da corretora, do conector, da conta e das regras de risco.
3. **Sem corretora exclusiva:** cada corretora/conector deve ser homologado separadamente.
4. **Automação governada:** o app deve automatizar monitoramento, sincronização, risco, auditoria, telemetria, alertas e suporte; a execução deve obedecer à política de risco.
5. **Dados reais:** em produção, indisponibilidade deve ser informada como indisponibilidade; não usar dados simulados como se fossem reais.
6. **Sem saques/transferências:** essa capacidade não faz parte do produto.
7. **IA como copiloto:** a IA analisa, explica, alerta e sugere; a autorização de execução é sempre determinada por regras e políticas verificáveis.

---

## 3. Arquitetura atual

```text
+------------------------------------------------------------------+
| XAU AI PRO Desktop (PC/Windows)                                  |
| React + Vite + Tauri v2                                          |
| Painéis, mercado, risco, posições, IA, alertas e conectividade   |
+----------------------------+-------------------------------------+
                             |
                             | HTTP local / WebSocket
                             v
+------------------------------------------------------------------+
| Gateway local                                                     |
| Python: FastAPI + compatibilidade com mt5_gateway                |
| Porta local 9001                                                  |
| Conta, símbolos, preços, posições, histórico, journal, risco     |
+----------------------------+-------------------------------------+
                             |
              +--------------+--------------+
              |                             |
              v                             v
+--------------------------+     +-------------------------------+
| MetaTrader 5 / EA        |     | Conectores universais          |
| Conta DEMO ou REAL       |     | MT5, MEXC, Binance e futuros   |
| Símbolos da corretora    |     | adaptadores homologados        |
+--------------------------+     +-------------------------------+

+------------------------------------------------------------------+
| Core Rust                                                         |
| Sessão MT5, heartbeat, WebSocket, fila e despacho de comandos    |
+------------------------------------------------------------------+
```

### Componentes principais

| Camada | Local principal | Responsabilidade |
|---|---|---|
| Desktop PC | `frontend/` + `frontend/src-tauri/` | Interface React, Tauri, notificações, build Windows |
| Core | `core/` | Sessão MT5, heartbeat, WebSocket, despacho e regras locais |
| Gateway | `backend/fastapi_gateway.py` e `backend/mt5_gateway.py` | API local, leitura MT5, contratos e proteções |
| Execução | `backend/*_execution.py` | Adaptadores MT5, Binance e MEXC |
| Risco | `backend/risk_gate.py` | Limites de volume, perda, exposição e posições |
| Auditoria | `backend/audit_log.py`, `backend/intent_log.py` | Registro sem segredos e reconciliação |
| Telemetria | `backend/watchdog.py`, `backend/guardian_engine.py` | Heartbeat, saúde, eventos e regras de proteção |
| Empacotamento | `*.spec`, `scripts/`, `installer/` | PyInstaller, Tauri, MSI, NSIS e instalador |
| EA | `Experts/` | Intocável neste ciclo |

---

## 4. Compatibilidade multicorretora e multiativos

### Corretoras/conectores

O produto deve trabalhar somente com conectores homologados, e não prometer compatibilidade universal sem teste.

| Tipo | Estado arquitetural |
|---|---|
| Corretoras MT5 | Compatibilidade pela instalação MT5 e pelos símbolos liberados pela conta/corretora |
| XM Global | Ambiente DEMO atual de validação |
| MEXC | Adaptador existente, execução bloqueada por padrão |
| Binance | Adaptador existente, execução bloqueada por padrão |
| Outros brokers/exchanges | Futuros adaptadores após homologação técnica, segurança e testes |

### Ativos

O app deve descobrir os símbolos do broker e normalizá-los internamente, respeitando diferenças como sufixos e contratos.

Exemplos de classes possíveis:

- Forex;
- metais;
- índices;
- commodities;
- energia;
- ações e CFDs, quando suportados;
- cripto spot;
- cripto futures, somente com política de margem e risco específica.

Para cada símbolo, o app deve respeitar os metadados fornecidos pelo conector/corretora:

- volume mínimo, máximo e step;
- `digits` e `point`;
- `trade_mode`;
- horário do mercado;
- spread;
- margem, alavancagem e permissões;
- moeda base e moeda de lucro.

---

## 5. Proteções atuais de execução

O sistema já possui uma base de proteção para execução DEMO e REAL.

### DEMO

O fluxo DEMO exige:

- `XAU_ENABLE_DEMO_ORDERS=1`;
- `confirm_demo=true`;
- conta identificada pelo MT5 como DEMO;
- terminal com negociação permitida;
- símbolo, lado, volume, SL e TP válidos;
- `order_check` antes do `order_send`.

### REAL

O fluxo REAL atualmente exige:

- `XAU_ENABLE_REAL_ORDERS=1`;
- arquivo `REAL_EMERGENCY_STOP` inexistente;
- `confirm_real=true`;
- `request_id` único;
- conta identificada pelo MT5 como REAL;
- negociação habilitada no terminal;
- símbolo, lado, volume, SL e TP válidos;
- `order_check` antes do `order_send`.

### Gateway universal

Uma solicitação universal de execução exige, adicionalmente:

```json
{
  "execute": true,
  "authorize_execution": true,
  "confirm_live": true
}
```

O kill switch universal bloqueia novas ordens quando ativo. Saques e transferências permanecem desabilitados.

> **Nota:** essas travas são necessárias, mas não constituem aprovação automática para uso comercial em conta REAL. Ainda faltam validações de persistência, risco contextual, reconciliação pós-ordem, instalação limpa e piloto controlado.

---

## 6. Trabalho executado nesta sessão

### 6.1 Correções aplicadas em infraestrutura de testes

Foram corrigidos dois testes que funcionavam apenas quando executados diretamente pelo Python, mas falhavam no `pytest` porque não inicializavam o contexto necessário.

| Arquivo | Correção |
|---|---|
| `tests/test_boot_backfill_integration.py` | Criada fixture isolada; asserts reutilizáveis para pytest e smoke direto; expectativa ajustada para terminal desconectado no MT5 fake |
| `tests/test_queue_gateway_integration.py` | Criada fixture isolada para gateway/fila/MT5 fake; suporte preservado para smoke direto; `handler.command` adicionado; rate limit isolado para evitar contaminação entre testes |

Nenhuma alteração foi feita em `Experts`.

### 6.2 Validações aprovadas

| Grupo | Resultado |
|---|---:|
| Boot/backfill via pytest | 4 aprovados |
| Smoke direto boot/backfill | aprovado |
| Risco, execução, reconciliação, conexões, auditoria e conta universal | 41 aprovados |
| Endpoints do gateway | 9 aprovados |
| Core Python, mercado, MCP, indicadores e sincronização MT5 | 23 aprovados |
| UI, alertas, telemetria, watchdog, guardian e fila | 54 aprovados |
| Vitest frontend | 24 aprovados |
| TypeScript | aprovado (`tsc --noEmit`) |
| Build Vite | aprovado |
| Smoke direto fila/gateway | aprovado |
| **Total de testes Python validados em lotes** | **131 aprovados** |

### 6.3 Artefato frontend validado

O build de produção Vite foi criado com sucesso em:

```text
frontend/dist/
```

O frontend usa React, Vite, Tauri, TanStack Query, Zustand, Lightweight Charts e notificações nativas Tauri.

---

## 7. Pendências para concluir a versão PC/Windows

### Gate A — Qualidade e versão

- [ ] Executar toda a suíte Python restante e consolidar o resultado completo.
- [ ] Executar `scripts/sync_version.py --check`.
- [ ] Unificar qualquer referência antiga de versão, especialmente documentos/configurações que ainda indiquem `1.2.0`.
- [ ] Executar `git diff --check`.
- [ ] Revisar `.gitignore` e separar fonte, artefatos, caches, logs, bancos locais e credenciais.

### Gate B — Core Rust

- [ ] `cargo test` em `core/`.
- [ ] `cargo clippy -- -D warnings` em `core/`.
- [ ] `cargo build --release` em `core/`.
- [ ] Copiar o binário aprovado para `frontend/src-tauri/core/`.
- [ ] Comparar SHA-256 do binário de origem e do recurso Tauri.

### Gate C — Gateway e desktop

- [ ] Empacotar gateway: `python -m PyInstaller --clean --noconfirm mt5-gateway.spec`.
- [ ] Validar existência e hash de `dist/mt5-gateway/mt5-gateway.exe`.
- [ ] Sincronizar bridge em `frontend/src-tauri/bridge/`.
- [ ] Empacotar launcher, se ainda fizer parte do instalador oficial.
- [ ] Executar `npm run tauri build`.
- [ ] Validar MSI e NSIS.
- [ ] Decidir e consolidar o papel do instalador Inno Setup para evitar duplicação de canais de release.

### Gate D — Instalação limpa

- [ ] Testar em VM ou máquina Windows limpa.
- [ ] Instalar o pacote oficial.
- [ ] Abrir sem MT5 e validar mensagens seguras.
- [ ] Abrir com MT5 DEMO e validar leitura de conta, símbolos, posições, cotações, histórico e journal.
- [ ] Validar reconexão de gateway/core/app.
- [ ] Validar kill switch e persistência após reinício.
- [ ] Validar desinstalação e política de retenção de dados.

### Gate E — Operação DEMO XM Global

- [ ] Confirmar classificação da conta como DEMO pelo `trade_mode` do MT5.
- [ ] Validar lista de símbolos e contratos específicos da XM Global.
- [ ] Validar atualizações em tempo real de preços, posições, histórico e journal.
- [ ] Validar ordem DEMO manual com lote mínimo, SL e TP.
- [ ] Validar `order_check`, ticket/deal e reconciliação de posição.
- [ ] Validar comportamento em reinício, conexão lenta, spread elevado e indisponibilidade de cotação.
- [ ] Registrar relatório do forward test DEMO.

### Gate F — Piloto REAL próprio controlado

Esta fase só começa após os Gates A até E serem aprovados.

- [ ] Conta REAL própria identificada corretamente pelo MT5.
- [ ] Capital de teste separado e previamente definido.
- [ ] Menor volume permitido pela corretora; começar com um ativo e uma posição por vez.
- [ ] SL e TP obrigatórios.
- [ ] Perda diária, exposição e quantidade de posições limitadas.
- [ ] Kill switch testado antes da sessão.
- [ ] Auditoria e reconciliação validadas após cada ordem.
- [ ] Testar rejeição, timeout, reconexão e recuperação sem duplicar ordem.
- [ ] Consolidar relatório de piloto antes de liberar para clientes.

---

## 8. Gaps técnicos para modo REAL comercial

Antes de liberar execução REAL automática para clientes, confirmar ou implementar:

- [ ] persistência de idempotência de `request_id` entre reinícios;
- [ ] auditoria completa antes e depois de cada tentativa de ordem;
- [ ] reconciliação automática de ticket, deal e posição;
- [ ] limites de risco efetivamente integrados ao fluxo REAL contextual;
- [ ] spread máximo por ativo/corretora;
- [ ] slippage máximo e métrica auditável;
- [ ] validação de mercado aberto e de horário de negociação;
- [ ] bloqueio por volatilidade/eventos relevantes, quando configurado;
- [ ] política de risco por classe de ativo;
- [ ] registro de corretora, conta, ativo e dispositivo autorizados;
- [ ] licenciamento/entitlement comercial;
- [ ] RBAC e trilha de auditoria para contas comerciais;
- [ ] mecanismo seguro de atualização e rollback.

---

## 9. Modelo de automação e IA

### Automação desejada

O sistema deve operar em tempo real com:

- inicialização e monitoramento automático do gateway;
- detecção de MT5, broker, conta, `trade_mode`, AutoTrading e símbolos;
- sincronização de conta, posições, histórico e journal;
- atualização de cotações e telemetria;
- reconexão e detecção de heartbeat degradado;
- alertas de spread, risco, conexão, eventos e divergências;
- auditoria e reconciliação contínuas;
- bloqueio automático de novas entradas diante de estado inseguro.

### Papel da IA

A IA deve funcionar como suporte operacional:

- explicar bloqueios e riscos;
- resumir estado de conta e exposição;
- analisar logs e telemetria;
- detectar anomalias;
- gerar relatórios;
- sugerir configuração e ações de redução de risco;
- oferecer assistência dentro do app.

Fluxo obrigatório:

```text
IA sugere ou explica
        ↓
Motor de risco determinístico valida
        ↓
Política de execução autoriza ou bloqueia
        ↓
Gateway executa somente se todos os gates passarem
        ↓
Auditoria + reconciliação + telemetria
```

---

## 10. Roadmap de lançamento

### Etapa 1 — PC/Windows

1. Concluir testes e builds.
2. Corrigir divergências de versão e higiene de repositório.
3. Gerar gateway, core, app Tauri, MSI e NSIS reproduzíveis.
4. Validar em instalação limpa.
5. Executar forward test DEMO XM Global.
6. Executar piloto REAL próprio, pequeno e controlado.
7. Definir licença, EULA, política de risco e suporte.
8. Somente então anunciar/vender/alugar a versão PC.

### Etapa 2 — Android

Iniciar somente depois da versão PC ser aprovada.

Escopo inicial recomendado para Android:

- dashboard remoto;
- alertas em tempo real;
- posições e histórico;
- risco e telemetria;
- suporte por IA;
- visualização de conectividade;
- kill switch e comandos autorizados.

O MT5/gateway/core permanecem no PC ou VPS. O Android deve ser cliente seguro, sem armazenar credenciais da corretora e sem substituir os controles do desktop.

---

## 11. Comandos de referência

### Python local do projeto

```powershell
C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO\.venv\Scripts\python.exe
```

### Frontend

```powershell
cd C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO\frontend
npm test
npx tsc --noEmit
npm run build
```

### Core Rust

```powershell
cd C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO\core
cargo test
cargo clippy -- -D warnings
cargo build --release
```

### Versão e release não destrutivo

```powershell
cd C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO
.venv\Scripts\python.exe scripts\sync_version.py --check
powershell -ExecutionPolicy Bypass -File scripts\validate_release.ps1
```

> O script `scripts/ciclo_limpo_123.py` remove artefatos de build. Só deve ser executado após preservação do trabalho local, revisão de Git e decisão explícita de iniciar o ciclo limpo.

---

## 12. Estado atual resumido

| Área | Estado em 21/09/2026 |
|---|---|
| Arquitetura PC | mapeada |
| Multiativos/multicorretora | direção de produto definida |
| EA em `Experts` | intocado |
| Testes Python por lotes | 131 aprovados |
| Frontend Vitest | 24 aprovados |
| TypeScript | aprovado |
| Build Vite | aprovado |
| Core Rust | pendente de validação neste ciclo |
| PyInstaller gateway | pendente |
| Tauri MSI/NSIS | pendente |
| Instalador/instalação limpa | pendente |
| DEMO XM Global em tempo real | pendente |
| Piloto REAL próprio | pendente |
| Lançamento comercial PC | não aprovado ainda |
| Android | posterior à aprovação da versão PC |
