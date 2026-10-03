# Sessão 03/10/2026 — Leitura da pasta Docs e os 3 workflows vermelhos

> Registro do ciclo. Escopo: ler a pasta `Docs` inteira (58 arquivos) e
> diagnosticar por que o `develop` está com **3 workflows vermelhos** desde o
> commit `57d8e89`.
>
> **Branch:** `develop` · **Versão:** 1.2.4 · **MQL5:** intocado

---

## 1. O que foi pedido

| Pedido | Resultado |
|---|---|
| Ler a pasta `docs` inteira | **58 arquivos** lidos (índice, arquitetura, 6 ciclos de sessão, políticas, contratos, benchmarks) |
| "últimas alterações, continuar trabalho do app" | Os 3 workflows vermelhos foram diagnosticados por log do CI e reproduzidos localmente |

---

## 2. Os 3 workflows vermelhos

`gh run list` no `57d8e89`:

| Workflow | Conclusão |
|---|---|
| `CI` | **verde** |
| `XAU AI PRO - validação universal` | `security` verde · **`quality` e `validate` vermelhos** |
| `CI/CD - XAU AI PRO` | **vermelho** (`Validar e Empacotar`) |
| `Security Checks` | 5 jobs verdes · só **`Dependency Audit` vermelho** |

Nenhum é falha de código do produto. São três causas diferentes, e só uma
tinha correção de verdade.

---

## 3. Defeito 1 — 2 testes medem artefato que o git não versiona ✅ CORRIGIDO

### Sintoma

```
tests/test_spec_gateway.py::test_origem_dos_modelos_existe_e_tem_artefato
    AssertionError: pasta de modelos ausente: .../frontend/src-tauri/Python/models
tests/test_spec_gateway.py::test_destino_bate_com_o_que_ai_inference_procura
    AssertionError: ai_inference resolveu para .../Python/models, que nao tem nenhum artefato
```

### Causa

`.gitignore:49` remove `**/Python/models/*.pkl`. Os `.pkl` e `.meta.json` são
**artefatos de treino** e não vão no git:

```
git ls-files 'frontend/src-tauri/Python/models'  ->  0
git ls-files 'Python/models'                     ->  0
```

Os dois testes medem esses artefatos. Na máquina do dono existem 36 `.pkl` em
cada pasta e passam; **num checkout limpo a pasta não existe** e o teste mede
zero. O CI roda o checkout limpo.

### Isto é o defeito do §2.4 do ciclo de 02/10 — invertido

O ciclo anterior registrou *"teste que dependia do disco local — verde numa
máquina, vermelho na outra"* e corrigiu com `skip`. Aqui é o **mesmo padrão ao
contrário**: o teste é sobre conteúdo que o repositório **por decisão não
versiona**. Não é teste instável; é teste que mede a coisa errada num ambiente
que não a tem.

### Correção

`pytest.skip` nos dois testes, com o motivo único `SKIP_SEM_ARTEFATO`. O padrão
já existia no projeto e é o mesmo:

- `tests/test_governanca_multi.py:39`
- `tests/test_ai_inference.py:71`

**O que foi preservado de propósito:** a asserção

```python
assert resolvido.name == "models"
```

ficou **antes** do `skip`. É ela que pega o defeito real — destino do `.spec`
diferente do caminho que o runtime resolve — e roda em qualquer checkout. O
`skip` cobre só a prova de que o artefato existe.

### Prova dos dois cenários

| Cenário | Comando | Resultado |
|---|---|---|
| Com modelos (máquina do dono) | `pytest tests/test_spec_gateway.py -q` | **9 passed** |
| Sem modelos (cenário do CI) | `XAU_MODELOS_DIR=<pasta vazia> pytest -q -rs` | **8 passed, 1 skipped** |

O segundo cenário é a prova de que a correção funciona onde o defeito
aparecia — não só onde já passava.

---

## 4. Defeito 2 — 6 vulnerabilidades `high` sem correção possível ⛔

### Sintoma

`Security Checks` → `Dependency Audit` vermelho, e **reproduzido localmente**:

```
npm audit --audit-level=high     # em backend/  ->  exit 1
6 high severity vulnerabilities
```

### A cadeia

```
workflow@4.8.9
└── @workflow/nest@4.0.25
    └── @swc/cli@0.8.1
        └── @xhmikosr/bin-wrapper@14.5.1
            └── @xhmikosr/downloader@16.3.1
                └── got@14.6.6
                    └── cacheable-request@13.0.19
                        └── http-cache-semantics@4.2.0
```

### Não existe correção — e isso foi verificado, não assumido

| Verificação | Resultado |
|---|---|
| `npm audit fix` (executado de verdade) | **não alterou nada** — as 6 continuam |
| `npm view http-cache-semantics versions` | última versão publicada é **4.2.0** — a que está instalada |
| Advisory **CVE-2026-93748 / GHSA-ch52-4w7c-c8xp** | **Patched versions: None** · Affected `<= 4.2.0` · Dependabot alerts: **0** |

A frase do advisory é literal: **não há versão corrigida**. `npm audit` segue
reportando porque a cadeia existe, não porque exista conserto.

### Por que isso não atinge o produto que o usuário instala

`workflow` é importado **só** em `backend/workflows/index.mjs` (rotas da
Vercel). O app desktop roda `backend/server-desktop.cjs`, que é **express
puro** e não toca essa cadeia — mesmo padrão registrado em
`SESSAO_20260930.md` §10.

### O que ficou em aberto — decisão do dono

O job roda `npm audit --audit-level=high` e falha sempre até a Vercel publicar
o patch. Duas saídas reais, nenhuma aplicada nesta sessão:

1. **Aceitar e documentar** — o advisory tem prazo de correção do upstream.
2. **Ajustar o job** para separar "sem correção disponível" de "high
   corrigível", mantendo `--audit-level=high` no frontend (que está em 0).

---

## 5. Defeito 3 — Super-Linter `quality` ⏸ DECISÃO DO DONO

### Sintoma

```
[ERROR] Errors found in BIOME_FORMAT
  Checked 201 files. Found 200 errors.
  .mcp.json format
[warn] Code style issues found in 31 files. Run Prettier with --write to fix.
```

### Causa

O repositório **não tem `biome.json` nem `.prettierrc`** (verificado). O Biome
aplica os *defaults* dele sobre um projeto escrito com outra convenção.

É exatamente o motivo pelo qual o ciclo anterior desligou o Prettier, com
justificativa escrita no próprio workflow
(`.github/workflows/xau-ai-pro-validation.yml`).

### Por que não foi aplicado

O dono já escreveu na sessão de 02/10:

> *"Não foi desligado: escolher quais linters o projeto usa é decisão do
> dono, e desligar só para pintar o CI de verde seria esconder defeito."*

Desligar o Biome repetiria essa decisão sem autorização. **Registrado, não
aplicado.**

---

## 6. O que mudou nesta sessão

| Arquivo | Mudança |
|---|---|
| `tests/test_spec_gateway.py` | `skip` nos 2 testes que medem artefato não versionado; asserção do runtime preservada antes do `skip` |
| `Docs/SESSAO_20261002_MODELOS_MULTI_E_SEGURANCA.md` | seções 7.2 e 7.3, escritas no ciclo anterior e nunca commitadas |
| `Docs/SESSAO_20261003_CI_VERMELHO_E_LEITURA_DOCS.md` | este documento |

As seções 7.2 e 7.3 do documento de 02/10 estavam no working tree desde então,
escritas e não commitadas:

- **7.2** — o defeito dos modelos sumirem aconteceu **três vezes** no mesmo
  ciclo, sempre com o build passando limpo
- **7.3** — `Temp/cargo-target/release/deps` foi apagado **durante** o build,
  e o `rustc` ainda ia ler os `.rlib` dali (`exit code: 101`)

---

## 7. O que NÃO foi feito, e por quê

| Pendência | Por que não fiz |
|---|---|
| Defeito 2 aplicado | Não existe versão corrigida. Escolher entre aceitar ou ajustar o job é decisão do dono. |
| Defeito 3 aplicado | Desligar o Biome é repetir a decisão que o dono reservou para si. |
| Build do app | `PLANO_MESTRE_20261002.md`: **nenhum build enquanto houver correção pendente**. Os defeitos 2 e 3 continuam abertos. |

---

## 8. A regra que este ciclo confirma

> **Verificar se o defeito existe antes de tratar a tela vermelha.**

Os três workflows estavam vermelhos e **nenhum** era defeito de código do
produto:

| Workflow vermelho | Realidade |
|---|---|
| `validate` | teste media artefato que o `.gitignore` remove — **corrigível** |
| `Dependency Audit` | advisory **sem patch disponível** — não corrigível |
| `quality` | linter com defaults, sem config no repo — decisão de dono |

O mesmo padrão que 30/09 §13 e 02/10 §9 registram, agora pela terceira vez: **o
alarme é real, mas a causa raramente é o que o nome do job sugere.** E a
tentação de "consertar" para pintar o CI verde é ela mesma o defeito.

---

*Documento de sessão. O estado do sistema são as políticas técnicas; a
precedência de leitura permanece em `SESSAO_20261002_MODELOS_MULTI_E_SEGURANCA.md`.*
