# 25/10/2026 — Fusão das cópias do EA e reanexo na 1.2.9

## O defeito medido

O terminal executava o **binário velho**:

| Local | Estado medido |
|---|---|
| `<Terminal>\MQL5\Experts\XAU_AI_PRO\` | fonte de **26/09**, `.ex5` de **18/10** |
| `<Terminal>\MQL5\Experts\estadoA_8445b74\XAU_AI_PRO\` | `.ex5` de 23/10, mas fonte velha: `EA_VERSION_STRING "1.2.0"`, `#property version "1.20"` |
| Repositório `Files\XAU_AI_PRO\MQL5\Experts\XAU_AI_PRO\` | fonte **1.2.9** (`#property version "1.290"`), `.ex5` compilado **23/10 18:28**, 441.234 B, **0 errors / 0 warnings** |

O journal de 24 e 25/10 imprimia `[VERSION] v1.2.0 | build 2026.10.23` — binário
compilado ontem a partir da cópia defasada em `estadoA_8445b74`, não do fonte
1.2.9. Compilar e "reanexar" não tinham efeito porque **os gráficos apontavam o
caminho errado** dentro de `Experts\`.

## O que foi feito

1. Backup (movido, não apagado):
   - `Experts\XAU_AI_PRO` → `C:\Users\Micro\AppData\Local\Temp\opencode\EA_anterior_20261025\XAU_AI_PRO`
   - `Experts\estadoA_8445b74` → `...\opencode\estadoA_anterior_20261025`
2. `robocopy` da árvore do repositório (1.2.9) para
   `<Terminal>\MQL5\Experts\XAU_AI_PRO\` — medido no destino: `.mq5` 23/10 17:09,
   `VersionManager.mqh` com `EA_VERSION_STRING "1.2.9"`, `.ex5` 23/10 18:28.
3. Dono reanexou os EAs nos gráficos apontando `XAU_AI_PRO`.

## Medido depois (journal `Logs\20261025.log`)

**13 gráficos** subindo com `[VERSION] v1.2.9 | Build=2026.10.23 | Stable=Yes |
Modulos=15` entre 02:20:41 e 02:21:41:
XAUUSD M5, USDCLP, USDCOP, USDSEK, USDJPY, USDCHF, USDCZK, USDCAD, USDCNH,
AUDUSD, NZDUSD, GBPUSD, USDBRL (H1) — e a instância do GOLD/H1 substituída.

Em cada gráfico: um único `v1.2.0` (instância velha morrendo) seguido do
`v1.2.9` ~1 s depois. Nenhum `v1.2.0` vivo depois de 02:21:41. Nenhum
`failed to load`.

## Ficou aberto

- `Experts\` ainda contém **~20 pastas-experimento** (`estadoA_*`, `T4_*`,
  `XAU_AI_PRO_FORENSIC_*`, `XAU_AI_PRO_HEALTH_A/B_20261004`, …) com `.ex5`
  de 24/09 a 18/10. Não são usadas pelos gráficos; arquivar é decisão do dono.
- Os backups em `Temp\opencode\` podem ser apagados depois de alguns dias de
  forward estável.
- Continuam em aberto os passos do ciclo 23/10: forward em DEMO com token de
  sessão e, só depois, autorizar ordens reais.

## Apêndice — incidentes do dia (25/10)

**1. `.mq5` sobrescrito por conteúdo alheio (02:47, restabelecido 02:50).**
O fonte do EA foi reescrito com o conteúdo de um script de teste
(`"""A versao que o MQL5 mostra...`), 9.706 B contra 52.998 chars do HEAD.
Restaurado de `HEAD` (`git checkout HEAD -- ...`): 56.708 B, primeiros bytes
`// `, `tests/test_versao_consistente.py` **6 passed** logo depois. O backup da
versão boa hoje é `git` (HEAD); os arquivos em
`C:\Users\Micro\XAU_AI_PRO_backups_20261025` são de restaura o **binário**
instalado (`Experts\` do terminal), e continuam lá.

**2. Trava de versão atualizada para a fonte única** (`1bc319f`): o regex do
`Print` no `tests/test_versao_consistente.py` aceita `+ EA_VERSION_STRING`;
prova negativa em `Temp/prova_reprint.py` (ajuda: `python Temp\prova_reprint.py`).

**3. Vulnerabilidades npm zeradas** no mesmo commit: frontend (undici HIGH +
2 vitest) e backend (body-parser) — `npm audit` 0/0 em ambos. Security Checks
do GitHub ficou **success** no `1bc319f`.
