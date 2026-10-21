<#--
  Captura de tela do XAU AI PRO — sem interferir no trabalho.
  ============================================================
  Uso:
    .\scripts\capturar_tela.ps1                        # 1 foto agora
    .\scripts\capturar_tela.ps1 -Segundos 10 -Vezes 6   # 6 fotos, 1 a cada 10s
    .\scripts\capturar_tela.ps1 -Pasta "$env:USERPROFILE\Pictures\Screenshots"

  Salva `Screenshot yyyy-MM-dd HHmmss.png` na pasta (padrao: a de Screenshots
  do usuario, onde o dono ja guarda as capturas do app). Nao clica, nao move
  janela, nao fecha nada: so le os pixels e grava o arquivo.
#>
param(
  [int]$Segundos = 0,
  [int]$Vezes = 1,
  [string]$Pasta = (Join-Path $env:USERPROFILE 'Pictures\Screenshots')
)

Add-Type -AssemblyName System.Windows.Forms, System.Drawing

if (-not (Test-Path -LiteralPath $Pasta)) {
  New-Item -ItemType Directory -Path $Pasta | Out-Null
}

function Capturar-Uma {
  $limites = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  $bmp = New-Object System.Drawing.Bitmap($limites.Width, $limites.Height)
  try {
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    try {
      $g.CopyFromScreen($limites.Location, [System.Drawing.Point]::Empty, $limites.Size)
    } finally {
      $g.Dispose()
    }
    $nome = "Screenshot $((Get-Date).ToString('yyyy-MM-dd HHmmss')).png"
    $caminho = Join-Path $Pasta $nome
    $bmp.Save($caminho, [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output "ok: $caminho"
  } finally {
    $bmp.Dispose()
  }
}

for ($i = 1; $i -le $Vezes; $i++) {
  Capturar-Uma
  if ($i -lt $Vezes -and $Segundos -gt 0) {
    Start-Sleep -Seconds $Segundos
  }
}
