# STATUS ATUAL DO PROJETO

## Estado medido em 13/11/2026 05:25 (versao PC 1.2.191)
- **Versao:** `1.2.191` nos 9 portadores de `scripts/sync_version.py`; `sync_version.py --check`
  = «Todos alinhados». `gateway_build = xau-ai-pro-1.2.191-universal-20261113`, medido no
  `dist/mt5-gateway/mt5-gateway.exe` pela bateria do artefacto.
- **Grafico da aba ROBO - causa real fechada:** o simbolo consultado era o **nome do modelo**
  (`MULTI_METALS`, do `MULTI_METALS.meta.json`), nao um par. `ListaModelos.escolher` gravava-o
  em `selectedSymbol` e em `/api/auto/config`; `parNaTela` devolvia-o tal e qual e o grafico pedia
  velas de `MULTI_METALS` - todas as fontes recusavam ("sem equivalente para este par"). Agora o
  card de classe nao escreve simbolo (troca so o periodo ou RECUSA com motivo) e a leitura filtra
  o nome de modelo em `parNaTela` e em `SeletorModelo`.
- **Prova de que o backend nunca aceitou o nome como ativo:** `classe_de('MULTI_METALS')=OUTROS`,
  `simbolo_valido('MULTI_METALS')=False`, `_tentativas_multi('MULTI_METALS','M5')=[]`; e o modelo
  de classe entra sozinho para o par: `_tentativas_multi('XAUUSD','M5')` -> `MULTI_METALS_M5`.
- **Prova da rota do grafico:** `_universal_candles('mt5','metals','XAUUSD')` -> `ok=True`,
  `count=10`, `source=mt5_gateway`, `fallback_publico=None`, ultima vela O 3.918,76 / H 3.921,40 /
  L 3.917,63 / C 3.919,43. O singular `'metal'` devolve as mesmas 10 velas; `MULTI_METALS` devolve
  `ok=False, count=0` - recusa com motivo, nunca dado falso.
- **Testes (medidos, 13/11):** vitest **83 ficheiros / 1019 testes verdes** (`VITEST_EXIT=0`),
  `tsc --noEmit` `TSC_EXIT=0`; `test_versao_consistente` **6 passed**;
  `test_ai_inference` **91 passed**; `test_candles_publicos_sem_conta` **16 passed**. Suite Python
  completa: **2 failed, 1529 passed, 2 skipped, 8 errors** - os 8 errors sao `tkinter` ausente no
  `.venv`, nao regressao.
- **Bateria do artefacto (gateway 1.2.191):** exit 0 - 5 rotas `401` sem token, `401` com token
  errado, `withdrawals_enabled=False`, `transfers_enabled=False`, ordem `execute=false` ->
  `stage=validated`. `bridge/mt5-gateway.exe` e `dist/mt5-gateway/mt5-gateway.exe` sao
  byte-identicos (`C42E18F9408A7AC4B281BA969BEE08577075D25ED923F3B485832BFE55308A8F`), e o NSIS
  empacota o `bridge` - logo o instalador leva o gateway certo.
- **Instaladores prontos, NAO instalados:** `dist/installers/XAU AI PRO_1.2.191_x64-setup.exe`
  (NSIS, 142 121 988 B, SHA256 `83553C5999E4AF1109D92310312B1469682F27B6A221E422C58B03207083B56E`)
  e `XAU AI PRO_1.2.191_x64_en-US.msi` (210 434 790 B). Roteiro do dono:
  [`INSTALAR_1_2_191_DONO.md`](./INSTALAR_1_2_191_DONO.md). O NSIS `1.2.183` construido antes
  (142 102 924 B) fica **substituido** por este e nao deve ser usado.
- **No ar:** o app instalado continua a **1.2.182** (arrancado 12/11 23:47:57). So muda depois de
  instalar o 1.2.191, e a pasta `bridge` deve ser apagada antes (AGENTS.md 7).
- **Conta (13/11 05:20):** MetaQuotes-Demo, 5 posicoes abertas todas com SL e TP, `ea=alive`,
  equity 12 746,21 / balance 12 755,27.
- **Documentacao de estado (limpeza de 13/11 05:33):** este ficheiro tinha o cabecalho
  `# STATUS ATUAL DO PROJETO` **duplicado** (linha 212) e o corpo inteiro repetido (as linhas
  254-388 eram identicas as 51-185, provado por comparacao antes de descartar). Agora ha **um**
  cabecalho, o bloco de 00:55 (1.2.183) desceu para `## HISTORICO` e o corpo aparece uma vez
  (e o banner de 25/10, que vinha colado ao bloco, tambem estava repetido no fim):
  24 752 -> 16 707 B. Nenhum bloco de estado foi perdido; a copia do antes esta em
  `Temp/STATUS_ATUAL.antes_dedup.md`.

---

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
| IA sobrescrevia ao voltar | painel remontava vazio e a sugestão automática rodava antes da leitura do motor → valores aplicados trocados | com limite guardado no motor, a sugestão **não roda**; campos mostram o que foi aplicado |
| Testes | — | **suite Python: 1561 passed, 2 skipped**; **vitest: 981 passed (81 arquivos)**; `tsc --noEmit` exit 0; artefato **exit 0** |
| App instalado | UI anterior (sem as duas correções) | 1.2.9 reconstruído e instalado; gateway novo no ar |

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



## Estado medido em 13/11/2026 02:05 (versao PC 1.2.191) - por ALFA

- **Versao:** `1.2.191` em `Docs/version.json` e nos 9 portadores de
  `scripts/sync_version.py`; `gateway_build = xau-ai-pro-1.2.191-universal-20261113`.
  A secao "00:55" abaixo fica como registro HISTORICO de 1.2.183 - nao foi reescrita.
- **Bundle congelado:** `dist/mt5-gateway` reconstruido (PyInstaller, 155 s, 3 498
  arquivos, 28 759 944 B, SHA256 `C42E18F9408A7AC4B281BA969BEE08577075D25ED923F3B485832BFE55308A8F`)
  e espelhado em `frontend/src-tauri/bridge`, que e o que o instalador empacota (nao o
  `dist`). `tests/test_artefato_congelado.py`: **8 passed** - recusa sem token, recusa
  com token errado, `withdrawals_enabled=False`, `transfers_enabled=False` e ordem
  `execute=false` em `stage=validated`.
- **Instalador construido, NAO instalado:** `dist/installers/XAU AI PRO_1.2.191_x64-setup.exe`
  (NSIS, 142 121 988 B) e `..._x64_en-US.msi` (210 434 790 B). O `bridge/mt5-gateway.exe`
  estagiado no `release` tem hash identico ao `dist` - o instalador levou o gateway certo.
  Instalar escreve em `%LOCALAPPDATA%\XAU AI PRO`, fora das raizes de escrita do agente:
  passo do dono, roteiro em `Docs/INSTALAR_1_2_191_DONO.md`.
- **Testes:** `test_ai_inference.py` **91 passed**, `test_versao_consistente.py` **6 passed**,
  `test_artefato_congelado.py` **8 passed**; suite Python inteira
  **1529 passed / 2 failed / 8 errors** - e os 10 pontos restantes sao TODOS
  `ModuleNotFoundError: No module named 'tkinter'` (P1.3633).
- **EA:** `#property version "1.391"` + `EA_VERSION_STRING "1.2.191"`, coerentes pela
  formula do teste (`1.2.191 -> 1.391`). Existem DUAS copias do EA (P1.3634): a do
  repositorio do EA e a embutida em `XAU_AI_PRO\MQL5\Experts\XAU_AI_PRO`, que e a que
  `test_versao_consistente.py` le.

---

## HISTORICO - blocos anteriores (o estado vigente esta no topo)

## Estado medido em 13/11/2026 00:55 (versao PC 1.2.183)
- **Versao:** `1.2.183` nos 8 manifestos; `gateway_build = xau-ai-pro-1.2.183-universal-20261113`.
- **Grafico da aba ROBO - causa real fechada:** o simbolo consultado era o **nome do modelo**
  (`MULTI_METALS`, do `MULTI_METALS.meta.json`), nao um par. `ListaModelos.escolher` gravava-o
  em `selectedSymbol` e em `/api/auto/config`; `parNaTela` devolvia-o tal e qual e o grafico pedia
  velas de `MULTI_METALS` - todas as fontes recusavam ("sem equivalente para este par"), e a tela
  dizia "Grafico indisponivel". Agora o card de classe nao escreve simbolo (troca so o periodo ou
  RECUSA com motivo) e a leitura filtra o nome de modelo em `parNaTela` e em `SeletorModelo`.
- **Prova de que o backend nunca aceitou o nome como ativo:** `classe_de('MULTI_METALS')=OUTROS`,
  `simbolo_valido('MULTI_METALS')=False`, `_tentativas_multi('MULTI_METALS','M5')=[]`; e o modelo
  de classe entra sozinho para o par: `_tentativas_multi('XAUUSD','M5')` -> `MULTI_METALS_M5`.
- **Prova da rota do grafico:** `_universal_candles('mt5','metals','XAUUSD')` -> `ok=True`,
  `count=10`, `source=mt5_gateway`, `fallback_publico=None`, ultima vela O 3.918,76 / H 3.921,40 /
  L 3.917,63 / C 3.919,43. O singular `'metal'` devolve as mesmas 10 velas; `MULTI_METALS` devolve
  `ok=False, count=0` - recusa com motivo, nunca dado falso.
- **Testes:** vitest **83 ficheiros / 1019 testes verdes** (`VITEST_EXIT=0`), `tsc --noEmit`
  `TSC_EXIT=0`, `vite build` exit 0. Bateria do artefacto (gateway 1.2.183): exit 0 - 5 rotas `401`
  sem token, `401` com token errado, sem saque/transferencia, ordem `execute=false` -> `validated`.
- **Instalador:** `XAU AI PRO_1.2.183_x64-setup.exe`, 142 102 924 B, SHA256
  `EEB57D996A9A5F9A47FC3EA1D29277BB9B9EF31CF536EE4E94594CFECC4D5AAD`; `XAU AI PRO.exe`
  13 998 080 B com FileVersion e ProductVersion `1.2.183`. **Nao instalado** - o instalador escreve
  fora das raizes permitidas do terminal, logo e acao do dono.
- **No ar:** o app instalado continua a **1.2.182** (arrancado 12/11 23:47:57), com a bridge
  anterior a 1.2.183. O grafico do app instalado so muda depois de instalar este NSIS.
- **Conta (snapshot do gateway, 13/11 00:5x):** 5 posicoes abertas, `ea=alive`, equity ~12.749.
- **Bundle MSI:** nao completou - `light.exe` escreveu `output.wixpdb` e nunca criou `output.msi`;
  a corrida foi terminada e o NSIS reconstruido com `--bundles nsis` (`TAURI_EXIT=0`), que e o
  entregavel.

### Instalacao 1.2.191 - concluida pelo CMD (13/11/2026)

Autorizada pelo DONO. Medido:

- App fechado (graceful -> force se preciso, 0 processos), bridge antiga apagada.
- `XAU AI PRO_1.2.191_x64-setup.exe` instalado /S; app declara FileVersion/ProductVersion **1.2.191**.
- `%LOCALAPPDATA%\XAU AI PRO\bridge\mt5-gateway.exe` SHA256 =
  `C42E18F9408A7AC4B281BA969BEE08577075D25ED923F3B485832BFE55308A8F`
  â€” gateway novo no aparelho (confere com INSTALAR_1_2_191_DONO.md).
- Bridge 484 MB; porcoes python intactas; MSI nao usado (o entregavel e o NSIS).
- App aberto pelo CMD; WS Online, EA no grafico (USDCAD 16385), 9002/9003/9011/9027 OPEN.
- Aba ROBO validada no instalado: par **USDSGD** (MT5), **3 sinais no grafico**,
  "Candles OHLC reais Â· MT5 Â· sinais do modelo", OHLC nao degenerada
  (Abr 1,2883/Max 1,28833/Min 1,28017/Fecha 1,28928668), nenhum "MULTI_METALS".
- TP/SL por posicao: nao verificado neste ciclo â€” nao ha posicoes abertas em
  USDSGD na hora da captura.
- Nenhum arquivo do repo foi commitado; so a instalacao no aparelho do dono.
