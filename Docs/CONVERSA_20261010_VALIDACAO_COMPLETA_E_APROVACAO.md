# CONVERSA 10/10/2026 (tarde) — validação completa, build, reinstalação e aprovação

> Continuação de
> [`CONVERSA_20261010_AMBIENTE_LIVRE_E_CORRECOES.md`](CONVERSA_20261010_AMBIENTE_LIVRE_E_CORRECOES.md).
> Os números são medidos; onde um número daqui divergir do que o comando medir
> agora, **o comando vence** — corrija aqui.
>
> **ESTADO: app novo instalado, rodando pelo atalho, todas as telas medidas.
> Nenhuma falha bloqueante. Duas pendências do dono no §7.**

---

## 1. O que o dono pediu

1. Ver as imagens das mais recentes até as outras pastas antes de continuar.
2. Seguir o mesmo padrão de trabalho: organizado, documentado, salvo em
   conversa, sempre fácil de ler nos dias seguintes.
3. Corrigir todos os itens restantes, validar tudo, testar, **aprovar 10/10 até
   o build**.
4. Limpar temp do Windows e arquivos regeneráveis e seguros.
5. **Desinstalar o app antigo, instalar o novo, executar pelo atalho, testar
   tudo, aprovar 10/10.**

---

## 2. As 82 imagens, lidas

| Pasta | Quantidade | O que documentam |
|---|---|---|
| raiz `Screenshots` | 26 | a evolução do app em 09/10: telas pretas com `Falha ao inicializar` (porta 9011 vs 9001), a tabela com `MULTI_METALS \| MULTI_METALS \| METALS`, e o estado bom de 20:28 |
| `XAU AI PRO APP` | 24 | três arcos: o que funcionava em 06/10 14:34 (300 candles), a regressão das 19:55 (gráfico "Identidade de mercado inválida"), e o log MT5 poluído |
| `XM GLOBAL` | 25 | o terminal web da corretora: menu de contexto, ferramentas de desenho, ordem com 1 clique, TP/SL em valor — o modelo que o menu do app copia |
| `MT5` | 5 | terminal com a conta 391773676, o EA no navegador, o diário com 4 negócios e o balance/crédito +5,62 |
| `RECORTES` | 2 | o dropdown de período (M1 "SÓGRÁFICO" vs M5 "MODELO") e o painel de ordem manual |

**A imagem que resume o ciclo**: `validacao_final_4/3/2/1` mostram a janela preta
com `Falha ao inicializar o ambiente local seguro. Motivo: gateway local não
autenticado. Endereço consultado: http://127.0.0.1:9011`. A correção da fonte
única da porta (`frontend/src/lib/portas.ts`) fez exatamente esse caso passar —
medido hoje, com `XAU_GATEWAY_PORT=9011` no ambiente e o app **sem tela preta**.

---

## 3. As medidas (comando, não adjetivo)

| Medida | Antes (doc anterior) | Agora |
|---|---|---|
| `pytest -q tests` | 1312 passed, 2 skipped | **1315 passed, 2 skipped** |
| `vitest run` | 869 / 65 arquivos | **874 passed / 66 arquivos** |
| `tsc --noEmit` | exit 0 | **exit 0** |
| `cargo fmt --check` / `check --locked` / `test --locked` | ok | **ok** |
| `pytest tests/test_mql5_compila.py` | 2 passed | **2 passed** (MetaEditor real) |
| `preflight --etapa app-rodando` | 0 falhas, 3 avisos | **0 falhas, 2 avisos** |
| nome de ativo no código (`frontend/src`, sem comentário) | 0 | **0** |

Suíte rodada **de novo** depois da correção do preflight (§5): 1315 passed.

---

## 4. O build e a reinstalação, passo a passo

Ordem que funcionou, e que o próximo ciclo pode repetir:

```
1. .\scripts\limpeza_segura.ps1 -Apply -DebugCache     # caches; preserve Temp\cargo-target
2. (Get-FileHash "$env:LOCALAPPDATA\XAU AI PRO\bridge\mt5-gateway.exe").Hash
   (Get-FileHash "frontend\src-tauri\bridge\mt5-gateway.exe").Hash
3. cmd /c "scripts\build_app.bat"                       # 7/7 etapas
4. remover %LOCALAPPDATA%\XAU AI PRO (desinstalar sozinho deixa lixo)
5. rodar o instalador novo
6. Start-Process "$env:USERPROFILE\Desktop\XAU AI PRO.lnk"
```

### Medidas do build

| Etapa | Resultado |
|---|---|
| build completo | 7/7, MSI **339,67 MB** e NSIS **219,64 MB** em `Temp\cargo-target\release\bundle` |
| hash da ponte no build | `F215E488AE17431A840EB59B96423A70B5C86544CD6894535E0BF9BB8DA18FDC` |
| hash da ponte instalada | **idêntico** — build reproduzível, ponte gravada 17:05 (não a de ontem) |
| desinstalação | `exit 0`, mas deixou `bridge`, `core`, `Python`, `uninstall.exe` |
| resíduos removidos | **1,39 GB** — a lição do AGENTS.md §7 |
| instalação nova | `exit 0`, ponte gravada às 17:05:14 (prova de que sobrescreveu) |
| processos | `XAU AI PRO` + `mt5-gateway` + `xau-ai-pro-core` |
| portas | gateway em **9011** (`XAU_GATEWAY_PORT` do ambiente), core em 9002/9003 |
| health sem token | **401** — fail-closed correto (AGENTS.md §4), não defeito |

A comparação de hash provou que a ponte instalada é a do build novo. Sem ela, o
`exit 0` do instalador não provaria nada (é a lição que já estava no §7).

---

## 5. Os defeitos achados na validação

### a) O preflight media a porta que ele mesmo inventava — CORRIGIDO

**MEDIDO**: com `XAU_GATEWAY_PORT=9011`, o app sobe o gateway em 9011 e o
preflight media **9001** — livre, porque o processo escutava em outra porta — e
respondia `[ ok ] porta 9001 (gateway) livre`. A regra 5 na forma mais difícil de
perceber: o aparelho de medir errava, e a resposta dizia que estava tudo bem.

Eram **dois** defeitos na mesma função:

1. `PORTAS = {"gateway": 9001, ...}` — fixa. A variável de ambiente do usuário,
   que o gateway obedece e que o frontend já aprendeu a perguntar
   (`frontend/src/lib/portas.ts`), era ignorada.
2. `checar_portas(esperar_livre=False)`: porta **livre** virava `ok`. A etapa se
   chama `app-rodando`; com o app rodando, porta livre é defeito — o processo não
   subiu. O teste existente afirmava justamente essa moleza
   (`test_portas_ignoradas_quando_o_app_esta_rodando`: `all(ok)` com as portas
   livres), que é o defeito que ele existia para pegar.

**Correção** (`scripts/preflight.py`):

- `porta_do_gateway()` lê `XAU_GATEWAY_PORT`; valor não numérico ou fora da
  faixa cai no padrão 9001.
- Na etapa `app-rodando`, porta livre agora é **falha**, com a dica dizendo para
  conferir a variável.

**Prova negativa medida** (AGENTS.md §6 — uma correção sem prova negativa não
prova nada):

| Cenário | Antes | Agora |
|---|---|---|
| `--etapa app-rodando` **sem** app | `[ ok ] porta 9001 livre` | **`[XX] porta 9011 livre` → BLOQUEADO: 3 falhas** |
| `--etapa app-rodando` **com** app | `[ ok ] porta 9001 livre` (porta errada) | **`[ ok ] porta 9011 ocupada (app em execucao)`** |
| `--etapa longa` sem app | ok | **ok** |

Três testes novos em `tests/test_preflight.py`, e o teste que media o número
fixo passou a apagar a variável antes de medir — ele reprovou na máquina do dono
justamente porque a medição antiga estava errada.

### b) O app fecha sozinho em sessão longa — NÃO CORRIGIDO

**MEDIDO**: duas vezes, no meio da validação por cliques (por volta de 20:18 e
21:30), os três processos morreram e sobraram **6 `msedgewebview2` órfãos**.
Não há `Application Error`/`Application Hang` no Event Viewer — só
`LiveKernelEvent` de rede (NDIS), que é ruído de outra coisa. Reabrido, ficou
vivo 280 s sem fechar.

Não foi corrigido: não há log nem stack para diagnosticar, e chutar causa sem
medida é o defeito que o AGENTS.md §6 existe para evitar. Fica registrado como
**próxima investigação**, com o sintoma exato para procurar.

### c) Linhas `ERROR` com "0 erros" no log do MT5 — não é do nosso fonte

**MEDIDO** agora e de novo nas capturas antigas:

```
20:05:03 MT5 ERROR  JSON errors: 0
20:05:03 MT5 ERROR  Python errors: 0
20:05:03 MT5 ERROR  Indicator errors: 0
```

`MQL5/.../Monitoring/HealthMonitor.mqh` **está correto**: cada `LogError` é
cercado por limite (`g_healthJSONErrors > 2`, `> 1`, `> 5`). A mensagem vem do
**EA anexado ao terminal, que não é o do repo** (o ciclogravado anterior já
tinha medido isso). Some quando o dono reanexar o EA do repo — a mesma
pendência do §7.

---

## 6. O que foi validado na tela (com o app novo, pelo atalho)

Todas as capturas estão em `%TEMP%\opencode\*.png` (**84 capturas**, 133
arquivos e 13,2 MB no total, com os scripts de automação). A automação foi
`PrintWindow` + `mouse_event` (clique, clique direito, roda e digitação); a
digitação por `SendKeys` **não** alcança o `input` dentro do WebView2, então a
busca do fuso ficou provada pelo teste unitário e pela lista aberta na tela, não
por teclado.

| Item da fila | Prova na tela |
|---|---|
| **1. IA não desliga ao trocar de aba** | `Ligar IA` → barra mostra `IA: Ativo`; fui a Histórico e voltei → **continuou `IA: Ativo`**; desliguei de volta |
| **3. Modelos com período certo** | `MODELOS TREINADOS · 28 artefatos · 37 de 37 períodos podem operar`; `MODELO MULTI_METALS 5M \| MULTI_METALS \| **M5**` e mais M15, H1, H4; `MODELO EURUSD 4H \| EURUSD \| H4` |
| **4. Menu do botão direito** | `TRADE` (Comprar `B`, Vender `S`, Stop loss no ponto `T`, Take profit no ponto `P`), `VER` (Afastar, Ajustar a janela, Linhas de grade), `DESENHAR` (Cursor, Linha de tendência, Linha horizontal, Apagar os desenhos). **Sem** menu do webview |
| **5. Excedente sob o gráfico** | uma linha de aviso só, cabeçalho único, chip de sinais com idade da leitura |
| **6. Fuso** | seletor abre em `auto · UTC-3 America/Sao_Paulo`, campo `Buscar cidade, pais ou zona`, lista com centenas de zonas e offsets (`UTC-9:30`, `UTC-11`...) e nomes repetidos com a zona entre parênteses. **O dono confirmou: está funcionando** |
| **Ícones SVG** | barra do gráfico com 10 botões de ícone nítidos + Candles/Linha/Área, EMA/RSI/MACD, M1..MN1 |

Com o MT5 aberto (conta 391773676), a leitura de ponta a ponta:

| Tela | Medida |
|---|---|
| Histórico | `Exibindo 20 operações e 8 movimentações · 50 registros`; `BUY`/`SELL` com símbolo; `BALANCE` e `CREDIT` **sem símbolo**, com o comentário do PIX — §10 medido em dado real |
| Carteira | `Contas conectadas 2/5` (MT5 e MEXC); coluna **SAQUES = "Bloqueados"** em todas — §2 visível na tela |
| Gráfico | `AUDUSD: 300 candles no timeframe M1` renderizando, com aviso de que clicar não arma ordem |
| Calendário | 98 eventos, filtro por dia e por país |
| Configurações | temas **Dourado** e **Laranja** (sem nome de ativo), `MT5 conectado`/`desconectado` conforme o terminal |
| Sistema | `GATEWAY OK`, latência 2,7 s, **Disco C: em 96%** |

---

## 7. O que exige ação do dono

1. **Reanexar o EA ao gráfico.** Compilar não reanexa, e são 21 arquivos MQL5 com
   autorização declarada no preflight. O EA anexado ao terminal é mais antigo que
   o do repositório — a prova são as linhas `ERROR ... errors: 0` do §5.c.
2. **Confirmar o AutoTrading do terminal.** Medido: `trade_expert = True`
   (botão Algotrading **ligado**) com a conta real 391773676, 0 posições
   abertas durante toda a validação. **Não mexi nesse botão** — é configuração
   sua. A validação do app foi feita só em leitura: motor e IA ficaram
   desligados o tempo todo.
3. **Decidir sobre o fechamento espontâneo do app (§5.b).** Se acontecer de
   novo, a primeira medida é rodar com o console aberto para ter o stack.

---

## 8. Ambiente

| Medida | Antes | Depois |
|---|---|---|
| disco C: livre | 8,24 GB | **9,51 GB** |
| `%TEMP%` | 3,59 GB / 31.803 arquivos | **2,06 GB / 30.921** (1,53 GB removidos) |
| processos do app | 3 (versão anterior) | **3** (XAU AI PRO, mt5-gateway, xau-ai-pro-core) |
| portas | — | 9011 (gateway), 9002, 9003 |

Limpeza: 4 itens de `%TEMP%` com mais de 3 dias. **Preservados**:
`%TEMP%\opencode` (área de trabalho das capturas), `%TEMP%\cargo-target` (cache
de build) e `teste_acl_xau` (protegido). `Temp\cargo-target\release\bundle` com
os instaladores novos também preservado — o dono pode precisar reinstalar.

`core\target` (0,36 GB) tinha sido criado por engano durante o `cargo check`,
porque o `CARGO_TARGET_DIR` era relativo ao `core/`. Removido. O caminho certo é
o absoluto de `Temp\cargo-target` — anotado para não repetir.

---

## 9. O que NÃO foi feito, e por quê

- **Corrigir o fechamento espontâneo do app**: sem log nem stack, qualquer
  correção seria chute.
- **Rodar o forward test / endurance**: exigem conta DEMO e tempo de mercado;
  não é passo de validação de build.
- **Commit**: o working tree continua com 102 arquivos pendentes (2º aviso do
  preflight). Commitar é decisão do dono, não do ciclo.
