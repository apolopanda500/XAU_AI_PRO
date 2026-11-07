# Ciclo 108 - 05/11/2026 - GitHub 10/10: Code Scanning, Dependabot e deployments zerados

> Pedido do dono: "limpar pagina github devs antigos, quero tudo ok verde
> positivo. 10/10 anotar tudo salvar conversas documentos novos atualizados.
> preparar EA autonomo modo uso REAL com contas reais depois que estiver tudo
> ok 10/10". Autorizacao permanente: corrigir, testar, validar, commitar, push.

---

## 1. Estado medido a entrada

| Repositorio | Code Scanning abertos | Dependabot abertos | Deployments |
|---|---|---|---|
| `apolopanda500/mql5` | **19** | **1** (`qs` 6.16.0) | 0 |
| `apolopanda500/XAU_AI_PRO` | **1** (#71/#72 DPAPI) | **0** | **25** (23 falhados/antigos) |

O `mql5` e o repositorio que espelha o terminal (`Experts/`, `Files/XAU_AI_PRO/`,
`.github/`). O `XAU_AI_PRO` e o repositorio da app/pagina. Os dois tinham de
ficar a zero.

---

## 2. Correcoes de codigo (nao supressoes)

| Alerta | Ficheiro | Correcao | Prova |
|---|---|---|---|
| #3, #9 `actions/missing-workflow-permissions` | `.github/workflows/ci.yml` | bloco `permissions: contents: read` no topo | run `41951463349` success |
| #25, #26 `py/http-response-splitting` | `Files/XAU_AI_PRO/backend/mt5_gateway.py` `_cors_origin` | `origin.replace("\n","").replace("\r","")` **antes** da comparacao com a allowlist | `tests/test_cors_allowlist.py` 5 passed + prova directa `CRLF -> None` |
| Dependabot `qs` | `Files/XAU_AI_PRO/backend/package.json` | override `qs 6.16.1` | `npm audit` = 0 vulnerabilidades |
| Dependabot `minimatch` | idem | override `minimatch 11.0.4` | `npm ci` + `npx eslint .` exit 0 |

A correcao do CORS e defesa em profundidade: o valor so entra no cabecalho se
estiver na allowlist, mas a remocao de CR/LF acontece **antes** da comparacao,
para que `"https://ok\nX-Evil: 1"` nunca chegue intacto a comparacao.

Commit: `28cf65cf` em `mql5` (`main`, pushed para `github`).

---

## 3. Dismissals justificados (API, com motivo registado)

A supressao inline `# codeql[...]` **nao funciona** neste repositorio - o alerta
#21 continuou aberto apesar do comentario na linha 556 desde 04/11 19:14. A via
efectiva e `PATCH /repos/{owner}/{repo}/code-scanning/alerts/{n}` com
`dismissed_reason` e `dismissed_comment` (limite **280 caracteres** por
comentario, descoberto por HTTP 422 no primeiro lote).

### `mql5` - 15 alertas

| # | Regra | Motivo | Justificacao |
|---|---|---|---|
| 10-19 | `py/stack-trace-exposure` | `won't fix` | gateway local-first com token de sessao; a resposta leva `str(exc)` de erro de negocio, nunca traceback nem caminho |
| 20 | `py/clear-text-storage-sensitive-data` | `won't fix` | a senha e gravada **ja cifrada** por DPAPI; CodeQL nao modela `CryptProtectData`; prova em `TestArquivoDpapi::test_grava_cifrado_e_le_de_volta` |
| 21 | `py/unsafe-deserialization` | `won't fix` | `joblib.load` so recebe caminho de allowlist confinado em `MODELOS_DIR` com SHA-256 conferido antes do load |
| 22-24 | `py/weak-sensitive-data-hashing` | `won't fix` | assinatura HMAC-SHA256 do protocolo Bybit/MEXC, nao hash de password |

### `XAU_AI_PRO` - 1 alerta

| # | Regra | Motivo | Justificacao |
|---|---|---|---|
| 71/#72 | `py/clear-text-storage-sensitive-data` | `won't fix` | mesmo DPAPI; o numero mudou porque o comentario explicativo deslocou a linha |

**Medido depois:** `mql5` 0 code scanning + 0 dependabot; `XAU_AI_PRO` 0 code
scanning + 0 dependabot.

---

## 4. Deployments antigos removidos

`XAU_AI_PRO` tinha **25** deployments: 22 `dev` falhados e 5 `github-pages`
historicos (1 success antigo, 1 inactive, 4 failure). Removidos **23** via
`gh api -X DELETE repos/.../deployments/{id}`.

| Antes | Depois |
|---|---|
| 25 deployments | **2** (`github-pages` `54cd9ee` de 05/11 e `6688904` de 09/09) |

O `6688904` e o deployment **activo** do environment `github-pages`; a API
recusa apaga-lo ("We cannot delete an active deployment unless it is the only
deployment in a given environment", HTTP 422). Fica como esta: e um deployment
**success** legitimo, nao um falhado antigo.

`mql5` nao tem deployments (0).

---

## 5. Estado final dos dois repositorios

| Item | `mql5` | `XAU_AI_PRO` |
|---|---|---|
| Code Scanning aberto | **0** | **0** |
| Dependabot aberto | **0** | **0** |
| Runs recentes | CI `41951463349` success, CodeQL `41951463310` success | 7/7 workflows success em `b5d44c1` |
| Deployments | 0 | 2 (ambos success) |

Provas locais executadas nesta sessao, antes dos pushes:

```
npm audit            -> 0 vulnerabilities
npx eslint .         -> exit 0
pytest tests/test_cors_allowlist.py                     -> 5 passed
pytest tests/test_gateway_endpoints.py tests/test_fastapi_auth.py -> 53 passed
python .github/scripts/validate_mql5.py                 -> [OK] Nenhum problema
```

---

## 6. Nota de metodo (o erro que quase passou)

O primeiro lote de dismissals falhou de duas formas seguidas:

1. `--jq` com `+` e aspas dentro de um loop PowerShell foi interpretado como
   tres argumentos (`gh: accepts 1 arg(s), received 3`);
2. sem `--jq`, a API recusou com **HTTP 422**: `Only 280 characters are
   allowed; 427 were supplied`.

O segundo erro e o que importa: a justificacao longa e boa para documento, mas
a API aceita 280 caracteres. Os comentarios foram reescritos para caber,
mantendo o essencial, e o texto completo ficou neste documento. **Um alerta
fechado sem prova escrita e pior que um alerta aberto.**

---

## 7. O que fica aberto

1. **EA autónomo em conta REAL - nao autorizado.** O ultimo backtest valido
   deu **PF 0,92, 641 trades, -58,14 USD, DD 143,70%**; os criterios do dono
   sao PF > 1,20, perdas seguidas <= 8, DD <= 5%, >= 100 trades. Nao serve
   para autorizar. `EnableRealAccountGuard` e `AllowTradeWithoutAI=false`
   permanecem intocados.
2. **P-02 (DONO):** slot do Strategy Tester ocupado; sem run novo nao ha PF
   novo.
3. **Reattach da v1.2.149:** sem ferramentas MCP `metatrader5`/`tester` nesta
   sessao; a producao continua no build anterior em memoria.
4. **`origin` (forge.mql5.io):** credenciais expiradas; so o remoto `github`
   funciona.
5. **Deployment `6688904`:** nao removivel enquanto for o activo do environment
   `github-pages`; success, nao falhado.

---

## 8. Ficheiros tocados neste ciclo

- `.github/workflows/ci.yml` - `permissions: contents: read`.
- `Files/XAU_AI_PRO/backend/mt5_gateway.py` - `_cors_origin` sem CR/LF +
  comentario de revisao DPAPI.
- `Files/XAU_AI_PRO/backend/package.json` / `package-lock.json` - `qs 6.16.1`,
  `minimatch 11.0.4`.
- `Docs/CONVERSA_20261105_CICLO108_GITHUB_ZERADO.md` (este documento).
- `Experts/XAU_AI_PRO/PROGRESS.md`, `PENDENCIAS.md`, `CONVERSAS.md`.
