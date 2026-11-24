$p = 'C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO'
$tok = $null
foreach ($l in Get-Content (Join-Path $p '.env')) {
   if ($l -match '^\s*XAU_GATEWAY_TOKEN\s*=\s*(.+)$') { $tok = $matches[1].Trim().Trim('"').Trim("'") }
}
"token_len=$($tok.Length)"
$own = Get-NetTCPConnection -LocalPort 9027 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess
"listener_pid=$own"
if ($own) {
   $pi = Get-CimInstance Win32_Process -Filter "ProcessId=$own"
   "started=$($pi.CreationDate)"
}
"health=" + (curl.exe -s -o NUL -w '%{http_code}' -H "Authorization: Bearer $tok" 'http://127.0.0.1:9027/api/health')
"predict_xauusd_h1=" + (curl.exe -s -o NUL -w '%{http_code}' -H "Authorization: Bearer $tok" 'http://127.0.0.1:9027/api/ai/predict?symbol=XAUUSD&timeframe=H1')
'--- err.log tail ---'
Get-Content (Join-Path $p 'gateway_9027_err.log') -Tail 10 -ErrorAction SilentlyContinue
