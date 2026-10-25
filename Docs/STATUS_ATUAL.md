# STATUS ATUAL DO PROJETO

**Data:** 25/10/2026
**Versão:** 1.2.9
**Status:** catálogo do MT5 **classificado pela hierarquia** (o ouro deixou de
ser `other`), gráfico servido **pela corretora**, conexões com escolha explícita
de conta, build 1.2.9 **instalado e no ar**. Pendências são **ação do dono**
(ver ABERTO).

---

## LEIA PRIMEIRO

**→ [`Docs/CONVERSA_20261023_CATALOGO_CLASSIFICADO_GRAFICO_MT5_E_128.md`](CONVERSA_20261023_CATALOGO_CLASSIFICADO_GRAFICO_MT5_E_128.md)**

Diz o que mudou, o que foi medido e o que ficou aberto. Este arquivo é o resumo.

---

## OS NÚMEROS (medidos em 23/10/2026)

| | |
|---|---|
| `pytest -q tests` | **1535 passed, 9 skipped** (268,72 s) |
| `tests/test_classificacao_catalogo.py` | **12 passed** |
| `tests/test_identidade_gateway_build.py` | **5 passed** |
| `tests/test_mql5_compila.py` | **2 passed** (MetaEditor invocado) |
| `tests/test_trading_mcp.py` | **24 passed** (inclui 4 novos: auth header) |
| `vitest run` | **979 passed** (81 arquivos) |
| `tsc --noEmit` | **exit 0** |
| `/api/universal/assets` no artefato | `XAUUSD=metal`, `EURUSD=forex` |
| gráfico no app 1.2.9 | **"Candles OHLC reais · MT5"** — não mais `yahoo` |
| instalador | `release\1.2.9\XAU AI PRO_1.2.9_x64-setup.exe` · 233,5 MB · NSIS `/S` **exit 0** |
| SHA256 do setup | `492943829738EFE1763234841981AB9AE0B1CBCD710BB0E2F51FB9D1FBCA67A7` |
| ponte instalada vs build | **IGUAIS por hash** (`66B416BD…17462`) |
| app no ar | app 1.2.9 · gateway 9011 · core 9002/9003 |
| disco livre após build+instala | **7,9 GB** |

Os 9 `skip` são os já documentados (CI Linux onde o MetaEditor não existe,
`PAINEL` vazio por decisão do dono). Não mascaram erro.

---

## O QUE FOI FEITO NO CICLO DE 25/10 (risco não salvava)

| item | antes (medido) | agora (medido) |
|---|---|---|
| "Aplicar limites ao motor" sem lote/banca/ATR | `ok: False` — *"defina no painel ... banca, risco por operacao (%), ATR..."*; campos voltavam vazios ao trocar de aba | **`ok: True`** — `configurar` julga só os campos **declarados** |
| Causa | `configurar` chamava `copia.valido()`, que responde "o motor PODE operar?" e exige o conjunto completo | completude é exigida só em `ligar()` (`/api/auto/start`), como já dizia o comentário do próprio painel |
| Prova negativa | — | `test_ligar_continua_exigindo_o_conjunto_completo`; SL/TP sem lote continua recusado (`test_pedido_sem_lote_ainda_recusado`) |
| Faixas declaradas | confiança 150 passava em alguns caminhos; `banca=0,5` não era julgado | cada campo tem faixa própria; valor fora dela **não entra** (pedido inteiro é recusado) |
| Gateway no ar | `.exe` anterior (recusava o Aplicar) | reconstruído, hash idêntico `dist`/instalado/`src-tauri`; `/health` 401 sem token |
| Testes | — | **suite inteira: 1561 passed, 2 skipped**; artefato **exit 0** |

---

## O QUE FOI FEITO NO CICLO DE 25/10 (exposição do motor)

| item | antes (medido) | agora (medido) |
|---|---|---|
| `max_exposure_pct` (risk_gate) | **5.0** — `exposure_pct` é `volume/capacidade*100` (capacidade 0,5 lote) → travava em **0,025 lote** | **100.0** — 100 = capacidade cheia; erros de unidade corrigidos |
| Síntoma real | motor respondia "exposição atingiu o limite de 5.0%" para sempre com 2–3 posições mínimas | exposição de 6% (3×0,01) passa; só bloqueia acima de 100% |
| Prova negativa | teste `exposure_pct: 5` "reprovava" por falta de `spread`/`notional` (§6) | teste agora exige spread/notional e usa `RiskLimits(max_exposure_pct=5)` explícito |
| Gateway no ar | `mt5-gateway.exe` 1.2.9 antigo (5%) | reconstruído, hash idêntico em `dist`/`instalado`/`src-tauri`; `/health` 401 sem token |
| Testes | — | `risk_gate`+`rejection`+`auto_engine`+`contrato`+`simulation` **183 passed**; gateway **79 passed**; artefato **exit 0** |

> Próximo bloqueio previsto: 3 posições abertas do EA × `max_posicoes = 2` do motor
> → o motor vai recusar "já há 3 posições (max 2)". Ação do dono: aumentar
> `Máximo de posições` para ≥ 4 **ou** fechar posições.

---

## O QUE FOI FEITO NO CICLO DE 23/10

| item | antes (medido) | agora (medido) |
|---|---|---|
| Classe do ouro no catálogo | `asset_class="other"` (`Metals\XAUUSD`) | **`metal`** |
| Causa | raiz comparada em minúsculo contra mapa em maiúsculo → **mapa morto**; `Metals` ausente | comparação sem caixa + raízes `Metals`/`Indices`/`Bonds`/`Energies`/`Shares` |
| Desempate do `Derivatives` | só o 2º nível (`Cash` → `cfd`) | **caminho inteiro** (`Cash Indices` → `index`) |
| Palpite por palavra | sem a `description` da corretora | `description` entra depois da hierarquia |
| Gráfico do par | Yahoo **4.025,00** (MT5 servia 4.016,46) | **MT5 4.022,28** |
| Mercado do motor | herdava o do escopo (`forex`) | derivado da **ficha do ativo** (`metals`) |
| Escolher a conta | não existia com todas as conexões ativas | botão **"Usar esta conta"** + chip **"Em uso"** |
| Nome da conexão | invadia a coluna CORRETORA | `table-layout: fixed` + quebra |
| "Casas decimais" | slider com **0 leitores** | removido (slider + campo do store) e documentado |
| Identidade do build | `1.2.4` escrito à mão em `main.rs` e `main.tsx` | derivada de `Docs/version.json` (`build.rs` + `version.ts`) |
| Versão do EA | `#property 1.240`, `EA_VERSION_STRING 1.2.4` | **1.2.9** (`#property version "1.290"`, `EA_VERSION_STRING "1.2.9"`, log MT5 confirma) |
| Gate de versão | **vermelho desde 1.2.5** | verde |

---

## PASSOS DA SESSÃO (para retomar)

1. Corrigir a identidade do build → `build.rs` + `XAU_GATEWAY_BUILD` +
   `version.ts`; 5 travas.
2. Bump/build/instalação 1.2.6 e 1.2.7 (tela preta resolvida, bootstrap
   provado: bridge antes do Core, core na versão esperada).
3. Par único na tela (`lib/parNaTela.ts`) — cabeçalho, barra inferior e gráfico
   passam a mostrar o mesmo par.
4. "Ativar" invisível na coluna AÇÕES → CSS; depois medido que **não havia**
   ação de escolher conta com tudo ativo → "Usar esta conta".
5. Abrir o app: **gráfico em Yahoo** com MT5 servindo candles → medir
   `asset_class` via artefato (`dist`→instalado) → achar o mapa morto.
6. Corrigir a classificação, criar `test_classificacao_catalogo.py`, medir
   `XAUUSD=metal`.
7. Remover "Casas decimais" (0 consumidores) + trava de fonte sem comentário.
8. Subir versão para 1.2.8, propagar ao EA, recompilar, build NSIS, instalar
   limpo, conferir por hash.
9. Reler as abas: **Carteira, Histórico, Calendário, Sistema, Risco,
   Operações e Configuração→Segurança/Plano/Confiança** continuam **não
   revisadas** neste ciclo.

---

## ABERTO (ação do dono, não do ciclo)

1. **~~Reanexar o EA no gráfico~~** ✅ **RESOLVIDO 25/10/2026** — EA em execução loga `[VERSION] v1.2.9 | build 2026.10.23` em múltiplos gráficos (XAUUSD,M5/H1, USDJPY,H1, USDCNH,H1, USDSEK,H1). Fonte: `#property version "1.290"` + `EA_VERSION_STRING "1.2.9"`.

2. **Credencial de conta real**: quando existir, `XAU_ACCOUNT_KIND=real`.
   Hoje a conta é `MetaQuotes-Demo` e o script de prontidão reprova nesse item.

3. **MCP de trading e o token de sessão**: token aleatório por execução (Tauri injeta); o do `.env` devolve **401** (fail-closed correto). Expor degrada a segurança — decisão do dono.

4. **Modelos**: 0 de 40 com edge medido acima do mínimo. O AUTO liga e não
   opera sem modelo. Baixar `min_edge` é proibido.

5. **Instalador**: MSI falha nesta máquina (`light.exe`); NSIS é o que funciona.

6. **Backup da instalação anterior**: `Temp\instalacao_anterior_20261022`
   (949 MB) — apagar depois de confirmar o app novo no ar?

7. **Conexão XMGlobal antiga** segue gravada; apagar é decisão do dono.

8. **Fechamento espontâneo do app** em sessão longa: medido em 10/10, sem log.

9. **Git**: ✅ **COMMITADO + PUSH** (25/10/2026, commit `7ce7043`) — bump 1.2.9, `build.rs`, `parNaTela`, `asset_registry`, testes MCP auth, `global.css`, `.mq5`/`.mqh`.

---

**Um documento antigo neste `Docs/` não está desatualizado por estar no fim da
lista — e sim por ser de um ciclo anterior. O `command` vence o número; o
documento mais recente manda.** Ver
`CONVERSA_20261023_CATALOGO_CLASSIFICADO_GRAFICO_MT5_E_128.md`.

