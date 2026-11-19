# PLANO MESTRE — XAU AI PRO PC & ANDROID 10/10 (status real em 18/11/2026)

Regras invioláveis: `.ex5` de produção (v1.2.214, MD5 `844081BF2D51D6A4072B150C3DDC6EBD`) imutável ·
gateway 9027/`AIGateway9027_Watchdog` intacto · tokens do `.env` nunca impressos ·
nehum processo global morto · zero código morto (`test_sem_codigo_morto.py` verde).

## Etapa 1 — UI e padronização (CONCLUÍDA, medindo por evidência)

| Item | Resultado real |
|---|---|
| Trilho lateral duplicado no mobile | `.sidebar` some em ≤768px (1 navegação) |
| Safe-area Android | `.topbar` com `env(safe-area-inset-top)` + **fullscreen sticky** no `MainActivity.kt` (barras do sistema somem; arrastar de cima as mostra transientes) |
| CORE MÁQUINA Android | "Modo Mobile" limpo (sem powershell/WMI) + latência do gateway |
| WS pós-login | chip reflete **HTTP vivo** ("Gateway HTTP") quando WS indisponível — sem falso SEM CONEXAO |
| Feed do Mini Terminal | MEXC/BINANCE/BYBIT/OKX **filtrados quando a corretora não está conectada na Carteira** (`useUniversalOverview` status `conectada`) |
| Overflow PRICE/FLUTUANTE ≤420px | quebra de linha + scroll horizontal em `.positions-table` |
| Botão recolher sidebar | alvo 40×32px, glyph « », `aria-expanded` |
| `CollapsibleSection` | componente com teste + usado em Configurações > Plano |
| Botões/abas/tabelas | acabamento mínimo em `design_system_10_10.css` (tabular-nums, hover em linhas, foco definido, GPU hints) |

## Etapa 2 — Testes (CONCLUÍDA)

`npx tsc --noEmit` limpo · `npx vitest run` **1035/1035** (85+ arquivos) ·
`pytest -q tests/test_sem_codigo_morto.py` **1/1** · `npm audit` **0**.

## Etapa 3 — PC + Android (PARCIAL)

**Android:** APK 1.2.183 compilado, instalado no SM-A057M, fullscreen aplicado,
login testado (wizard + "Lembrar sessão" 7/30/90 dias persistiu após reinstalação),
feed sem resíduos, HTTP/WS sincronizado, screenshots em `android_*.png` na sessão.

**PC:** build limpo/local do instalador NSIS ainda **não executado** — o fluxo
`scripts\build_app.bat` exige `.venv` externo à worktree. Alternativa oficial:
workflow `Build Installer` roda ao publicar a Release v1.2.183 (dispara com o push
da tag `v1.2.183`). Dono já é avisado disso a cada ciclo.

## Etapa 4 — Sites 24/7 (CONCLUÍDA)

`site/status.html` (integridade/release via API pública do GitHub), `index.html`
com link Status & Hashes, `pages.yml` com trigger `release: [published]`
(portal republica sozinho a cada release).

## Pendências conhecidas (fora deste ciclo)

1. Rotação do `XAU_GATEWAY_TOKEN` (exposta em transcript anterior) — AÇÃO DO DONO.
2. Windows `.exe` local — depende de autorização ou da Release v1.2.183 (CI).
3. Backend `fastapi_gateway.py`: filtro de corretoras desabilitadas no feed do servidor
   — hoje o frontend filtra por conexão da Carteira; extensão do servidor fica para ciclo seguinte.
4. `WindowTitlebar.tsx` (botões de janela no app): o app usa a **moldura nativa** do
   Windows; adicionar moldura custom duplicaria o chrome do SO. Só se o Dono quiser um
   design frameless.
