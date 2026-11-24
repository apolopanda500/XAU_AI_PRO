# Reinicia o gateway de IA na porta 9027 lendo o token da UNICA fonte: .env
# Nao imprime o token; apenas o comprimento.
$ErrorActionPreference = 'Continue'
$p = 'C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO'
Set-Location $p

$tok = $null
foreach ($l in Get-Content (Join-Path $p '.env')) {
   if ($l -match '^\s*XAU_GATEWAY_TOKEN\s*=\s*(.+)$') {
      $tok = $matches[1].Trim().Trim('"').Trim("'")
   }
}
if (-not $tok) { 'FALHA: token nao lido do .env'; exit 1 }
"token_len=$($tok.Length)"

Get-NetTCPConnection -LocalPort 9027 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
   "matando_pid=$($_.OwningProcess)"
   Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

$env:XAU_GATEWAY_TOKEN = $tok
$env:XAU_GATEWAY_PORT  = '9027'

Start-Process -FilePath (Join-Path $p '.venv\Scripts\python.exe') `
   -ArgumentList '-m', 'uvicorn', 'backend.fastapi_gateway:app', '--host', '127.0.0.1', '--port', '9027' `
   -WorkingDirectory $p -WindowStyle Hidden `
   -RedirectStandardOutput (Join-Path $p 'gateway_9027_out.log') `
   -RedirectStandardError (Join-Path $p 'gateway_9027_err.log')

Start-Sleep -Seconds 10
$code = curl.exe -s -o NUL -w '%{http_code}' -H "Authorization: Bearer $tok" 'http://127.0.0.1:9027/api/health'
"health=$code"
$code2 = curl.exe -s -o NUL -w '%{http_code}' -H "Authorization: Bearer $tok" 'http://127.0.0.1:9027/api/ai/predict?symbol=XAUUSD&timeframe=H1'
"predict_xauusd_h1=$code2"
