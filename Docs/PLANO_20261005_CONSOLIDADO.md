# PLANO CONSOLIDADO — 05/10/2026

Tudo que o dono pediu nesta rodada, em ordem de execução, com a MEDIDA que
justifica cada item. Onde o número diverge do código, o código ganha — e o
número aqui está corrigido.

---

## 1. AUDITORIA DOS "FIXOS" — o instalador está limpo?

**Pergunta:** o app sai com conta logada, credencial ou código preso, para que
qualquer usuárioInstale e configure sozinho?

**Resposta medida: SIM, está limpo.** Evidência:

| O que foi procurado | Onde | Resultado |
|---|---|---|
| `.env` com credencial | `dist/`, `Temp/cargo-target/release/bundle/`, `%LOCALAPPDATA%\XAU AI PRO\` | **nenhum arquivo** |
| `.env` no instalador | `mt5-gateway.spec` → `datas` | só `Docs/version.json`, `Python/models/**/*`, dados do MetaTrader5 |
| `.env` no git | `git ls-files` | só os 5 `.example`; os reais **não** estão versionados |
| Conta MT5 como configuração | `Config.mqh`, `ExecutionEngine.mqh`, `asset_registry.py`, `mt5_gateway.py` | o número `391773676` aparece **só em comentário de medição**, nunca em código executado |
| Caminho do terminal MT5 | `_ensure_mt5()` | **não** há caminho fixo: exige `terminal64.exe` já rodando e chama `initialize()` na sessão do usuário |
| Ativo presumido | `useAppStore.ts:288` | `selectedSymbol: ''` — vazio, sem par padrão |
| Login/senha em claro | `%APPDATA%\XAU AI PRO\connections.dpapi.json` | **nada** de login, e-mail ou senha; o arquivo tem 1242 bytes e é cifrado por DPAPI |
| Token de sessão | Tauri injeta por sessão | o `.env` não vence o token; sem token o gateway responde **401** (fail-closed correto) |

**O que NÃO é fixo e não pode virar:** `broker_registry.py` (é o catálogo),
`universal_contracts.py` (`Literal` = o que é suportado) e as tabelas de
mapeamento. AGENTS.md §3 autoriza os três explicitamente.

**Risco residual honesto:** o rótulo da conexão é `broker:market:nome do
usuário` e hoje aparece o nome de quem configurou (`Henrique Carvalho @
XMGlobal-MT5 14`). Isso fica em `%APPDATA%` do próprio usuário, criado em
tempo de execução — **não viaja no instalador**. Em máquina nova o arquivo não
existe. Ainda assim, o rótulo é o primeiro campo visível da tela de contas e
não deve ser um valor herdado de outra máquina.

---

## 2. HISTÓRICO — as recargas "não carregam": CAUSA RAIZ MEDIDA

Não é defeito de leitura. É **filtro**.

**MEDIDO na conta 391773676 (`history_deals_get`, 3650 dias):**

```
total de deals: 5
por tipo: {'BALANCE': 2, 'CREDIT': 1, 'BUY': 1, 'SELL': 1}

04/10 23:12  SELL     entry=1 val=  2.01 vol=0.01 sym='BTCUSD' comment='[tp 86584.30]'
04/10 22:46  BUY      entry=0 val=  0.00 vol=0.01 sym='BTCUSD' comment=''
04/10 18:53  CREDIT   entry=0 val=  5.62 vol=0.0  sym=''      comment='Credit-In-100%-$100-NewClients'
04/10 18:53  BALANCE  entry=0 val=  5.52 vol=0.0  sym=''      comment='CD-AST-PIC 265376085'
04/10 18:53  BALANCE  entry=0 val=  0.10 vol=0.0  sym=''      comment='EXP05-AST-PIC 265376085'
```

**Todos os 5 são de 04/10.** A aba abria com período **"Hoje"** (05/10), que
vira `start = meia-noite de hoje` no gateway → **zero deals** → as DUAS
tabelas vazias. O dono viu "as recargas não carregam"; elas estavam no MT5, no
gateway e no histórico, só que fora da janela pedida.

**Correção:** período padrão passa a **30 dias** (`days = '30'`). O seletor
continua com "Hoje" e com "Tudo".

**E as formas, medidas:** o comentário da XM é **código interno**
(`CD-AST-PIC 265376085`, `EXP05-AST-PIC`), não "Deposit via PIX". A
`formaMovimentacao` devolve `nao informada` para esses — que é a resposta
honesta. O código bruto aparece na coluna de descrição, e é a única verdade
disponível.

---

## 3. O QUE VAI MUDAR, E COMO SE PROVA

### 3.1 Histórico — fidelidade MT5
- [ ] Período padrão 30 dias (causa raiz acima).
- [ ] Colunas de custo que **existem no dado e estavam escondidas**: comissão,
      swap, e `IN`/`OUT`. MEDIDO: o gateway já manda `commission`, `swap`,
      `fee` e `entry`, e a tabela só mostrava o PnL somado.
- [ ] Resultado = `profit + comissão + swap`, com as três colunas visíveis —
      para que a soma seja conferível e não uma caixa-preta.
- [ ] Movimentações: mostrar **tipo do deal do MT5** (BALANCE/CREDIT/CHARGE/
      COMMISSION/BONUS) junto do rótulo em português.
- [ ] Ticket e ordem na linha, para o operador bater o número com o MT5.
- [ ] Colspan do estado vazio corrigido ao novo número de colunas.

### 3.2 Calendário
- [ ] Bandeiras maiores e mais vivas (hoje 15px, esmaecidas na linha da tabela).
- [ ] Colorir: impacto, dia da semana, categorias.
- [ ] **Navegação de dia funcionando** — "as páginas seguintes e anteriores
      estão vazias". Causa a investigar: a semana seguinte só tem horários
      ESTIMADOS, e o filtro por país/impacto pode estar zerando tudo.
- [ ] Fonte e números ~1 ponto maiores na tabela.

### 3.3 Robô — página única
- [ ] Remover **"Ativo e Período"** e **"Acompanhar modelos"**.
- [ ] Restar: operação automática completa (com modelos e o liga/desliga), o
      **gráfico no meio** no estilo XM, e embaixo o **MiniTerminal ao vivo** e as
      **operações abertas**.
- [ ] Referência visual: `my.xm.com/pt/symbol-info/BTCUSD`.

### 3.4 Configurações — contas e sessões
- [ ] Diagnóstico do que trava hoje em salvar/sincronizar, medido.
- [ ] Salvar deve ser **um caminho só**, sem depender de descobrir três campos.
- [ ] Sincronizar precisa dizer o que sincronizou e o que não.

### 3.5 Robô
- [ ] Nada de fixo: o app abre sem par, sem conta e sem corretora, e o dono
      configura.

---

## 4. ORDEM DE VALIDAÇÃO

Uma por uma, e o número medido a cada etapa:

1. `npx tsc --noEmit`
2. `npx vitest run` (frontend)
3. `pytest -q tests`
4. `pytest -q tests/test_mql5_compila.py` (MetaEditor de verdade)
5. `scripts\preflight.py --etapa app-rodando`
6. `scripts\build_app.bat`
7. `scripts\conferir_bundle_gateway.py`
8. Desinstalar, instalar o NSIS, abrir pelo atalho, medir processos e portas.

**Base verde no início desta rodada:** 1118 Python · 342 frontend (25 arquivos)
· `tsc` limpo · MQL5 2 · preflight ok (1 aviso de arquivos pendentes).

---

## 5. O QUE NÃO SERÁ FEITO, E POR QUÊ

- **Não** vou inventar a "forma" do depósito a partir de `CD-AST-PIC`. O código
  é interno da XM e não está documentado; chutar seria pior que dizer
  "não informada".
- **Não** vou criar seção nova sem dado. Se a seção não tem consumidor real,
  não entra (AGENTS.md §9).
- **Não** mexo nas regras de saque/transferência: `withdrawals_enabled` e
  `transfers` permanecem `False` (AGENTS.md §2).