# XAU AI PRO 1.2.181 — entrega "do PC ao Android"

Data da medicao: 17–18/11/2026 (horario local do PC).
Escopo autorizado: trabalho autonomo (validar, testar, corrigir, documentar).
Proibicoes respeitadas: nenhum token/chave rotacionado; `.ex5` de producao nao
alterado; inputs de risco intactos; sem `amend`/force-push de historico ja
publicado (a tag `v1.2.181` foi criada nesta sessao e apontada para o commit
final antes de qualquer release publicada).

---

## 1. O que foi entregue

| Item | Estado | Prova |
|---|---|---|
| Central de comando movel (somente leitura) | entregue | 22 testes pytest + 13 testes vitest |
| Rota `GET /api/mobile/control` | entregue | contrato com `read_only=true`, `commands_enabled=false` |
| Lado de ordem pendente MT5 (tipos 2–7) | corrigido | 6 testes parametrizados novos |
| Layout do painel no telefone (<=720px) | corrigido | capturas 07/09/10 no aparelho |
| Barra lateral em trilho no telefone (<=720px) | corrigido | captura final no aparelho |
| Instalador Windows 1.2.181 | publicado | instalacao silenciosa validada |
| APK Android 1.2.181 | publicado | instalado e auditado no SM-A057M |
| Release GitHub `v1.2.181` | publicada (nao draft) | 3 assets, e a `latest` |
| Portal GitHub Pages | no ar, detectando os assets | HTTP 200 + API conferida |

### 1.1 Commits

```
813996f3 fix(mobile): barra lateral vira trilho de 64px no telefone   <- main (nao esta na tag)
5e04111f fix(mobile): lado de ordem pendente MT5 e layout do painel no telefone
4314a886 feat(mobile): central de comando somente leitura no app e rota GET /api/mobile/control
2eba9e24 Merge remote-tracking branch 'origin/main' into feat/upgrade-10-10
```

`main` foi avancada por fast-forward (`15a22317..813996f3`) — sem reescrita.

**Tag `v1.2.181` aponta para `5e04111f`.** O commit `813996f3` (trilho da
sidebar) ficou de fora da tag: o GitHub recusou a atualizacao do ref
("Cannot update this protected ref"), e mover tag de release publicada e
versionamento, nao e decisao para tomar sozinha. O APK desta release e o build
de `5e04111f` — ou seja, **tag, artefato e instalacao no aparelho sao todos do
mesmo commit**, que e o que importa. O trilho de 64px foi medido no aparelho
com o build de `813996f3` (capturas 10/11) e fica documentado como pendencia de
publicacao.

### 1.2 Artefatos (Release `v1.2.181`)

| Arquivo | Tamanho | SHA256 |
|---|---|---|
| `XAU_AI_PRO_Setup_1.2.181.exe` | 67 258 861 B (64,1 MB) | `1FB621D9C0F6855894E80FC1A991C5DEA782486F4A9B6177A58D8FAF63A44C41` |
| `XAU_AI_PRO_1.2.181.apk` | 396 122 677 B (377,8 MB) | `0471396C2866CED366BD3CA7402CCC1EAC1A844BFB3981852163BAE1128975E4` |
| `SHA256SUMS.txt` | 186 B | — |

Link: https://github.com/apolopanda500/XAU_AI_PRO/releases/tag/v1.2.181

---

## 2. O que mudou, com medida antes/depois

### 2.1 Painel movel

- **Antes:** a aba Sistema so mostrava a saude da maquina. Nenhuma leitura de
  conta, posicoes ou risco no celular.
- **Depois:** `MobileCommandCenter` renderiza conta (login, servidor, saldo,
  equity, margem livre), posicoes, ordens pendentes, limites de risco e saude
  do gateway, com selo `SOMENTE LEITURA` em todos os estados.

### 2.2 Fail-closed

`ehRetratoSeguro()` so aceita o payload com `read_only === true` **e**
`commands_enabled === false`. Servidor que nao declarar leitura nao pinta nada.
Prova: teste de UI e captura 08 (gateway derrubado → painel recusa).

### 2.3 Terminal mudo nao vira "conta zerada"

`positions_available` / `pending_orders_available` vem do terminal. Sem eles,
lista vazia significaria "sem posicao" mesmo quando a leitura falhou. Testes
`test_terminal_mudo_nao_vira_conta_zerada` e
`test_posicoes_em_formato_inesperado_nao_e_silencio`.

### 2.4 Lado de ordem pendente (defeito medido no aparelho)

- **Antes:** `_LADOS` cobria so `0`/`1` (posicao). Ordem pendente do MT5
  (tipos 2..7) aparecia como `desconhecido` → a tela escrevia "lado nao
  informado" **mesmo com lado definido no terminal**.
- **Depois:** `2/4/6 = compra`, `3/5/7 = venda`. 6 testes parametrizados.

### 2.5 Layout no telefone

- **Antes:** `.content` tem `contain: layout paint`; o que passava da borda era
  **cortado**, nao rolavel. O selo, as tags e os numeros apareciam pela metade.
- **Depois:** media query `<=720px` faz as linhas quebrarem, alinha o valor a
  direita quando cabe e permite quebra de palavra quando nao cabe.
- **Segunda medicao (mesma sessao):** a sidebar fixa de 232px consumia a maior
  parte da largura util. Abaixo de 720px ela vira trilho de 64px (icones e
  `aria-label` preservados; so o rotulo visual some).

### 2.6 Numeros de teste

| Suite | Resultado |
|---|---|
| `pytest tests/test_mobile_control.py` | **22 passed** |
| `vitest run` (worktree) | **84 arquivos / 1024 testes passed** |
| `tsc --noEmit` | **exit 0** |
| `npx tauri android build --apk --debug --target aarch64` | **APK gerado** |
| `ISCC.exe` (Inno Setup 6) | **Successful compile** |
| Instalacao silenciosa do Setup | app instalado responde `v1.2.181` |

---

## 3. O que NAO foi feito, e por que

1. **APK assinado de release.** O APK publicado e **debug** (assinado com a
   chave de debug, 1 ABI `arm64-v8a`). E o artefato que foi instalado e
   auditado no aparelho; trocar a assinatura exigiria desinstalar o app
   validado. Fica como proximo passo: gerar keystore, configurar
   `signingConfigs` no `gen/android`, rebuildar e reauditar.
2. **MSI do Tauri.** O portal usa `-setup.exe`/`.exe` e `.apk`; o MSI nao e
   necessario para o fluxo publicado e o espaco livre em `C:` (~8 GB) e
   limite para um `tauri build` com ~750 MB de resources. O instalador Inno
   cobre o mesmo caso de uso e foi validado ponta a ponta.
3. **Corrigir os 25 testes pre-existentes que derrubam o `ci`.** Sao de
   corretoras `planned` (`binance/mexc/bybit/okx`), modelos `.pkl`
   gitignored e divergencia `#property version "1.391"` /
   `EA_VERSION_STRING "1.2.191"` contra `VERSION=1.2.181`. Corrigir o
   `#property version` exige **recompilar e reanexar o EA de producao**, o que
   nao esta autorizado nesta janela; reativar corretoras `planned` seria
   mudanca de risco.
4. **`Security Checks`.** Falha por `npm audit`: 6 vulnerabilidades high em
   `vite`/`vitest`/`picomatch`/`tinyglobby`, todas de ferramenta de build,
   pre-existentes ao trabalho.

---

## 4. Auditoria no aparelho (SM-A057M, Android 15, `R9XY1016R6V`)

1. APK instalado com `adb install -r -t` → `versionName=1.2.181`.
2. Login por `POST /api/auth/login` contra o gateway demo (`adb reverse
   tcp:9001`) → tela inicial.
3. Aba **Sistema** → painel `Central de comando` com selo `SOMENTE LEITURA`,
   bloco CONTA (login 51234567, MetaQuotes-Demo, saldo 10.000,00 USD, equity
   10.084,50 USD, margem livre 9.744,50 USD) e bloco POSICOES (XAUUSD compra
   0,10 +47,00).
4. Gateway derrubado → painel entra em estado de recusa com motivo (sem
   inventar zero).
5. `logcat --pid`: **nenhum crash do app**; apenas `[WS] erro` do websocket,
   esperado porque o servidor demo nao serve WS.

Capturas: `Files/Temp/visual_audit_latest/01..10`.

---

## 5. Estado do GitHub

| Workflow | Resultado | Observacao |
|---|---|---|
| `CI` | success | suite principal |
| `Pylint` | success | — |
| `Rust` | success | — |
| `Pages` | success | portal republicado |
| `ci` (build.yml) | failure | 25 testes pre-existentes (item 3.3) |
| `XAU AI PRO - validacao universal` | failure | mesma familia de testes, pré-existente |
| `Build Installer` (tag) | failure | roda pytest antes de empacotar; mesma causa |
| `Security Checks` | failure | `npm audit`, pre-existente |

Por isso a release foi publicada **manualmente**, com artefatos construidos e
medidos localmente — e nao pelo workflow de tag.

---

## 6. O que exige decisao do dono

1. **Quer o APK assinado de release?** Isso troca a assinatura e obriga
   desinstalar/reinstalar no telefone (perde a sessao salva).
2. **Quer que eu alinhe `#property version` e `EA_VERSION_STRING` ao
   `VERSION`?** Exige recompilar o EA e reanexar no grafico — passo fora do
   repositorio, e mexe no binario de producao.
3. **Quer que eu ataque as 25 falhas pre-existentes do `ci`?** Elas misturam
   catalogo de corretoras (risco) com artefatos de modelo (dados), entao
   precisam de escopo definido antes.
4. **O trilho de 64px esta fora da release.** A tag `v1.2.181` e ref protegida
   e o GitHub recusou mover para `813996f3`. Opcoes: (a) liberar a atualizacao
   da tag e eu republico o APK; (b) criar `v1.2.182` so com essa correcao
   visual (exige bump de `Docs/version.json`/frontend para nao mentir); (c)
   deixar `813996f3` apenas em `main`.
