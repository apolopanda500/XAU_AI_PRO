# Sessao 04/10/2026 — App real, modelos x EA, conta XM 391773676

> Conta REAL XMGlobal-MT5 14 (STANDARD). Saldo $5.62 + credito $5.62.
> Regra da sessao: anotar tudo, corrigir de verdade. Risco manual do dono
> nao se toca (BUY 0.01 BTCUSD sem SL, decisao dele).

## Quem opera o quê (para validar no app)

| Caminho | Decide | Rota | Onde na tela |
|---|---|---|---|
| MODELOS | `.pkl` via `ai_inference` | Motor (`/api/auto/*`) -> `UniversalRouter` | Aba Robo: Automacao + Acompanhar |
| EA | `.ex5` no terminal | Heartbeat + `/api/ea/*` | EA / Sistema |
| Manual | operador | Mesa (`/api/trade/order`, MT5) | Mesa XM+MT5 |

## Feito nesta sessao

1. Painel simples: LOTE + SL + TP + AUTO (banca/risco/perdas/ATR fora).
2. SL/TP em preco cheio OU distancia (digitou 0.1/0.2: vira distancia;
   preco errado nao vira distancia absurda — trava metade do preco).
3. Piso de lote 0.01: conta de $1 opera.
4. `backend/symbols.py`: fonte unica de simbolo (todos os formatos).
5. `symbol_aliases.json`: `mt5: XAUUSD -> GOLD` (ouro XM STANDARD e GOLD).
6. Motor multi-alvos, slot com corretora, sem duplicar.
7. Ficha de especificacao por ativo (ideia da pagina da XM).
8. Acompanhar: marcadores no candle, posicoes desenhadas, EMA, 1-clique,
   TP/SL arrastavel estilo MT5.
9. Mesa XM+MT5: ticket sem seletor de corretora (o defeito antigo).
10. Build 1.2.4 reinstalado com tudo; bundle com 39 modelos.

## Validacao medida

- Python 962 passed · frontend 212 passed · tsc limpo.
- `order_check` GOLD 0.01 ao vivo: retcode 0, margem $4.14.
- Ouro cripto ao vivo: Binance PAXG 4145.8, Bybit/OKX XAUT ~4141.

## Pendente (fora do codigo)

- EA parado (heartbeat 02/10): reanexar no grafico.
- Exchanges sem chave API: so leitura publica.
- Gateway Python proprio so com app fechado (porta do bridge).
