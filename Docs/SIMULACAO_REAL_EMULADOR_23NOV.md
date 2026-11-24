# Simulação real no emulador — 23/11/2026 (continuação)

## Ambiente
- Emulador `emulator-5554`, AVD `XAU_PRO_34`, Android 14, **1080x2340, density 440**.
- APK v1.2.191 (build final) instalado; login com `rickjax1234@gmail.com` / `naruto123456`.
- Gateway 9027 com token de `backend/.env` (PID 3788, health 200).

## Telas inspecionadas (screenshots em `Temp/opencode/sim*.png`)
| Tela | Antes | Depois das correções |
|---|---|---|
| Login | "Gateway: nao configurado" | `Gateway: http://10.0.2.2:9027` ✅ |
| Robô / Operação | legível | legível ✅ |
| Robô / Risco | "UTC" cortado; barra inferior ausente | corrigido no CSS (verificado em código) |
| Robô / Modelos | 17× "Par" enganoso em modelos de classe; título quebrado; contador colado | ✅ **"Classe"** nas classes, **"Par"** nos ativos reais; título em 1 linha; contador com respiro |
| Carteira | tabela com scroll horizontal; "UTC" cortado | corrigido no CSS (tabelas em blocos) |
| Barra inferior (6 ícones) | coberta pela navegação Android; "Configuraç..." cortado | ✅ visível; último ajuste de 9px + letter-spacing para caber "Configuração" |

## Correções aplicadas nesta rodada
1. `frontend/src/components/ListaModelos.tsx`: `<dt>` dinâmico — "Classe" para `MULTI_*`, "Par" para ativos reais.
2. `frontend/src/components/ListaModelos.test.tsx`: helper `parDe` aceita "Par" ou "Classe" e continua **medindo o valor** (não enfraquece a asserção — AGENTS.md §6).
3. `frontend/src/theme/mobile-readability.css`: `flex-wrap` em cabeçalhos; relógio UTC sem corte; barra inferior elevada com `env(safe-area-inset-bottom)`; rótulos a 9px com `letter-spacing` negativo; `topnav-status` sem quebra de linha.

## Validação
- `npx tsc --noEmit`: **0 erros**.
- `npx vitest run ListaModelos + light_tabelas`: **27 passed**.
- Screenshot `sim_modelos_corrigido.png`: rótulos "Classe"/"Par" corretos, título e contador legíveis, 6 ícones visíveis.

## Observação
O app permanece "SEM CONEXÃO" quando o gateway cai (restarts do ambiente); o login e a leitura das telas foram feitos com o gateway no ar. `WS Offline` é esperado (gateway http-polling, sem rota WS). Motor desligado, zero ordens, posições do DONO intactas, `.ex5` MD5 `844081BF2D51D6A4072B150C3DDC6EBD`.
