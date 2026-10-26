# 22/10/2026 — Modelos: 0 de 40 têm edge medido

> Ciclo anterior: [`CONVERSA_20261022_BATERIAS_FIXADAS_CI_VERDE_E_DEPLOY.md`](CONVERSA_20261022_BATERIAS_FIXADAS_CI_VERDE_E_DEPLOY.md).
> Este documento existe porque a medição de hoje **contradiz** o número que
> estava publicado no catálogo e precisa ficar escrita antes de qualquer
> decisão sobre publicar ou não.

## O que foi pedido

Reconstruir os modelos e revalidar todos, "para validar de verdades", com a
meta de "todos aptos operar".

## O que foi medido

### 1. Base de dados nova, real, do MT5

`scripts/exportar_dataset_mt5.py` exporta M5 do terminal em páginas de 50.000
barras (120.000 reprova com `(-2, 'Terminal: Invalid params')`), layout de 15
colunas, dedupe por `(Time, Symbol)` mantendo o mais novo, escrita atômica.

`..\Data\dataset_mt5_20261022.csv` — **700.000 linhas únicas**, 7 símbolos
(100.000 barras cada), de 16/05/2025 (XAUUSD) e 19/06/2025 (fiats) até
23/10/2026. BTCUSD e ETHUSD não existem no MetaQuotes-Demo: esses dois
continuam só com o dataset antigo.

### 2. Dois defeitos de medição encontrados e corrigidos

O retreino inicial deu `+0,16`/`+0,17` de edge em **todos** os fiats, em todos
os timeframes. Era falso, por duas causas independentes:

| Defeito | Efeito medido | Correção |
|---|---|---|
| `reamostrar("M5")` retornava antes de derivar indicadores (`if alvo == base: return`) | export do MT5 traz `ATR = 0`; `atr_seguro` cai no piso `1e-9`; o alvo perde a faixa NEUTRA: **{2: 0,508, 0: 0,492, 1: 0,000}** | caminho M5 passa por `_derivar_indicadores` |
| `_derivar_indicadores` pulava a coluna inteira quando **qualquer** valor era diferente de zero | no dataset combinado 98,8% das linhas têm zero, então a coluna era pulada e ficava zerada | preenche **linha a linha** (`isna | ==0`), derivando só o que falta |
| edge comparado contra `1/3` | acurácia 0,50 num alvo 50/49/1 virava "+0,17 de edge" sem prever nada | palpite = **classe majoritária** da fatia de teste |

Depois da correção, `XAUUSD M15`: `ATR zero = 0,000`, `ATR mediana = 4,23`,
alvo `{2: 0,408, 0: 0,393, 1: 0,198}`.

Provas negativas (as duas baterias reprovam com o código antigo):

- `tests/test_timeframe_m5_deriva_atr.py` — mede que o caminho antigo devolve
  classes `{0, 2}` e neutro `0,0`; 4 testes.
- `tests/test_train_v2.py::test_palpite_e_a_classe_majoritaria_e_nao_1_por_classe`
  — com alvo 90/10, o palpite tem de passar de 0,80 (o `1/3` antigo reprova).

### 3. Resultado do retreino honesto: **0 de 40**

`scripts/treinar_ia.py --dry-run` com 831.665 linhas únicas (legacy +
`dataset.csv` + MT5), 5 folds cronológicos, `min_edge = 0,05`:

```
publicados: 0 de 40 combinacoes
Nenhum modelo passou na porta de qualidade.
```

Melhores edges por símbolo (M5 / M15 / H1 / H4):

| Símbolo | M5 | M15 | H1 | H4 |
|---|---|---|---|---|
| AUDUSD | −0,029 | +0,008 | −0,016 | +0,002 |
| BTCUSD | −0,001 | −0,000 | −0,023 | −0,008 |
| ETHUSD | −0,015 | −0,000 | −0,018 | −0,073 |
| EURUSD | −0,040 | +0,010 | −0,013 | −0,095 |
| GBPUSD | −0,056 | +0,036 | −0,030 | −0,007 |
| NZDUSD | −0,030 | +0,019 | +0,018 | −0,059 |
| USDCAD | −0,006 | +0,037 | +0,019 | −0,064 |
| USDJPY | −0,027 | −0,000 | +0,002 | +0,017 |
| XAUUSD | −0,018 | −0,027 | +0,022 | −0,041 |

Nenhum fold estável (a porta exige 4 de 5 folds positivos). O maior número da
tabela é `+0,037` (USDCAD M15), abaixo do mínimo `0,05`.

### 4. O problema é o dado, não a floresta

`scripts/estudo_sinal.py` compara a regra mais simples possível — "subiu nas
últimas k barras, compra", janela escolhida **no treino** — com a mesma
classe majoritária do teste:

| | |
|---|---|
| combinações medidas | 32 (8 símbolos × 4 timeframes) |
| com edge positivo | **1** (USDCAD H4, +0,0685) |
| esse único, em tercos independentes | −0,036 / +0,053 / +0,042 |

Com 32 testes e limiar de 0,05, um positivo por acaso é o esperado; o próprio
candidato falha no primeiro terço. Não é sinal.

Autocorrelação do retorno normalizado por ATR (lags 1, 6, 24, 48) em 21
séries: **|r| máximo = 0,046**, e a única estrutura consistente é
**autocorrelação negativa** de lag 1 no M5 (−0,02 a −0,036) — bounce de
bid/ask, que não paga o spread (18 pontos ≈ 1,8 pips no EURUSD contra
~0,2 pip de movimento típico).

Conclusão medida: neste dado, neste alvo (direção do próximo candle,
normalizada por ATR, 3 classes) e nestes horizontes, **não há sinal
direcional**. Trocar de modelo não cria sinal; mexer no limiar de publicação
só publicaria ruído — o que o AGENTS proíbe.

## Estado do catálogo (importante)

- `Python/models` tem 39 artefatos, **28 com `publicable = true`**.
- Esses 28 foram gravados com o baseline `1/3` e sem o dataset do MT5. O edge
  deles está, portanto, **~0,06–0,07 acima do real** — é o mesmo defeito que
  produzia o `+0,17` acima.
- O retreino honesto está em `--dry-run`: **nada foi gravado**, o catálogo não
  mudou.
- Ou seja: o número `28 publicáveis` que o app mostra hoje **não sobrevive à
  régua corrigida**.

## O que foi feito no resto da sessão (medido)

| Item | Prova |
|---|---|
| Tema claro em tabelas e grades | `frontend/src/theme/light_tabelas.test.ts` 5 testes; `light_legivel` + `robo_limites` = 9 passed |
| Tokens `--panel-2`/`--surface`/`--surface-2` que nenhum tema definia | adicionados em `:root`, aliasando `--panel2`/`--panel` |
| Painel de login automático do MT5 | 13 testes de autostart + 47 de endpoints |
| Arte dos cards por classe | `AssetArt.test.tsx` 4 testes |
| Exportador MT5 | `test_exportar_dataset_mt5.py` 4 testes |
| Suíte inteira | **1513 passed, 9 skipped**; frontend **930 passed**; `tsc` exit 0 |

## O que NÃO foi feito e por quê

- **Não gravei os 25 modelos do retreino inicial.** Eles saíram do pipeline com
  o baseline defeituoso; gravar agora seria publicar número falso.
- **Não baixei `min_edge`.** Seria a única forma de "todos aptos operar" e é
  exatamente o que o AGENTS proíbe (afrouxar trava para parar de reprovar).
- **Não reescrevi o catálogo para 0 publicáveis.** Zerar o catálogo muda o
  comportamento do produto (a IA para de operar) e é decisão do dono, não do
  agente.

## 5. Alvo líquido de custo (pedido do dono, medido depois)

O dono escolheu testar o alvo que só conta movimento que paga o custo. Foi
implementado em `train_v2.construir_target(..., custo_rel=...)` +
`custo_rel_de_spread(df, ponto)`, com `treinar(..., ponto=...)`.

O custo é o **spread do MT5 em pontos** convertido pelo `point` real do
símbolo (`symbol_info(symbol).point`), medido em 22/10/2026:

| Símbolo | point | custo relativo típico |
|---|---|---|
| XAUUSD | 0,01 | ~0,01%–0,05% por operação |
| EURUSD/GBPUSD/AUDUSD/NZDUSD/USDCAD | 0,00001 | ~0,02%–0,03% |
| USDJPY | 0,001 | ~0,02% |

Comissão não está no dataset, então a medida é **otimista**.

Provas negativas (5 testes, `tests/test_alvo_liquido_custo.py`): degrau de
+0,06% com custo de 0,04% vira **NEUTRO**; sem custo o mesmo degrau era
**COMPRA**; movimento de +2% continua COMPRA; `ponto` 10x menor vale 10x menos.

Resultado (`scripts/estudo_alvo_liquido.py`, 28 combinações, alvo líquido):

```
publicaveis: 0 de 28
```

| Símbolo | M5 | M15 | H1 | H4 |
|---|---|---|---|---|
| XAUUSD | −0,060 | −0,018 | +0,024 | −0,046 |
| EURUSD | −0,056 | +0,015 | −0,016 | −0,113 |
| GBPUSD | −0,083 | +0,023 | −0,027 | +0,005 |
| USDJPY | −0,055 | +0,002 | −0,006 | +0,000 |
| AUDUSD | −0,057 | +0,018 | −0,021 | −0,005 |
| NZDUSD | −0,073 | +0,002 | +0,016 | −0,054 |
| USDCAD | −0,039 | +0,042 | +0,015 | −0,042 |

O padrão é o mesmo do alvo bruto, agora **pior e mais claro**: no M5 o modelo
perde 0,04–0,08 de acurácia contra a classe majoritária em todos os símbolos
(prevê direção onde a direção não paga o spread), e os folds mostram
degradação monotônica nos primeiros folds (−0,14 a −0,39). Os edges positivos
de M15/H1 aparecem só na fatia final — instabilidade, não sinal.

## Conclusão do ciclo

Duas réguas honestas (direção bruta e direção líquida de custo), 68
treinamentos, 32 testes de regra simples e 21 séries de autocorrelação
apontam para o mesmo lugar: **não há edge direcional neste dado, neste alvo,
nestes horizontes**. O catálogo de 28 publicáveis não sobrevive a nenhuma das
duas.

## Pergunta aberta para o dono

O alvo líquido de custo foi medido e também reprovou (0 de 28). Restam:

1. horizonte maior (8–24 candles) com banda neutra mais larga — ainda não
   testado e é o único que muda a relação sinal/ruído do rótulo;
2. histórico mais longo em H1/H4 (o export cobre 16 meses; H4 tem ~2.000
   candles, o que é pouco para 5 folds) — precisa de `copy_rates_range` ou de
   outro provedor;
3. aceitar 0 publicáveis e deixar a IA sem operar até existir modelo que bata
   a régua.

Qual vale investigar primeiro?
