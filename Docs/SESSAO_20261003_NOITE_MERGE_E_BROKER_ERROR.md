# Sessão 03/10/2026 (noite) — Causa raiz dos 4.246 `BROKER_ERROR` e o merge em `main`

> Complemento da tarde. Escopo: (1) mergear `develop` em `main`, que era o
> que resolvia o cron; (2) investigar por que o forward test não passa.
>
> **Branch:** `develop` + `main` · **Conta:** `MetaQuotes-DEMO`, intocada

---

## 1. Merge `develop` → `main` — feito, com 4 conflitos resolvidos ✅

`main` foi de `84a84c5` para **`46fd23b`**.

### Os conflitos eram 4 `package-lock.json` e nada mais

| Arquivo                                | Causa                                                   | Resolução               |
| -------------------------------------- | ------------------------------------------------------- | ----------------------- |
| `ai-text-demo/package-lock.json`       | deletado no `develop` (commit `6a0ff13`, "ciclo limpo") | **mantida a deleção**   |
| `aigateway/package-lock.json`          | idem                                                    | **mantida a deleção**   |
| `sandbox-quickstart/package-lock.json` | idem                                                    | **mantida a deleção**   |
| `backend/package-lock.json`            | alterado dos dois lados                                 | **versão do `develop`** |

> Zero conflito em código, em workflow ou em teste. Verificado por
> `git merge-tree` e por um merge de verdade num clone descartável — o que
> também evitou empurrar um merge quebrado.

### O que o `main` ganhou com o merge

| Item                                               | Estado em `origin/main` |
| -------------------------------------------------- | ----------------------- |
| `ref: develop` no `maintenance.yml`                | **6 ocorrências**       |
| passo "Diagnosticar branch"                        | presente                |
| `fastapi` / `uvicorn` no `requirements-ci.txt`     | presentes               |
| `pytest.ini` com `--basetemp=.pytest-tmp-basetemp` | presente                |
| `build_app.bat` com `/E` + trava MULTI             | presente                |
| `scripts/app_producao.bat`                         | presente                |

**O cron das 10:17 UTC está corrigido pela causa raiz.** Foi o merge que levou a
correção para onde o agendamento realmente lê.

### O que disparou

`deploy.yml:75` faz deploy de produção na Vercel quando `github.ref == main`,
e `docker-publish.yml` publica imagem. Foi uma decisão do dono, e o resultado
está no log do GitHub.

---

## 2. Os 4.246 `BROKER_ERROR` — causa raiz medida

O `Docs\MAPEAMENTO_10_10_VERIFICADO_20260930.md` registrou "3,4 erros de broker
por ciclo" e Reprovou a janela sem dizer **quais** erros. Fui medir o CSV real.

### O primeiro obstáculo: o CSV é UTF-16 LE

`MQL5\Files\Data\forward_test_events.csv` abre com `FF FE` — é o **mesmo
defeito de encoding** que a sessão de 02/10 achou no `dataset_legacy`. Lido
como UTF-8, `BROKER_ERROR` vira `B R O K E R _ E R R O R` e a contagem dá
**zero**. Foi por isso que a primeira leitura devolveu 0 e pareceu que o
problema não existia.

### O que os 4.246 são

| Código                 | Quantidade      | Significado          |
| ---------------------- | --------------- | -------------------- |
| **`EXEC_NO_MARGIN`**   | **4.165** (98%) | margem insuficiente  |
| `EXEC_RETRY_FAILED`    | 74              | retentativa esgotada |
| `EXEC_LOOP_DETECTED`   | 4               |                      |
| `EXEC_SPREAD_TOO_HIGH` | 3               |                      |

Ou seja: **não é "o EA reconectando a toda hora", que é como o documento de
30/09 descrevia.** É **margem esgotada**, e 98% dos casos.

### A distribuição por dia desmente "3,4 por ciclo"

| Dia           | BROKER_ERROR  |
| ------------- | ------------- |
| 24/08 a 03/09 | 0 a 2 por dia |
| **04/09**     | **938**       |
| 09/09         | 54            |
| **16/09**     | **801**       |
| **17/09**     | **1.452**     |
| **22/09**     | **918**       |
| demais        | 0 a 3         |

A média de 3,4 esconde **três dias de pico** e o resto quase limpo. Dividir
4.246 por 1.251 starts produz um número que não descreve nenhuma dessas manhãs.

### E a distribuição por hora fecha a causa

| Hora    | `EXEC_NO_MARGIN` |
| ------- | ---------------- |
| 01h     | 50               |
| 02h     | 24               |
| **03h** | **1.047**        |
| **04h** | **933**          |
| **05h** | **1.245**        |
| 06h–10h | 164 → 310        |
| 20h–21h | 2                |

**77% dos erros estão entre 03h e 05h** — a janela de **menor liquidez e
rolagem de swap** do Forex. Nos mesmos dias, `TRADE_OPEN` foi normal (25, 34 e
35 aberturas nessas horas). Não é o sistema semeando loucura: é a conta
demostrada ficando sem margem na hora em que o mercado fecha.

Os símbolos batem com a explicação: `GBPUSD` (757), `EURUSD` (644),
`NZDUSD` (631) — pares de spread baixo que concentram posição pequena.

### Os 535 eventos estão malformados

`Status: ERROR2026.08.31 03:50:08` — mensagem colada com a próxima linha, sem
quebra. São 535 de 29.684 (1,8%). Não muda a conclusão, mas o leitor de eventos
descarta essas linhas e qualquer contagem derivada delas fica baixa.

---

## 3. O que NÃO foi feito, e por quê

| Pendência                     | Por quê                                                                                                                                                                                    |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Corrigir a margem no EA**   | `.mq5` exige recompilar no `MetaEditor64` **e reanexar ao gráfico**. O MetaTrader do dono está aberto desde 14:24 com o EA em uso no treino. Mexer agora derrubaria o treino em andamento. |
| **Rodar o endurance 24h/72h** | São 24 h a 7 dias de relógio. Não cabe nesta sessão, e precisa do EA fixado antes — senão mede o defeito de margem outra vez.                                                              |
| **Aprovar a janela**          | Reprovar foi correto. O que muda é o **motivo**: não são 3,4 erros por ciclo, são 4.165 de margem esgotada em 3 madrugadas.                                                                |
| **Conta REAL**                | Por decisão do dono, **por último**. E o motivo está registrado: ele está treinando EA na `DEMO`.                                                                                          |

### Conta REAL: o que falta, medido

| Item                  | Estado                                                               |
| --------------------- | -------------------------------------------------------------------- |
| Conta corretora       | `MetaQuotes-DEMO` — credencial, não código                           |
| Trava de margem no EA | **não existe** (não há `OrderSend` nem checagem de margem no `.mq5`) |
| Forward test          | reprovado por margem                                                 |
| Endurance 24h/72h/7d  | nunca executado                                                      |

---

## 4. A regra que este ciclo confirma

> **Média não é distribuição.**

`4.246 / 1.251 = 3,4` é um número correto e um número inútil: ele descreve
uma média que **nenhum dia teve**. Os dias reais são 0, 0, 1, 938, 0, 0, 0,
54, 0, 801, 1.452, 0, 0, 918.

E a segunda metade:

> **Contagem zero pode ser erro de leitura.**

Os 4.246 "não existem" quando o CSV é lido como UTF-8. Era o mesmo defeito de
encoding do ciclo de 02/10, em outro arquivo. Nenhum teste cobria a leitura do
CSV do forward test.

---

_Documento de sessão. Precedência de leitura: `SESSAO_20261003_TARDE_BUILD_APAGAVA_MODELOS.md`._
