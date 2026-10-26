# 23/10/2026 — Catálogo classificado, gráfico da corretora e versão 1.2.8

> Ciclo anterior: [`CONVERSA_20261022_MODELOS_SEM_EDGE_MEDIDO.md`](CONVERSA_20261022_MODELOS_SEM_EDGE_MEDIDO.md)
> e [`CONVERSA_20261022_BATERIAS_FIXADAS_CI_VERDE_E_DEPLOY.md`](CONVERSA_20261022_BATERIAS_FIXADAS_CI_VERDE_E_DEPLOY.md).
>
> Este documento existe porque **o defeito central deste ciclo não estava em
> nenhuma tela**: o catálogo que a corretora publica chegava ao app com o ouro
> classificado como `other`, e a consequência aparecia em dois lugares que
> pareciam independentes — o gráfico (dado público) e o motor (mercado errado).
> Fica escrito com os números medidos, antes e depois.

## O que foi pedido

Continuar todos os trabalhos sem interrupção: corrigir motores, fazer o gráfico
seguir a lista, revisar botão a botão no app instalado e deixar o app pronto
para uso real. A ordem permanente do dono continua valendo: **medir antes e
depois**, nunca declarar pronto sem número.

---

## 1. O DEFEITO CENTRAL: a hierarquia da corretora era código morto

### Medido antes

```
symbol_info("XAUUSD").path   == "Metals\\XAUUSD"     (MetaQuotes-Demo, conta 113568614)
/api/universal/assets?broker=mt5  ->  asset_class == "other"   (XAUUSD)
```

Com `asset_class="other"`, `mercadoDoAtivo("other")` devolve `null`, e a cadeia
do painel termina em `market === ''`:

- `AcompanharModelos`/`PriceChart`: `configurado=false` → consulta
  `/api/publico/ohlc` → **ouro do Yahoo**;
- `OperacaoAutomatica`: sem ficha, cai em `marketSalvo` do escopo
  (`mt5:forex`) → **o motor liga com o mercado da CONTA, não do ativo**.

O número que prova que não era detalhe: no mesmo minuto, a tela mostrava
**4.025,00** (Yahoo) e o MT5 servia **4.016,46** — 8,50 de diferença no ativo
de maior peso do projeto.

### Duas causas, as duas medidas

| Causa | Efeito |
|---|---|
| `raiz` era comparada em minúsculo (`metals`) contra raízes escritas como a corretora publica (`Metals`, `Forex`) | o mapa **nunca** casava; toda classificação vinha do palpite por palavra |
| `Metals` não existia no mapa (só `Derivatives\Spot Metals\...`) | e o palpite não via `GOLD`: o texto era `name + path + base + profit` = `"XAUUSD METALS XAUUSD XAU USD"`, sem a `description` ("Gold vs US Dollar") |

Consequência de leitura: `_asset_class` era um mapa de hierarquia que **parecia**
funcionar porque o palpite por palavra acertava fiats e cripto. O ouro foi o
primeiro ativo cuja palavra não aparecia no texto.

### Corrigido

- comparação **sem caixa** dos dois lados;
- raízes que as corretoras publicam: `Metals`/`Metal`/`Precious Metals`/
  `Commodities` → `metal`, `Indices` → `index`, `Bonds` → `bond`,
  `Energies`/`Energy` → `commodity`, `Stocks`/`Shares` → `equity`;
- desempate do `Derivatives` no **caminho inteiro** (era só o 2º nível; por isso
  `Derivatives\Cash\Cash Indices\AUS200Cash` voltava `cfd`);
- a `description` da corretora entra no palpite, **depois** da hierarquia.

### Medido depois

```
/api/universal/assets?broker=mt5   XAUUSD asset_class=metal   EURUSD=forex
gráfico: "Candles OHLC reais · MT5 · sinais do modelo"   4.022,28
```

Travas novas: `tests/test_classificacao_catalogo.py` (12 passed) com os `path`
**reais** do terminal — inclusive a prova negativa que reprova com o código
antigo (`Metals\XAUUSD` sem a palavra GOLD) e a que impede `SOL` de casar
dentro de "Solvar".

### Trava do lado do frontend

O backend devolve `equity` e o mapa do frontend só conhecia `stock`:
`mercadoDoAtivo("equity") === null` — o mesmo defeito em ações.
`frontend/src/lib/volumeUnidade.test.ts` ganhou 3 casos (os dois nomes viram
`stocks`; `other`/`cfd` continuam `null`).

---

## 2. CONEXÕES: não havia como ESCOLHER a conta

**Medido no app 1.2.7:** as três conexões apareciam como ativas, o botão de cada
linha dizia "Desativar", e a escolha só era gravada no caminho `activate` — que
só existe quando a linha está desativada. Com tudo ativo, o operador não tinha
saída: `escopoAtivo()` vazio, faixa "sem corretora", seletor sem catálogo e o
AUTO recusando com "sem catálogo da corretora". **A recusa estava certa; a ação
para sair dela não existia.**

- `ConnectionSettings`: botão **"Usar esta conta"** (grava broker + market + ID)
  e chip **"Em uso"** na linha escolhida;
- `td:first-child` quebrava o nome em cima da coluna CORRETORA
  (`Henrique Carvalho @ XMGlobal-MT5 14` invadia `MT5`): `table-layout: fixed`,
  quebra de linha e `min-width` na coluna de ações;
- 2 testes novos (16 no arquivo), um deles **negativo**: a conta em uso não
  oferece o mesmo botão.

---

## 3. "CASAS DECIMAIS" ERA UM CONTROLE SEM CONSUMIDOR

`SettingsCore.tsx` tinha o slider e o store tinha `precision: 2`. Medido:
**zero leituras** de `settings.precision` no código todo (as outras ocorrências
eram o próprio slider, o default e o `digits` da ficha em `marketApi.ts`).

O comentário do arquivo dizia "ficou só a precisão decimal, que o formatador
realmente usa" — **comentário que mentia sobre o próprio código**, o defeito que
o AGENTS 6 descreve. E a premissa era a proibida no AGENTS 9: preço, volume e
moeda têm precisões diferentes, e quem manda é a ficha do símbolo.

Removidos o slider, o campo do store e o texto mentiroso; a tela passa a dizer
de onde a precisão vem. Trava: `frontend/src/lib/precisaoGlobal.test.ts`
(lê o fonte **sem comentário** — o arquivo pode documentar a remoção).

---

## 4. IDENTIDADE DO BUILD (o "tela preta" de release)

A identidade do gateway estava escrita à mão em dois lugares
(`frontend/src-tauri/src/main.rs` com `xau-ai-pro-1.2.4-...` e `main.tsx`).
Agora `build.rs` lê `../../Docs/version.json` e emite
`cargo:rustc-env=XAU_GATEWAY_BUILD`; `main.rs` usa `env!`; `sync_version.py`
grava `GATEWAY_BUILD` em `frontend/src/version.ts`.

`tests/test_identidade_gateway_build.py` — **5 passed**, incluindo a prova
negativa do leitor de literal.

---

## 5. VERSÃO: o EA estava três bumps atrás

O gate `tests/test_versao_consistente.py` estava **vermelho desde 1.2.5**:
o `.mq5` dizia `#property version "1.240"`, `EA_VERSION_STRING "1.2.4"` e o
`Print` anunciava v1.2.4, enquanto o produto era 1.2.7.

Corrigido até **1.2.8** em `XAU_AI_PRO.mq5` e `VersionManager.mqh`, recompilado
pelo `tests/test_mql5_compila.py` (**2 passed**, invoca o MetaEditor de verdade).

**Achado separado, do terminal:** o EA *anexado ao gráfico* loga
`[VERSION] v1.2.0` — ou seja, o EA rodando é anterior até ao 1.2.4 que estava
no fonte. Compilar não reanexa (AGENTS 7). Isso é **ação do dono**.

---

## 6. BUILD E INSTALAÇÃO 1.2.8

```
scripts\build_app.bat  -> exit 1 (bundle MSI: light.exe falhou)
npx tauri build --bundles nsis -> exit 0
release\1.2.8\XAU AI PRO_1.2.8_x64-setup.exe   233,5 MB
SHA256 492943829738EFE1763234841981AB9AE0B1CBCD710BB0E2F51FB9D1FBCA67A7
```

Instalação limpa (app fechado, `bridge` apagado, NSIS `/S`): **exit 0**,
`FileVersion 1.2.8`, `bridge\mt5-gateway.exe` com hash **igual** ao do repo
(`66B416BD…17462`), bootstrap com "bridge MT5 autenticado e pronto antes do
Core" e "core autenticado e respondendo na versao esperada".

Disco: `Temp\cargo-target` recriado a cada build (~4 GB) e o MSI exige ~2 GB
livres. Antes de cada build: apagar `Temp\cargo-target`, `dist` e o bundle
anterior. O MSI é per-machine (`Error 1925` sem admin) — **NSIS é o instalador
que funciona** nesta máquina.

---

## 7. MEDIÇÕES DO CICLO

| Verificação | Resultado |
|---|---|
| `pytest -q tests` | **1535 passed, 9 skipped** (após a continuação da seção 11) |
| `pytest tests/test_classificacao_catalogo.py` | 12 passed |
| `pytest tests/test_identidade_gateway_build.py` | 5 passed |
| `pytest tests/test_mql5_compila.py` | 2 passed (MetaEditor real) |
| `npx vitest run` | **950 passed** (77 arquivos, após a seção 11) |
| `npx tsc --noEmit` | exit 0 (havia 3 erros em `precisaoGlobal.test.ts`, corrigidos na seção 11) |
| `/api/universal/assets` no artefato | `XAUUSD=metal`, `EURUSD=forex` |
| App instalado | 1.2.8, portas 9002/9003 (core) e 9011 (gateway), IA ligada em XAUUSD |

---

## 8. O QUE NÃO FOI FEITO, E POR QUÊ

- **Reanexar o EA.** Compilar não reanexa; o EA no gráfico continua v1.2.0.
- **Publicar modelos.** Continua **0 de 40** com edge medido acima do mínimo
  (`CONVERSA_20261022_MODELOS_SEM_EDGE_MEDIDO.md`). Baixar `min_edge` é proibido.
- **MSI.** `light.exe` falha nesta máquina; NSIS cobre a instalação.
- **Revisão das abas restantes** (Histórico, Calendário, Sistema, Risco,
  Operações, Configuração→Segurança/Plano/Confiança). **Carteira revisada na
  seção 11.**
- **Ordem manual DEMO pelo app** para provar o caminho completo de execução.

## 9. PERGUNTAS PARA O DONO

1. Reanexar o EA no gráfico (ou autorizar script)? Sem isso o EA em execução
   não é o código medido.
2. O AUTO fica ligado em XAUUSD com 0 modelos publicáveis — isso é o esperado,
   ou você quer que a tela recuse ligar quando não há modelo com edge?
3. Instalador: seguimos só com NSIS?

## 10. ARQUIVOS TOCADOS NESTE CICLO

```
backend/asset_registry.py                       hierarquia, `Metals`, desempate, description
tests/test_classificacao_catalogo.py            novo (12)
frontend/src/components/ConnectionSettings.tsx  "Usar esta conta" + chip
frontend/src/components/ConnectionSettings.test.tsx  +2
frontend/src/theme/global.css                   .tabela-conexoes / .conexao-acoes
frontend/src/components/SettingsCore.tsx        slider removido
frontend/src/hooks/useAppStore.ts                campo `precision` removido
frontend/src/lib/precisaoGlobal.test.ts          novo (3)
frontend/src/lib/volumeUnidade.ts                equity -> stocks
frontend/src/lib/volumeUnidade.test.ts           +3
frontend/src/lib/parNaTela.ts(.test.ts)          regra unica do par na tela
frontend/src/components/AcompanharModelos.tsx    gráfico segue a lista
frontend/src/components/StatusBar.tsx            par unico
frontend/src/components/OperacaoAutomatica.tsx   recusa com motivo ao ligar
frontend/src-tauri/build.rs, src/main.rs         identidade do build derivada
frontend/src/main.tsx, src/version.ts            GATEWAY_BUILD
scripts/sync_version.py                          grava e checa GATEWAY_BUILD
tests/test_identidade_gateway_build.py           novo (5)
MQL5/Experts/XAU_AI_PRO/XAU_AI_PRO.mq5           1.2.8 (#property + Print)
MQL5/Experts/XAU_AI_PRO/Enterprise/VersionManager.mqh  EA_VERSION_STRING 1.2.8
Docs/version.json                                1.2.8
```

---

## 11. CONTINUAÇÃO — CARTEIRA, TESTES VERDES E O QUE ELES ESCONDIAM

### 11.1 A suíte inteira estava vermelha, e o doc dizia verde

MEDIDO ao retomar: `pytest -q tests` -> **1 failed, 1534 passed**, no teste
`test_universal_router_dispatch.py::test_gateway_build_derives_from_version_json`.
Ele procurava o literal `xau-ai-pro-1.2.8-universal-20261022` dentro de
`main.tsx` — mas desde 22/10 o literal mora em `version.ts` (gerado) e o
`main.tsx` importa `GATEWAY_BUILD`. **O teste reprovava o código correto.**

Isto é o defeito do AGENTS §6 na direção oposta: a bateria nova
(`test_identidade_gateway_build.py`) já media a regra certa; a antiga repetia a
suposição. Corrigida para medir os três lados de verdade: `version.ts` contém o
valor, `main.tsx` importa e **não** escreve literal, `main.rs` usa
`env!("XAU_GATEWAY_BUILD")` e o `build.rs` lê `Docs/version.json`.

O `tsc --noEmit` também **não** estava em exit 0: `precisaoGlobal.test.ts`
importava `node:fs`, `node:path` e `__dirname` sem tipagem (o projeto não tem
`@types/node`). Seguiu o padrão já usado em `light_tabelas.test.ts`
(`@ts-expect-error`) — nenhuma regra foi afrouxada.

### 11.2 CARTEIRA: o resultado aberto era calculado e jogado fora

MEDIDO em `PortfolioHomeSafe.tsx`:

| antes | agora |
|---|---|
| `Row.pnl` somava `profit` das posições, mas **nenhuma coluna lia** o campo | coluna **"Resultado aberto"** |
| `money()` exigia `n >= 0`; posição perdedora virava `--` | número com sinal (`+12,00` / `-25,00`) e classe `pos`/`neg` |
| saldo negativo virava `--` (indistinguível de "sem dado") | aparece como `-12,50` |
| comentário dizia "a lista sai de uma fonte única" com `SOURCES` escrito à mão | comentário corrigido: rótulos do catálogo; `market` explícito porque MT5 é agregado (`other`) |

O `--` significa **"o gateway não mandou"** em toda a app; usá-lo para um
prejuízo é apagar a informação que o operador mais precisa ver. O teste novo
`PortfolioHomeSafe.test.tsx` (4) tem a **prova negativa**: a posição perdedora
tem de sair como `-25,00` com `td.neg`; passar por um formatador que rejeita
negativo reprova.

### 11.3 MEDIÇÃO FINAL DESTA CONTINUAÇÃO

```
pytest -q tests        1535 passed, 9 skipped  (268,72 s)
vitest run              950 passed (77 arquivos)
tsc --noEmit            exit 0
app no ar               XAU AI PRO 12316 · gateway 9011 (pid 12996) · core 9002/9003 (pid 13080)
```

### 11.4 ARQUIVOS DESTA CONTINUAÇÃO

```
tests/test_universal_router_dispatch.py             mede version.ts/build.rs, nao literal em main.tsx
frontend/src/lib/precisaoGlobal.test.ts             tipagem dos built-ins do Node
frontend/src/components/tabs/PortfolioHomeSafe.tsx  coluna resultado + sinal + saldo negativo
frontend/src/components/tabs/PortfolioHomeSafe.test.tsx  novo (4)
Docs/CONVERSA_20261023_...md                        esta secao
Docs/STATUS_ATUAL.md                                numeros atualizados
```

> Nota: o git continua com **60 entradas pendentes** em `git status --porcelain`
> (medido após esta continuação). Nada foi commitado — não foi pedido.
