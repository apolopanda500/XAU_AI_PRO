# RELATÓRIO FINAL 10/10 — 18/11/2026 (worktree `Temp\ciclo_10_10`, branch desta release)

Base: `origin/main` (`6683b528`, merge 1.2.182) · alvo: v1.2.183
`.ex5` (v1.2.214, MD5 `844081BF2D51D6A4072B150C3DDC6EBD`), gateway 9027,
tokens e inputs de risco — **INTOCADOS**.

## Evidência de testes (executados nesta máquina)

```
npx tsc --noEmit                 -> limpo
npx vitest run                   -> 85+ arquivos, 1035 passed (1035)
pytest -q tests/test_sem_codigo_morto.py -> 1 passed
npm ci (145 pkgs) + npm audit    -> 0 vulnerabilidades
```

## Correções aplicadas e medidas no aparelho real (SM-A057M)

1. **Login:** sessão de 7/30/90 dias (`xau-session-until`, `sessionExpirou()`).
   A sessão persistiu após `adb install -r` (prova: app abriu logado em 22:51).
2. **Primeiro acesso:** `FirstRunWizard` (3 passos: Conexão → Permissões → Governança),
   exibido só com `xau_onboarding_done != 1`; buildado e validado visualmente.
3. **Feed sem resíduos:** filtro `lib/terminalFeed.ts` + `useUniversalOverview`
   (`conectada`); tela Operações com **"Nenhum evento."** (antes: MEXC+BINANCE).
4. **HTTP/WS:** chip "Gateway HTTP" quando WS inavegável; AUTO habilitado via HTTP.
5. **Layout mobile:** `.sidebar` oculta ≤768px; `.topbar` com `env(safe-area-inset-top)`;
   **fullscreen sticky** no MainActivity (barras do sistema somem; swipe transiente).
6. **Wrappers:** `CollapsibleSection` (teste próprio + em Configurações>Plano).
7. **Sites:** `status.html` + link menu; `pages.yml` com trigger `release: published`.

## AndroidManifest + MainActivity (Android fullscreen)

`MainActivity.kt`: `WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE`
com `WindowInsetsCompat.Type.systemBars()` — tela cheia por padrão; a barra do
sistema aparece ao arrastar da borda e se oculta sozinha.

## Hashes do artefato (teste interno, NÃO release pública)

Ver `SHA256SUMS.txt` gerado junto a este ciclo na pasta de release; o APK de
distribuição oficial deve vir da GitHub Action (`build-android.yml`) ao publicar v1.2.183.

## Não feito (explícito)

- Push, merge externo, tag e Release v1.2.183 — aguardam OK do Dono.
- `.exe` Windows local — fora deste ciclo (CI ou autorização).
- Filtro backend de corretoras no `fastapi_gateway.py` — ciclo seguinte.
- Rotação `XAU_GATEWAY_TOKEN` — pendência do Dono.
