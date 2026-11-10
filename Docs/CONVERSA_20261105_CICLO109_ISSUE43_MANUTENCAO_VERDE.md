# Ciclo 109 - 05/11/2026 - issue #43: a manutenção falhava por testar a branch errada

> Origem: o dono apontou https://github.com/apolopanda500/XAU_AI_PRO/issues/43
> — "Falha automática de manutenção", aberta desde 28/10 com 8 comentários de
> falha, um por dia. Pedido: tudo verde.

---

## 1. O sintoma

| Facto | Medição |
|---|---|
| Issue | #43, `bug`, aberta 28/10 16:43, comentada 8× por `github-actions` |
| Runs | um por dia às 10:17 UTC, todos `failure`, de 28/10 a 04/11 |
| Último sucesso antes da série | run `40535601489`, 27/10 15:54 |
| Logs dos runs falhados | **404** — os runs já não existem na API |
| Fecho automático | **não existia**: o workflow só sabia abrir/comentar, nunca fechar |

O 404 é parte do problema: sem log, o alerta diário não tinha como ser
investigado a partir da própria issue.

---

## 2. Como a causa foi medida

Como os logs antigos não existiam, o workflow foi disparado à mão
(`workflow_dispatch`) para produzir um run novo com log completo:

```
run 41954293907  branch pedida: main  (o YAML fazia checkout de `develop`)
Validar Python -> 5 failed, 1473 passed, 86 skipped, 2 errors
FAILED tests/test_vip_progress.py::test_linha_corrompida_nao_derruba_a_leitura - assert 0.0 == 500.0
FAILED tests/test_vip_progress.py::test_fora_da_janela_nao_conta               - assert 0.0 == 100.0
FAILED tests/test_vip_progress.py::test_cripto_e_forex_sao_contados_separadamente - assert 0.0 == 6000.0
FAILED tests/test_vip_progress.py::TestVolumeRealmenteMedido::test_escada_nao_mente_quando_o_registro_nao_tem_quantidade
FAILED tests/test_vip_progress.py::TestVolumeRealmenteMedido::test_volume_de_ordem_conta_e_nao_e_duplicado
ERROR  tests/test_bundle_gateway_artefato.py::TestArtefatoQuandoExiste (2×)
```

E o diff entre as branches:

```
git log --oneline main -- tests/test_vip_progress.py
  8fdc5b0 fix(ci): testes com data relativa, fixture de classe na ordem certa e follow-redirects 1.16.2

git diff main develop -- tests/test_vip_progress.py
  - "at": (datetime.now(utc) - 1 dia)
  + "at": "2026-10-01T12:00:00+00:00"

git diff main develop -- tests/test_bundle_gateway_artefato.py
  - @pytest.fixture / @classmethod   (ordem corrigida em main)
  + @classmethod / @pytest.fixture   (ordem antiga em develop)
```

**Causa raiz:** o workflow tem `ref: develop` no checkout. `develop` está **9
commits atrás** da `main` nas correções de CI, então o job diário reprovava
testando código que já não é o que embarca. Não era defeito de código nem de
infraestrutura — era o instrumento a medir a coisa errada.

Por que ninguém viu: `develop` tem CI próprio e verde (corre a suite com outra
seleção de dependências), então a branch parecia saudável. Só o job de
manutenção, que instala `requirements-ci.txt` e roda `pytest -q tests` inteiro,
batia na diferença.

---

## 3. Correção aplicada

`.github/workflows/maintenance.yml`:

| # | Mudança | Porquê |
|---|---|---|
| 1 | **removido `ref: develop`** | o agendamento tem de testar a branch default, que é o que embarca |
| 2 | novo passo **"Registar o codigo testado"** | publica branch + commit e avisa quando o run é numa branch não-default; a próxima falha já não custa uma sessão |
| 3 | novo passo **"Fechar a issue quando o ciclo passar"** (`if: success()`) | o ciclo fecha sozinho, com comentário que nomeia o run que o fechou |
| 4 | corpo da issue passou a citar **branch e commit** | o log pode desaparecer; o registo na issue não |
| 5 | comentário do `ref:` reescrito com a **medição** | para o próximo agente não repor o `ref:` "para consertar o cron" |

Nada disto toca código de aplicação, gateway, MQL5 ou parâmetros de risco.

### 3.1 O que NÃO se fez

- **Não** se mergeou `main` em `develop`. `develop` está 564 commits à frente
  e divergiu; resolver isso é decisão do dono, não efeito colateral de um fix
  de CI.
- **Não** se apagou nenhum passo de teste. A cobertura é a mesma.
- **Não** se afrouxou nenhum teste para o job passar.

---

## 4. Prova

```
run 41954896373  event=workflow_dispatch  head=7ed7d3e  -> success
  Registar o codigo testado: branch em execucao: main | commit: 7ed7d3e | default: main
  Validar Python:  1476 passed, 88 skipped, 4 warnings in 119.49s
  Validar backend: npm ci + npm run lint + npm audit --audit-level=high -> exit 0
  Fechar a issue quando o ciclo passar -> issue #43 fechada
```

Estado da issue:

```
#43  state=CLOSED  closedAt=2026-11-05T02:26:12Z
comentário: "Ciclo de manutenção **verde** no run 65 (branch `main`, commit
`7ed7d3e`). ... fechada automaticamente pelo workflow."
```

Issues abertas no repositório depois disto: **0**.

Runs do commit `7ed7d3e`: `Manutencao Automatica Segura`, `Rust`,
`XAU AI PRO - validacao universal`, `ci`, `Pylint`, `Validacao e
Empacotamento`, `Security Checks`, `CI` — todos **success**; `CodeQL` em
execução no fecho deste documento.

---

## 5. Porque isto importa mais do que parece

Um alerta que dispara todos os dias e nunca é investigado **treina o operador
a ignorar o canal**. Durante 8 dias houve um "vermelho" permanente na página
do repositório — e se um dia a manutenção apanhasse um defeito real, ele
ficaria invisível no meio do ruído.

Duas regras que ficam:

1. **Um health check tem de medir o que embarca.** Branch de integração que
   não é publicada não é o objecto do check.
2. **Todo alerta automático precisa de um caminho de fecho.** Abrir sem fechar
   não é observabilidade, é uma caixa de correio cheia.

---

## 6. Ficheiros

- `.github/workflows/maintenance.yml` — correção (commit `7ed7d3e`).
- `Docs/CONVERSA_20261105_CICLO109_ISSUE43_MANUTENCAO_VERDE.md` (este).
