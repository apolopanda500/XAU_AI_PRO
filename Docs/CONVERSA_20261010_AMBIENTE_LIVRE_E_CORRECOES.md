# CONVERSA 10/10/2026 — ambiente livre, defeitos medidos e build reinstalado

> Registro do ciclo. Os números são medidos; onde um número daqui divergir do
> que o comando medir agora, **o comando vence** — corrija aqui.

## O que o dono pediu, em ordem

1. **"não coloque nomes de ativos em códigos para não ficar presos ou
   dependentes, todos sejam livres e se comunicam ligações"**
2. **"proximo em sequencia total ate finalizar todos itens"** — fechar a fila
   toda, sem parar no meio
3. **"depois anotar tudo documentar salvar conversas, atualizar documentos
   escritos"**
4. **"validar 10/10 build completo + desinstalar app antigo + instalar app novo
   + executar pelo atalho rodar aprovar testar tudo 10/10"**
5. **"manter ambiente limpo e seguro para o trabalho sem interrupcao"**
6. **"deixar o catalogo sem icone apenas lista opcional"** — decisão sobre os
   ícones

---

## 1. Nenhum ativo preso no código

Medido varrendo `frontend/src` (1.603 linhas com nome de ativo no repositório
inteiro; a maioria em teste, em tabelas de mapeamento que o §3 permite, e em
comentário de medição):

| Arquivo | Era | Agora |
|---|---|---|
| `components/RobotMarketBar.tsx:42` | `(selectedSymbol \|\| 'XAUUSD')` | símbolo vazio **recusa com motivo**: chip `sem ativo`, `—` na faixa, zero cotações pedidas |
| `components/tabs/AIControlTab.tsx:40` | `... \|\| 'XAUUSD'` | símbolo vazio não chama gateway; aviso na tela diz onde escolher |
| `components/ModelCover.tsx:42` | `/XAU\|GOLD\|.../` → classe pelo **nome** | classe vem de `assetClass`; sem ela, cor **neutra** |
| `components/StatusBar.tsx:215` | `placeholder="ex.: XAUUSD"` | `digite ou escolha da lista` |
| `components/tabs/HistoryTab.tsx:357` | `'Opcional (ex.: BTCUSD)'` | `'Opcional'` |

**Trava nova**: `frontend/src/ativoPresumido.test.ts` (6 testes). Lê o fonte com
`import.meta.glob`, remove comentário/docstring e reprova nome de ativo no
código. Provas negativas medidas: `|| 'XAUUSD'` → reprova; `["XAUUSD"]` →
reprova; token `'BTC'` no mapeador → reprova.

### A decisão do dono sobre ícone (item 6)

`lib/assetIcons.ts` **perdeu 8 listas de nome/moeda** (`XAU`, `GOLD`, `BTC`,
`SOL`, `DOGE`, `USDT`, `USD`...) e o palpite de par de forex por comprimento
(`6 LETRAS = PAR`).

A forma de cumprir a regra: **a função não recebe mais o símbolo**. Era
`assetIcon(symbol, assetClass)` — a classe tinha prioridade, mas a função ainda
podia ler o nome quando a classe faltava. Agora é `assetIcon(assetClass?)`, e
ela não tem como adivinhar porque não recebe o nome.

- Sem classe → **sem sigla** (`SEM_ICONE = ''`). Acabou o `AST` inventado.
- `AssetIcon` devolve `null` sem sigla; `ModelCover` não desenha o selo.
- Mesmo metal, mesma sigla: `metal` dá `MET` sempre (antes `XAUUSD` dava `Au`).

Trava: `@ts-expect-error` em `assetIcon('XAUUSD','metal')` — o `tsc` confirma
que é erro de compilação. **Se alguém devolver o parâmetro, o build quebra.**

---

## 2. Os defeitos da fila

### a) A IA desligava ao sair e voltar da aba ROBÔ

**Causa medida**: `iaLigada` era `useState(false)` dentro de
`OperacaoAutomatica`. A aba ROBÔ monta e desmonta o componente inteiro, então
sair e voltar zerava o interruptor — e `useInferenciaIA` usava o valor para
decidir se chamava o gateway, então a inferência parava sem o operador pedir.

**Correção**: `hooks/useIaLigada.ts`, store zustand **sem `persist`**. A escolha
vale para a sessão e morre com o app — o `useAppStore` tem `persist`, e colocar
lá faria a IA voltar ligada no dia seguinte, que é o que o comentário original
proibia.

Teste: `useIaLigada.test.tsx` (3). Provas: desmontar/remontar mantém ligada;
estado compartilhado entre árvores; e **nada vai para o `localStorage`**.

### b) `MOTIVO: já há 0 posições (max 0)` com o motor ligado

**Dois defeitos, ambos medidos:**

1. **`configurar` gravava o valor inválido e só depois validava.** A resposta
   dizia `ok: False` e o valor inválido já estava dentro do motor. A captura de
   20:15 mostrava o resultado: motor LIGADO, `max_posicoes = 0`, e todo ciclo
   recusando com um motivo que não explicava nada.
   **Correção**: valida na **cópia** (`dataclasses.replace`) e só grava se
   válida.

2. **A mensagem dizia o motivo errado.** `"já há 0 posições (max 0)"` com
   NENHUMA posição aberta manda o operador olhar as posições, quando o defeito
   era o **limite não declarado** — a regra 5 do AGENTS.md na forma mais cara.
   **Correção**: `_declarado_impossivel()` julga só o que o pedido **declarou**
   (`valido()` não pode: para ele zero quer dizer ausente), e o ciclo separa os
   dois motivos.

Testes: `tests/test_auto_engine.py` +7. Prova negativa: pedido misto
`{max_posicoes: 0, lote: 0.5}` não aplica metade.

### c) `MULTI_METALS | MULTI_METALS | METALS` na tabela de modelos

**Causa medida**: os três artefatos de classe (`MULTI_METALS`, `MULTI_FIAT`,
`MULTI_CRYPTO`) têm o nome do arquivo com underscore, então
`if "_" not in nome: continue` **não** os descartava — mas
`simbolo, tf = nome.rsplit("_", 1)` pegava `tf = "METALS"`, o pedaço errado do
nome. Resultado na tela: coluna Modelo e coluna Par com o mesmo texto, e a
coluna Período dizendo `METALS`.

**Correção** (`backend/ai_inference.py`): o nome vem do `symbol` que o modelo
**gravou** no treino, e o período também. Modelo de classe vira **uma linha por
período** que ele cobre (o `MULTI_METALS` tem 4). A coluna Modelo mostra o
`label`; a chave da linha é `id|timeframe` (React reutilizava o nó errado com
`key={m.id}` repetido).

E o contador: dizia "28 modelos" contando linhas. Agora
**"28 artefatos · 37 de 37 períodos podem operar"** — 39 artefatos, três com
quatro linhas cada.

Testes: `tests/test_ai_inference.py` +4, `ListaModelos.test.tsx` +4.

### d) Menu do botão direito estilo XM

**Causa medida**: o clique direito abria o menu **do webview** (Recarregar,
Inspecionar, Imprimir). O dono: "quando tem direito tem que abrir todas funcoes
do menu".

**Correção**: `charts/MenuGrafico.tsx` + `theme/menu-grafico.css`. TRADE no
topo (a única cor do menu), VER, DESENHAR, LIMPAR.

**A regra de 08/10/2026 vale aqui também**: "o clique não arma ordem" — MEDIDO
então, dois cliques criaram três linhas montadas na conta real. Por isso
COMPRAR/VENDER **não criam linha**: passam o lado e o preço para o pai, que é
dono do botão `Colocar ordem`. Se o menu criasse linha, seria o 1-clique que foi
removido, só que pelo botão direito.

Não entrou "Propriedades", "Arquivos", "Opções": são menu da **plataforma** XM.
Copiar o rótulo sem a função é o defeito do §9 — controle que o operador
acredita ter.

Testes: `PriceChart.menu.test.tsx` (5).

### e) Excedente sob o gráfico

**Causa medida**: a área mostrava **dois cabeçalhos empilhados** — o do
`AcompanharModelos` (`Gráfico ao vivo` + `BTCUSD · H1 · MT5 · ao vivo`) e o do
`PriceChart` (`<h2>BTCUSD</h2>` + a fita OHLC). O dono: "e so tres coisas,
entao tire o excedente, deixa apenas mesmos itens".

**Correção**: o cabeçalho do pai saiu. Sobrou o chip de sinais — a **única**
informação que o gráfico não tem — e a **idade da leitura** passou a valer nele
(antes a faixa dizia "ao vivo" com a cotação parada).

E as **três** linhas de aviso (erro, "carregando candles", "candles
indisponíveis") viraram **uma**, com o primeiro motivo que se aplicar.

### f) Fuso com 18 cidades

**Causa medida**: 18 cidades escritas no código, sem busca. O dono: "tem como
os usuarios achar um pais".

**Correção**: o catálogo vem do `Intl` do sistema (`supportedValuesOf`) — mais
de 400 zonas, contra 18 escritas à mão. Nenhum nome de cidade no código, que é a
regra do §3 aplicada a fuso. E a **busca** casa em cidade, país e zona IANA.

Defeito achado no caminho: duas zonas com o **mesmo nome** vindo do `Intl`
("Brasília" em `America/Sao_Paulo` e em `America/Bahia`) — quando o nome
repete, a **zona** entra entre parênteses.

Testes: `fuso.test.ts` +3, `SeletorFuso.test.tsx` ajustado.

---

## 3. Ícones da barra do gráfico

O dono: "tem icones no graficos mas nao da pra ver nada, barras de ferramentas
etc". **Causa medida**: os rótulos eram glifos Unicode (`⌁` `⊞` `⊟` `⤢`,
`⏻`, `◷`, `📡`) que a fonte do app não tem — viravam caractere substituted do
tamanho de uma letra. E `✛` estava em **dois** botões (cursor e crosshair).

**Correção**: `charts/IconesGrafico.tsx` (13 SVG) e `components/Icones.tsx`
(4 SVG). `currentColor`, então seguem o tema.

Cinco provas negativas medidas: glifo no lugar do SVG → 4 falhas; cursor =
crosshair → 2 falhas; preso = livre → 1 falha; texto puro → 3 falhas; emoji `🔒` → 1 falha.

---

## 4. Estado medido (números, não adjetivo)

| Medida | Antes | Depois |
|---|---|---|
| `pytest tests` | 1299 passed, 2 skipped | **1312 passed, 2 skipped** |
| `vitest run` | 847 passed, 2 falhas | **869 passed / 65 arquivos** |
| `tsc --noEmit` | erro nos multi | **exit 0** |
| `cargo fmt --check` / `check` / `test` | ok | **ok** |
| `pytest test_mql5_compila.py` | ok | **2 passed** |
| `preflight --etapa app-rodando` | ok | **0 falhas, 3 avisos** |
| nome de ativo no código (`frontend/src`) | 6 | **0** |
| listas de tokens no mapeador | 8 | **0** |
| linhas de modelo na lista | 36 (3 multi com período errado) | **48 (12 multi com período certo)** |

Suíte rodada **3 vezes seguidas**: 869/65 em todas. A falha intermitente que
apareceu antes era estado compartilhado entre arquivos de teste (o store
`useIaLigada` é de módulo) — fechada com `zerarIaLigada()` no `afterEach`.

---

## 5. O defeito do deploy que quase passou

**MEDIDO**: o build regenerou o gateway (`dist/mt5-gateway`, 02:13:30) e copiou
para `frontend/src-tauri/bridge`, mas o app **instalado** continuou com o
gateway de **10/09 19:44** — o instalador NSIS compara a versão do arquivo e,
como o `.exe` tem a mesma versão 1.2.4, **não sobrescreve**. Só os arquivos
novos (`bridge/_internal`) foram escritos.

Consequência medida na tela: o frontend novo (contador "28 artefatos") com o
backend velho (`MULTI_METALS` com `PERÍODO = METALS`) — dois lados do mesmo
dado divergindo, que é a regra 5 na forma mais difícil de perceber.

**Como se descobre**: hash. `Get-FileHash` do instalado contra o do build.

**Correção aplicada**: remover `%LOCALAPPDATA%\XAU AI PRO\bridge` antes de
reinstalar. Depois disso o hash bateu (`175E634408...`) e a tela passou a
mostrar os 4 períodos do `MULTI_METALS`.

**Fica registrado para o próximo ciclo**: o `build_app.bat` não avisa que a
bridge instalada pode estar defasada. Quem validar build precisa comparar o
hash, não a data do instalador.

---

## 6. Ambiente

- Limpeza segura aplicada: `scripts\limpeza_segura.ps1 -Apply -DebugCache`
  (caches de desenvolvimento, 26 itens). Instalador e `Temp\cargo-target`
  **preservados** — o build precisa deles.
- Disco: 6,92 GB livres → 6,94 GB.
- Gateways duplicados (um da sessão anterior segurando a 9011 com token velho)
  foram parados; o app subiu o seu.

---

## 7. O que exige ação do dono

1. **Reanexar o EA ao gráfico** — compilar não reanexa, e 21 arquivos MQL5 estão
   com autorização declarada no preflight.
2. **Os temas `xau_dark` / `btc_dark`** (`hooks/useAppStore.ts:5`) são apelidos
   de cor com nome de ativo. Renomear mexe na preferência já salva e nas classes
   CSS `wallpaper-xau`/`wallpaper-btc`. Renomeio ou deixo?

---

## 8. O que NÃO foi feito, e por quê

- **Independência do MT5**: candles, conta e EA ainda vêm do terminal. Renomear
  rótulo não remove a dependência — é mudança arquitetural.
- **Treino automático**: não existe rota POST de treino. O treino continua
  offline em `Python/ai/train_v2.py`.
- **`_ROTULO_ALGORITMO`** (`backend/ai_inference.py`) ficou sem uso depois que o
  nome do modelo passou a ser `ATIVO PERÍODO`. Não foi removido para não quebrar
  quem o importa; pode sair no próximo ciclo.
