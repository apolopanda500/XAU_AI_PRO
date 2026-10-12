# Conversa 11/10/2026 — sub-abas duplicadas, sr-only, gráfico, plano

> Estado medido ao fim do ciclo. Números medidos na máquina; se divergirem do
> que o comando mostrar, o comando vence.

## O que o dono reportou

Capturas em `C:\Users\Micro\Pictures\Screenshots` (12:24–12:29, MT5 fechado
12:02–12:27): "sub abas duplicadas", "0 candles", "Gráfico indisponível:
candles ausentes ou inválidos no upstream" escrito POR CIMA de um gráfico com
300 candles desenhados, e motor AUTO recusado sem dizer onde ativar o plano.

## O que foi feito (com medida)

| Defeito | Antes | Depois | Trava |
|---|---|---|---|
| Sub-abas duplicadas | `OperacaoAutomatica` inteiro renderizado em Operação **e** em Risco (2× AUTO, 2× seletor de par, tabela de modelos 2×) | `visao: 'operacao' \| 'risco'`; risco renderiza só os limites abertos + `Aplicar limites ao motor`; `ListaModelos` saiu do painel e vive só na sub-aba Modelos | `RobotTabs.test.tsx` (36/36): Risco com 0 `.robo-auto-topo`, Modelos com a tabela só na aba certa |
| `sr-only` não-global | só `.market-page .sr-only`; 5 usages fora do escopo vazavam na tela | regra `.sr-only` global no fim de `global.css` | `theme/sr_only.test.ts` (3/3) |
| Erro de gráfico contraditório | poll de 30s gravava `erroVelas` por cima de candles já carregados | `erroDeVelas(motivo, temCandles)` (purа) + `textoDoAlertaDeErro`; `candlesRef` limpa ao trocar de identidade | `AcompanharModelos.grafico.test.tsx` (fake timers: aviso vira "Atualização falhou… mostrando os últimos candles", e **não** "indisponível") + `PriceChart.regras.test.ts` |
| Motivo falso de candles (gateway) | `_universal_candles` jogava fora o motivo de `_mt5_candles` e reembrulhava lista vazia → "candles ausentes ou inválidos no upstream" | `_leitura_mt5()` propaga `error` + `reason_code` da sessão ("terminal MT5 nao conectado ou nao autorizado" / "sem candles de X") | `tests/test_mt5_candles_diagnostics.py` (10/10, +3 novos) |
| Plano AUTO sem desbloqueio | 403 `PLAN_REQUIRED` virava "recurso nao liberado…: auto_engine"; frontend sem 1 consumidor das rotas `/api/subscriptions/*` | `SettingsCore` → nova aba **Plano** (`PlanoConfig.tsx`): catálogo/me/activate; `recusaDePlano()` em `ligar()` escreve "exige VIP ou VIPS — ative em Configurações → Plano" | `PlanoConfig.test.tsx` (4/4) + `RobotTabs.test.tsx` (+2) |

Backend: `backend/mt5_gateway.py` (`_universal_candles`).
Frontend: `OperacaoAutomatica.tsx`, `RobotTabs.tsx`, `AcompanharModelos.tsx`,
`PriceChart.tsx`, `SettingsCore.tsx`, `PlanoConfig.tsx` (novo),
`hooks/queries.ts` (`useAssinatura`, `usePlanosCatalogo`, `ativarPlanoLocal`),
`theme/global.css`, `theme/robo.css`, `theme/settings.css`.

## Validação (11/10, ~13:30–13:50)

- `pytest -q tests`: **1330 passed, 2 skipped** (era 1327).
- `npx vitest run`: **889 passed, 11 failed** — os MESMOS 11 pré-existentes
  (`ListaModelos.test.tsx` 1 + `EconomicCalendarTab.test.tsx` 10). Nenhum
  falha nova.
- `npx tsc --noEmit`: limpo.
- `scripts\build_app.bat`: completo (frontend, core 3m48s, gateway PyInstaller,
  NSIS+MSI).
- Instalação: app parado → `bridge` apagado → NSIS `/S` →
  hash `mt5-gateway.exe` instalado **=** repo
  (`2EDC5BEB4B45F09267892EE055E5E318BCF18696C3FE8A927B76ABDD3E12F55B`).
- App reiniciado: `XAU AI PRO`/`mt5-gateway`/`xau-ai-pro-core` no ar, portas
  9011/9002/9003 ocupadas, `/api/health` responde 401 sem token (fail-closed
  correto).
- `preflight.py --etapa app-rodando`: **nenhuma falha bloqueante** (2 avisos:
  21 arquivos MQL5 com autorização declarada de ciclos anteriores — exigem
  compilar no MetaEditor64 + reanexar; 124 arquivos pendentes no git).

## O que NÃO foi feito

- Linhas TP/SL velhas após trocar de aba/período (regressão anterior) — não
  tocado neste ciclo.
- Barra lateral de desenho / lista de indicadores — não tocado.
- EA: nenhuma alteração `.mq5`/`.mqh` neste ciclo; os 21 arquivos declarados
  continuam exigindo compilação + reanexar (§7 do AGENTS).
- "Gateway indisponível: Failed to fetch" sem endpoint no texto — candidato
  barato, não implementado.

## Pergunta para o dono

1. O app instalado novo precisa ficar aberto com o MetaTrader 5 ligado para a
   validação em tela (as capturas de 12:24 foram com o MT5 fechado)? Se sim,
   posso abrir o MT5 e conferir o estado dos três defeitos corrigidos.
2. As 11 falhas pré-existentes (EconomicCalendar 10, ListaModelos 1) são de
   outro agente/ciclo — devo atacá-las aqui ou elas têm dono?
