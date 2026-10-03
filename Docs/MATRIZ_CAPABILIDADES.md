# Matriz de capabilities por corretora e mercado

> Gerado por `scripts/gerar_matriz_capacidades.py` a partir de
> `backend/broker_registry.py`. **Nao editar a mao**: a fonte da verdade e o
> registro, e `--check` reprova se o arquivo estiver desatualizado.
>
> Dados publicos: 2026-10-01

## A coluna "Leitura" estava invertida (corrigido 01/10/2026)

O gerador preenchia a coluna "Leitura" com `read_only`, que vale
`not execution` (`broker_registry.py:178`) e significa **"não executa
ordem"**. Rotulado como "Leitura", isso invertia a verdade:

| | Antes (errado) | Agora |
|---|---|---|
| Corretora que **não** executa ordem | `OK` | depende de `public_data` |
| Corretora que **entrega** dado publico | `nao` | depende de `public_data` |

Como nenhuma corretora deste registro executa ordem nesta versão, **todas as
linhas exibiam "OK"** — o documento afirmava leitura confirmada para todos os
17 pares, e a evidência não sustentava nenhuma dessas afirmações.

A correção usa `public_data` (existe dado público sem credencial?), campo que
passou a ser exposto em `capability_matrix()`. A legenda também mudou: "OK"
prometia uma verificação que o script nunca fez. O script é derivado do
registro — ele **não** sonda as APIs, então a coluna responde "o que o registro
declara", nunca "o que foi testado agora".

Travado por `TestMatrizLeituraNaoInvertida` (4 testes), inclusive um que
reintroduziu o bug de propósito para provar que o teste pega a volta.

## Como ler

**A coluna "Leitura" responde a uma pergunta so: existe dado publico desta
corretora sem credencial?** Vem de `public_data` no registro.

- **sim**: a corretora expoe dado publico (cotacao, candles, catalogo) sem
  credencial. Isso **nao** significa que a resposta foi testada agora — e o que
  o registro declara.
- **nao**: a corretora nao expoe dado publico; leitura de conta depende de
  credencial configurada pelo operador.

Sobre o resto:

- **unavailable**: declarado honestamente pelo gateway. Ausencia de dado e
  declarada, nunca preenchida com valor inventado.
- **unsupported**: o adaptador nao implementa este endpoint para a corretora.
  O gateway responde com `status: unsupported` e lista vazia — nunca com `ok`
  e dado fabricated.

## Leitura de dados

| Corretora | Mercado | Leitura | Status | Capabilities |
| --- | --- | --- | --- | --- |
| `mt5` | `forex` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `account`, `positions`, `orders`, `history`, `journal` |
| `mt5` | `metals` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `account`, `positions`, `orders`, `history`, `journal` |
| `mt5` | `indices` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `account`, `positions`, `orders`, `history`, `journal` |
| `mt5` | `stocks` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `account`, `positions`, `orders`, `history`, `journal` |
| `mt5` | `commodities` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `account`, `positions`, `orders`, `history`, `journal` |
| `mt5` | `bonds` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `account`, `positions`, `orders`, `history`, `journal` |
| `mt5` | `crypto-spot` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `account`, `positions`, `orders`, `history`, `journal` |
| `mt5` | `crypto-futures` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `account`, `positions`, `orders`, `history`, `journal` |
| `mt5` | `other` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `account`, `positions`, `orders`, `history`, `journal` |
| `binance` | `crypto-spot` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `depth`, `trades`, `stats24h`, `account`, `positions`, `history` |
| `binance` | `crypto-futures` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `depth`, `trades`, `stats24h`, `account`, `positions`, `history` |
| `mexc` | `crypto-spot` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `depth`, `trades`, `stats24h`, `account`, `positions`, `history` |
| `mexc` | `crypto-futures` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `depth`, `trades`, `stats24h`, `account`, `positions`, `history` |
| `bybit` | `crypto-spot` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `depth`, `trades`, `stats24h`, `account`, `positions`, `history` |
| `bybit` | `crypto-futures` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `depth`, `trades`, `stats24h`, `account`, `positions`, `history` |
| `okx` | `crypto-spot` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `depth`, `trades`, `stats24h`, `account`, `positions`, `history` |
| `okx` | `crypto-futures` | sim | `active` | `assets`, `quotes`, `batch_quotes`, `candles`, `depth`, `trades`, `stats24h`, `account`, `positions`, `history` |

## Execucao

Nenhuma corretora executa ordem real nesta versao. `execution` esta vazio em
todas as linhas e `withdrawals`/`transfers` sao `false` em todas. Isso e
intencional: a ordem real depende de uma etapa explicita e separada, com conta
demo validada, teste de rejeicao, auditoria e kill switch conferidos.

## Corretoras ainda planejadas

| Corretora | Mercado | Status | Capabilities |
| --- | --- | --- | --- |
| `bitget` | `crypto-spot` | planejada | nenhuma |
| `bitget` | `crypto-futures` | planejada | nenhuma |
| `coinbase` | `crypto-spot` | planejada | nenhuma |
| `coinbase` | `crypto-futures` | planejada | nenhuma |
| `kraken` | `crypto-spot` | planejada | nenhuma |
| `kraken` | `crypto-futures` | planejada | nenhuma |
| `kucoin` | `crypto-spot` | planejada | nenhuma |
| `kucoin` | `crypto-futures` | planejada | nenhuma |

## Cobertura por familia de dado

| Endpoint | Dado | Onde funciona |
| --- | --- | --- |
| | |   | ` | a | s | s | e | t | s | ` |   | | |   | c | a | t | a | l | o | g | o |   | d | e |   | a | t | i | v | o | s |   | | |   | M | T | 5 |   | e |   | a | s |   | 4 |   | e | x | c | h | a | n | g | e | s |   | | |
| | |   | ` | q | u | o | t | e | s | ` |   | | |   | c | o | t | a | c | a | o |   | d | e |   | u | m |   | a | t | i | v | o |   | | |   | M | T | 5 |   | e |   | a | s |   | 4 |   | e | x | c | h | a | n | g | e | s |   | | |
| | |   | ` | b | a | t | c | h | _ | q | u | o | t | e | s | ` |   | | |   | c | o | t | a | c | a | o |   | e | m |   | l | o | t | e |   | | |   | M | T | 5 |   | e |   | a | s |   | 4 |   | e | x | c | h | a | n | g | e | s |   | | |
| | |   | ` | c | a | n | d | l | e | s | ` |   | | |   | v | e | l | a | s |   | p | o | r |   | t | i | m | e | f | r | a | m | e |   | | |   | M | T | 5 |   | e |   | a | s |   | 4 |   | e | x | c | h | a | n | g | e | s |   | | |
| | |   | ` | d | e | p | t | h | ` |   | | |   | b | o | o | k |   | d | e |   | o | f | e | r | t | a | s |   | | |   | 4 |   | e | x | c | h | a | n | g | e | s | ; |   | M | T | 5 |   | n | a | o |   | e | x | p | o | e |   | | |
| | |   | ` | t | r | a | d | e | s | ` |   | | |   | n | e | g | o | c | i | o | s |   | r | e | c | e | n | t | e | s |   | | |   | 4 |   | e | x | c | h | a | n | g | e | s | ; |   | M | T | 5 |   | n | a | o |   | e | x | p | o | e |   | | |
| | |   | ` | s | t | a | t | s | 2 | 4 | h | ` |   | | |   | e | s | t | a | t | i | s | t | i | c | a | s |   | 2 | 4 | h |   | | |   | 4 |   | e | x | c | h | a | n | g | e | s | ; |   | M | T | 5 |   | n | a | o |   | e | x | p | o | e |   | | |
| | |   | ` | a | c | c | o | u | n | t | ` |   | | |   | c | o | n | t | a |   | e |   | s | a | l | d | o |   | | |   | M | T | 5 |   | e |   | a | s |   | 4 |   | e | x | c | h | a | n | g | e | s | , |   | c | o | m |   | c | r | e | d | e | n | c | i | a | l |   | | |
| | |   | ` | p | o | s | i | t | i | o | n | s | ` |   | | |   | p | o | s | i | c | o | e | s |   | a | b | e | r | t | a | s |   | | |   | M | T | 5 |   | e |   | a | s |   | 4 |   | e | x | c | h | a | n | g | e | s | , |   | c | o | m |   | c | r | e | d | e | n | c | i | a | l |   | | |
| | |   | ` | h | i | s | t | o | r | y | ` |   | | |   | h | i | s | t | o | r | i | c | o |   | d | e |   | t | r | a | d | e | s |   | | |   | M | T | 5 |   | e |   | a | s |   | 4 |   | e | x | c | h | a | n | g | e | s | , |   | c | o | m |   | c | r | e | d | e | n | c | i | a | l |   | | |
| | |   | ` | o | r | d | e | r | s | ` |   | | |   | o | r | d | e | n | s |   | | |   | s | o | m | e | n | t | e |   | M | T | 5 |   | | |
| | |   | ` | j | o | u | r | n | a | l | ` |   | | |   | j | o | u | r | n | a | l |   | d | o |   | t | e | r | m | i | n | a | l |   | | |   | s | o | m | e | n | t | e |   | M | T | 5 |   | | |

## O que esta declarado e nao entregue

- **DOM e negocios recentes no MT5**: o terminal nao expoe book de ofertas via
  esta ponte. `/api/universal/depth?broker=mt5` responde `unavailable` com o
  motivo, e nao com lista vazia.
- **Conta em corretora de exchange** (Bybit, OKX, Binance, MEXC): exige
  credencial configurada pelo usuario via `backend/connection_store.py` com
  DPAPI. Sem credencial, o gateway declara `unavailable`; nunca tenta sem.
- **XM Global e demais corretoras MT5**: nao sao adaptadores separados. Toda
  corretora com terminal MT5 e acessada pelo adaptador `mt5`, que descobre os
  simbolos reais em `GET /api/assets`. XM Global, XM.COM, Pepperstone e
  qualquer outra MT5 funcionam pelo mesmo caminho.
