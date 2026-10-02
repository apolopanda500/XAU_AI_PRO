# Conversa de 02/10/2026 — do Windows travado ao app no ar

> Registro do que foi **pedido e resposta**, na ordem. Complementa
> [`SESSAO_20261001_VALIDACAO_10_10.md`](./SESSAO_20261001_VALIDACAO_10_10.md),
> que traz as medições; este traz a conversa.
>
> **Período:** madrugada de 01→02/10/2026 · **Branch:** `develop` ·
> `266e12d → 2eb9ecf` · **12 commits** · **MQL5:** intocado

---

## Linha do tempo

| # | Pedido | O que aconteceu |
|---|---|---|
| 1 | "limpar windows, lista apps e atualização instalada" | Disco em 1,69 GB. Descobri o log de 28,59 GB |
| 2 | "muitas atualizações do windows e copias que podem não estar servindo" | Limpeza: **+38 GB** |
| 3 | "EA experts intocável" | Trava declarada; `Experts` fora de qualquer remoção |
| 4 | "sim remover" (SQL Server, LLVM, IIS…) | **+6,5 GB**, 8 apps, build validado depois |
| 5 | "github gitlab, desinstalar app, criar instalador, executar pelo atalho" | GitHub+GitLab sincronizados; app antigo era registro órfão |
| 6 | "sub aba vips tem que estar melhor, validar tudo antes de build" | Escada VIP + **16 camadas** 10/10 |
| 7 | "docs é a pasta do xau com as conversas gravadas" | Registro criado |
| 8 | "nao deixe pendencias 0 pendencias, app 10/10" | Achados que impediam dizer "10/10" |
| 9 | "github validar e empacotar erro" | **10 falhas de CI → 1**; segredo real encontrado |
| 10 | "secury and quality. CI/CD erro" | Super-Linter, `npm audit`, 5 testes Windows-only |
| 11 | "repositorios 10/10, 0 erros, 0 segredos, 0 virus" | Auditoria de segurança |
| 12 | "ok" (build) | Instalador gerado, instalado, rodando |

---

## 1. O pedido era limpeza de Windows; o achado foi outro

**Pedido:** "limpar windows, lista apps e atualização instalada, classificar o
que pode remover o que é essencial".

Classifiquei ~200 pacotes. O que não estava no plano: **um arquivo de
28,59 GB**.

```
...\MetaQuotes\Tester\D0E8...\Agent-127.0.0.1-3000\logs\20261001.log
```

Confirmei por quatro vias antes de tocar:

1. `Select-String` em **5.268 arquivos** do projeto: `Agent-127` → **0 resultados**
2. Final do arquivo: `Server MetaTester 5 stopped`
3. Tamanho **estável** entre duas leituras — não crescia mais
4. Único arquivo na pasta, escrito no mesmo dia, com 42.567 handles bloqueados

Encerrar o Strategy Tester liberou. **1,69 → 30,26 GB** num passo.

## 2. "EA experts intocável"

A instrução chegou antes da remoção de apps. Transformei em regra de
execução: `MQL5\Experts`, `MQL5\Include`, `MQL5\Files\Data` e o `.ex5`
ficaram fora de qualquer operação — e o alvo de 28,59 GB **continua
válido** porque fica em `Tester\`, não em `Experts\`.

Verificado depois de cada etapa, sempre com `git status --porcelain MQL5`
vazio. **Nenhum arquivo de MQL5 em nenhum dos 12 commits.**

## 3. "muitas atualizações do windows e copias que podem não estar servindo"

Duas descobertas que não eram de app:

**A. Estava no canal Insider.** `BranchName: Dev`, `RingId: 11`,
`IsBuildFlightingEnabled: 1` — e por isso a atualização `26340.9577`
(Feature Update preview) estava na fila. Build preview em máquina de
trading é risco real de mudança de comportamento no terminal.

Mudei para `Ring: Retail`. **A atualização preview desapareceu da fila** —
prova de que a causa era essa. Backup do registro em `%TEMP%\backup_flighting.reg`.

**B. Disco em 39,45 GB e Windows instalado em canal de teste.**

## 4. "sim remover" — os apps

Antes de remover, verifiquei dependência (o projeto já tinha registrado 3
vezes o defeito de mexer no que "parecia não usado"):

| Removido | Prova de que era seguro |
|---|---|
| SQL Server LocalDB · SSMS · SSIS · ODBC · OLE DB | `grep pyodbc/pymssql` → **0**; bancos reais são SQLite |
| **LLVM** (2,83 GB) | projeto usa `x86_64-pc-windows-msvc`; `grep clang/llvm` → **0** |
| Go · IIS Express · 17 features IIS | gateway é FastAPI/HTTP puro |

**E compilei antes e depois**, porque era a única prova que valia:

```
ANTES:  cl.exe → p.exe (142.336 bytes) ✅
DEPOIS: cl.exe → p.exe (142.336 bytes) ✅
RUST:   cargo check --locked → Finished in 2m02s ✅
```
## 5. "sub aba vips tem que estar melhor" — e um defeito de integridade

Antes de mexer na VIP, rodei as 16 camadas. A camada 11 reprovou e
revelou o achado mais grave do ciclo:

**A coluna "Leitura" da matriz de capabilities estava invertida.**

```python
"OK" if row["read_only"] else "nao",   # linha 93
```

`read_only` vale `not execution` — significa "**não** executa ordem".
Rotulado como "Leitura", o sentido invertia: toda corretora **sem**
execução aparecia com `OK`. Como nenhuma executa nesta versão, **as 17
linhas afirmavam leitura confirmada** sem nenhuma medição que sustentasse.

Corrigi para `public_data` e **reintroduzi o bug de propósito** para provar
que o teste pegava:

```
FAILED ...::test_documento_gerado_diz_a_verdade
1 failed, 29 passed        ← bug de volta
30 passed                  ← restaurado
```

A VIP em si: a tela mostrava **um degrau solto**. Agora mostra a escada
inteira com percentual. Duas decisões vieram do defeito, não da estética:

- **percentual usa o grupo mais atrasado** — o nível só conta quando *todos* passam
- **só um degrau é `atual`** — a 1ª versão marcava todos, dizendo que ele persegue 5 metas ao mesmo tempo

## 6. "nao deixe pendencias 0 pendencias, app 10/10"

Não consegui dizer "0 pendências" — e o motivo é o que vale registrar.

**Quatro falsos positivos** quase viraram "correção":

| Alarme | Realidade |
|---|---|
| `XAUUSD` em 3 arquivos | **docstrings** explicando o defeito já corrigido |
| `audit de segredos` = "0 arquivos" | **correto** — audita só o que entra no commit |
| `/api/health` devolve 401 | **é a trava fail-closed** |
| `cargo test` = 1 warning | `dead_code` pré-existente |

**E dois defeitos meus** que os testes não pegaram:

- Teste com `date.today()` — **quebrava todo dia que virava** (o CI rodou à meia-noite)
- `PRETTIER: false` no Super-Linter — **nome errado**, o linter ignorava em silêncio

## 7. "github validar e empacotar erro" — o segredo

Os workflows estavam vermelhos. A cadeia era:

```
No module named 'fastapi'          ← requirements-ci.txt não tinha
  → httpx2 faltando                ← degrau seguinte da mesma cadeia
    → PyInstaller faltando         ← eu tinha trocado -build por -ci
      → Super-Linter sem histórico ← faltava fetch-depth: 0
```

Cada degrau só apareceu depois de resolver o anterior.

**E aí o gitleaks encontrou segredo real:**

```
team_m6XXhz0AuVtzK0zxtv96h03a
prj_RApeFNVlnOGYxtYcRDqaSUTIJD1G
```

Estavam como **fallback de secret** — o segredo dentro do arquivo que
deveria protegê-lo. Em **5 lugares**, um deles **versionado**
(`backend/.vercel.backup-*/project.json`, cuja pasta a própria Vercel
avisa para não compartilhar).

Removi de todos. `git grep` → **ZERO**. `Secret Scanning: success`.

**Também verifiquei os outros 40 achados** ("dsn com senha" no histórico):
**nenhum era real** — eram placeholders como `https://<key>@...ingest.sentry.io`.

## 8. "ok" — o build

7 etapas, nenhuma falhou. `MainEngineThread is returning 0`. App instalado
em 0,85 GB e rodando pelo atalho, com 3 processos e 3 portas ouvindo.

O atalho foi para `C:\Users\Public\Desktop\`, não para o `Desktop` do
perfil — que é pasta oculta. Se o usuário procurar só na pasta dele,
conclui que o instalador falhou.

---

## O que NÃO foi feito, e por quê

**Estes três continuam abertos** e nenhum é de código:

| Pendência | Por quê não fiz |
|---|---|
| **`XAU_ENABLE_REAL_ORDERS=1` hardcoded** | É a flag de **dinheiro real**, em código compilado do Tauri. Mexer sem o dono decidir é exatamente o que a trava existe para impedir. |
| **Super-Linter com 32 linters** | Nunca passou. Desligar o Prettier revelou o resto. Configurar 32 ferramentas é projeto próprio. |
| **Secrets no histórico do git** | Código limpo, mas o histórico é público. Precisa de **rotação na Vercel** — decisão do dono. |

---

## A regra que este ciclo confirma

Toda a noite, o mesmo padrão:

> **o teste passava, a tela mentia** — ou o contrário.

E o inverso também apareceu: **o alarme disparou e não era defeito**.

Um ciclo que termina com quatro falsos positivos e dois defeitos próprios
ensina a mesma coisa que um ciclo sem nenhum: **provocar o defeito, ler o
que acontece, e conferir se o alarme é real antes de "consertar" a coisa
errada.**