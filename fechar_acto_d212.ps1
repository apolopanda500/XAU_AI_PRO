$base = 'C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\XAU_AI_PRO\EQUIPE'
$ids  = Join-Path $base 'IDS.md'
$lock = Join-Path $base 'LOCK.md'

$l1 = 'USADO | D | D-214 | ALFA | 23/11/2026 00:56:00 | CORRECAO DA FONTE DO TOKEN: aspa dupla parasita removida do .env (69 -> 68 caracteres); gateway 9027 reiniciado (PID 9572) a ler a fonte unica; health=200 e predict=200; EA recuperou com [AI] GATEWAY RECUPERADO'
$l2 = 'USADO | P1 | P1.13682 | ALFA | 23/11/2026 00:56:00 | MEDIDO: margem de 0.01 lote XAUUSD = 36.05 USD (alavancagem 1:100) e volume_min=0.01; conta real de 8.32 USD nao consegue abrir posicao em nenhum simbolo; bloqueio de capital, nao de configuracao'

Add-Content -LiteralPath $ids -Value $l1 -Encoding UTF8
Add-Content -LiteralPath $ids -Value $l2 -Encoding UTF8

$novo = @'
# LOCK DE OPERACAO - EQUIPE

- **ESTADO:** LIVRE
- **Ultimo dono:** ALFA
- **Libertado:** 23/11/2026 00:56:00
- **Acto:** D-212 (execucao parcial; ver `EQUIPE/ACTO_D-212_20261123.md`)
- **Feito:** 9 reattaches com o payload D-212; `.env` corrigido (aspa parasita); gateway 9027 com health=200 e predict=200; EA a receber IA.
- **Aberto:** conta do terminal em DEMO 113568614 (decisao do DONO); saldo real 8,32 USD insuficiente para 0,01 lote; escada P-208-C divergente do TP configurado.
'@
Set-Content -LiteralPath $lock -Value $novo -Encoding UTF8

'--- IDS tail ---'
Get-Content -LiteralPath $ids -Tail 2
'--- LOCK ---'
Get-Content -LiteralPath $lock -TotalCount 4
