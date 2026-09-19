$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:9001'
function Get-Api([string]$path) { $r = Invoke-RestMethod ($base + $path) -TimeoutSec 5; if($null -eq $r){ throw "$path sem resposta" }; return $r }
$health = Get-Api '/api/health'
$capabilities = Get-Api '/api/capabilities'
$status = Get-Api '/api/status'
$assets = Get-Api '/api/assets'
$quote = Get-Api '/api/mt5/quote?symbol=XAUUSD'
$positions = Get-Api '/api/positions'
$journal = Get-Api '/api/journal?limit=5'
$history = Get-Api '/api/history?days=30&symbol=XAUUSD'
if(-not $health.ok){ throw 'Gateway health falhou' }
if(-not $capabilities.ok -or $capabilities.real_orders_enabled){ throw 'Capacidades ou trava REAL inválidas' }
if(-not $status.terminal_connected){ throw 'MT5 desconectado' }
if(-not $status.ea_heartbeat.live){ throw 'Heartbeat do EA ausente ou antigo' }
if($status.account.mode -notin @('DEMO','REAL')){ throw 'Modo de conta desconhecido' }
if([int]$assets.count -le 0){ throw 'Catálogo de ativos vazio' }
if([string]::IsNullOrWhiteSpace([string]$quote.symbol)){ throw 'Cotação XAUUSD ausente' }
if($null -eq $positions.positions){ throw 'Resposta de posições inválida' }
if([int]$journal.count -lt 1){ throw 'Journal MT5 sem linhas reais' }
if($null -eq $history.deals){ throw 'Histórico inválido' }
[pscustomobject]@{ Health='PASS'; MT5='PASS'; EA='LIVE'; AccountMode=$status.account.mode; Assets=$assets.count; Quote=$quote.symbol; Positions=$positions.positions.Count; JournalLines=$journal.count; HistoryDeals=$history.count }
