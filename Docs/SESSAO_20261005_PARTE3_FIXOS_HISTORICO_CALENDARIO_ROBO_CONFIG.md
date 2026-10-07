# SESSÃO 05/10/2026 — PARTE 3: FIXOS, HISTÓRICO, CALENDÁRIO, ROBÔ, CONFIGURAÇÕES

Documento de trabalho. Sem data e sem hora de propósito: as regras valem para
sempre, os números não.

---

## 1. OS "FIXOS" — AUDITORIA COM MEDIDA

Pergunta do dono: *"quando o app foi realmente lançado com a versão final do
instalador tem que estar livres de fixos, nada de contas logadas ou códigos
presos, tudo de forma padrão para ser configurado por qualquer usuário"*.

**Resposta: SIM, o instalador está limpo.**

| O que | Onde foi procurado | Resultado |
|---|---|---|
| `.env` com credencial | `dist/`, `Temp/.../bundle/`, `%LOCALAPPDATA%\XAU AI PRO\` | **nenhum arquivo** |
| `.env` no instalador | `mt5-gateway.spec` → `datas` | só `Docs/version.json`, `Python/models/**/*`, dados do MetaTrader5 |
| `.env` no git | `git ls-files` | só os 5 `.example` |
| Conta MT5 como configuração | `Config.mqh`, `ExecutionEngine.mqh`, `asset_registry.py`, `mt5_gateway.py` | `391773676` aparece **só em comentário de medição** |
| Caminho do terminal MT5 | `_ensure_mt5()` | **não existe**: exige `terminal64.exe` rodando e usa `initialize()` |
| Ativo presumido | `useAppStore.ts:288` | `selectedSymbol: ''` |
| Login/senha em claro | `%APPDATA%\XAU AI PRO\connections.dpapi.json` | **nada**; 1242 bytes, cifrado por DPAPI |
| Token de sessão | Tauri injeta por sessão | `.env` não vence o token; sem token o gateway dá **401** (fail-closed) |

**O que continua não sendo "fixo" e é proibido virar:** `broker_registry.py`
(catálogo), `universal_contracts.py` (`Literal` = o que é suportado) e tabelas de
mapeamento. AGENTS.md §3 autoriza os três.

---

## 2. HISTÓRICO — AS RECARGAS "NÃO CARREGAM": CAUSA RAIZ

**MEDIDO** com `history_deals_get` na conta 391773676 (3650 dias):

```
total de deals: 5
por tipo: {'BALANCE': 2, 'CREDIT': 1, 'BUY': 1, 'SELL': 1}

04/10 23:12  SELL     entry=1 val=  2.01 vol=0.01 sym='BTCUSD' comment='[tp 86584.30]'
04/10 22:46  BUY      entry=0 val=  0.00 vol=0.01 sym='BTCUSD' comment=''
04/10 18:53  CREDIT   entry=0 val=  5.62 vol=0.0  sym=''  comment='Credit-In-100%-$100-NewClients'
04/10 18:53  BALANCE  entry=0 val=  5.52 vol=0.0  sym=''  comment='CD-AST-PIC 265376085'
04/10 18:53  BALANCE  entry=0 val=  0.10 vol=0.0  sym=''  comment='EXP05-AST-PIC 265376085'
```

**Todos de 04/10.** A aba abria com período **"Hoje"** (05/10) → `start =
meia-noite de hoje` → **zero deals** → as duas tabelas vazias.

**Correção:** período padrão **30 dias**. "Hoje" e "Tudo" continuam na lista.

**E a "forma" do depósito, medida:** o comentário da XM é **código interno**
(`CD-AST-PIC 265376085`), não "Deposit via PIX". A função devolve
`não informada` — resposta honesta. O código bruto aparece na coluna de
descrição e agora também o **tipo do deal do MT5** (BALANCE/CREDIT/CREDIT…).

---

## 3. O QUE MUDOU, POR ARQUIVO

### `frontend/src/components/tabs/HistoryTab.tsx`
- Período padrão 30 dias.
- Faixa de dia (MT5) e linha com **só a hora**; a data completa fica no `title`.
- Colunas novas: **Volume · S/L · T/P · Comissão · Swap · Resultado**.
- Movimentações: coluna **Forma**, **tipo do deal** e `title` com ticket+forma.

### `frontend/src/lib/historico.ts`
- `formaMovimentacao()` — PIX, cartão, transferência, cripto, boleto, cheque,
  bônus, comissão, correios. **Nunca inventa**: texto desconhecido → `nao
  informada`.
- `Deal` ganhou `type`, `ticket`, `entry`, `commission`, `swap`, `fee`, `sl`,
  `tp`, `sl_price`, `tp_price` — todos presentes no payload do gateway.

### `frontend/src/hooks/useEconomicData.ts`
- Mapa moeda→país de 8 para **18 entradas**. **NZD e ALL caíam em bandeira
  branca** 🏳 — meia dúzia de eventos sem bandeira. Medido no feed: ALL, AUD,
  CNY, JPY, EUR, NZD, GBP, CAD, USD, CHF.

### `frontend/src/components/tabs/EconomicCalendarTab.tsx` + `traduzirEvento.ts`
- Tradução em 3 camadas, com marcação `en` quando o dicionário não cobre.
- **Sete abas de dia SEMPRE** (antes só os dias com evento).
- Cor: dia com alto impacto, linha por impacto, hoje marcado.
- Detalhe alinhado (`dl` com rótulo de largura fixa) e **a descrição do evento
  aparece** — ela era mapeada e descartada.
- Faixa de bandeiras por país, gerada da semana visível.

### `frontend/src/components/RobotTabs.tsx` + `OperacaoAutomatica.tsx` + `SeletorModelo.tsx`
- Saiu o bloco **"Ativo e Período"** (4 blocos → 3).
- **Modelo** foi para dentro da operação automática.
- O par é **lido** no painel e **escolhido** na barra inferior.

### `frontend/src/components/ConnectionSettings.tsx`
- Botão de salvar **não morre mais**: as pendências são listadas.
- Corretora e mercado **nunca travam** (o `disabled={busy}` contradizia o
  comentário do próprio arquivo).
- Mercado nasce escolhido.
- Sessão do terminal lida em texto: detectada ou não.

### `backend/mt5_gateway.py`
- `_lado_de_deal` passou a recusar **booleano**: `True == 1` em Python, e um
  `type: true` virava **SELL** na tela.

---

## 4. NÚMEROS DESTA RODADA

| Etapa | Antes | Depois |
|---|---|---|
| Python | 1112 | **1118** (+6, `test_lado_de_deal.py`) |
| Frontend | 342 (25 arq.) | **374** (26 arq.) |
| `tsc` | limpo | limpo |
| MQL5 | 2 passed | 2 passed |
| Preflight | 1 aviso | 2 avisos (disco 7,68 GB · 88 arquivos no git) |

Bundle: NSIS **219,4 MB** e MSI **339,4 MB**. `conferir_bundle_gateway.py`: OK.
Instalado e aberto pelo atalho: gateway, app e core no ar; **9001, 9002, 9003
respondendo**; `terminal64` intacto.

---

## 5. O QUE NÃO FOI FEITO, E POR QUÊ

- **Não** chutei a "forma" do depósito a partir de `CD-AST-PIC`. O código é
  interno da XM e não está documentado. Preferi "não informada" ao invênt.
- **Não** criei seção sem dado. `Era o que o dono pediu?` — não nesta rodada.
- **Não** mexi em saque/transferência: `withdrawals_enabled` e `transfers`
  seguem `False` (AGENTS.md §2).
- **Não** commitei nada. 88 arquivos pendentes, incluindo 394 linhas novas em
  `tests/` e o plano deste ciclo.

## 6. PERGUNTAS PARA O DONO

1. A forma do depósito/ saque na XM é o **código interno** (`CD-AST-PIC`).
   Você sabe o que ele quer dizer? Se souber, entra no dicionário; se não,
   continua "não informada" e o código bruto fica visível.
2. O rótulo das conexões MT5 hoje mostra o **nome de quem configurou**
   (`Henrique Carvalho @ XMGlobal-MT5 14`). Quer que o app proponha um rótulo
   neutro, tipo "Sessão MT5 · metals", em vez do nome do terminal?
3. Quer que eu organize os 88 arquivos pendentes em commits separados?