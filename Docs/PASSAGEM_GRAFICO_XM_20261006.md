# PASSAGEM — gráfico operacional e ordem por clique (06/10/2026)

Documento de trabalho para qualquer agente que pegar este projeto.
Sem data e sem hora de propósito: as regras valem para sempre, os números não.
**Se um número aqui divergir do que o comando medir, o comando vence; corrija o número.**

Estado do repositório no fim desta sessão: **`pytest` 1253 verdes**, **`vitest` 652
verdes**, **`tsc --noEmit` limpo**, **`preflight --etapa app-rodando` todo `[ok]`**,
instalador `1.2.4` gerado. Versão **não** foi alterada: a 1.2.4 é a build final
deste ciclo; a próxima alteração é 1.2.5.

---

## 1. A REFERÊNCIA: as capturas da XM

O dono mandou telas de `https://my.xm.com/pt/symbol-info/BTCUSD` para servir de
referência de gráfico e de ordem. Elas estão em
`C:\Users\Micro\Pictures\Screenshots\` e valem como medida.

### A conta (medido no painel "Gerir")

| campo | valor |
|---|---|
| conta | XAU AI PRO #391773676 · XMGlobal-MT5 14 · Hedge |
| Capital | $10,50 |
| **Saldo** | **$4,88** |
| Margem / Margem Livre | $0,00 / $10,50 |
| Crédito | $5,62 |
| **Alavancagem** | **1000:1** |

### O RISCO DESSES NÚMEROS — leia antes de ligar execução real

Com `0,01 BTCUSD` a 85.523 o nocional é **$855**. A 1000:1 a margem exigida é
`855 / 1000 = $0,855` — que é exatamente o **"Requisito de margem $0,85"** que a
XM mostra. Confere.

Consequências medidas:

- Uma oscilação adversa de **0,57%** consome toda a margem.
- O stop 1:1 a 200 pontos é **0,23%** — menos de metade do caminho até a margem
  ser chamada. **O stop padrão está perto demais da margem para esta
  alavancagem.**
- O **saldo livre é $4,88**, menor que o nocional em 175x.

Isto é a razão de a recomendação ser **DEMO antes de conta real**, e a razão de
o `risk_gate` e o `order_check` não serem opcionais.

### A matemática de dinheiro confirmada pela própria XM

Modo `Quantidade`, entrada **85.376,63**, volume **0,01**:

| | valor na tela | nível | distância |
|---|---|---|---|
| take profit | 2,00 USD | 85.576,64 | 200 pontos |
| stop loss | −2,00 USD | 85.176,64 | 200 pontos |

`2,00 / (0,01 × 1) = 200`. **Confirma a conta de `nivelDoValor`**
(`frontend/src/lib/ordemGrafico.ts`), que foi escrita a partir das capturas de
14h12 e 14h14 do mesmo dia. Stop de um lado e alvo do outro, conforme o lado da
ordem.

A XM escreve também: *"Os montantes finais podem diferir dos valores
introduzidos"* — o nível é derivado e aproximado.

---

## 2. O QUE ESTÁ FEITO E MEDIDO

### 2.1 Ordem por clique no gráfico — os 4 passos do `Docs/ORDEM_PELO_GRAFICO_20261006.md`

| passo | onde | teste |
|---|---|---|
| 1. `PriceChart` em modo de ordem | `charts/PriceChart.tsx` (`modoOrdem`, `ordem`, `onArmarOrdem`) | `PriceChart.ordem.test.tsx` |
| 2. Arrastar e apagar as três linhas | mesmo arquivo, efeito das linhas + `overlayOrdemRef` | mesmo arquivo |
| 3. Painel de confirmação | `AcompanharModelos.tsx` (`robo-ordem-painel`) | `AcompanharModelos.ordem.test.tsx` |
| 4. `/api/trade/order` com `confirm` | `AcompanharModelos.tsx` (`enviarOrdem`) | mesmo arquivo |

O clique **arma**; o envio é o botão `Colocar ordem a <preço>`.

### 2.2 Defeitos do produto achados e corrigidos

| defeito | causa medida | arquivo |
|---|---|---|
| Histórico vazio | `group=f"*{symbol}*"` no MT5 é sensível a caixa e a XM publica `btcusd` em minúscula | `mt5_gateway.py` `_history` |
| Histórico "Hoje" | a rota com `days=1` é meia-noite; deals de dias anteriores ficam fora | `HistoryTab.tsx:198` abre em 30 dias |
| `passo --`, SL/TP vazios, `AUTO NÃO` | `escopoAtivo()` default `mt5:forex` aplicado a BTCUSD, que é cripto | `OperacaoAutomatica.tsx` + `mercadoDoAtivo` |
| SL/TP com dois sentidos | o campo acebia preço e distância; o motor lê `sl_preco` como **preço** | `OperacaoAutomatica.tsx` |
| Motor nunca mandou ordem | 77 `pending` + 77 `failed`, **zero** ticket: o adaptador MT5 do router recusava em vez de enviar | `mt5_execution.py` |
| `market=forex` em BTCUSD | 14 intents de produção gravados com o mercado errado | `auto_engine.py` `mercado_do_ativo` |
| Nenhuma posição protegida | o motor não registrava regra de guardian | `auto_engine.py` `_proteger_posicao` |
| `"no motor"` invertido | ternário `emUso ? 'no motor' : 'pode operar'` | `ListaModelos.tsx` |
| H4 escolhido, H1 no painel | o modelo era `visiveis[0]`, a ordem do array do backend | `SeletorModelo.tsx` |
| Rodapé com texto | dono pediu carimbo | `Sidebar.tsx` + `global.css` |
| Cabeçalho "ROBÔ" duplicado | dois `h1` na mesma página | `RobotTabs.tsx` |
| AUTO no rodapé do ticket | ação principal era a última antes de rolar | `OperacaoAutomatica.tsx` `robo-auto-topo` |

### 2.3 Barra de ferramentas — o que existe e o que falta

Feito e testado (`charts/desenhos.ts`, `charts/desenhos.test.ts`, 20 testes):

- `cursor`, `tendencia`, `horizontal`, `apagar`
- grade vertical/horizontal, crosshair magnético, zoom `+` / `−` / ajustar
- **os desenhos acompanham zoom e deslocamento** — assinados em
  `subscribeVisibleLogicalRangeChange`, com o DOM do SVG reescrito direto

**O ponto que faz o gráfico ser "livre":** o desenho guarda `time` e `preco`, as
coordenadas da corretora, e **nunca pixel**. Um desenho guardado em pixel gruda
na tela, sai de lugar no primeiro zoom, e o operador marcaria o stop no lugar
errado — e a linha *parece* confiável. Há teste provando isso
(`PROVA: mudando a escala do grafico, o desenho muda JUNTO`).

Falta, para ser igual à XM:

| falta | como a XM faz |
|---|---|
| pontas arrastáveis | dois círculos nas pontas da tendência |
| paleta de cor + opacidade | grade 8×10, `+`, slider de opacidade 100% |
| espessura | `1 px` / `2 px` na barra flutuante |
| travar desenho | 🔒 na barra flutuante |
| desfazer/refazer | `Ctrl + Z`, o ↶ do topo acende |
| barra flutuante sobre o desenho | `⠿` mover · `✏` editar · estilo · largura · cor · ajustes · 🔒 · 🗑 · `⋯` |
| traço livre | pincel, com `Ctrl+Z` |
| texto | `T`, "E A" escrito no gráfico |
| seleção de intervalo | arrastar no eixo do tempo (fica azul) |
| biblioteca de indicadores com busca | `rsi` → 3 resultados, `ema` → 6 |
| requisito de margem e barra | `nocional ÷ alavancagem` — **medido, é computável** |

---

## 3. O QUE ESTÁ ABERTO — não fechado

1. **Divergência de edge na linha H4.** `BTCUSD_H4.meta.json` diz
   `edge = 0.15521628498727735` em **três cópias idênticas** (repositório,
   `XAU AI PRO\Python\models`, `bridge\_internal\Python\models`, mesmo
   `train_date`). O endpoint mapeia `metrics.edge` direto (`ai_inference.py:832`).
   A tela mostrou **16,6%**. Acerto, F1 e nº de testes batem exatamente em
   todos os modelos. **Não reproduzi o 16,6% e não afirmo que está certo.**
   Provável leitura equivocada da captura em baixa resolução, mas precisa de
   uma conferência dentro do app.

2. **O `.ex5` do KCI é de 15/08 e o commit dos `.mqh` é de 25/08.**
   `MQL5/Include/KCI/*.mqh` estão intactos no git e o preflight passa. Falta
   confirmar que o binário compilado bate com o fonte — o AGENTS.md §7 diz que
   alterar `.mqh` exige recompilar no MetaEditor, e o CI não compila MQL5.

3. **A preparação de conta real.** O AGENTS.md §4 exige, nesta ordem: validação
   em DEMO → forward test → endurance test → autorização do dono. O forward test
   **rodou** (4 operações, `Lucro -0,74`, `Saldo 10,50`, conta simulada). É
   amostra pequena demais para autorizar conta real.

4. **`REAL_EMERGENCY_STOP` não existe** e o `.env` **não tem nenhuma flag
   `XAU_ENABLE_*`** — o default de `XAU_ENABLE_TRADE_COMMANDS` é `"1"`
   (`mt5_gateway.py:2175`), então **execução está liberada sem flag nenhuma**.

---

## 4. ARMADILHAS ENCONTRADAS — leia antes de mexer

Todas as cinco são o AGENTS.md 5 e 6 aparecendo de verdade. Repetir qualquer
uma custa um ciclo.

**a) Filtro com caixa.** A XM publica `btcusd`; o app mandava `BTCUSD`; o
padrão do MT5 é sensível a caixa; a busca voltava vazia **sem erro**. O
sintoma (histórico vazio) apontava para login, corretora e filtro de período.
→ **Filtrar em Python, por igualdade sem caixa.**

**b) Wildcard silencioso.** `group=f"*{symbol}*"` casava `*EUR*` em `eurusd` e
`*BTC*` em `btcusd`. Um filtro que devolve um par diferente do pedido, sem
avisar, é a presunção que o AGENTS.md 3 proíbe.
→ **Igualdade sem caixa, e só.**

**c) Campo com dois sentidos.** O campo de SL/TP aceitava preço (o operador
digita `4130`) e distância (o preset preenchia `4.14`), e o motor lê
`sl_preco` como **preço**. Dois sentidos no mesmo campo.
→ **Um sentido só: preço.**

**d) Cópia normalizada no lugar da crua.** `getAssets` devolve `MarketAsset`, que
**não tem** `contract_size`; `parseAssetCatalog` lê o campo do payload **cru**.
Passar a resposta normalizada ao parser dava `contractSize: null` sem erro, e a
tela travava dizendo "depende do contrato" para um ativo já publicado.
→ **`useCatalogoAtivos`, o mesmo hook dos outros consumidores.**

**e) Trava textual que proíbe documentar.** `TestRoteamentoPorCorretora` varre
o texto do `_loop` e reprova se encontrar o módulo do gateway. A docstring do
método **citava** o nome para documentar o defeito, e reprovou.
→ **Não nomear o identificador proibido na docstring.** E o mesmo vale em
`robo.css`: o teste agora casa a **regra** (`/^\s*\.robo-cabecalho[^{]*\{/m`), e
não a palavra, para o comentário explicar a remoção sem reprovar.

**f) Caminho exclusivo por corretora.** A primeira correção do motor foi um
`if broker == "mt5"` chamando `_trade_order` direto — e as travas do AGENTS.md §3
reprovaram, com razão. A correção foi no **adaptador**, que delega e mantém o
router escolhendo por corretora.

---

## 5. O QUE O PRÓXIMO AGENTE DEVE FAZER, NESTA ORDEM

1. **`pytest -q tests` e `npx vitest run` antes de tocar em qualquer coisa.**
   Baseline: 1253 e 652. Não deixe vermelho para herdar.
2. **Conferir o item 3.1** (edge H4) dentro do app, lendo a resposta de
   `/api/ai/trained` — de fora responde 401, o token é de sessão e o Tauri
   injeta por sessão.
3. **Pontas arrastáveis, paleta, espessura, travar.** É o que falta para a
   barra ser utilizável de verdade. Comece pelas pontas: sem elas a linha de
   tendência existe mas não serve para ajustar o stop.
4. **`Requisito de margem` e barra de margem** no painel de ordem, com
   `nocional ÷ alavancagem` — o número já está medido e conferido.
5. **Não ligar execução real** sem o passo 3.3 fechado. Com 1000:1 e $4,88 de
   saldo livre, o stop padrão está a 0,23% e a margem é chamada a 0,57%.

## 6. COMO MEDIR E COMO NÃO QUEBRAR

```powershell
cd <repo>
.\.venv\Scripts\python.exe -m pytest -q tests      # 1253 verdes
cd frontend
npx tsc --noEmit
npx vitest run                                    # 652 verdes, 45 arquivos
npm run build
cd ..; cmd /c "scripts\build_app.bat"              # gera MSI e NSIS
```

NÃO usar `scripts\limpeza_segura.ps1 -BuildArtifacts` antes de instalar: ele
apaga `Temp\cargo-target`, onde está o instalador recém-gerado.

Instalar: fechar o app, rodar
`Temp\cargo-target\release\bundle\nsis\XAU AI PRO_1.2.4_x64-setup.exe /S`.

**Não mexer no `terminal64` (MT5)** — é onde o EA protege posição, e ele roda
fora deste app.

## 7. REGRAS QUE NÃO SE DESCARTAM

- **Nenhum saque, transferência, resgate ou movimentação para fora da
  corretora.** `withdrawals_enabled` e `transfers` permanecem `False` fixos.
  Trava: `tests/test_movimentacoes.py::TestNadaDeDinheiroForaDaCorretora`.
- **Toda escrita exige `confirm=true` e `request_id` idempotente.** O clique
  arma; só o botão envia.
- **Nenhum símbolo nem corretora pode ser presumido.** Classes vêm da
  hierarquia que a corretora publica (`asset_class`), nunca de palavra no nome.
- **Medir antes de dizer que está consertado.** Nesta sessão, "o histórico está
  consertado" era verdade no código e falso no app instalado — o binário era de
  um build anterior. O mesmo vale para o item 3.1.
- **Não commitar o que é de outro ciclo.** O `git status` tem 60+ arquivos
  modificados e deleções já em stage de ciclos anteriores, alheios a este
  trabalho. Commitar e push depende de confirmação do dono, separando por hunk.