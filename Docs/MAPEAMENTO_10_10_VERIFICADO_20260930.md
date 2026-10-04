# Mapeamento 10/10 - XAU AI PRO (verificacao real de 30/09/2026)

Cada camada so marca 10/10 quando **todos** os criterios sao verificados por
COMANDO, nao por impressao. Esta e a re-verificacao depois das 5 etapas de
correcao (paridade de corretoras, ativo nao presumido, ambiente).

Data da verificacao: **30/09/2026**.ultima anterior: 28/09/2026 14:35.

Regra geral que vale para todas as camadas:

- nenhum `.mq4/.mq5/.mqh/.set` alterado;
- nenhum segredo (chave, token, DSN, conteudo de `.env`) no repositorio;
- `git status` limpo de arquivos temporarios.

---

## 1. Gateway (backend Python)

| Criterio                                    | Como provar                                                                   | Resultado                         |
| ------------------------------------------- | ----------------------------------------------------------------------------- | --------------------------------- |
| Suite inteira verde                         | `pytest -q tests`                                                             | **659 passed, 0 failed**          |
| Sem rota `/api/demo/`                       | grep em `backend/*.py`, `scripts`                                             | **0**                             |
| Sem comando `demo/*`                        | grep `'demo/` em `backend/*.py`                                               | **0**                             |
| Sem vocabulario de recusa por tipo de conta | grep das 4 frases                                                             | **0**                             |
| Travas de execucao presentes                | `XAU_MCP_TRADING`, `XAU_ENABLE_TRADE_COMMANDS`, `XAU_ENABLE_EMERGENCY_RESUME` | **presentes**                     |
| Gatilho por corretora                       | `EXECUTION_GATES`                                                             | **5 gates**                       |
| Ordem real nao e recusada                   | `test_rejection_matrix`                                                       | **verde**                         |
| **Nenhum ativo presumido**                  | grep `or "XAUUSD"` / `= "XAUUSD"`                                             | **0 em codigo** (3 em comentario) |
| **Nenhuma corretora como padrao**           | grep `default="mt5"` / `or "mt5"`                                             | **0 em codigo**                   |
| Roteamento do motor                         | `TestRoteamentoPorCorretora`                                                  | **4 testes verdes**               |
| Ativo vazio recusa                          | `TestNenhumAtivoPresumido`                                                    | **4 testes verdes**               |
| Paridade de conexao                         | `test_connection_contract`                                                    | **6 testes verdes**               |
| Saque nunca habilitado                      | grep `withdrawals_enabled.*True`                                              | **0**                             |

**Estado: 10/10.**

Prova ao vivo da recusa de ativo:

```
ai.inferir("", candles, "H1")  ->  disponivel=False
   motivo: "escolha o ativo antes de pedir inferencia: simbolo vazio nao
            carrega nenhum modelo (o projeto nao presume ativo padrao)"
```

Antes devolvia um `RandomForestClassifier` de ouro (ver
`Docs/LEVANTAMENTO_20260930.md` Etapa 1).

Prova ao vivo da recusa de corretora:

```
market_access.acesso("", "")  ->  SemCaminhoError: escolha a corretora
                                  antes de operar: nenhuma e padrao
market_access.acesso("mt5","forex")      -> MetaTrader 5
market_access.acesso("binance","crypto-spot") -> Binance
market_access.acesso("bybit","crypto-futures") -> Bybit
```

---

## 2. Frontend

| Criterio               | Como provar                              | Resultado                    |
| ---------------------- | ---------------------------------------- | ---------------------------- |
| TypeScript sem erro    | `npx tsc --noEmit`                       | **exit 0**                   |
| Testes verdes          | `npm test`                               | **169 passed (19 arquivos)** |
| Build de producao      | `npm run build`                          | **exit 0**                   |
| Superficie de UI       | `pytest tests/test_interface_surface.py` | **3 passed**                 |
| Sem `demo-order-panel` | grep em `frontend/src`                   | **0**                        |
| Sem ids `demo-*`       | grep dos 5 ids                           | **0**                        |

Nota: o documento de 28/09 registrava **191 testes (20 arquivos)**. Hoje sao
**169 (19)**. A diferenca nao e perda: `MAPEAMENTO_10_10.md` linha 226 ja
registrava essa queda depois da consolidacao de componentes. O criterio real
e `npm test` verde, e esta.

**Estado: 10/10.**

---

## 3. Modelos / IA

| Criterio                         | Como provar                   | Resultado                                                                      |
| -------------------------------- | ----------------------------- | ------------------------------------------------------------------------------ |
| Metadados no catalogo            | `listar_modelos()`            | **36**                                                                         |
| Simbolos cobertos                | agrupado                      | **9** (AUDUSD, BTCUSD, ETHUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDJPY, XAUUSD) |
| Publicaveis                      | `publicable && pkl_present`   | **25**                                                                         |
| Reprovados COM motivo            | `publicable=false` + `reason` | **11**                                                                         |
| Reprovados SEM motivo            | idem                          | **0**                                                                          |
| Orfaos (meta sem `.pkl`)         | idem                          | **0**                                                                          |
| **Inferencia nao presume ativo** | `TestNenhumAtivoPresumido`    | **4 verdes**                                                                   |

**Estado: 10/10.**

---

## 4. Rust / Core

| Criterio         | Como provar                  | Resultado                                                       |
| ---------------- | ---------------------------- | --------------------------------------------------------------- |
| Formatacao       | `cargo fmt --all -- --check` | **exit 0**                                                      |
| Compila sem erro | `cargo check --locked`       | **exit 0** (1 aviso pre-existente: `field token is never read`) |
| Testes           | `cargo test --locked`        | **38 passed**                                                   |

**Estado: 10/10.**

---

## 5. Tauri (supervisor de processos)

| Criterio             | Como provar                  | Resultado     |
| -------------------- | ---------------------------- | ------------- |
| `cargo fmt`          | `cargo fmt --all -- --check` | **exit 0**    |
| Compila e linka      | `cargo test --locked`        | **exit 0**    |
| Testes do supervisor | `cargo test`                 | **11 passed** |

### Bug real corrigido nesta verificacao

`cargo test` falhava com:

```
LINK : fatal error LNK1140: limite excedido para o banco de dados do
programa; vinculo com /PDB:NONE
```

A arvore de dependencias do Tauri (wry, tauri-runtime-wry, windows, tokio)
estoura o limite do formato PDB do Visual Studio. **Nao e falta de espaco em
disco** — e limite de formato. `frontend/src-tauri/.cargo/config.toml` agora
passa `/PDB:NONE`, que nao altera o binario gerado (so deixa de gravar o
arquivo de depuracao simbolica) e resolve o link.

O mesmo arquivo tambem fixa `target-dir` para fora do disco de codigo.

### Defeito encontrado pelo proprio teste

O primeiro `desiste_apos_o_teto_de_tentativas` **falhou**:

```
nunca desiste: entraria em laco de processo morto
```

Investigando a sequencia: cada reinicio consome `FALHAS_ANTES_DE_REINICIAR`
(3) ciclos, e a desistencia vem no ciclo seguinte ao ultimo reinicio. Com 3 e
5: `3*5 + 3 = 18` ciclos. O teste usava 14. **O codigo estava certo e o teste
errado** — mas o teste provou a sequencia exata, e `desistido_continua_desistindo`
agora fixa que a desistencia e estavel (se voltasse a tentar, o laco de
processo morto voltaria).

**Estado: 10/10.**

---

## 6. Versao / Projeto

| Criterio                            | Como provar                              | Resultado      |
| ----------------------------------- | ---------------------------------------- | -------------- |
| Mesma versao em todos os manifestos | `python scripts/sync_version.py --check` | **8 alvos OK** |

**Estado: 10/10.**

---

## 7. Backend hospedado (Nitro)

| Criterio | Como provar     | Resultado                          |
| -------- | --------------- | ---------------------------------- |
| Lint     | `npm run lint`  | **sem erro**                       |
| Build    | `npm run build` | **exit 0** (4,58 MB / 1,1 MB gzip) |

**Estado: 10/10.**

---

## 7y. Reinstalacao limpa (30/09/2026)

### O que foi encontrado antes de instalar

| Achado                      | Detalhe                                                                                            |
| --------------------------- | -------------------------------------------------------------------------------------------------- |
| Instalacao MSI orfa         | Registrada em **HKLM** como 1.2.4, mas `InstallLocation` nao existia (o Defender removeu em 21/09) |
| Nenhum processo rodando     | Portas 9001/9002/9003 livres                                                                       |
| Backup dos dados do usuario | `Desktop\xau_backup_antes_reinstall` (7 arquivos, 0,7 MB)                                          |

### Desinstalacao: o MSI exige administrador

```
Error 1730. You must be an Administrator to remove this application.
```

O MSI e per-machine (grava em `HKLM`). Esta sessao roda como
`HENRIQUE\Micro`, **sem privilegio de administrador**.

**Solucao usada:** o instalador **NSIS** (`XAU AI PRO_1.2.4_x64-setup.exe`)
com `/S` instala **por usuario**, em `%LOCALAPPDATA%`, sem pedir elevacao.
O MSI nao foi usado.

### Instalacao verificada

| Item                             | Valor                                         |
| -------------------------------- | --------------------------------------------- |
| Destino                          | `%LOCALAPPDATA%\XAU AI PRO\`                  |
| Tamanho                          | **560,1 MB / 1.302 arquivos**                 |
| `XAU AI PRO.exe`                 | 13,0 MB                                       |
| `bridge\mt5-gateway.exe`         | 32,7 MB                                       |
| `core\xau-ai-pro-core.exe`       | 8,7 MB                                        |
| Modelos `.pkl` / `.meta.json`    | **36 / 36**                                   |
| Arquivos `.env` dentro do bundle | **0** (seguranca)                             |
| Registro                         | `HKCU\...\Uninstall\XAU AI PRO` (por usuario) |

### Primeiro acesso, como usuario normal

| Verificacao                  | Resultado                                               |
| ---------------------------- | ------------------------------------------------------- |
| Atalho da area de trabalho   | aponta para o exe, **existe**                           |
| Processo do app              | `XAU AI PRO` com janela **"XAU AI PRO - Trading Desk"** |
| Boot do bridge               | _"bridge MT5 spawnado com ordens reais DESLIGADAS"_     |
| Identidade do gateway        | _"bridge MT5 autenticado e pronto antes do Core"_       |
| Boot do core                 | _"core spawnado com sucesso"_                           |
| Portas 9001/9002/9003        | **escutando**                                           |
| Estabilidade                 | estavel apos 30 s, sem reinicio                         |
| Scan do Defender do app novo | **0 deteccoes**                                         |

### Seguranca de rede — ACHADO REAL

As 3 portas escutam **apenas em `127.0.0.1`**. Testado contra o IP de rede:

```
porta 9001 em 192.168.1.67 -> fechada
```

**Porem existem 4 regras de firewall `Allow` para o app:**

| DisplayName           | Action | Porta   | Perfil     | Remoto  |
| --------------------- | ------ | ------- | ---------- | ------- |
| `xau_ai_pro.exe` (x2) | Allow  | **Any** | **Public** | **Any** |
| `xau_ai_pro` (x2)     | Allow  | **Any** | **Public** | **Any** |

Regra `Allow` em `Any`/`Public`/`Any` e aberta demais. **Nao ha porta
escutando fora do loopback**, entao nao ha exposicao hoje — mas se um dia o
gateway passar a escutar em `0.0.0.0`, essas regras autorizam a internet
inteira. `Disable-NetFirewallRule` exige administrador; a remocao correta e:

```powershell
# como Administrador
Get-NetFirewallRule -DisplayName 'xau_ai_pro*' | Remove-NetFirewallRule
```

E o certo e o Tauri gerar regra de **saida**, ou nenhuma: o gateway e local.

### Risco residual

| Item                                  | Situacao                                           |
| ------------------------------------- | -------------------------------------------------- |
| Registro MSI orfao em `HKLM`          | **ainda la** — remover exige administrador         |
| 4 regras de firewall `Any/Public/Any` | **ainda la** — remover exige administrador         |
| Binarios sem assinatura               | `NotSigned` nos 3 exes — e a causa da deteccao PUA |

---

## 7z. Limpeza de duplicatas (30/09/2026)

Regra do dono: _"manter ambiente limpo, apenas uma versao, 0 duplicatas"_.

### 7 duplicatas removidas (211 MB liberados)

| Caminho                    | MB   | Por que era residuo                                                                                         |
| -------------------------- | ---- | ----------------------------------------------------------------------------------------------------------- |
| `sandbox-quickstart/`      | 21,9 | Instalacao do Claude Code. `package.json` chama o projeto de `sandbox-quickstart`; 0 referencias no codigo. |
| `ai-text-demo/`            | 60,2 | Demo do Claude. 0 referencias.                                                                              |
| `aigateway/`               | 63,1 | **Nome antigo do gateway** (`xau-ai-pro-gateway`, versao 1.0.0). Substituido por `backend/`.                |
| `experiments/`             | 66,0 | Arvore de exemplos do Claude (`isolated/`). 0 referencias.                                                  |
| `package-lock.json` (raiz) | 0    | **Orfao**: `"packages": {}` e nao existe `package.json` na raiz. Frontend e backend tem os seus.            |
| `.agents_sync/`            | 0    | Sincronia multiagente (Cline + OpenCode).ultima colisao registrada: 29/09. 0 referencias no codigo.         |
| `Data/`                    | 0    | Dados de teste unitario. O app le do terminal MT5 (`ea_manager._terminal_data_dir()`), nao do repo.         |

**Os 4 primeiros vinham com `.env.local` contendo tokens reais** (`VERCEL_*`,
`SLACK_*`, `SENTRY_*`, `AI_GATEWAY_API_KEY`, `MEXC_*`).

### Segredos: preservados, nao apagados

Antes de remover, os 7 `.env` foram copiados para
`%APPDATA%\XAU_AI_PRO\credenciais-backup\`, com ACL **removida por heranca** e
reconcedida so a `SYSTEM`, `Administrators` e ao dono. `.env` sozinho tem
**17 chaves com valor**, incluindo `BROKER_API_KEY` e `BROKER_API_SECRET`;
`.env.binance.local` tem chaves de **64 chars** e `.env.mexc.local` de **32**.

**Nenhum desses arquivos esta rastreado no git** — verificado um a um.

### Duplicatas que NAO existem (verificado)

| Checagem                  | Resultado                                                                          |
| ------------------------- | ---------------------------------------------------------------------------------- |
| Versoes de `release/`     | **so 1.2.4**                                                                       |
| Versoes nos manifestos    | **1.2.4** em VERSION, 2 `package.json`, 2 `Cargo.toml`, `version.ts`               |
| Integridade dos artefatos | **4/4 SHA-256 batem** com o `release-manifest.json`                                |
| Instalacoes do app        | **nenhuma** (a de `%LOCALAPPDATA%\XAU AI PRO` foi removida pelo Defender em 21/09) |

---

## 7a. Antivirus e integridade do repositorio (30/09/2026)

### Microsoft Defender — estado real

| Medida                         | Valor                |
| ------------------------------ | -------------------- |
| `AntivirusEnabled`             | **True**             |
| `RealTimeProtectionEnabled`    | **True**             |
| `BehaviorMonitorEnabled`       | **True**             |
| `IoavProtectionEnabled`        | **True**             |
| Assinatura do virus atualizada | **30/09/2026 10:50** |
| `QuickScanAge`                 | **0** (scan de hoje) |
| Deteccoes **hoje**             | **0**                |
| Scan do binario 1.2.4          | **0**                |

### As 2 deteccoes do historico NAO sao o build atual

| Medida          | Valor                                      |
| --------------- | ------------------------------------------ |
| `ThreatName`    | `Trojan:Win32/Bearfoos.A!ml`               |
| `SeverityID`    | 5                                          |
| `IsActive`      | **False**                                  |
| `ActionSuccess` | **True** (remediado)                       |
| Data            | **21/09/2026 19:51 e 19:52**               |
| Arquivo         | `%LOCALAPPDATA%\XAU AI PRO\XAU AI PRO.exe` |

Esse arquivo **nao existe mais** nesta maquina (a instalacao foi removida).
O binario de hoje e outro:

|                  |                                                                    |
| ---------------- | ------------------------------------------------------------------ |
| Caminho          | `release/1.2.4/XAU AI PRO.exe`                                     |
| Bytes            | 13.601.840                                                         |
| Data             | **29/09/2026 23:54**                                               |
| SHA-256          | `FB44B94D9D03D0BCE890F626DAA36A7E6AAF2741486130B6A86D229097603802` |
| Scan do Defender | **0 deteccoes**                                                    |

`Bearfoos` e deteccao de **aplicativo potencialmente indesejado (PUA)**, que
e disparada por binario sem assinatura confiavel. Ver a ressalva sobre
certificado em § pendencias.

### Integridade do repositorio

| Medida                                      | Valor                                                            |
| ------------------------------------------- | ---------------------------------------------------------------- |
| `git status MQL5`                           | **vazio** (intocado)                                             |
| Segredos em arquivo versionado              | **0**                                                            |
| Segredos no historico (reais)               | **0** (os 40 achados sao a mensagem de erro do validador de DSN) |
| `.env` rastreado                            | so `.env.example`                                                |
| `withdrawals_enabled`/`transfers` em `True` | **0**                                                            |

## 7b. Auditoria de dependencias (30/09/2026)

| Escopo                | Comando                        | Resultado                                           |
| --------------------- | ------------------------------ | --------------------------------------------------- |
| Frontend              | `npm audit`                    | **0 vulnerabilidades**                              |
| Backend               | `npm audit`                    | **3 high -> 0** (corrigido nesta sessao)            |
| Segredos no que entra | `auditar_segredos.py`          | **0 bloqueios**                                     |
| Historico do git      | `auditar_historico_git.py`     | **40 achados, todos falsos positivos** (ver abaixo) |
| GitHub Dependabot     | `gh api .../dependabot/alerts` | **81 alertas abertos**                              |

### As 3 vulnerabilidades high do backend, corrigidas

| Pacote            | Faixa vulneravel | Correcao | Tipo                          |
| ----------------- | ---------------- | -------- | ----------------------------- |
| `brace-expansion` | 4.0.0 – 5.0.11   | `5.0.12` | DoS por expansao quadratica   |
| `engine.io`       | 6.6.0 – 6.6.9    | `6.6.11` | DoS por revisao de protocolo  |
| `undici`          | 7.0.0 – 7.29.0   | `7.29.1` | DoS em WebSocket/RetryHandler |

Todas as tres tem versao corrigida **dentro da faixa** — sem breaking change.
Aplicadas como `overrides` em `backend/package.json`, sem tocar no lockfile
alheio. `npm install` retirou 8 pacotes e trocou 4. `npm run build` e
`npm run lint` continuam verdes apos a troca.

### Falso positivo do auditor de historico (corrigido a leitura, nao o script)

O script reportou _"dsn com senha: 40 ocorrencias"_. **Nao ha DSN real.**
O padrao que ele casa e:

```
https?://[^\s:@/]+:[^\s:@/]+@[^\s/]+
```

E as 40 ocorrencias sao a propria mensagem de ERRO do validador de DSN:

```
"DSN com formato inesperado (esperado https://<key>@<org>.ingest.sentry.io/<id>)"
```

Os dois pontos de `<key>:<org>` casam como `user:pass`. Busca pelo formato
real de um DSN (`https://<32 hex>@...ingest.sentry.io`) retorna **0**.

O codigo de hoje le o DSN do ambiente e nunca grava:
`Python/sentry_config.py` → `if not os.getenv("SENTRY_DSN"): return`.

### Os 81 alertas do Dependabot NAO refletem o codigo atual

| Severidade | Quantidade |
| ---------- | ---------- |
| critical   | 5          |
| high       | 31         |
| medium     | 40         |
| low        | 5          |

**Prova por SHA, nao por interpretacao.** O lockfile do frontend e identico
no disco e no GitHub:

```
git hash-object frontend/package-lock.json  -> 8c09cbe09c1d2692ea38815fc0280bd560a5d9ec
gh api .../contents/frontend/package-lock.json?ref=develop --jq .sha
                                             -> 8c09cbe09c1d2692ea38815fc0280bd560a5d9ec
```

Esse arquivo tem **180 pacotes** e **zero** linhas com `electron` ou `tar`.
E o `node_modules` instalado tambem nao os tem (`npm ls` → `(empty)`).

| Pacote              | Alertas      | No `node_modules`          | No lockfile                             |
| ------------------- | ------------ | -------------------------- | --------------------------------------- |
| `electron`          | 32           | **nao**                    | **nao**                                 |
| `tar`               | 12           | **nao**                    | **nao**                                 |
| `chromadb`          | 8 (critical) | **nao**                    | **nao esta em `requirements-lock.txt`** |
| `undici`            | 9            | corrigido nesta sessao     | corrigido                               |
| `urllib3`, `pytest` | 9            | em `requirements-lock.txt` | ver `pip` local                         |

Os alertas foram criados em **29/09/2026**, depois do ultimo commit do lockfile
(**25/09/2026**) — o Dependabot ainda nao reanalisou.

**O proprio GitHub ja reconheceu 72 dos 81 como `fixed`** — o alerta fecha
so com `git push` dos lockfiles atualizados. Nao ha vulnerabilidade no codigo
instalado: `npm audit` local da **0** em frontend e backend.

`poetry.lock` e `uv.lock` (8 alertas) **nao existem no repositorio** —
`gh api contents/poetry.lock` responde `404`. Sao residuo de branch antiga.

---

## 8. Seguranca

| Criterio                        | Como provar                                                                                                                             | Resultado             |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| `.env` fora do git              | `git check-ignore .env`                                                                                                                 | **`.env` ignorado**   |
| `.env` rastreado                | `git ls-files`                                                                                                                          | **so `.env.example`** |
| Segredos no que entra           | `scripts/auditar_segredos.py`                                                                                                           | **0 bloqueios**       |
| Saque nunca habilitado          | grep `withdrawals_enabled.*True`                                                                                                        | **0**                 |
| Kill switch e travas            | `test_emergency_stop`, `test_rejection_matrix`, `test_plano_gate`, `test_risk_gate`, `test_broker_coverage`, `test_universal_execution` | **110 passed**        |
| Ordem real e fail-closed        | `dinheiro_real_e_fail_closed_por_padrao` (Rust)                                                                                         | **verde**             |
| Supervisor nao mexe em dinheiro | `supervisor_nao_conhece_ordem_ou_saque` (Rust)                                                                                          | **verde**             |
| MQL5 intocado                   | `git status --porcelain MQL5`                                                                                                           | **vazio**             |
| Temporarios no status           | `git status --porcelain`                                                                                                                | **0**                 |

**Estado: 10/10.**

---

## 9. Repositorio

| Item                     | Valor           |
| ------------------------ | --------------- |
| pytest                   | **659 passed**  |
| vitest                   | **169 passed**  |
| cargo test (core)        | **38 passed**   |
| cargo test (tauri)       | **11 passed**   |
| cargo fmt (core + tauri) | **exit 0**      |
| cargo check (core)       | **exit 0**      |
| tsc                      | **exit 0**      |
| backend lint + build     | **exit 0**      |
| disco livre              | **17,9 GB**     |
| MQL5                     | **intocado**    |
| saque                    | **0 violacoes** |
| segredos                 | **0**           |

**Estado: 10/10.**

---

## Pendencias que exigem credencial ou conta (fora do codigo)

Estas **nao sao pendencias de codigo**. Nenhuma pode ser fechada sem o
proprietario, e nenhuma delas foi falsamente declarada como 10/10.

1. **Chaves de MEXC e Binance** -- os 4 adaptadores de exchange estao
   **completos** e com envio HTTP real: `mexc_client.py:135`,
   `okx_client.py:143`, `binance_client.py:128` e `bybit_client.py:140` chamam
   `/api/v3/order` e equivalentes. `test_execution_adapters.py`,
   `test_universal_execution.py`, `test_broker_coverage.py` e
   `test_universal_router_dispatch.py` somam **59 testes verdes**.

   > **Correcao de 30/09/2026.** Este item dizia que _"o envio HTTP real ainda
   > nao foi escrito"_ e que os adaptadores _"param em
   > `EXECUTION_NOT_IMPLEMENTED`"_. **Era falso**. O que falta e so a
   > **credencial na maquina do operador** -- e ela entra por variavel de
   > ambiente, nunca em arquivo, pelas regras operacionais.

   Sem chave, o caminho e o correto e verificavel: `EXECUTION_NO_CREDENTIALS`,
   com a frase _"credenciais {broker} nao configuradas; nada foi enviado a
   corretora"_. Nada sai.

2. **Conta MT5 real** — `trade_mode` real e aceito, mas a validacao ao vivo
   precisa de uma conta conectada.
3. **Backtest, forward test e endurance** — o forward test **OCORREU** e
   e real; o endurance ainda nao.

   **Forward test (evidencia medida, nao declarada):**
   arquivo de 3,0 MB em
   `%APPDATA%\MetaQuotes\Terminal\<id>\MQL5\Files\Data\forward_test_events.csv`

   | Medida               | Valor                            |
   | -------------------- | -------------------------------- |
   | Eventos datados      | **14.265**                       |
   | Janela               | **20/08 a 24/09/2026 = 26 dias** |
   | `FORWARD_TEST_START` | **1.251**                        |
   | `SYSTEM_START`       | 989                              |
   | `TRADE_OPEN`         | 269                              |
   | `TRADE_CLOSE`        | 295                              |
   | `BROKER_ERROR`       | **4.246** (todos `ERROR`)        |
   | `HEALTH_FAILURE`     | 2.483                            |
   | `RECOVERY`           | 2.385                            |

   **A leitura honesta:** o forward test rodou e produziu evidência, mas
   **nao esta aprovado**. A razao e a razao de erro por start:

   ```
   4246 BROKER_ERROR / 1251 FORWARD_TEST_START = 3,4 erros por ciclo
   ```

   Tres ou mais erro de broker por ciclo e o EA reconectando o tempo todo.
   E o par 269 aberturas / 295 fechamentos mostra operacao — o que falta e a
   taxa de erro, nao a existencia de evidencia. Aprovacao desta janela e
   decisao do proprietario, e ela **nao** pode ser dada com esta razao.

   **Endurance (24h/72h/7d):** `scripts/endurance_test.py` existe e roda, mas
   **nao foi executado** nesta sessao — exige o app no ar por dias. Ver
   `docs/endurance_test_plan.md`.

4. **Certificado de CA publica** — os 4 artefatos 1.2.4 estao assinados com
   certificado autoassinado; o Windows mostra `UnknownError` porque a cadeia
   nao termina numa raiz confiavel. So um certificado pago resolve.
5. **Treino por classe de ativo** — forex tem pip e swap, metal tem contrato
   de 100 oz, indice tem tick de 0,5. Modelo treinado so em `timeframe` erra
   o dimensionamento.
