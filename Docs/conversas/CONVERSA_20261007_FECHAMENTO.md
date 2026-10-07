# CONVERSA — 07/10/2026, da recuperação de corrupção ao build pendente

Registro do que foi pedido, do que foi medido e do que ficou aberto. Para o
**estado** e as **ações**, ler `../PASSAGEM_20261007_PRIMEIROS_PASSOS.md` — este
arquivo é a linha do tempo.

---

## 1. A CORRUPÇÃO

O pedido foi ler `Docs/` e continuar o trabalho. Ao medir, três arquivos
estavam **zerados** — bytes `0x00` do começo ao fim:

| arquivo | tamanho | recuperação |
|---|---|---|
| `.git/index` | 105.608 | `git read-tree HEAD` |
| `.git/refs/stash` | 41 (espaços) | **não recuperável** — o stash foi perdido |
| `frontend/.../PriceChart.tsx` | 19.157 | **source map do `dist`** de 20:47 |

O `.tsx` tinha **o mesmo tamanho** do `HEAD`, e o `git diff` dizia
`Bin 19157 -> 19157 bytes` — que parece "arquivo binário", não arquivo
destruído. A cópia boa estava em três lugares; o `.map` do build era o mais
novo e o mais completo (71.001 bytes).

**Se tivesse seguido a leitura de "binário modificado" e feito `git checkout`,
teria perdido 24 horas de uma vez** — porque o `HEAD` não tinha `modoOrdem`.

## 2. O QUE FICOU SEM CÓPIA

`BarraFerramentas.tsx` (21:40) e `PriceChart.desenhos.test.tsx` (21:40) são
**mais novos** que o build de 20:47. A barra ganhou 10 props que a versão
restaurada não passava.

**Perdi a ligação, não o código**: `desenhos.ts` tinha todas as funções, a
barra tinha todos os botões. Só o `PriceChart` que os conectava não existia
mais. **Os 19 testes que reprovavam eram a especificação** — foram eles que
disseram o que reconstruir.

Implementado nesta sessão, com os 19 em verde: pontas arrastáveis · seleção ·
paleta por desenho · espessura · opacidade · trava (com guarda no
`mousedown`) · desfazer/refazer por **lista** e não delta · `Ctrl + Z` na raiz.

## 3. "O HISTÓRICO DEMORA CARREGAR"

O dono pediu duas coisas: a demora, e que o app não ficasse **dependente do
MT5 ligado**.

**MEDIDO antes de corrigir**, porque o sintoma apontava para a rede:

```
history_deals_get 1 dia / 30 / 90 / 3650    0,1 ms  (os quatro)
copy_rates BTCUSD H1 300                   4,5 ms
copy_rates BTCUSD M5 300                  79,6 ms
```

Dez anos respondem no mesmo tempo que um dia. **O MT5 não era o gargalo.**

A demora era a tela mentindo: `if (busyRef.current) return` **descartava** a
requisição quando o filtro mudava durante um carregamento. Digitar `BTCUSD` são
seis eventos de teclado, e cinco buscas foram jogadas fora.

E a dependência: com o terminal fechado, `deals: []` é **o mesmo payload** de
uma conta sem operação, e a tela dizia "Nenhum registro no período" — uma tela
de **sucesso** com zero linhas.

Corrigido nos três lados: produtor declara `connected`, hook expõe
`desconectado`, tela diz **o que fazer**.

## 4. O REQUISITO DE MARGEM QUE O CICLO ANTERIOR RECUSOU

O dono mandou corrigir "tudo que está faltando em relação a XM, MT5 e XAU AI
PRO".

A XM mostra `Requisito de margem $0.85`. O ciclo anterior recusou, e escreveu
que a alavancagem *"é um número que a corretora calcula e que o app não tem de
onde ler"*.

**A corretora publica.** MEDIDO nos dois lados: painel `Gerir` da XM diz
`Alavancagem 1000:1`; `account_info().leverage` devolve `1000`.

E a conta confere: `0,01 × contract_size 1,0 × 85.376,63 = 853,77`, e
`853,77 ÷ 1000 = 0,85` — que é o `$0.85` da XM.

**O motivo do ciclo anterior estava certo; a conclusão, errada.** O número não
era estimativa: era a conta, ainda não lida.

`contract_size` é obrigatório junto: BTCUSD tem `1`, EURUSD `100.000`, GOLD
`100`. Com palpite de `1`, o número estaria **certo por coincidência no
BTCUSD** — e quem conferiu ali não conferiria no forex.

**A barra de margem ficou de fora, por decisão**: é `requisito ÷ margem livre`,
e a margem livre muda a cada tique.

## 5. O INSTALADOR NOVO — FEITO, E DEPOIS FICOU DEFASADO

`build_app.bat` exit 0 em 7/7. NSIS 230 MB, MSI 356 MB. Desinstalado o
antigo, instalado o novo, rodado pelo atalho: gateway `mt5-gateway.exe`
PID 9348, core 6368, portas 9001/9002/9003, `preflight` todo `[ok]`.

**O estado do usuário sobreviveu** — o NSIS não toca `%APPDATA%\XAU_AI_PRO`.

## 6. O QUE O APP INSTALADO MOSTROU

O dono mandou screenshots do app novo. **Quatro defeitos, medidos na tela:**

1. **Gráfico vazio** — `Identidade de mercado inválida` / `sem candles reais
   para .` O ponto final é o **período vazio** chegando no `PriceChart`, e o
   rodapé dizia `BTCUSD · — ·`.
2. **`AUTO NÃO` de novo** — o mercado do par tinha sumido do painel.
3. **Campo SL espremido a ~10 px**, com o rótulo em coluna de **um caractere**.
4. **12 registros** na tela contra 11 deals do MT5.

**O 4 era um erro meu de leitura:** medi 11 deals às 00:30 e a conta continuou
operando — entrou mais um. A reconciliação fecha (§7).

O 1 e o 2 eram **a mesma causa**: `AcompanharModelos` lia só `auto.market` e
`auto.timeframe`, e o motor começa sem par. **AGENTS.md §5 na forma que o
próprio arquivo documenta com 40 linhas** — dois componentes, o mesmo dado, uma
versão com reserva e outra sem.

O 3 era **do grid, não do componente**: `minmax(0, 1.35fr)` permite a coluna
chegar a zero, e o grid serve primeiro as colunas `auto`, que têm conteúdo
intrínseco.

## 7. A RECONCILIAÇÃO — EU ERREI, E O DONO ME FAZEU MEDIR DE NOVO

Às 00:30 me relatei: *"faltam $5,11 sem deal"* — com três hipóteses (saque,
margem retida, sessão diferente) e **nenhuma confirmada**.

O dono mandou o log do Strategy Tester. **A conta fechava:**

```
soma dos 19 deals = +9,56
balance + credit  = 3,94 + 5,62 = 9,56   ← bate
equity            = 9,56                 ← e o equity É a soma
```

**Não faltava dinheiro. Faltavam deals** — a conta operava enquanto eu media, e
eu comparei uma soma antiga com um saldo novo.

É o **AGENTS.md §5 aplicado a mim mesmo**, e na forma mais humilhante: relatei
um número com três hipóteses, e a resposta era a mais boba. **Para conta ativa,
a conferência é o `equity`.**

## 8. GOLD

O dono: *"vamos acompanhar a corretora GOLD"*.

MEDIDO: o catálogo publica **`GOLD`** com `contract_size = 100`;
**`XAUUSD` não existe** no terminal XM; os artefatos do app são
`XAUUSD_H1/H4/M15/M5`.

O alias **já existia** — `symbol_aliases.json` tem `{"mt5": {"XAUUSD": "GOLD"}}`,
e o gateway o aplica em candles, cotação, ordem e inferência. **O que não
existia era o sentido na tela.**

Corrigido nos dois lados: o produtor declara `model_symbol`, e `fichaDoAtivo`
busca por `symbol` e depois por `modelSymbol` — **nessa ordem**, porque com
`modelSymbol` primeiro um ativo receberia a ficha de outro, e em forex isso é
100.000× o preço, silencioso.

## 9. O BACKTEST QUE O DONO NÃO QUIS RODAR

O log do Strategy Tester estava no caminho e respondia GOLD:

| | medido |
|---|---|
| par | `GOLD, M5` |
| duração | 4h26min33s · 15.020.685 ticks |
| operações | **923** (491 wins / 417 losses) |
| WinRate | **53,20%** |
| Profit | **−334,01** |
| PF | **0,48** |
| Sharpe | **−9,31** |
| perfil | `SL=80 · TP=160` — **1:2** |

**53,20% de acerto com PF 0,48** é a assinatura de stop curto com alvo longo.

E o binário medido é de **23/09**, de uma pasta **fora do repositório**. Decisão
do dono: **não rodar** — 4h30 medindo o binário velho não diria nada sobre o
código de hoje.

O log também acusa: `SendNotification falhou | Erro=4014`, `Failed=14394`.

## 10. A TRAVA QUE PROÍBIA DOCUMENTAR

O teste *"o mapa é config e o código não tem nome de ativo"* reprovou **no texto
que documentava a medição**. É o AGENTS.md §4e: **trava textual que proíbe
documentar é o defeito, não a proteção.**

Corrigido com `tokenize` (não regex: `#` dentro de string não é comentário).
**A regra do §3 foi mantida; o que mudou foi o teste.**

## 11. O QUE FICOU PARA O PRÓXIMO

1. **Build** — o app instalado é anterior a quatro correções.
2. **Verificar na tela** — gráfico, ouro pelo `GOLD`, SL/TP lado a lado,
   requisito de margem, pontas, paleta, `Ctrl + Z`, histórico.
3. **Indicadores com busca** — `rsi` → 3 resultados, como a XM.

**E o item que não é do app:** a conta real **opera com o app desligado**.
4 perdas de ~1,50, todas `[sl …]`, stop de 0,23% a 1000:1. Com $3,94 de saldo
livre, três stops comem 15% da conta.

---

## MENSAGENS QUE MUDARAM O RUMO

| o dono disse | o que mudou |
|---|---|
| *"olhar imagens"* | 48 capturas da XM e do MT5 viraram **medida**, e o `market.css` deixou de ser opinião |
| *"agora juntar todas imagens e corrigir 10/10"* | o caminho virou: comparar, listar, corrigir por ordem |
| *"o historico demora carregar"* | mediu-se que **a rede não era o gargalo** (0,1 ms) e o defeito era do cliente |
| *"falta pouco. ok 10/10"* | parou de aceitar "quase" e passou a exigir prova |
| *"validar tudo um por um… nada morto ou fingindo"* | commit com 157 arquivos, e o teste de código morto como criterion |
| *"não roda backtest e continuar validação antes da build"* | poupou 4h30 medindo o binário de setembro |
| *"vamos acompanhar a corretora GOLD"* | o alias passou a ser o caminho, e não o palpite |
| *"salvar toda conversa"* | este arquivo |

## O QUE EU ERREI, E O QUE CUSTOU

| erro | custo | como ficou registrado |
|---|---|---|
| Tratar `.tsx` zerado como "binário modificado" | quase perdeu 24 h | `AGENTS.md` §14 |
| `git checkout` do `HEAD` seria o caminho "natural" | idem | `AGENTS.md` §14 |
| Comparar soma antiga com saldo novo | relatei $5,11 inexistente | `PASSAGEM_20261007` §2.1 |
| Ler 11 deals às 00:30 e concluir "falta 1 registro" | accusei a contagem | `PASSAGEM_20261007` §1 |
| Ler "11 deals" como "12 é bug" | tempo de um ciclo | idem |
| Falar "fiz 10/10" com o binário defasado | o dono precisou mandar print | `PASSAGEM_20261007_PRIMEIROS_PASSOS` §4 |
| Escrever trava que proíbe documentar | um ciclo | `AGENTS.md` §6.4 |

**A lição que atravessa todos: medir antes de dizer. Das sete vezes, as duas em
que eu não medi custaram ciclo — e nenhuma delas foi o código.**