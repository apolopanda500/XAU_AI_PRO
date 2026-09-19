$ErrorActionPreference='Stop'
$base='http://127.0.0.1:9001'; $s=Invoke-RestMethod "$base/api/status" -TimeoutSec 5
$source=Get-Content (Join-Path $PSScriptRoot '..\backend\mt5_gateway.py') -Raw
$checks=@(
 [pscustomobject]@{Name='MT5 conectado';Result=[bool]$s.terminal_connected},
 [pscustomobject]@{Name='EA heartbeat vivo';Result=[bool]$s.ea_heartbeat.live},
 [pscustomobject]@{Name='Conta identificada';Result=([int]$s.account.login -gt 0)},
 [pscustomobject]@{Name='Modo DEMO/REAL conhecido';Result=($s.account.mode -in @('DEMO','REAL'))},
 [pscustomobject]@{Name='Trava REAL ativa';Result=($source -match 'XAU_ENABLE_REAL_ORDERS')},
 [pscustomobject]@{Name='Produção liberada';Result=$false}
)
$checks | Format-Table -AutoSize
if($checks | Where-Object { -not $_.Result }){ exit 2 }
