# Instalar o XAU AI PRO 1.2.191 no PC — roteiro do DONO

> Este passo escreve em `%LOCALAPPDATA%\XAU AI PRO`, que fica **fora** das raizes de
> escrita do agente. Por isso o agente constroi, mede e prova o instalador, mas
> **nao executa** a instalacao. Quem executa e o dono. Nada aqui apaga dado de
> conta, posicao ou historico.

## 1. O que ja esta pronto e medido (13/11/2026 02:05)

| Artefato | Caminho | Bytes | SHA256 |
|---|---|---|---|
| Instalador NSIS (usar este) | `dist\installers\XAU AI PRO_1.2.191_x64-setup.exe` | 142 121 988 | `83553C5999E4AF1109D92310312B1469682F27B6A221E422C58B03207083B56E` |
| Instalador MSI (alternativa) | `dist\installers\XAU AI PRO_1.2.191_x64_en-US.msi` | 210 434 790 | `7F9E4E4B83872C5E5962569A01603B93688DA0AF0A09C41EC657FA9C22C61C54` |
| Executavel do app | `dist\installers\XAU AI PRO.exe` | 13 998 592 | `296EAE0213EA6A1390A0653D51684C8714715808CD3E59CF7949294A74959059` |
| Gateway que vai dentro | `dist\mt5-gateway\mt5-gateway.exe` | 28 759 944 | `C42E18F9408A7AC4B281BA969BEE08577075D25ED923F3B485832BFE55308A8F` |
| Gateway anterior (rollback) | `dist\mt5-gateway.bak_182\mt5-gateway.exe` | 28 759 944 | `3D1149F3D6441BFA4FF201158FA07F075B35C7BFF96EB983B8A179D868BBEC65` |

**Por que existe o passo 3 abaixo (a armadilha da bridge defasada).** O
`tauri.conf.json` empacota `bridge/**/*`, e o instalador NSIS compara a **versao
do arquivo** antes de sobrescrever. O gateway instalado e o novo declaram a mesma
versao de arquivo, entao o instalador pode pular a copia e deixar o gateway
**velho** em `%LOCALAPPDATA%\XAU AI PRO\bridge`. Ja aconteceu uma vez neste
projeto (frontend novo rodando com backend velho). Apagar a pasta antes e o que
torna o `exit 0` do instalador uma prova, em vez de uma suposicao.

## 2. Antes de instalar (conferir o que baixou/construiu)

```powershell
Set-Location "C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO"
(Get-FileHash "dist\installers\XAU AI PRO_1.2.191_x64-setup.exe" -Algorithm SHA256).Hash
```

Tem de sair `83553C59...B56E`. Se sair outro valor, **pare** — o arquivo nao e o
que foi medido.

## 3. Instalar

1. Feche o app **XAU AI PRO** pela janela (nao precisa fechar o MetaTrader 5).
2. Confirme que nao sobrou processo:

   ```powershell
   Get-Process -Name "XAU AI PRO","mt5-gateway" -ErrorAction SilentlyContinue | Format-Table Name,Id
   ```

   Se aparecer algum, feche-o pelo Gerenciador de Tarefas.
3. Apague a bridge instalada (e o que garante que o gateway novo entra):

   ```powershell
   Remove-Item "$env:LOCALAPPDATA\XAU AI PRO\bridge" -Recurse -Force
   ```

4. Rode o instalador:

   ```powershell
   & "C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO\dist\installers\XAU AI PRO_1.2.191_x64-setup.exe"
   ```

5. Ao final, **confira por hash, nao por data**:

   ```powershell
   (Get-FileHash "$env:LOCALAPPDATA\XAU AI PRO\bridge\mt5-gateway.exe" -Algorithm SHA256).Hash
   ```

   - `C42E18F9...08A8F` → o gateway novo entrou. **OK.**
   - `3D1149F3...EC65`  → o instalador nao sobrescreveu: repita o passo 3 e o 4.
   - arquivo ausente → a bridge nao foi instalada: copie com
     `robocopy "dist\mt5-gateway" "$env:LOCALAPPDATA\XAU AI PRO\bridge" /MIR`.

6. Prova de que o gateway instalado declara a versao certa (mesma medicao que o
   agente roda no artefato congelado):

   ```powershell
   Set-Location "C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO"
   .\.venv\Scripts\python.exe scripts\medir_artefato_gateway.py --exe "$env:LOCALAPPDATA\XAU AI PRO\bridge\mt5-gateway.exe" --porta 9123
   ```

   Esperado: `gateway_build : xau-ai-pro-1.2.191-universal-20261113`,
   `withdrawals_enabled = False`, `transfers_enabled = False`, `401` sem token e
   com token errado, `ordem execute=false -> 200 ... stage=validated`.

## 4. O que conferir na tela (aba ROBO) — criterio de aceite

Nao presuma a carteira: leia as posicoes abertas na hora. Medido em 13/11/2026 05:10Z:
**2 posicoes** abertas, ambas EURUSD buy (tickets `11381095235` e `11381273395`), cada uma com SL e TP.

| # | O que olhar | Aceite | Se falhar |
|---|---|---|---|
| 1 | Cabecalho da fonte das velas | diz **MT5** (nunca "yahoo"/"publico") | colete `%LOCALAPPDATA%\XAU AI PRO\gateway_autostart.log` e a pasta `Logs\` do terminal no instante da falha |
| 2 | OHLC da ultima vela | open/high/low/close **diferentes** (vela nao degenerada) | idem acima; vela degenerada foi o sintoma do fallback publico |
| 3 | Linhas de TP/SL | desenhadas sobre **todas** as posicoes abertas (medido: 2 EURUSD) | anote o par e o horario |
| 4 | Simbolo pedido | e o **par** (ex. `XAUUSD`), nunca o nome do modelo (`MULTI_METALS`) | se aparecer `MULTI_*`, o frontend nao e o novo |

Se 1–4 passarem, o ciclo fecha: o gateway 1.2.191, com o `mercadoCanonico` e o
`parNaTela` novos, esta no aparelho.

## 5. Rollback (se a aba ROBO piorar)

O app em si volta reinstalando o mesmo instalador. O gateway volta assim:

```powershell
Set-Location "C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO"
robocopy "dist\mt5-gateway.bak_182" "$env:LOCALAPPDATA\XAU AI PRO\bridge" /MIR
```

Depois disso a bridge volta a declarar `1.2.183` (`3D1149F3...EC65`). E por isso
que o `dist\mt5-gateway.bak_182` (484 MB) **nao** foi apagado.

## 6. O que NAO fazer

- Nao instalar com o app aberto (o arquivo em uso nao e substituido).
- Nao confiar em data/tamanho: os dois gateways tem **exatamente** 28 759 944 B.
  So o hash distingue.
- Nao apagar `dist\mt5-gateway.bak_182` antes de a aba ROBO passar nos 4 itens.
- Nao ha saque, transferencia ou movimentacao de saldo em nenhum passo deste
  roteiro — e nao deve haver.
