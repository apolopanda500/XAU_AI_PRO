# CONVERSA 11/10/2026 (manhã) — journal `AI: 0 falhas` como ERROR, e o build defasado

> Continuação de
> [`CONVERSA_20261010_VALIDACAO_COMPLETA_E_APROVACAO.md`](CONVERSA_20261010_VALIDACAO_COMPLETA_E_APROVACAO.md).
> Os números são medidos; onde um número daqui divergir do que o comando medir
> agora, **o comando vence** — corrija aqui.

## 1. O que o dono pediu

Ver a última screenshot de hoje, **corrigir os erros** que ela mostra e checar
**apps duplicados**.

A screenshot `Screenshot 2026-10-11 111844.png` (Terminal ao vivo, 11:18:44)
mostrava o journal poluído com 4 linhas `ERROR` por ciclo, **todas com contador
zero**:

```
11:18:36  ERROR  ME 0 ... XAU_AI_PRO (USDJPY,H1) File errors: 0
11:18:36  ERROR  IO 0 ... XAU_AI_PRO (USDJPY,H1) JSON errors: 0
11:18:36  ERROR  GE 0 ... XAU_AI_PRO (USDJPY,H1) Python errors: 0
11:18:36  ERROR  JE 0 ... XAU_AI_PRO (USDJPY,H1) Indicator errors: 0
```

## 2. Apps duplicados — MEDIDO, não presumido

| Medida | Valor |
|---|---|
| processos do app | **3** (XAU AI PRO, mt5-gateway, xau-ai-pro-core) |
| janelas com título XAU | **1** (`XAU AI PRO - Trading Desk`, PID 10060) |
| portas escutando | 9011 (gateway), 9002, 9003 |

**Não havia duplicata.** Um gateway, um core, uma janela. Nada a encerrar.

## 3. O erro `errors: 0` como ERROR já estava corrigido — mas o build está defasado

Duas descobertas independentes, ambas medidas:

1. **O código correto já existia no repo.** `classificarJournal`
   (`frontend/src/lib/journalKind.ts`) já tratava `errors: 0` → INFO desde
   10/10 (função `errosPluralDeclarados`), com teste em `journalKind.test.ts`.
   `UniversalLiveTerminal.tsx` já importa e usa o classificador.

2. **O app instalado roda build anterior.** Prova por **hash** e por **data**
   (AGENTS.md §7 — hash, não data, mas aqui os dois concordam):

   | Medida | Valor |
   |---|---|
   | hash `mt5-gateway.exe` instalado | `F215E488…18FDC` |
   | hash `mt5-gateway.exe` repo | `974D7FCA…CAB1B7` |
   | iguais | **NÃO** |
   | `journalKind.ts` modificado | 10/10 **21:17** |
   | `app.exe` instalado | 10/10 **17:16** |

   O fonte é 4h mais novo que o app. A tela de 11:18 pintava ERROR porque
   rodava a build antiga — **não era bug de código**.

## 4. O erro de código REAL, que a build nova ainda não cobria

A correção de 10/10 cobriu `errors: 0` (JSON/Python/Indicator). Mas o EA
(`HealthMonitorSummary()`, `Monitoring/HealthMonitor.mqh:762`) também emite o
dump do watchdog em **português**:

```
AI: 0 falhas
RSI: 23 falhas
```

Traçando `AI: 0 falhas` no classificador: `falhasDeclaradas` procura
`Failures:` (não casa), `errosPluralDeclarados` procura `errors:` (não casa),
`erroDeclarado` procura `Error:` (não casa) — e caía no passo 3, onde
`VEREDITO` casava a **palavra** `\bfalhas?\b` → **ERROR**. Mesmo defeito do §5,
terceira variante.

### A correção (frontend/src/lib/journalKind.ts)

Nova função `falhasModuloDeclaradas` (lê `<módulo>: <n> falhas`, o número
manda), integrada no passo 1 ao lado de `falhasDeclaradas`/`errosPluralDeclarados`:

```ts
function falhasModuloDeclaradas(linha: string): number | null {
  const m = linha.match(/\b\w+\s*:\s*(\d+)\s+falhas\b/i);
  return m ? Number(m[1]) : null;
}
```

Não casa `falhas=98` (sem `:`) — esse é o `[BACKUP]`, tratado pela etiqueta.

### Prova negativa (AGENTS.md §6)

Antes da correção, o teste novo `AI: 0 falhas e INFO, nao ERROR` **reprovava**
(`expected 'ERROR' to be 'INFO'`), com 24 passed / 1 failed. Depois: verde.

## 5. As medidas, depois

| Medida | Antes | Depois |
|---|---|---|
| `journalKind.test.ts` | 22 passed | **25 passed** |
| `UniversalLiveTerminal.journal.test.tsx` | 4 passed | **4 passed** |
| `tsc --noEmit` | exit 0 | **exit 0** |
| suíte vitest completa | — | **869 passed / 12 failed** |

### As 12 falhas NÃO são desta correção (comprovação §11)

Falhas em `ListaModelos`, `EconomicCalendarTab`, `RobotTabs` — sobre
`MULTI_METALS`/`METALS`, calendário e i18n. Os 3 arquivos rodam **isolados** e
falham **11 de 82** na mesma natureza. Os 6 arquivos (fonte + teste) já estavam
**modificados no working tree antes desta conversa** — não foram tocados aqui.
É o build defasado do §2 da conversa anterior (o contador novo com o backend
velho). Meu `journalKind` não aparece em nenhuma lista de falhas.

## 6. O que exige ação do dono

1. **Reinstalar com a pasta limpa** (§7): a correção só chega à tela depois de
   `Remove-Item "$env:LOCALAPPDATA\XAU AI PRO\bridge" -Recurse -Force` e rodar
   o instalador novo. Sem isso, o journal continua pintando vermelho no
   saudável.
2. **Reanexar o EA ao gráfico** (pendência de 10/10): os defeitos
   `HEALTH_WD_MODULE_TIMEOUT` e `RSI: 23 falhas` que apareceram às 08:07 **não
   existem no fonte atual** — vieram de um EA ainda mais antigo anexado.
3. **Commit**: o working tree está com 115 arquivos pendentes. Commitar é
   decisão do dono.
