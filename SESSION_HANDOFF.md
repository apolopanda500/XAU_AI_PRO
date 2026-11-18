# SESSION_HANDOFF â€” Ponto de Retomada InstantÃ¢nea (XAU_AI_PRO)

> **Ãšltima AtualizaÃ§Ã£o:** 2026-11-18 06:00 (America/Sao_Paulo)
> **Regra de Ouro:** Leia este arquivo inteiro antes de tocar em qualquer cÃ³digo. Pedido sem mediÃ§Ã£o Ã© intenÃ§Ã£o, nÃ£o prova.

---

## 1. Fotografia Exata do Sistema (Estado Medido no Fechamento)

| Componente | VersÃ£o / Identificador | Status & Prova Medida |
| :--- | :--- | :--- |
| **EA MQL5 (ProduÃ§Ã£o)** | `v1.2.214` (`#property "1.414"`) | **Intocado e rodando.** BinÃ¡rio `XAU_AI_PRO.ex5` (`1 066 188 B`, MD5 `844081BF2D51D6A4072B150C3DDC6EBD`). |
| **App & Release Oficial** | `v1.2.181` (Tag `5e04111f`) | **Publicada no GitHub Releases** com `XAU_AI_PRO_Setup_1.2.181.exe` (64,1 MB), `XAU_AI_PRO_1.2.181.apk` e `SHA256SUMS.txt`. |
| **Branch `main` (App)** | Commit `d450127b` | ContÃ©m a central mobile somente leitura (`GET /api/mobile/control`), trilho lateral de `64px` (`813996f3`) e `Docs/RELATORIO_ENTREGA_1.2.181.md`. |
| **Portal Web (GitHub Pages)** | `apolopanda500.github.io/XAU_AI_PRO/` | **Online (HTTP 200)** com dois selos reais (`App 1.2.181` + `EA MQL5 1.2.214`) e download automÃ¡tico via API de Releases. |
| **RepositÃ³rio EA (`mql5`)** | Commit `2a9b5675` (`github/main`) | **CI 100% Verde** (`ci.yml` com guarda de versÃ£o, `CodeQL` e `Secret Scanning`). |
| **Gateway Local & Core Rust** | `mt5-gateway.exe` + `xau-ai-pro-core.exe` | Gerenciados pelo `AIGateway9027_Watchdog` na porta `9027` + telemetria nativa via crate `sysinfo` (`< 5 ms`). |
| **Aparelho Mobile Testado** | Samsung `SM-A057M` (Android 15) | APK instalado e validado ao vivo (login, painel somente-leitura, comportamento *fail-closed* ao derrubar gateway). |

---

## 2. Travas de SeguranÃ§a & Regras para os PrÃ³ximos Agentes

1. **Zero AlteraÃ§Ã£o na ProduÃ§Ã£o sem Ordem ExplÃ­cita:** NÃ£o recompilar o `XAU_AI_PRO.ex5` nem reiniciar o gateway de produÃ§Ã£o sem autorizaÃ§Ã£o direta do Dono.
2. **Isolamento de Trabalho:** Sempre abrir uma `git worktree` limpa a partir de `main` antes de editar cÃ³digo (nunca usar `git add -A` em Ã¡rvores sujas de outros agentes).
3. **Zero CÃ³digo Morto & Zero Dados Fabricados:** Todo mÃ³dulo novo deve ter consumidor ativo e testes passando (`pytest`, `vitest`, `cargo test`). Nunca fabricar features sintÃ©ticas (ex.: 25 -> 30) para mascarar erros de contrato.
4. **Segredos Protegidos:** Nunca imprimir ou gravar o conteÃºdo de `.env` (`XAU_GATEWAY_TOKEN`) em logs ou commits.

---

## 3. Fila PrioritÃ¡ria para a PrÃ³xima SessÃ£o (Ordem de ExecuÃ§Ã£o)

1. **[AÃ‡ÃƒO DO DONO â€” SEGURANÃ‡A] Rotacionar `XAU_GATEWAY_TOKEN`:**
   - Gerar novo token aleatÃ³rio de 64 caracteres, atualizar os dois `.env` (repositÃ³rio e pasta instalada no Windows) e reiniciar a tarefa `AIGateway9027_Watchdog`.
2. **[PRIORIDADE 1 â€” CI/SEGURANÃ‡A] Zerar Vulnerabilidades `npm audit` no Frontend:**
   - Atualizar `vite`, `vitest`, `picomatch` e `tinyglobby` em `frontend/` para deixar o workflow `Security Checks` 100% verde.
3. **[PRIORIDADE 2 â€” RELEASE v1.2.182] Publicar Trilho Mobile 64px + APK Assinado (Keystore):**
   - Rodar `scripts/sync_version.py` para `1.2.182` (apenas no App/Frontend, sem relabelar o EA `1.2.214`), gerar *keystore* de release e publicar o APK assinado + `.exe` na `Release v1.2.182`.
4. **[PRIORIDADE 3 â€” PARECER TÃ‰CNICO] Acesso Remoto Somente-Leitura 24/7:**
   - Avaliar o parecer salvo em `MQL5/Files/Monitoring/` para consulta remota via tÃºnel privado mantendo `real_orders_enabled=false`.
5. **[PRIORIDADE 4 â€” PÃ“S-FORWARD] IntegraÃ§Ã£o Nativa Rust FFI + SlippageTracker + ONNX:**
   - Unificar contrato de features (15/25/30) no retreinamento, exportar `.onnx` real e ligar `RustBridge.mqh` + `SlippageTracker.mqh` no EA.
