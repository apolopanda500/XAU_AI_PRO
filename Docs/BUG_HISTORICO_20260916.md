# Bug registrado: Histórico travado e PNL sem cores

Data: 2026-09-16
Área: frontend / aba Histórico
Severidade: alta

## Sintomas

- A aba Histórico aparenta travar quando MEXC ou Binance retornam 503.
- A tabela não mostra respostas parciais por corretora.
- Ganhos não ficam claramente verdes.
- Perdas não ficam claramente vermelhas.
- Valores de PNL com vírgula decimal podem ser interpretados incorretamente.

## Causa provável

- Consulta agregada aguardando fontes indisponíveis.
- Formatação numérica usando `Number()` sem normalização de vírgula/ponto.
- Instalador pode estar usando build anterior ao código corrigido.

## Correção esperada

- Usar respostas parciais com `Promise.allSettled`.
- Exibir erro individual de MT5, MEXC ou Binance sem bloquear as demais.
- Normalizar PNL local antes de comparar o sinal.
- Linha e célula de PNL positivas em verde.
- Linha e célula de PNL negativas em vermelho.
- Recompilar e reinstalar antes da validação final.

## Critério de aceite

Com uma corretora retornando 503, o Histórico continua utilizável; com PNL positivo e negativo, as cores aparecem corretamente; o filtro de período continua funcionando.
