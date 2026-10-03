# Sessão 03/10/2026 (madrugada) — Cooldown de margem: o EA parou de insistir

> Complemento da noite. Escopo: item 1 do plano (a trava de margem no EA),
> depois de medir o CSV do forward test.
>
> **Conta:** `MetaQuotes-DEMO`, intocada · **MQL5:** 2 arquivos `.mqh`

---

## 1. O plano estava errado, e a medicao que mostrou isso

O ciclo da noite anterior registrou "falta trava de margem no `.mq5`". Fui
implementar e **a trava existia**, com 79 linhas, `OrderCalcMargin` nativo e
chamada no lugar certo:

```
Enterprise/MarginChecker.mqh      79 linhas, CheckMargin com OrderCalcMargin
Enterprise/SmartExecution.mqh:365 CMarginChecker::CheckMargin(...)
Enterprise/SmartExecution.mqh:373    return EXEC_NO_MARGIN;
Enterprise/SmartExecution.mqh:909 OrderSend(...)          <- so depois
```

**Os 4.165 `EXEC_NO_MARGIN` eram a trava funcionando.** Ela recusou a ordem.
O defeito nunca foi "não trava de margem".

## 2. O defeito real: insistir depois de recusado

| Medido no CSV (UTF-16, 24/08 a 02/10) | Valor |
|---|---|
| `EXEC_NO_MARGIN` | 4.165 de 4.246 `BROKER_ERROR` |
| Intervalo mediano entre recusas do **mesmo** símbolo | **2 a 3 s** |
| Menor intervalo observado | **0 s** |
| Maior rajada (mesmo segundo, mesmo símbolo) | **4** |

Margem esgotada não se resolve em dois segundos. Ela volta com swap, depósito
ou fechamento de posição. Tentar de novo a cada 2 s é trabalho garantidamente
perdido — e o log de 1.452 eventos num dia esconde o sinal que importa.

## 3. A correção

`Enterprise/MarginChecker.mqh`:

1. `CheckMargin` consulta o cooldown **antes** de calcular margem
2. cada `return false` chama `RegisterBlock` e abre uma janela
3. backoff exponencial por símbolo: 60 s → 120 s → 240 s → … → 3600 s
4. `EXEC_NO_MARGIN` deixa de ser ruído e vira estado

## 4. O erro que eu cometi dentro da correção

A primeira versão zerava `m_consecutive_blocks` quando a janela expirava. Por
simulação com a mesma lógica e os mesmos parâmetros:

| Variante | Recusas/dia (8 símbolos) |
|---|---|
| **zerando o contador** | **691.200** |
| mantendo o contador | **217** |

Zerar fazia a trava voltar ao estado inicial a cada 60 s, e o par
(60 s de espera + 1 recusa) se repetia ~1.080 vezes por dia. **A correção
mantinha exatamente a taxa do defeito** — e ainda assim o `.mq5` compilava
limpo e a suíte Python passava.

> Nenhum teste cobria isso: a suíte Python não compila MQL5, e o EA só
> executa com conta conectada. O defeito só apareceu porque **simulei a lógica
> antes de confiar nela**.

O contador agora zera por um evento **observável** — a margem ter voltado — e
não por um timer.

## 5. A prova

Simulação da lógica final (mesmos parâmetros do `.mqh`), 1,7 dia, 8 símbolos,
margem esgotada do início ao fim:

| | Recusas/dia |
|---|---|
| sem cooldown (comportamento medido) | 691.200 |
| **com cooldown** | **217** |
| | **redução de 3.191×** |

Outros cenários, todos verdes:

| Cenário | Resultado |
|---|---|
| Margem esgota → volta → esgota de novo | opera normalmente após recuperar (18.220 concessões na janela livre) |
| Bloqueio de `EURUSD` afeta `NZDUSD`? | **não** — bloqueio é por símbolo |
| 80 símbolos com limite de 64 | rastreia 64, sem escrita fora do array |

## 6. Um segundo defeito, pré-existente, encontrado na compilação

`Core/ExecutionEngine.mqh:278` usava `OrderSendResult()`:

```
error 256: undeclared identifier 'OrderSendResult'
Result: 2 errors, 3 warnings
```

`OrderSendResult()` **não existe em MQL5**. A linha veio do commit `dbdce10` e
**nunca compilou**: não havia `.ex5` versionado (`.gitignore:37`) para revelar
isso, e a suíte Python não compila MQL5.

Substituído por `GetLastError()` com tradução explícita do `ExecResult`:

```
CAUSA=margem insuficiente (erro_api=134, sem_margem=134)
CAUSA=spread alto demais (erro_api=27)
CAUSA=erro_api=4108
```

Isto faz o `BROKER_ERROR` **dizer a causa**, que era exatamente o que faltava
para o log de 30/09 não ser diagnosticável.

## 7. Compilação

```
MetaEditor64 /compile
Result: 0 errors, 0 warnings, 11231 ms
XAU_AI_PRO.ex5  419.654 bytes
```

Os 3 `warning 63` vieram de `ArrayResize` em array estático; resolvidos com
arrays de tamanho fixo (`MARGIN_COOLDOWN_MAX_SYMBOLS`), que é a forma correta
em MQL5 e evita `ArraySize` sobre array dimensionado.

## 8. O que NÃO foi feito, e por quê

| Pendência | Por quê |
|---|---|
| **Reanexar o EA ao gráfico** | Derruba o treino do dono na DEMO, que está em andamento. Compilar **não** reanexa — o `.ex5` novo só entra em vigor quando alguém trocar o EA no gráfico. |
| **Rodar o forward test novo** | Precisa do EA reanexado primeiro. |
| **Endurance 24h/72h** | Mesma razão, e são 24 h a 7 dias de relógio. |
| **Conta REAL** | Por decisão do dono, **por último**. |

> ⚠️ **O `.ex5` novo está no disco, mas o EA que está rodando é o velho.**
> Reverter o EA no gráfico (ou trocar por um `.ex5` antigo) traz os 2-3 s de
> volta. A correção só está ativa depois da reanexão.

## 9. A regra que este ciclo confirma

> **Simular a lógica antes de confiar nela.**

O `.mq5` compilava limpo, a suíte Python passava com 833 testes, e a correção
era **pior que o defeito**. Nada disso aparece sem executar a lógica — nem
compilador nem suíte pega um backoff que reseta no lugar errado.

E o par do ciclo:

> **Ausência de `.ex5` no git esconde compilação quebrada.**

`ExecutionEngine.mqh` esteve quebrado desde `dbdce10` e ninguém viu, porque o
artefato que prova a compilação não é versionado por decisão. O build do
repositório "não compila MQL5" (AGENTS.md), então o CI nunca vai pegar isso.

---

*Documento de sessão. Precedência de leitura: `SESSAO_20261003_NOITE_MERGE_E_BROKER_ERROR.md`.*