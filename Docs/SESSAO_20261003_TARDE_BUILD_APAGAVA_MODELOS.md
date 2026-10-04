# Sessão 03/10/2026 (tarde) — Os 3 defeitos novos que a leitura da pasta Docs não tinha achado

> Registro do ciclo. Escopo: continuar o trabalho depois de
> `SESSAO_20261003_CI_VERMELHO_E_LEITURA_DOCS.md`, medindo o estado real em vez
> de confiar no documento anterior.
>
> **Branch:** `develop` · **Versão:** 1.2.4 · **MQL5:** intocado

---

## 1. O ponto de partida

O documento da manhã registrou 3 workflows vermelhos e corrigiu 1 deles. Ao
medir o estado real, `gh run list` mostrou outra coisa:

| Situação                                      | O que a medição mostrou |
| --------------------------------------------- | ----------------------- |
| `CI` nos 3 últimos pushes                     | **verde**               |
| `Manutencao Automatica Segura` (hoje, 14:45Z) | **vermelho — e é novo** |

Ou seja: o defeito que a manhã fechou já estava verde, e apareceu um que
ninguém tinha registrado. Os três defeitos deste ciclo **não são** os três do
documento da manhã.

---

## 2. Defeito 1 — o build apagava os 3 modelos MULTI a cada execução 🔴 MAIS GRAVE

### O sintoma que ninguém viu

`Docs\SESSAO_20261002_MODELOS_MULTI_E_SEGURANCA.md` §7.2 descreve, com honestidade,
que os modelos MULTI sumiram **três vezes** no mesmo ciclo e que o build
passava limpo nas três. O documento atribuiu as ocorrências à **remoção manual
de `dist\`**. Essa leitura estava incompleta: a remoção manual foi um dos
fatores, mas existia uma causa que se repetia sozinha.

### A causa, medida

`scripts\build_app.bat`, passo [6/7], linha 95, rodava:

```bat
robocopy "%ROOT%\Python\models" "%ROOT%\frontend\src-tauri\Python\models" /MIR ...
```

`/MIR` **espelha**: apaga no destino tudo que não está na origem. E:

| Pasta                                        | Conteúdo medido em 03/10/2026   |
| -------------------------------------------- | ------------------------------- |
| `Python\models` (origem, raiz)               | 72 arquivos, **zero `MULTI_*`** |
| `frontend\src-tauri\Python\models` (destino) | 36 `.pkl` e **zero `MULTI_*`**  |

Os três modelos são publicados por `train_multi.MODELOS_DIR` (linha 80) em
`frontend\src-tauri\Python\models` — **o próprio destino do comando**. A origem
nunca teve os MULTI, porque ninguém os entrena lá.

> **O build apagava, da pasta que o `mt5-gateway.spec:24` empacota, exatamente
> os 3 modelos que o instalador precisa.**

Os 174 MB só sobreviviam em `dist\`, `bridge\` e
`Temp\cargo-target\release\bridge\` — três espelhos, nenhum deles a origem. Um
`limpeza_segura.ps1 -BuildArtifacts` teria apagado `dist\` e o gateway junto.

### Por que nenhum teste pegou

Os testes de `tests/test_spec_gateway.py` medem o `.spec` e o artefato **já
construído**. O `/MIR` roda **entre os dois** — no meio do build. Não existe
nenhum ponto de teste que observe o espelhamento, e o `robocopy` termina com
código 0.

### A correção

1. `/MIR` → **`/E`** na linha 95. `/E` copia sem apagar o que já está no destino.
2. **Trava de artefato** depois do `robocopy`: o build agora **falha** se
   qualquer um dos 3 `MULTI_*.pkl` ou `MULTI_*.meta.json` faltar no destino,
   com mensagem que diz o que treinar e onde restaurar.
3. **3 testes novos** em `tests/test_spec_gateway.py` que leem o `build_app.bat`
   como texto e valem em qualquer checkout.

### A prova

| Cenário                                         | Resultado                                           |
| ----------------------------------------------- | --------------------------------------------------- |
| Trava sem os 3 modelos                          | `EXIT=1`, mensagem de erro                          |
| Trava com os 3 modelos                          | `EXIT=0`, "Modelos MULTI presentes no destino: OK." |
| Trava com `.pkl` e sem `.meta.json`             | `EXIT=1` — o caso parcial também é pego             |
| `test_governanca_multi.py` antes da restauração | 25 `skip` por artefato ausente                      |
| `test_governanca_multi.py` **depois**           | **30 passed**                                       |

Os 3 modelos foram restaurados de `frontend\src-tauri\bridge\_internal\Python\models`
para a pasta de origem.

### Uma correção dentro da correção

A trava foi escrita primeiro com `!VAR!` dentro do `for`. Isso exigiria
`setlocal EnableDelayedExpansion` **global**, que mudaria a interpretação de
`!` em todos os `echo` do build. Reescrita com `goto` para rótulos do próprio
script, sem tocar no `setlocal`.

---

## 3. Defeito 2 — o CI agendado roda uma branch 53 commits velha

### Sintoma

`Manutencao Automatica Segura` vermelho às 14:45Z de 03/10, abrindo a issue #25:

```
ERROR tests/test_fastapi_auth.py
ERROR tests/test_fastapi_capabilities.py
E   ModuleNotFoundError: No module named 'fastapi'
Interrupted: 2 errors during collection
```

### A causa

O workflow **tem** a correção — verificado no arquivo:

```
ref: develop          # maintenance.yml linha 35
fastapi / uvicorn     # requirements-ci.txt na develop
```

E mesmo assim falha. Porque **o workflow agendado do GitHub usa a versão do
YAML que está na branch default**, e a branch default do repositório é `main`:

| Verificação                                               | Resultado         |
| --------------------------------------------------------- | ----------------- |
| `gh repo view --json defaultBranchRef`                    | **`main`**        |
| `maintenance.yml` em `origin/main` tem `ref: develop`?    | **0 ocorrências** |
| `maintenance.yml` em `origin/develop` tem `ref: develop`? | 1 ocorrência      |
| `requirements-ci.txt` em `origin/main` tem `fastapi`?     | **não**           |
| `develop` à frente de `main`                              | **53 commits**    |

O `ref: develop` foi escrito na `develop` — e a `develop` é justamente a branch
que o agendamento **não lê**. Enquanto `main` estiver 53 commits atrás, a
correção existe e não tem efeito.

### O que NÃO foi feito, e por quê

---

## 4. Defeito 3 — 199 `ERROR` que não eram teste quebrado

### Sintoma

A suíte local morria na coleta:

```
PermissionError: [WinError 5] Acesso negado:
  'C:\Users\Micro\AppData\Local\Temp\pytest-of-Micro'
606 passed, 25 skipped, 199 errors in 192.15s
```

### A causa

`C:\Users\Micro\AppData\Local\Temp\pytest-of-Micro` tem **ACL corrompida**. Nem o
próprio dono consegue lê-la — `Get-Acl` responde `UnauthorizedAccessException`.
Não é defeito do produto: é o cache temporário padrão do pytest nesta máquina.

`scripts\limpeza_segura.ps1` **já registra isso**, na seção "LIMITACAO HONESTA"
da função `Resolve-Icacls`: _"NÃO resolve o `.pytest_cache` desta máquina: lá nem
o próprio dono consegue ler a pasta, e só o shell elevado reverte."_

### A correção

`pytest.ini`, dentro de `addopts`:

```ini
addopts = -ra --basetemp=Temp/pytest-basetemp
```

---

## 5. O que mudou nesta sessão

| Arquivo                                              | Mudança                                                           |
| ---------------------------------------------------- | ----------------------------------------------------------------- |
| `scripts/build_app.bat`                              | `/MIR` → `/E` na linha dos modelos; trava de artefato dos 3 MULTI |
| `tests/test_spec_gateway.py`                         | 3 testes novos que travam o defeito 1                             |
| `pytest.ini`                                         | `--basetemp` dentro do repositório                                |
| `Docs/SESSAO_20261003_CI_VERMELHO_E_LEITURA_DOCS.md` | documento da manhã (não commitado)                                |
| `Docs/SESSAO_20261002_MODELOS_MULTI_E_SEGURANCA.md`  | §7.2/7.3 da sessão anterior (não commitadas)                      |

## 6. Estado medido ao fim

| Camada                  | Resultado                                                                                      |
| ----------------------- | ---------------------------------------------------------------------------------------------- |
| pytest                  | **833 passed, 0 errors**                                                                       |
| MODELOS MULTI na origem | **3 restaurados** (174 MB)                                                                     |
| MQL5                    | intocado                                                                                       |
| Build                   | **não executado** — `PLANO_MESTRE_20261002.md`: nenhum build enquanto houver correção pendente |

## 7. O que ficou em aberto

| Pendência                               | Por quê                                                                                                       |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| **Merge de `develop` em `main`**        | Dispara deploy de produção na Vercel. Decisão do dono. Enquanto isso, o cron das 10:17 UTC continua falhando. |
| `Dependency Audit` (6 `high` sem patch) | Já registrado na sessão da manhã. Sem correção upstream.                                                      |
| Super-Linter `quality`                  | Já registrado. Escolha de linters é decisão do dono.                                                          |

## 8. A regra que este ciclo confirma — e o lugar onde ela falhou

> **Verificar se o defeito existe antes de tratar a tela vermelha.**

O documento da manhã aplicou a regra aos 3 workflows vermelhos. Ela se
confirmou — mas o erro do ciclo seguinte foi o oposto: **confiar no documento e
não medir**. O `Docs` dizia "3 workflows vermelhos" e o `gh run list` dizia
outra coisa. O documento dizia que o defeito era o `.spec` sem `datas`; a causa
era o `/MIR` do `build_app.bat`.

A regra completa, então, é:

> **Medir antes de tratar. E quando a causa foi creditada a um evento isolado,
> procurar a causa que se repete sozinha.**

O `/MIR` apaga os modelos em **todo** build, não no build em que alguém apagou
`dist\` três vezes. As três ocorrências que o documento atribuiu à mão humana
eram o mesmo defeito automático, visto três vezes.

### A prova

| Comando                    | Resultado                                      |
| -------------------------- | ---------------------------------------------- |
| `pytest -q tests` (antes)  | 606 passed, 25 skipped, **199 errors** (192 s) |
| `pytest -q tests` (depois) | **833 passed, 0 errors** (111 s)               |

Não há argumento extra: **é o comando exato do `AGENTS.md`**.

### Duas leituras erradas no caminho

| O que fiz                                                        | Por que errou                                                                                                                                                                                                               |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `basetemp = Temp/pytest-basetemp` como chave solta do `[pytest]` | O pytest **9.1.1 aceita sem erro e ignora**. Continua dizendo `configfile: pytest.ini`, continua usando o `%TEMP%`, e emite `PytestConfigWarning: Unknown config option: basetemp`. Só a flag de linha de comando funciona. |
| Contar `(` e `)` no `.bat` para validar sintaxe                  | Deu `abre=27 fecha=27` e **não prova nada**: o `echo "modelos nao carregam"` tem parênteses que não são bloco. O que validou foi **executar os 3 cenários**.                                                                |

Resolver exige **merge de `develop` em `main`**. Isso é decisão do dono:
`main` é a branch de release, `deploy.yml` linha 75 faz **deploy de produção
na Vercel** quando o `github.ref` é `main`, e `docker-publish.yml` publica
imagem. Um merge não é uma correção de código — é uma mudança de branch.

**Duas saídas, nenhuma aplicada nesta sessão:**

1. **Merge de `develop` em `main`** — o `ref: develop` já está correto; só falta
   chegar lá. Cuidado: dispara deploy de produção.
2. **Não ter workflow agendado em branch que não é a default** — ou mudar a
   default branch do repositório para `develop`.

> ⚠️ A alternativa "ligar o workflow em `main`" produziria um cron **verde por
> engano**: pareceria resolvido e não estaria.

---

_Documento de sessão. O estado do sistema são as políticas técnicas; a
precedência de leitura permanece em `SESSAO_20261003_CI_VERMELHO_E_LEITURA_DOCS.md`._
