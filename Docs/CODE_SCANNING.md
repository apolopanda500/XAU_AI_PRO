# Code scanning: 19 alertas, o que CodeQL viu e o que era real

Medido em 04/10/2026 com `gh api repos/apolopanda500/XAU_AI_PRO/code-scanning/alerts`:
**19 alertas abertos, 16 `error` e 3 `warning`**.

| Regra | Qtd | Arquivo | Real? |
|---|---|---|---|
| `py/unsafe-deserialization` | 1 | `backend/ai_inference.py` | **SIM** |
| `py/path-injection` | 4 | `backend/ai_inference.py` | **SIM** |
| `py/stack-trace-exposure` | 9 | `backend/fastapi_gateway.py` | nao |
| `py/http-response-splitting` | 2 | `backend/mt5_gateway.py` | nao |
| `py/weak-sensitive-data-hashing` | 3 | `bybit_client.py`, `mexc_client.py` | nao |

## O QUE ERA REAL: travessia de caminho ate execucao de codigo

Cadeia comprovada, do HTTP ate o `pickle`:

```
mt5_gateway.py:3105   ai_inference.inferir(m.simbolo, df, m.timeframe)
auto_engine.py:194    self.simbolo = str(payload["simbolo"]).upper()   # sem validacao
ai_inference.py:216   pkl = MODELOS_DIR / f"{simbolo}_{timeframe}.pkl"
ai_inference.py:231   modelo = joblib.load(pkl)
```

`simbolo` vinha da REQUISICAO HTTP e era concatenado no caminho sem nenhuma
validacao. Um simbolo com `../` escapava da pasta de modelos e chegava no
`joblib.load`: desserializar um `.pkl` de caminho escolhido **e execucao de
codigo arbitrario**, porque `pickle` carrega e executa.

A correcao tem DUAS defesas porque uma so nao fecha:

1. **`_nome_de_artefato`** barra na origem: `^[A-Z0-9]{1,12}$` e allowlist
   fechada de timeframe (medida nos artefatos reais: M5, M15, H1, H4).
   `..`, `/`, `\` e `%2e%2e` nao passam.
2. **`_caminho_confinado`** barra no destino: o caminho **resolvido** precisa
   estar dentro de `MODELOS_DIR` (`resolve()` + `is_relative_to`).

So a primeira nao fecha: `MODELOS_DIR` vem de `XAU_MODELOS_DIR` (ou de um app
instalado), e um link simbolico dentro da pasta apontaria para fora.
`tests/test_traversal_modelos.py::TestCaminhoConfinado::test_symlink_para_fora_e_recusado`
cobre exatamente esse caso — e sem ele, apagar a defesa 2 nao quebraria nada
visivel.

Prova de que a correcao nao quebrou o produto: `ai_inference._carregar("XAUUSD", "H1")`
continua devolvendo um `RandomForestClassifier` real, e 9 ataques (incluindo
symlink) sao recusados.

## O QUE O CODEQL SO REPORTAVA

**`py/stack-trace-exposure` (9)** — as linhas apontam `return` de dado
(`chart_attach.listar_graficos()`, `boot_status()`) ou `str(exc)` de
`ValueError`/`PermissionError`. Nao ha nenhum `traceback.format_exc`,
`exc_info=True` nem `logger.exception` no arquivo. E `str(exc)` aqui e a regra
do projeto: **recusa com motivo**, nao recusa generica.

**`py/http-response-splitting` (2)** — `_cors_origin` so devolve a origem se
ela estiver em `CORS_ORIGINS`, uma allowlist de 8 entradas. Medido:
`http://evil.com` -> `None`; origem com `\r\n` -> `None`. A origem so chega ao
cabecalho depois de passar na allowlist.

**`py/weak-sensitive-data-hashing` (3)** — e `hmac.new(secret, ..., hashlib.sha256)`
para assinatura de requisicao em Bybit e MEXC. SHA-256 dentro de HMAC e
exatamente o uso correto; o alerta assume hash de senha onde nao ha.

Nenhum dos 14 foi "corrigido", porque corrigir seria trocar algo certo por algo
errado.

## O QUE NAO ESTA COBERTO

**O code scanning so roda porque o GitHub tem CodeQL ligado no repositorio.**
Verificado: **nao existe workflow CodeQL em `.github/workflows/`** (11 arquivos,
nenhum CodeQL). O que roda e o CodeQL default do GitHub, que nao esta no
repositorio e portanto nao se configura junto com o resto do CI.
