# Acto ALFA-004 — Decisão de execução: MT5 local por enquanto (23/11/2026)

## Decisão do DONO (verbatim)
> "nao vou usar o app versao pc e tambem apk versao android, ambos ainda faltam trabalhar para funcionar no EA expertesl, no caso vou precisar abrir o mt5 e rodar o EA POR ENQUANTO, ate colocar no vps ok"

## O que muda
- **Canal de operação agora:** EA no terminal MT5 local (Windows), 17 gráficos, conta real 391773676 (XM Global MT5 14).
- **App PC e APK Android:** suspensos como canal de operação — ainda falta trabalho para integrarem o EA/Experts. Não são mais pré-requisito para o forward real.
- **Gateway 9027:** continua necessário para a IA do EA (`/api/ai/predict`), com token de 68 caracteres (raiz `.env`). Ver ALFA-001.
- **Futuro:** migração para VPS — fora deste ciclo.

## Estratégia em vigor (ALFA-002 / v1.2.222-223)
- Banca < US$ 100 → CRESCIMENTO PURO, sem stop a subir (SL da entrada permanece).
- Banca média (≥100) → stop acima da entrada; banca grande → alvos maiores.
- Alvos curtos, acertividade alvo >90% (ainda **não medida** — ver ALFA-003).
- Até **20 posições simultâneas** em vários símbolos (decisão do DONO neste ciclo).
- `MaxOpenPositions=50` no código já acomoda 20; o bloqueio real é `[REAL GUARD] max posicoes SEM stop por simbolo = 1` (decisão pendente: subir ou manter 1 por símbolo/20 total).

## Pendências que o DONO ainda precisa decidir (ALFA-003 + este acto)
1. Posições sem stop por símbolo: manter 1 (total 20) ou subir?
2. `MaxCorrelatedTrades=3`: manter ou subir para acompanhar 20 posições?
3. Risco por trade: vivo = 1,00 USD (20,9% do saldo) vs teto 10% declarado — alinhar para `RiskPerTradePercent=0,50`?
4. Medidor de acertividade por trade fechado: implementar antes de medir os 90%?
5. Site 24/7: túnel Cloudflare (já criado) ou apenas local?

## Estado atual (medido)
- Gateway 9027: 200, IA respondendo (16 símbolos).
- Motor: desligado (`ativo=false`) — aguardando a ordem final de operação do DONO.
- `.ex5` produção intacto; posições abertas do DONO intactas.
- Nenhuma automação nova no Windows (DONO vetou tarefas agendadas).
