# FILA RESTANTE — estado verificado em 05/10/2026

Documento de passagem. Sem data e sem hora de propósito: as regras valem para
sempre, os números não.

---

## REGRA DESTA FASE

Você pediu: **"faca tudo e deixe build para o final"**. Então nesta fase:
- **um item por vez**;
- **validação completa só no fim** (mas `tsc` a cada passo, porque código que
  não compila não é "pendente", é lixo);
- **build só depois de tudo**, com a suíte inteira rodando antes.

Motivo, e é o mesmo de sempre: cada ciclo anterior meu empilhou seis ou sete
mudanças e só no fim validou. Foi assim que passaram o gráfico preto, a trava
do AUTO, o par que não trocava, o "Acompanhar modelos" sem gráfico e a barra
de latência invisível.

---

## 1. CAUSA DA LATÊNCIA — PROVADA, não estimada

**Medido no código, sem build:**

| Fato | Onde |
|---|---|
| Toda rota GET exige `Authorization: Bearer` e tem **rate limit por minuto** | `backend/mt5_gateway.py:2792` `_autorizado()` |
| O token **é** injetado no `window.fetch` por um interceptor | `frontend/src/lib/tauri.ts:41` `installGatewayAuth` |
| A barra usava `fetch` cru e lia só `d.corretoras` | `frontend/src/components/LatenciaBar.tsx` |
| Em **429**, o corpo vem `{ok:false}` **sem `corretoras`** | idem |

**A cadeia do furo:** 429 → `d.corretoras` é `undefined` → `setMedicoes([])` →
`if (!medicoes.length) return null` → **a barra some da tela**.

**Consequência:** 401, 429 e "nenhuma corretora configurada" produziam a
**mesma** tela — um espaço vazio. O operador concluía que latência não existe.

**O que mudou:** a barra lê o **status antes do corpo** e distingue os quatro
estados, cada um com a sua frase: `medindo…` · `sem corretora` · `sem token`
(401) · `cota do minuto` (429) · `gateway fora`. **Ela nunca desaparece** — e
`cota do minuto` diz explicitamente que **não é corretora fora do ar**.

Ainda **não** confirmado dentro do app instalado: qual dos quatro estados é o
real em execução. Isso só o app aberto mostra.

---

## 2. SERVIDORES MT5 COMO CONTAS DISTINTAS

Você escolheu: **vários servidores viram contas distintas, sem credencial no
app**.

**Restrição medida:** o MT5 não expõe lista de servidores nem de contas.
`account_info()` devolve só a sessão atual, e os servidores ficam em
`accounts.dat`, cifrado. Trocar de servidor de verdade exige **autenticar**.

**O que foi feito:**
- campo **Servidor** deixou de ser `readOnly` e virou editável;
- o servidor entra no **rótulo** da conexão — é isso que faz
  `XMGlobal-MT5 14` e `XMGlobal-MT5 20` virarem duas linhas em vez de uma
  sobrescrever a outra;
- **conferência de divergência**: se o servidor digitado difere do servidor do
  terminal, a tela avisa e diz que a troca verdadeira acontece no terminal.

O app continua fail-closed: sem sessão do terminal aberta, o campo não conecta
nada. Dizer o nome do servidor não é autenticar nele.

---

## 3. CALENDÁRIO — 100% em PT-BR

**Medido antes:** o feed devolveu **82 eventos** e **61 títulos distintos (69
ocorrências) caíam fora** das 162 entradas escritas a mão. Cobertura: **16%**.

**Agora:** 224 entradas, cobertura **82/82 = 100%**, verificado contra o feed
real.

Também: bandeira **quadrada** (26/30/34 px, saturação 1,5) com o **nome do
país escrito ao lado**; fonte da tabela 12,8 → 13,4 px; botão **"Ontem"** que vai
direto ao dia e só aparece quando existe evento naquele dia.

**Três defeitos que os testes pegaram e a tela não mostraria:**
1. chaves com `m/m` **nunca eram consultadas** — o sufixo era removido antes da
   busca; corrigi, corrigi de novo errado, o teste fechou;
2. **sufixo duplicado**: "Preços das matérias-primas **(m/m) m/m**" — a guarda
   testava fim de string e a tradução escreve o sufixo dentro de parênteses;
3. eu perdia a instituição: "Preços das matéria-primas" sem o **ANZ**.

E um defeito **do teste**: a lista de palavras inglesas tinha `[a-z]*` e casava
`Sentiment` com **"Sentimento"**, acusando 16 títulos corretos.

---

## 4. FONTE PÚBLICA DE PREÇO

`backend/mercado_publico.py` — três fontes, **nenhuma com chave**, todas medidas
nesta máquina:

| Fonte | Cobre | Medido |
|---|---|---|
| Binance | cripto | 200 · **368 ms** · BTC **85821,95** |
| Yahoo | ouro, forex, cripto, índices | 200 · **578 ms** · ouro **4167,60** |
| Frankfurter | forex **diário** (só D1) | 200 · **77 ms** · EURUSD **1,1204** |

Ligado como **fallback declarado** em `_universal_candles`: só entra quando a
corretora **não devolveu vela**, e sempre com `fonte`, `fonte_url`,
`execucao: false` e `observacao`. Preço de terceiro **nunca** vira preço de
execução. Rota nova: `/api/publico/ohlc`.

**Não** validei contra as landing pages de `biquote.io`, `marginpad.io` e
`londonstrategicedge.com` que apareceram na pesquisa: sem documentação
versionada, e o gráfico do Robô é onde a ordem é montada.

---

## 5. ESTADO VERIFICADO

| Etapa | Resultado |
|---|---|
| `tsc --noEmit` | limpo |
| `vitest` | **395 passed** em 28 arquivos |
| `pytest` | **1144 passed, 1 failed** |
| MQL5 | **2 passed** |
| preflight | 2 avisos, nada bloqueante |

A única falha é `test_bundle_gateway_artefato`: ele **abre o executável já
gerado** e confere que todo módulo do backend está dentro. `backend/mercado_publico.py`
é novo, o `.spec` já o declara (o teste do spec passa), mas o executável em
disco é anterior. **Só um build fecha este teste** — e é exatamente o build que
você mandou para o final. Não foi contornado.

---

## 6. FILA QUE FALTA

1. ~~Causa da latência~~ **feita** (falta confirmar qual dos 4 estados ocorre no app)
2. **Preços ao vivo** — rota pública pronta e medida fora; falta o caminho instalado
3. Indicadores RSI, volume, EMA, com liga/desliga e valores
4. Mini barras inferior e lateral do gráfico, com função real em cada botão
5. Botão de IA para configurar risco ao vivo
6. Preços na tabela de operação automática + compactar mais
7. Sessões por classe — forex, cripto, índice, metais, fiat
8. Movimentações reconstruídas em 100% MT5
9. Acessibilidade — sub-aba com zoom e casas decimais de 1 a 5
10. **Build, instalação e validação final**