# STATUS ATUAL DO PROJETO

**Data:** 23/10/2026
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
| `vitest run` | **950 passed** (77 arquivos) |
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
| Versão do EA | `#property 1.240`, `EA_VERSION_STRING 1.2.4` | **1.2.8** (recompilado pelo MetaEditor via teste) |
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

1. **Reanexar o EA no gráfico.** O EA em execução loga `[VERSION] v1.2.0`
   enquanto a fonte já é 1.2.8. Compilar não reanexa (AGENTS 7).
2. **Credencial de conta real**: quando existir, `XAU_ACCOUNT_KIND=real`.
   Hoje a conta é `MetaQuotes-Demo` e o script de prontidão reprova nesse item.
3. **MCP de trading e o token de sessão**: token aleatório por execução; o do
   `.env` devolve **401** (fail-closed correto). Expor degrada a segurança —
   decisão do dono.
4. **Modelos**: 0 de 40 com edge medido acima do mínimo. O AUTO liga e não
   opera sem modelo. Baixar `min_edge` é proibido.
5. **Instalador**: MSI falha nesta máquina (`light.exe`); NSIS é o que funciona.
6. **Backup da instalação anterior**: `Temp\instalacao_anterior_20261022`
   (949 MB) — apagar depois de confirmar o app novo no ar?
7. **Conexão XMGlobal antiga** segue gravada; apagar é decisão do dono.
8. **Fechamento espontâneo do app** em sessão longa: medido em 10/10, sem log.
9. **Git**: **60 entradas** pendentes em `git status --porcelain` (bump 1.2.8,
   `build.rs`, `parNaTela`, `asset_registry`, testes novos, `global.css`,
   `.mq5`/`.mqh`). Commit não foi feito — não pedido; o doc do ciclo lista os
   arquivos tocados.

---

**Um documento antigo neste `Docs/` não está desatualizado por estar no fim da
lista — e sim por ser de um ciclo anterior. O `command` vence o número; o
documento mais recente manda.** Ver
`CONVERSA_20261023_CATALOGO_CLASSIFICADO_GRAFICO_MT5_E_128.md`.

