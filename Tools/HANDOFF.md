# HANDOFF — estado medido do terminal

> Este arquivo e o **ponto de entrada para quem assume o terminal**: um agente novo,
> o dono depois de reiniciar o PC, ou o proximo turno do ALFA.
> Nada aqui e suposto: cada numero foi medido com comando e a data/hora esta na
> propria linha. Se um numero divergir do que o comando medir agora, **o comando vence**.
>
> Ultima medicao: **13/11/2026 00:33 local** (terminal em `2026-11-13T05:10:12Z`).

---

## 1. Conta e terminal

| Item | Medido |
|---|---|
| Servidor | `MetaQuotes-Demo` (MetaQuotes Ltd.) |
| Login | `113568614` — Henrique Carvalho |
| Tipo | **demo**, hedging, `read_only=false` |
| Balance / Equity | `12 777,11` / `12 777,13` USD |
| Margem usada / livre | `22,12` / `12 755,01` USD |
| Lucro flutuante | `+0,02` USD |
| Conexao | `synchronized`, ping ~`213,7 ms`, ultima autorizacao `2026-11-12T20:32:59Z` |
| Build do terminal | `6316`, x64, `experts_trade_allowed=true`, `mcp_trade_allowed=true` |
| Disco livre | `4 584 MB` |
| RAM disponivel | `3 564 MB` de `16 305 MB` |

## 2. Posicoes abertas (medidas agora)

| Ticket | Lado | Simbolo | Volume | Abertura | SL | TP | Lucro | Comentario |
|---|---|---|---|---|---|---|---|---|
| `11381095235` | buy | EURUSD | 0,01 | 13/11 05:02:49 | `1.10450` | `1.10750` | `-0,03` | `copilot auto` |
| `11381273395` | buy | EURUSD | 0,01 | 13/11 05:18:58 | `1.10450` | `1.10750` | `+0,05` | `copilot auto` |

- As **3 posicoes anteriores** (GBPUSD SELL, USDCAD BUY, AUDUSD SELL) **nao existem mais**:
  foram fechadas e o motor abriu estas duas EURUSD.
- Sao **2 posicoes**, exatamente o que `max_posicoes = 2` permite
  (`backend/auto_engine.py:202/367`, `backend/risk_gate.py:33`). A pergunta antiga
  "subir o limite ou aceitar a recusa?" deixa de estar em aberto por ora: o limite
  esta sendo respeitado, nao violado.
- Ambas tem **SL e TP no servidor**. Nenhuma delas e ordem pendente.

## 3. Versao (uma so fonte, 9 portadores)

`Docs/version.json` = **`1.2.191`**. `scripts/sync_version.py` propagou para os 9
portadores e a medicao confirmou **1.2.191 em todos, zero 1.2.183**:

`VERSION`, `pyproject.toml`, `backend/package.json`, `frontend/package.json`,
`frontend/src-tauri/Cargo.toml`, `frontend/src-tauri/tauri.conf.json`,
`core/Cargo.toml`, `frontend/src/version.ts` (`APP_VERSION`) e o `build`
(`xau-ai-pro-1.2.191-universal-20261113`).

EA: `#define EA_VERSION_STRING "1.2.191"` e `#property version "1.391"`
(`2*100+191 = 391`). **O EA nao esta na lista dos 9 portadores** — o teste
`tests/test_versao_consistente.py` calcula a formula a partir do `.mq5`.

> **Duas copias do EA** (ver AGENTS.md §15): a canonica em
> `MQL5\Experts\XAU_AI_PRO\` (lida pelo MetaEditor e pelo grafico) e a **embutida**
> em `MQL5\Files\XAU_AI_PRO\MQL5\Experts\XAU_AI_PRO\` (lida pelo teste). As duas
> tem `104 834 B`; **tamanho nao distingue copia**. Mexa na canonica; se o teste
> precisar passar, sincronize a embutida. Decidir remover a embutida e P1.3634
> (decisao de arquitetura, do dono).

## 4. Artefatos (hashes medidos)

| Artefato | Bytes | SHA256 |
|---|---|---|
| NSIS `dist\installers\XAU AI PRO_1.2.191_x64-setup.exe` | 142 121 988 | `83553C59…B56E` |
| MSI `dist\installers\XAU AI PRO_1.2.191_x64_en-US.msi` | 210 434 790 | `7F9E4E4B…C61C54` |
| EXE solto `dist\installers\XAU AI PRO.exe` | 13 998 592 | `296EAE02…59059` |
| Gateway construido `dist\mt5-gateway\mt5-gateway.exe` | 28 759 944 | `C42E18F9…08A8F` |
| Gateway em `frontend\src-tauri\bridge\` | 28 759 944 | `C42E18F9…08A8F` |
| Gateway de rollback `dist\mt5-gateway.bak_182\` | 28 759 944 | `3D1149F3…EC65` |

`DIST == BRIDGE` e **True**: o defeito da *bridge defasada* foi corrigido com
`robocopy /MIR` e reverificado. Como `tauri.conf.json` empacota `bridge/**/*` (e
**nunca** `dist`), essa igualdade de hash e a unica prova honesta de que o
instalador carrega o gateway 1.2.191.

## 5. O que esta INSTALADO nao e o que foi CONSTRUIDO

| Item | Medido |
|---|---|
| `%LOCALAPPDATA%\XAU AI PRO\bridge\mt5-gateway.exe` | 28 759 944 B, mtime `11/12/2026 23:09:52` |
| SHA256 instalado | `B786CAD4C8912862D78A9764FC67ED0A4B38E29E8AD7ADCB67B37C6C1A73230A` |
| Igual ao `dist` 1.2.191? | **False** |

`B786CAD4…` e **exatamente** o hash que a bridge defasada tinha antes do
`robocopy /MIR`. Conclusao medida: **o app que esta no ar executa o gateway
1.2.183**. Qualquer captura da aba ROBO feita agora mediria o comportamento
antigo — atribuir isso ao codigo novo seria erro de medicao.

O instalador compara **FILE VERSION** antes de sobrescrever, e os dois gateways
declaram a mesma versao e o mesmo tamanho; so o hash os distingue. Por isso o
passo a passo manda **apagar** `%LOCALAPPDATA%\XAU AI PRO\bridge` antes de
instalar. Runbook: `Docs\INSTALAR_1_2_191_DONO.md`.

## 6. Passo fisico pendente (acao do dono — fora das raizes de escrita do agente)

1. Fechar o app `XAU AI PRO` e confirmar que nao ha processo `mt5-gateway`.
2. `Remove-Item "$env:LOCALAPPDATA\XAU AI PRO\bridge" -Recurse -Force`
3. Rodar `dist\installers\XAU AI PRO_1.2.191_x64-setup.exe`
   (SHA256 esperado `83553C59…B56E`).
4. Conferir `%LOCALAPPDATA%\XAU AI PRO\bridge\mt5-gateway.exe` = `C42E18F9…08A8F`.
5. Abrir o app e capturar a aba **ROBO** com 4 criterios:
   - a fonte das velas diz **MT5** (nunca `yahoo`);
   - OHLC **nao degenerado** (open != close em todas as velas);
   - **TP/SL desenhados** sobre as posicoes abertas (hoje: os 2 EURUSD acima);
   - o simbolo exibido e o **PAR** (`EURUSD`), nunca `MULTI_*`.
6. Se cair na fonte publica, guardar `gateway_autostart.log` e `Logs\`.

**Rollback:** o bundle anterior esta intacto em `dist\mt5-gateway.bak_182`
(`3D1149F3…EC65`). Por isso reinstalar e reversivel e `bak_182` **nao se apaga**
antes do passo 5 passar.

## 7. Testes (numeros honestos)

| Suite | Comando | Resultado |
|---|---|---|
| Suite Python inteira | `pytest -q --continue-on-collection-errors` | **2 failed, 1529 passed, 2 skipped, 16 warnings, 8 errors** (304,65 s) |
| As 3 travas decisivas | `pytest -q tests\test_versao_consistente.py tests\test_ai_inference.py tests\test_artefato_congelado.py` | **105 passed** (6 + 91 + 8) em 12,15 s |
| Frontend | `npx vitest run` | **83 arquivos / 1019 testes passed** |
| TypeScript | `npx tsc --noEmit` | **0 erros** |

**Todos os 10 pontos restantes (2 failed + 8 errors) sao tkinter.** Nenhum e de IA,
de versao ou de bundle.

## 8. Bloqueios conhecidos (com dono)

| ID | Bloqueio | Dono | Como fecha |
|---|---|---|---|
| **P1.3633** | `tkinter` ausente no `.venv` (10 testes). O unico Tk real esta **fora** das raizes de leitura (`…\uv\python\cpython-3.11-…`). Varredura em `MQL5` achou 0 `_tkinter.pyd`, 0 `tkinter\__init__.py`, 0 `tcl86t.dll`. | dono (perm) | (a) incluir a base do uv como raiz de **leitura** e copiar `_tkinter.pyd`/`tcl86t.dll`/`tk86t.dll`/`Lib\tkinter\`/`tcl\` para o `.venv`, provando com `import tkinter`; ou (b) aposentar `app\` e seus testes. **Proibido:** apagar, `xfail` ou `skip`. |
| **P1.3635** | `app\` = UI Tkinter legada (48 `.py`, 22 com tkinter), **fora** do produto empacotado (`tauri.conf.json` so leva `Python/models`, `core/xau-ai-pro.core.exe`, `bridge/**/*`). | dono + DELTA | remover/arquivar com os testes, ou declarar mantida com Tk como pre-requisito de dev. O README ainda diz "aplicacao legada em Tkinter" de proposito, ate essa decisao. |
| **P1.3634** | Duas copias do EA (§3). | dono | decidir a canonica e remover/submodular a embutida. Metade documental fechada em AGENTS.md §15. |
| **P1.3636** | Instalador pronto e provado por hash, **nao instalado** (grava em `%LOCALAPPDATA%`, fora das raizes de escrita). | dono | o passo 6 acima. |
| **P1.3595** | O bit de negociacao nao sobrevive a reinicio do terminal; nenhuma ferramenta MCP o restaura (5 rotas medidas); so a GUI `F7 > Comum`. O watcher `retomar-forward.ps1` **nao** esta rodando. | dono | ao reiniciar: religar o botao e conferir. E o risco #1 do restart. |
| **P1.3620** | `medicao.jsonl` e `FORWARD.md` tem MD5 mas nao `fonte_sha256`. | CMD | adicionar o campo. |
| **P1.3630** | Contrato de `/api/universal/account` e `/api/universal/history` em corretora `planned` (ambos 501 ou assimetria documentada). | CMD | uma linha muda em `test_gateway_endpoints.py`. |

## 9. Repositorios (nada commitado)

| Repo | Caminho | Branch / HEAD | Entradas sujas |
|---|---|---|---|
| App | `…\MQL5\Files\XAU_AI_PRO` | `develop` / `e0e899d0` | 47 |
| EA | `…\MQL5\Experts\XAU_AI_PRO` | `main` / `b2907ee2` | 179 |

- **Nada foi commitado** (D-3: nenhum commit misturando fontes de varios agentes
  neste estado). Nao usar `git add -A`.
- Arquivos de producao **nao** tocados pelo ALFA: `backend/mt5_gateway.py`,
  `backend/broker_registry.py`, `backend/auto_engine.py`,
  `backend/connection_service.py`.
- `Temp\cargo-target` (2,4 GB) foi removido **somente depois** de
  `COPIA_CONFERE=True` nos 3 instaladores.

## 10. Ordem sugerida ao reiniciar o terminal/PC

1. Abrir o MetaTrader 5 e conferir que a conta sincronizou (§1).
2. **Religar o botao de negociacao algoritmica** (`F7 > Comum`) e reavaliar
   `P1.3595` — sem isso o motor nao opera.
3. Conferir que existem no maximo `2` posicoes e que cada uma tem SL e TP (§2).
4. Rodar o passo fisico do §6 (instalar 1.2.191 e capturar a aba ROBO).
5. Rodar `pytest -q tests\test_versao_consistente.py tests\test_ai_inference.py tests\test_artefato_congelado.py`
   e exigir `105 passed` antes de qualquer outra mudanca.
6. So depois de o passo 5 do §6 passar: apagar `dist\mt5-gateway.bak_182` e os
   artefatos de teste em `MQL5\Files\Temp`.

## 11. Nao faca

- Nao apagar `dist\mt5-gateway.bak_182` antes do passo 5 do §6 passar (e o rollback).
- Nao `xfail`/`skip`/afrouxar os 10 pontos de tkinter.
- Nao commitar misturando fontes de varios agentes.
- Nao apagar `frontend\src-tauri\bridge` para "forcar" atualizacao: o
  `robocopy /MIR` a partir de `dist\mt5-gateway` e o caminho provado.
- Nao declarar instalado sem o hash do passo 4 do §6.
- Nao editar `.venv\pyvenv.cfg`: ele e auto-referente mas **nao** e o defeito
  (o stdlib foi copiado para `.venv\Scripts\Lib`). Backup em
  `MQL5\Files\Temp\pyvenv.cfg.bak_alfa_0135`.
## 12. Atualizacao 13/11/2026 05:25 -03:00 (ALFA) â€” releitura do disco

Onde este anexo divergir das secoes acima, **vale este anexo** (as secoes 1..11 sao o retrato de 00:33).

- Gateway instalado `B786CAD4...` (12/11 23:09:52) difere do dist `C42E18F9...` (13/11 01:02:54): **passo fisico pendente**.
- EXE instalado e **1.2.182** (13 996 032 B); o do dist e 13 998 592 B (1.2.191). Nao basta olhar a versao declarada nos arquivos: o produto instalado esta **duas versoes atras**.
- Carteira agora: **3 posicoes** â€” 2 EURUSD 0,01 `copilot auto` (motor do app) e 1 GBPUSD 0,21 magic `2026001` `XAU_AI_PRO` (EA no grafico).
- **Dois atores na mesma conta.** Antes de capturar a aba ROBO, deixe apenas um ligado; ver P1.3639.
- Disco 3,89 GB livres. Repos: app `develop e0e899d0` 48 sujos; EA `main b2907ee2` 179 sujos. Nada commitado.
- Continuam valendo: os 10 pontos tkinter (P1.3633/P1.3635), a escolha da copia canonica do EA (P1.3634) e o contrato de `/api/universal/*` (P1.3630).


---

## 22/11/2026 20:20 -03:00 (DELTA) - conta real autorizada pelo DONO: regras escritas no canal (D-207)

- **Ordem do DONO, verbatim:** `eu DONO autorizo usar conta real apartir de agora, SIM excrever novas regras entendeu` (22/11 20:11 local).
- **Escrito no canal EQUIPE:** `DECISOES.md` `D-207` (governanca: 10 regras + nota de conciliacao com o `D-208` do ALFA), `AUTORIZACOES.md` (linha `Enviar ordem em conta real` e limite 2 da seccao 2), `PROTOCOLO.md` §11, `GATE_REAL.md` (seccao da autorizacao), `QUADRO_ESTADO.md` (medicao de 22/11), `AGENTE_2.md` (escopo actualizado + entrada de diario). O `ALFA` escreveu em paralelo `REGRAS_CONTA_REAL.md` (`D-208`, 18 regras de operacao).
- **Medido (conta real, 20:13-20:14 local):** XM Global Limited, `XMGlobal-MT5 14`, login `391773676`, `type=real`, hedging, USD; saldo **8,55**, credito **2,61**, equity **11,16**, margem livre **11,16**; **12** graficos com `XAU_AI_PRO.ex5`; **1** posicao `BTCUSD` buy 0,01 (`263610219`, sem SL, TP a ser alterado por fora) e **0** ordens pendentes.
- **`GATE_REAL` continua 3 de 12.** A autorizacao **nao** muda cor de criterio nenhum: o gate passa a ser placar de prontidao, nao permissao.
- **O que continua a travar o EA nao e' a permissao:** `[SAFETY] Free margin low` (6,46 a 9,97 contra piso 10,00), `[CIRCUIT] HIGH DRAWDOWN 6,54%` -> `SAFE MODE`, mercado fechado ao fim de semana, `BlockRealAccounts=true`/`EnableRealAccountGuard=true` nos 12 graficos.
- **Nada de codigo tocado:** zero compilacao, zero reattach, zero alteracao de inputs, zero ordem. `.ex5` intocado.
- **Para quem assumir:** ler `DECISOES.md` `D-207` + `REGRAS_CONTA_REAL.md` `D-208` + `GATE_REAL.md` (seccao da autorizacao). Em divergencia, vale a regra **mais restritiva**.
