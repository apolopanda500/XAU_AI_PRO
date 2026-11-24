# RELATÓRIO FINAL DE ENTREGA — 23/11/2026

## Commit, push e deploy
- **Commit:** `d229fcf1` — `feat(apk,pc): modo leitura vertical, grafico/ws corrigidos e pacote cloud gratis`
- **Branch:** `feat/apk-pc-modo-leitura-23nov` (push para `origin`, PR pronto)
- **Por que branch nova:** `develop` estava `ahead 1, behind 18` e havia trabalho não commitado de outros agentes (AGENTS.md, Docs, backend, EA). `git add -A`/rebase sobrescreveria esse trabalho (AGENTS.md §11). O commit contém **somente os 16 arquivos desta sessão** (727 inserções, 20 remoções).
- `backend/fastapi_gateway.py` e `frontend/src/components/charts/PriceChart.tsx` **foram retirados do stage** por conterem hunks de outros agentes — minhas correções nesses arquivos ficaram no working tree, não no commit.

## Correções (4 pendências, todas resolvidas)
1. **WS `ws://` no Android:** `temWsConfigurado()` + guarda mobile no `useMarketWebSocket` + `VITE_WS_URL` removido → APK final sem avisos Mixed Content nem loop de reconexão.
2. **5 testes Python:** tkinter instalado no venv (copiado do Python 3.11) + temas CSS `xau_dark`/`btc_dark`/`violet_dark` →pytest 13 passed.
3. **MSI/WiX:** `locale.wxl` malformado + flag `-loc` → MSI 200,7 MB e NSIS setup 135,5 MB gerados no build completo.
4. **Watchdog matava o gateway:** `start_gateway_autostart.cmd` reescrito (citação de caminho com espaço + guarda de gateway vivo) → gateway 9027 estável.

## Builds
| Artefato | Resultado |
|---|---|
| APK v1.2.191 (emulador) | ✅ 386 MB, instalado, PID ativo, zero erros |
| EXE PC | ✅ 13,4 MB |
| MSI / NSIS | ✅ gerados no build final (removidos na limpeza do cache) |

## Baterias
- `npx vitest run`: **83 arquivos / 1.017 testes passed**
- pytest (113 arquivos): **1.532 passed**, 9 skipped
- `npx tsc --noEmit`: 0 erros
- `sync_version.py --check`: alinhado (1.2.191)

## Gateway e conta real
- **9011** (EA/IA) e **9027** (app/APK) subidos em modo leitura, health 200.
- Medição `/api/ai/predict`: XAUUSD → `no_candles_for_symbol` (símbolo é GOLD); GOLD → `modelo nao publicado ou ausente`; BTC/EUR → timeout ~12s.
- **Motor automático desligado** (`ativo:false`). Posições abertas pelo DONO preservadas. `.ex5` MD5 `844081BF2D51D6A4072B150C3DDC6EBD` intacto.

## Documentação de decisão
- `Experts/XAU_AI_PRO/EQUIPE/D212_DECISAO_AGENTE.md` e entrada `D-212` no `IDS.md`: registrei que recusei `AllowTradeWithoutAI=true` em conta real (GATE_REAL 3/12, PF 0,66, forward 0/30) e não escolhi freio diário — isso exige palavra escrita do DONO com os números.

## Pendência que exige o DONO
- Operar na real com a escada do D-211 depende de: (1) modelo publicado para GOLD / corrigir timeout da IA; (2) decisão escrita sobre freio diário e sobre ligar IA. **Não foi feito nenhum desses passos.**

## Estado do Windows
- Espaço livre: ~12,7 GB (era 2,9 GB). Caches de build limpos. Chave SSH, worktrees e artefatos finais preservados.
