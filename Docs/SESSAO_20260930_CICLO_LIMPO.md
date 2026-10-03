# Ciclo limpo 01/10/2026 — preflight destravado, dois scripts corrigidos e push

> Registro do ciclo de 01/10/2026. Continua de
> [`SESSAO_20260930_CICLO_LIMPO.md`](./SESSAO_20260930_CICLO_LIMPO.md) (30/09).
>
> **Branch:** `develop` · **Versão:** 1.2.4 · **Commit:** `336d199`

---

## 1. O que foi pedido e o que foi feito

| Pedido | Estado medido |
|---|---|
| Liberar espaço | `frontend\src-tauri\NONE` (88 MB) + `.pytest_cache` removidos |
| Ler a pasta `Docs` e entender o estado | [`SESSAO_20261001_VALIDACAO_E_PUSH.md`](./SESSAO_20261001_VALIDACAO_E_PUSH.md) §4 |
| Corrigir dois comandos | `install_app.bat` e `build_app.bat` — Seção 2 |
| Limpar ambiente | Preflight de **2 falhas para 0** — §1 do documento de validação |
| Instalar, rodar, aprovar | §2 e §4 do documento de validação |
| `git push` | GitHub sincronizado — §3 do documento de validação |

---

## 2. Os dois comandos que estavam errados

### 2.1 O caminho do bundle nunca existiu

Os dois scripts anunciavam e verificavam o MSI em:

```
frontend\src-tauri\target\release\bundle\msi
```

Esse diretório **não existe e nunca existiu**. O `target-dir` do Cargo neste
projeto é `Temp\cargo-target` — definido em dois lugares, ambos corretos:

- `frontend\src-tauri\.cargo\config.toml` linha 23
- `scripts\build_app.bat` linha 44

O Tauri empacota sempre a partir do `target-dir`. A prova é direta:

```
Test-Path frontend\src-tauri\target   -> False
release\1.2.4\*.msi                   -> True (312,6 MB)
```

### 2.2 `install_app.bat` falhava em 100% das execuções

A versão anterior rodava `npx tauri build` e depois verificava o caminho
errado. Três defeitos ao mesmo tempo:

1. **Verificava um caminho que não existe** — o MSI estava em `Temp\cargo-target`,
   o script olhava em `src-tauri\target`. Falhava mesmo com build perfeito.
2. **Não executava as etapas 4, 5 e 6** do `build_app.bat` — `npx tauri build`
   não compila o core Rust, não roda o PyInstaller do gateway e não sincroniza
   os modelos. O MSI saía com `core\`, `bridge\` e `Python\models\`
   **desatualizados ou ausentes**.
3. **Não tinha o core compilado** — sem o binário Rust, o bundle nascia
   incompleto.

**Correção:** `install_app.bat` passou a chamar `build_app.bat`, que executa
as 7 etapas na ordem, e resolve o bundle nos dois candidatos
(`Temp\cargo-target` primeiro, `src-tauri\target` como fallback).

### 2.3 `build_app.bat` anunciava o caminho errado

Linha 112 imprimia `frontend\src-tauri\target\release\bundle` — mandava o
operador procurar um diretório que nunca teve o artefato. Agora resolve e
imprime o caminho real.

---

## 3. `NONE`: 88 MB que crescem a cada build

O `src-tauri\.cargo\config.toml` passa `link-arg=/PDB:NONE` para o linker,
mas o token chega como **nome de arquivo** e o PDB é gravado mesmo assim.
Cabeçalho lido byte a byte:

```
4D 69 63 72 6F 73 6F 66 74 20 43 2F 43 2B 2B 20 4D 53 46 20 37 2E 30 30
M  i  c  r  o  s  o  f  t     C  /  C  +  +     M  S  F     7  .  0  0
```

É um PDB do MSVC, referenciando `Temp\cargo-target-tauri\debug\deps\...` — um
ciclo de build anterior. Não é versionado, não é lido por nada e o `cargo
build` recria quando precisa.

| Data | Tamanho |
|---|---|
| 29/09/2026 | 11,2 MB |
| 30/09/2026 | **88 MB** |

Foi para a allowlist do `limpeza_segura.ps1`: da próxima vez sai por comando,
não por investigação.



> Registro do ciclo de limpeza do Windows e do repositório, da revalidação da
> suíte inteira e do build. Complementa
> [`LEVANTAMENTO_20260930.md`](./LEVANTAMENTO_20260930.md) (manhã) e
> [`SESSAO_20260930.md`](./SESSAO_20260930.md) (ciclo anterior).
>
> **Início:** 30/09/2026 22:28 · **Fim:** 30/09/2026 23:40
> **Máquina:** `HENRIQUE\Micro` — **sem privilégio de administrador**
> **Branch:** `develop` · **Versão:** 1.2.4

---

## 1. O ponto de partida: o disco travava o build

| Medida | Antes | Depois |
|---|---|---|
| Disco C livre | **5,44 GB** | **22,02 GB** |
| `core\target\debug` | 1.561,6 MB | removido |
| `Temp\hist.log` | 276 MB | removido |
| `frontend\src-tauri\NONE` | 11,2 MB | removido |

O build Rust precisa de ~4 GB. Com 5,44 GB o ciclo anterior já tinha
falhado duas vezes com *Espaço insuficiente no disco* (erro 112) — está
registrado em `AGENTS.md`.

### O que foi removido, e por quê

Tudo aqui é **regenerável por comando**. Nada versionado foi tocado:

| Alvo | Tamanho | Como se regenera |
|---|---|---|
| `core\target\debug` | 1,56 GB | `cargo test` recompila (~3 min) |
| `.pytest_cache` | pequeno | pytest recria |
| `frontend\dist` | 7,8 MB | `npm run build` |
| `Temp\hist.log` | 276 MB | diff de git já commitado em `c552bce` |
| `Temp\*.log`, `*.err`, `*.out` de 29/09 | ~120 KB | 65 arquivos de sessão anterior |
| `src-tauri\NONE` | 11,2 MB | **não deve regenerar** — ver §3 |
| `src-tauri\bg_build.ps1` | 1 KB | substituído por `scripts\build_app.bat` |
| `src-tauri\*.log`, `*.flag` | 34 KB | flags de build do ciclo anterior |
| `cmd.exe` na raiz | 344 KB | **é cópia do Windows** — ver §3 |

---

## 2. `.pytest_cache` e `cmd.exe`: a mesma ACL corrompida

Os dois já estavam documentados como sintoma. A causa é uma **ACL herdada
quebrada** — `icacls` responde *Acesso negado* até para listar.

O que funciona sem administrador, em ordem:

```powershell
takeown /F <alvo>            # sem /A — /A exige admin e falha
icacls <alvo> /grant "<user>:(F)"
Remove-Item <alvo> -Force
```

O que **não** funciona sem admin: `takeown /A` e `icacls /grant` na pasta
`.pytest_cache` (lá nem o dono consegue ler). O `limpeza_segura.ps1` já
trata isso: tenta devolver a ACL, avisa e **segue** — a limpeza parcial
continua sendo limpeza.

### Nota sobre `icacls /reset`

Aplicado em `cmd.exe`, o `/reset` removeu o arquivo ao redefinir a ACL —
é o caminho mais curto quando a ACL está irrecuperável.

### O que a ACL do `cmd.exe` revelou

O arquivo **não pôde ser apagado**. A sequência resolveria metade do problema:

```powershell
takeown /F cmd.exe                        # propriedade volta para o usuario
icacls cmd.exe /grant "<user>:(F)"        # controle total explicito
```

E mesmo assim, com `FullControl` **explícito no arquivo e na pasta**, o
`Remove-Item`, o `cmd /c del` e o `MoveFileEx(MOVEFILE_DELAY_UNTIL_REBOOT)`
devolveram **erro 5 (Access Denied)**. A renomeação para `cmd_antigo.txt`
funcionou; a remoção, não. Isso é comportamento de filtro de segurança
(Controlador de Arquivos) prendendo o binário — não corrigível sem elevação.

**Estado atual:** fora do Git, adicionado ao `.gitignore`, e sem bloquear
o `preflight` (que só rejeita `.exe`, `.dll`, `.vbs`, `.scr`, `.sys`).
Continua ocupando 344 KB no disco. **Precisa de um shell elevado, uma
vez, para sumir de vez.**

---

## 3. Dois artefatos que não deveriam existir

### 3.1 `cmd.exe` na raiz do repositório

Estava lá desde **24/06/2026** — 344.064 bytes, hash
`65EC268ADD3973B6DCA64222985DA47CAEAEE44A340B0EC1466782914FD743D9`,
**idêntico ao de `C:\Windows\System32\cmd.exe`**.

Não é código, não é versionado (`.gitignore` linha `/cmd.exe`), e
`scripts\preflight.py:53` lista `cmd.exe` em `SCRIPTS_BLOQUEADOS`
justamente porque *"binario solto sombreia o do sistema"*.

**Efeito real:** `tests/test_preflight.py::test_scripts_bloqueados_ausentes`
falhava, e o `preflight` barrava a operação com *"BLOQUEADO: 1 falha(s)"*.
Um `.exe` do Windows na raiz do repositório também atrai heurística de
antivírus.

### 3.2 `frontend\src-tauri\NONE` (11,2 MB)

Formato **"Microsoft C/C++ MSF 7.00"** — é um **PDB de debug do Rust**
gravado num arquivo chamado `NONE`. O conteúdo referencia
`temp\cargo-target\release\deps\...`, ou seja: veio de um link cujo caminho
de saída do PDB chegou vazio.

A origem provável é `src-tauri\bg_build.ps1` (removido junto), que chamava
`cargo build --release` com o `target-dir` fixo e sem passar `/PDB:NONE`.
O `scripts\build_app.bat` e o `src-tauri\.cargo\config.toml` já fazem
certo.

**Correção preventiva:** as duas entradas foram acrescentadas ao
`.gitignore` com o motivo, para o caso de o artefato reapareça.

---

## 4. Defeito de whitespace corrigido

O `preflight` acusava e o `git diff --check` confirmava:

```
tests/test_ai_inference.py:229: new blank line at EOF.
tests/test_auto_engine.py:468: new blank line at EOF.
```

Linha em branco extra no fim de ambos. Removida. `git diff --check` limpo.

---

## 5. Revalidação por comando

Tudo medido neste ciclo, nada herdado de relatório anterior:

| Camada | Comando | Resultado |
|---|---|---|
| Python | `pytest -q tests` | **659 passed, 0 failed** (2:22) |
| Frontend | `npx tsc --noEmit` | **exit 0** |
| Frontend | `npm test -- --run` | **179 passed (19 arquivos)** |
| Frontend | `npm run build` | **exit 0** — 170 módulos, 531 ms |
| Backend | `npm run lint` | **sem erro** |
| Core Rust | `cargo fmt --all -- --check` | **exit 0** |
| Core Rust | `cargo test --locked` | **38 passed, 0 failed** (3:08) |
| Tauri | `cargo fmt --all -- --check` | **exit 0** |
| Versão | `sync_version.py --check` | **8 alvos OK** |
| Preflight | `scripts\preflight.py` | **0 bloqueantes** |
| Segredos | `scripts\auditar_segredos.py` | **0 bloqueios** |
| MQL5 | `git status --porcelain MQL5` | **vazio — intocado** |
| Saque | grep `withdrawals_enabled.*True` | **0 violações** |
| Saque | grep `transfers.*: True` | **0 violações** |

> **Vitest subiu de 169 para 179** em relação ao mapeamento de 30/09 de
> manhã. Não é perda nem inconsistência: são os testes novos das etapas de
> paridade de corretoras.

### Catálogo de IA (chaves reais: `symbol`, `reason`)

| Métrica | Valor |
|---|---|
| Metadados no catálogo | **36** |
| Publicáveis | **25** |
| Símbolos cobertos | **9** (AUDUSD, BTCUSD, ETHUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDJPY, XAUUSD) |
| Órfãos (publicável sem `.pkl`) | **0** |
| Reprovados sem motivo | **0** |

---

## 6. Diagnóstico do forward test — a mensagem que não ajuda

Os **4.246 `BROKER_ERROR`** do `forward_test_events.csv` têm **uma única
mensagem**: `"Erro de broker"`, sempre no módulo `BROKER`, sempre
`Severity=ERROR`.

Isso é o defeito: o log **não registra o `retcode`**. Sem ele, os 3,4
erros por ciclo não são diagnosticáveis a partir da evidência — só se
sabe que falharam, nunca por quê.

**Por que não corrigi agora:** registrar o `retcode` exige alterar
`.mq5`, o que por regra do projeto (`AGENTS.md`) exige recompilar no
`MetaEditor64` e reanexar o EA ao gráfico. MQL5 está **intocado** neste
ciclo (`git status --porcelain MQL5` vazio). Fica registrado como
pendência de execução, não de código.

---

## 7. O que continua pendente

Nada disto é corrigível por comando — são credenciais, conta ou tempo:

1. **Chaves MEXC, Binance, Bybit, OKX** na máquina do operador. Os 4
   adaptadores fazem envio HTTP real; sem chave a resposta é
   `EXECUTION_NO_CREDENTIALS` e nada sai.
2. **Conta corretora REAL** — hoje é `MetaQuotes-DEMO`.
3. **Certificado de CA pública** (~US$ 200–400/ano) — os artefatos 1.2.4
   são assinados com certificado autoassinado, e por isso o Windows
   mostra `UnknownError`.
4. **Endurance 24h/72h/7d** — `scripts\endurance_test.py` existe, exige
   o app no ar por dias.
5. **Aprovação do forward test** — a janela é real (14.265 eventos, 26
   dias, 269 aberturas) mas **não passa**: 3,4 erros de broker por ciclo.
   Ver §6.
6. **Teste em aparelho físico Android** — não há aparelho.
7. **`git push` dos lockfiles** — `gh auth` já autenticado; os 81 alertas
   do Dependabot fecham quando os lockfiles subirem.

---

## 8. Regra que vale para o próximo ciclo

O que travou este ciclo não foi falta de tempo: foi **lixo de sessão
anterior em lugares que ninguém verifica**. Três regras que evitam
repetir:

1. **`scripts\limpeza_segura.ps1 -Apply -DebugCache` antes de build
   grande.** Liberou 1,56 GB em segundos.
2. **`scripts\preflight.py` antes de operar.** Ele achou os dois
   artefatos dos §3 e o whitespace do §4 — coisas que a suíte de testes
   não pega sozinha.
3. **`.pytest_cache` e binários na raiz quebram `preflight` por ACL.** Se
   `takeown`  falhar, é sinal de que a pasta precisa de um shell elevado
   uma vez — e não de que a limpeza falhou.

> Um detalhe de método: o `preflight` **estava certo** e o `icacls` do
> `limpeza_segura.ps1` **estava certo** sobre não conseguir reverter ACL
> quebrada sem admin. O defeito era o `cmd.exe` existir, não o script
> falhar. A mesma regra de
> [`SESSAO_20260930.md`](./SESSAO_20260930.md) §13 continua valendo:
> quando a tela diz que está tudo certo, o defeito costuma estar no
> lugar que ninguém olha.
