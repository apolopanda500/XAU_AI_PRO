# REGRA DO CICLO — REBUILD SO NO FIM (2026-10-02)

Mudanca de metodo decidida pelo dono apos dois ciclos de ~40 min cada:

> _"vamos deixar rebuild para o final. isso leva muito tempo... toda hora tem
> erros. mudar forma de trabalhar URGENTE"_

## O PROBLEMA QUE A REGRA RESOLVE

O rebuild **nao testa nada**. Ele so empacota o que ja esta escrito. No ciclo
de 02/10 ele rodou **tres vezes** e **nenhum** dos tres achou os defeitos que
ele proprio escondia:

| Build | O que fez                 | Defeito que nao pegou                                   |
| ----- | ------------------------- | ------------------------------------------------------- |
| 1     | gerou instalador perfeito | `metas_vip` e `acesso` fora do bundle                   |
| 2     | gerou instalador perfeito | a rota `/api/vip/progress` nao existia no gateway local |
| 3     | gerou instalador perfeito | —                                                       |

O tempo do build foi gasto **empacotando o defeito**, nao em acha-lo. E cada
build leva ~40 min porque o `Temp\cargo-target` e recompilado a cada ciclo.

## A REGRA

**Nenhum build enquanto houver correcao pendente.** A ordem e sempre:

1. `pytest -q tests` — a suite inteira, nao um arquivo
2. `npx tsc --noEmit` + `vitest run` + `npm run lint`
3. `preflight.py` — tem que sair `EXIT=0`
4. `git push` nos dois remotos
5. **So entao**: `build_app.bat`, instalar, testar pelo atalho
6. Se o teste pelo atalho falhar, o ciclo **volta ao passo 1** sem build

O passo 6 e o que fecha o ciclo: build so quando nao ha nada mais a corrigir.

## POR QUE ISSO DA MAIS RESULTADO, E NAO MENOS

Um build de 40 min que pega zero defeito tem custo alto e informacao zero.
Com a regra, cada correcao e validada em **segundos** contra a suite, e o
build vira o que deveria ser: a **ultima** etapa, nao a primeira.

## O QUE SUBSTITUI O BUILD COMO PROVA

Estes testes existem exatamente porque a suite roda contra o **FONTE** e o
build roda contra o **EMPACOTADO** — e nada cobria a distancia entre os dois:

| Teste                               | Cobre                                     |
| ----------------------------------- | ----------------------------------------- |
| `tests/test_spec_gateway.py`        | modulo existe no fonte e entrou no `.exe` |
| `tests/test_rotas_gateway_local.py` | rota existe no gateway local (9001)       |

Os dois foram escritos porque o build **nao** acusou nada. Um build passa e
o app sobe quebrado; esses testes reprovam em **menos de 1 segundo**.

## DE QUE O DONO ACHOU ERRADO

Quando ele escreveu _"todas correcoes e melhorias nao foram atualizadas o app
esta com erros"_, a verificacao encontrou `metas_vip` e `acesso` ausentes do
bundle. **As correcoes estavam no fonte e nao no app.** Foi exatamente esse
padrao que os dois testes acima agora fecham.

## TAMBEM VALE PARA O TEMPO DE COMPILACAO

`Temp\cargo-target` fica **fora** do disco de codigo e **nao** e apagado entre
ciclos. O Rust so recompila o que mudou. Apagar esse cache e o que transforma
um ciclo de 40 min num de horas — e nao compra nada.

---

## 1. Estado medido em 02/10/2026
