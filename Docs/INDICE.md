# Índice de Docs — XAU AI PRO

Atualizado em **11/10/2026**. Este mapa existe porque a pasta chegou a ter
61 arquivos com quatro "FINAL" e cinco "HANDOFF" disputando o mesmo assunto.

**Comece por:** [`CONVERSA_20261011_TEMAS_RENOMEADOS_E_ESTADO_MEDIDO.md`](./CONVERSA_20261011_TEMAS_RENOMEADOS_E_ESTADO_MEDIDO.md) —
**o ciclo de 11/10**: app novo rodando pelo atalho, `0 falhas bloqueantes`, e a
lacuna fechada — a pergunta de temas com nome de ativo (`xau_dark`/`btc_dark`) que
o ciclo anterior deixou em aberto **já estava resolvida no código**
(`dourado_dark`/`laranja_dark`, com migração da preferência) e só faltava
documentar. Sem commit: é decisão do dono.
Depois: [`CONVERSA_20261010_VALIDACAO_COMPLETA_E_APROVACAO.md`](./CONVERSA_20261010_VALIDACAO_COMPLETA_E_APROVACAO.md) —
**o ciclo de 10/10 que fechou tudo**: as 82 imagens lidas, o build 7/7, a
reinstalação limpa (hash da ponte medido, 1,39 GB de resíduo removidos), as
telas medidas uma por uma e **dois defeitos a mais** — o preflight que media
9001 fixa enquanto o produto usava 9011 (corrigido, com prova negativa) e o app
que fecha sozinho em sessão longa (medido, não corrigido). `1315 passed`,
`874 vitest`, `tsc` limpo.
Depois: [`CONVERSA_20261010_AMBIENTE_LIVRE_E_CORRECOES.md`](./CONVERSA_20261010_AMBIENTE_LIVRE_E_CORRECOES.md) —
os 6 defeitos da fila e a decisão dos ícones.
Antes: [`PASSAGEM_20261008_MONITOR_GRAFICO_CALENDARIO.md`](./PASSAGEM_20261008_MONITOR_GRAFICO_CALENDARIO.md) —
o gráfico que nunca aparecia (`symbols_get()` sem a guarda de sessão, 0 → 1640
ativos) e o terminal que pintava ERROR em sete checks que diziam `OK`, porque
casava `Failures`/`Error:` em vez do valor.
Segurança: [`CODE_SCANNING.md`](./CODE_SCANNING.md) — os 19 alertas do CodeQL.

---

## Referência do estado atual

| Documento | Quando | Sobre |
| --------- | ------ | ----- |
| **`CONVERSA_20261011_TEMAS_RENOMEADOS_E_ESTADO_MEDIDO.md`** | 11/10 | **Leitura de entrada.** App novo rodando pelo atalho, `0 falhas`, e a **lacuna fechada**: a pergunta de temas `xau_dark`/`btc_dark` já estava resolvida no código (`dourado_dark`/`laranja_dark`, com migração da preferência) — este ciclo só documentou. Sem commit. |
| **`CONVERSA_20261010_VALIDACAO_COMPLETA_E_APROVACAO.md`** | 10/10 tarde | Build 7/7, reinstalação limpa com hash medido, cada tela validada, e os 2 defeitos achados na validação (preflight com porta fixa — corrigido; app que fecha sozinho — medido). `1315 passed`, `874 vitest`, 9,51 GB livres. |
| **`CONVERSA_20261010_AMBIENTE_LIVRE_E_CORRECOES.md`** | 10/10 | **Os 6 defeitos da fila** (IA que desligava, `max 0`, `MULTI_METALS`, menu do botão direito, excedente sob o gráfico, fuso) e a decisão do dono sobre ícone. |
| **`PASSAGEM_20261008_MONITOR_GRAFICO_CALENDARIO.md`** | 08/10 | **Leitura de entrada.** Os três defeitos medidos, as quatro provas negativas, e **o app no ar sem backend** (porta 9001 sem dono). `1283 passed`, `773 vitest`, `tsc` limpo. |
| **`CONVERSA_20261008_MONITOR_GRAFICO_CALENDARIO.md`** | 08/10 | **A conversa na ordem**: as 6 perguntas, o que cada resposta mudou, e as **3 premessas do resumo anterior que o comando mediu diferente**. |
| **`CONVERSA_20261003_04_DO_WINDOWS_AO_APP_PRONTO.md`** | 03→04/10 | **A conversa na ordem: 6 pedidos, 7 defeitos medidos, o cooldown de margem (3.191×), o EA que não compilava desde `dbdce10`, e as 7 pendências reais.** |
| **`SESSAO_20261003_NOITE_MERGE_E_BROKER_ERROR.md`** | 03/10 noite | **Merge `develop` → `main` (`46fd23b`, 4 conflitos de lockfile) e a causa raiz dos 4.246 `BROKER_ERROR`: 4.165 `EXEC_NO_MARGIN` entre 03h–05h. Conta DEMO preservada.** |
| ---                                                    | ---         | ---                                                                                                                                                                                       |
| **`SESSAO_20261003_TARDE_BUILD_APAGAVA_MODELOS.md`**   | 03/10 tarde | **O `robocopy /MIR` que apagava da pasta do `.spec` os 3 modelos MULTI a cada build; o cron que lê a branch errada; os 199 `ERROR` de ACL corrompida. `833 passed`.** Leitura de entrada. |
| **`SESSAO_20261003_CI_VERMELHO_E_LEITURA_DOCS.md`**    | 03/10 manhã | **Os 3 workflows vermelhos: um corrigido (teste media artefato fora do git), um sem patch no upstream, um que é decisão do dono. Plus a leitura dos 58 docs.**                            |
| **`SESSAO_20261002_MODELOS_MULTI_E_SEGURANCA.md`**     | 02/10 noite | **O ciclo dos 3 modelos MULTI: os 4 defeitos que so apareceram na medicao, o bundle do instalador, a seguranca verificada e o que ficou em aberto.**                                      |
| **`PLANO_MESTRE_20261002.md`**                         | 02/10       | Plano dos 8 ciclos: VIP, modelos multi, operação multi-asset.                                                                                                                             |
| **`CONVERSA_20261002_DO_WINDOWS_AO_APP.md`**           | 02/10       | **A conversa do ciclo, na ordem: 12 pedidos, o que cada um virou e o que ficou aberto.**                                                                                                  |
| **`SESSAO_20261001_VALIDACAO_10_10.md`**               | 01/10 noite | **16 camadas validadas 10/10, a coluna "Leitura" da matriz estava invertida, e a sub-aba VIPs ganhou a escada inteira.**                                                                  |
| **`SESSAO_20261001_VALIDACAO_E_PUSH.md`**              | 01/10       | **Sessão completa: do build travado ao VIP por volume. 13 commits, tudo medido.**                                                                                                         |
| **`VIP_PROGRESSAO.md`**                                | 01/10       | **Pesquisa: como PrimeXBT, IC Markets e IBKR estruturam nível por volume.** Referência, não registro.                                                                                     |
| **`MAPEAMENTO_10_10_VERIFICADO_20260930.md`**          | 30/09       | 10/10 real, camada por camada, com o comando de cada prova.                                                                                                                               |
| **`LEVANTAMENTO_20260930.md`**                         | 30/09       | Paridade de corretoras + as 5 etapas executadas.                                                                                                                                          |
| **`SESSAO_20260930_CICLO_LIMPO.md`**                   | 30/09       | Ciclo de limpeza: disco, artefatos, `NONE`, `cmd.exe`                                                                                                                                     |
| `SESSAO_20260930.md`                                   | 30/09       | Estado verificado do build 1.2.4 assinado                                                                                                                                                 |
| `AUDITORIA_20260929.md`                                | 29/09       | Auditoria de segurança e integridade com comandos reproduzíveis                                                                                                                           |
| `CORECOES_OPERACAO_20260929.md`                        | 29/09       | Correções do motor de operação automática                                                                                                                                                 |
| `HANDOFF_20260928.md`                                  | 29/09 03:00 | Snapshot do build 1.2.4 anterior (mantido por referência)                                                                                                                                 |
| `MAPEAMENTO_10_10.md`                                  | 28/09       | Avaliação camada por camada com comando de prova                                                                                                                                          |
| `ESTADO_E_PENDENCIAS.md`                               | 27/09       | Estado e pendências daquele ciclo                                                                                                                                                         |

> **Atenção:** os documentos de 27 a 30/09 descrevem ciclos anteriores. Para
> saber o que é verdade **hoje**, o `SESSAO_20261001_VALIDACAO_10_10.md` tem
> precedência — ele tem a precedência sobre o próprio documento de 01/10.

---

## Políticas técnicas (vigentes)

Estas descrevem regras que **continuam valendo**. Não são registros de sessão.

| Documento                    | Assunto                                                |
| ---------------------------- | ------------------------------------------------------ |
| `risk_control_policy.md`     | Política única de risco; regras do Risk Control Center |
| `model_governance_policy.md` | Governança de IA: `min_edge`, `publicable`, reprovação |
| `security_checklist.md`      | Checklist de segurança operacional                     |
| `failover_matrix.md`         | Matriz de failover dos 9 cenários                      |
| `ARCHITECTURE.md`            | Arquitetura e decisões técnicas do sistema             |

---

## Build, instalação e operação

| Documento                               | Assunto                         |
| --------------------------------------- | ------------------------------- |
| `INSTALL.md`                            | Instalação                      |
| `ACOMPANHAMENTO_OFICIAL_PC_20260921.md` | Acompanhamento do build para PC |
| `TESTE_APK_EMULADOR.md`                 | Teste do APK no emulador        |
| `PRODUCAO_ANDROID.md`                   | Produção Android                |
| `DEPLOY_GATEWAY_REMOTO_ANDROID.md`      | Deploy do gateway remoto        |
| `endurance_test_plan.md`                | Plano do teste de endurance     |
| `production_readiness.md`               | Prontidão para produção         |
| `production_gate_etapa24.md`            | Gate de produção                |

---

## Corretoras e ativos

| Documento                       | Assunto                                            |
| ------------------------------- | -------------------------------------------------- |
| `MATRIZ_CAPABILIDADES.md`       | Capacidades por corretora e ativo                  |
| `TROUBLESHOOTING_NEW_BROKER.md` | Diagnóstico de corretora nova                      |
| `MARKET_SYMBOLS` (código)       | Símbolos negociáveis — ver `app/market_symbols.py` |

---

## IA e dados

| Documento                       | Assunto                         |
| ------------------------------- | ------------------------------- |
| `REFERENCE_NOTES.md`            | Notas de referência de treino   |
| `ANALISE_ESTRUTURA_20260918.md` | Análise da estrutura do dataset |
| `BUG_HISTORICO_20260916.md`     | Histórico de bugs de dados      |

---

## Produto e roadmap

| Documento                                     | Assunto                         |
| --------------------------------------------- | ------------------------------- |
| `DECISOES_PRODUTO_20260925.md`                | Decisões de produto tomadas     |
| `STATUS_ATUAL.md`                             | Status do projeto               |
| `PLANO_CORRECAO.md`                           | Plano de correção               |
| `PLANO_EXECUCAO_v1.2.3.md`                    | Plano de execução da v1.2.3     |
| `PLANO_PRODUTO_VERIFICAVEL_20260923.md`       | Plano de produto verificável    |
| `RELATORIO_UI_UX_E_NOTAS_PRODUTO_20260925.md` | Relatório de UI/UX              |
| `ROADMAP_STORE.md`                            | Roadmap de publicação           |
| `ciclo_guardian_watchdog.md`                  | Ciclo do Guardian e do watchdog |

---

## MCP e plugins

| Documento                 | Assunto                          |
| ------------------------- | -------------------------------- |
| `MCP_ECOSSISTEMA.md`      | Ecossistema MCP                  |
| `MCP_INTEGRATIONS.md`     | Integrações MCP                  |
| `GITHUB_ISSUES_CONFIG.md` | Configuração de issues no GitHub |
| `PROJECT_PROFILE.md`      | Perfil do projeto                |
| `PLATFORM_PATTERNS.md`    | Padrões de plataforma            |

---

## Removidos em 30/09/2026

Treze documentos de julho e agosto, quando o projeto ainda era outra coisa.
Todos estavam versionados e continuam recuperáveis:

```
git show <commit-antigo>:Docs/<arquivo>
```

| Removido                           | Data original | Motivo                                           |
| ---------------------------------- | ------------- | ------------------------------------------------ |
| `AUDITORIA_V1.0.md`                | 30/07         | Auditoria de julho, outro produto                |
| `AUDITORIA_V1.0_FINAL.md`          | 31/07         | Marcada "Bloqueado — falta o código-fonte do EA" |
| `CORRECOES_APLICADAS.md`           | 30/07         | Correções de julho                               |
| `ROADMAP_V1.0.md`                  | 30/07         | Roadmap substituído pelo atual                   |
| `ACAO_IMEDIATA.md`                 | 31/07         | "Aguardando sua ação" de julho                   |
| `LITELLM_FIX.md`                   | 02/08         | Correção de um proxy específico                  |
| `FASE_8_HARDENING.md`              | 03/08         | Fase de agosto                                   |
| `MCP_CONFIGURACAO_CLINE.md`        | 09/08         | Registro de sessão de agosto                     |
| `AUDITORIA_V1.2.0.md`              | 18/08         | Auditoria feita por "MetaTrader Assistant"       |
| `FINAL_RELEASE_etapa25.md`         | 24/08         | Release v1.2.0-RC1                               |
| `HANDOFF_XAU_AI_PRO_20260923.md`   | 23/09         | Substituído pelo handoff de 28/09                |
| `HANDOFF_2026-09-14_XAU_AI_PRO.md` | 14/09         | Sessão antiga                                    |
| `HANDOFF_XAU_AI_PRO_20260925.md`   | 25/09         | Substituído pelo handoff de 28/09                |

---

## Sessoes de 09/10/2026

| documento | o que responde |
|---|---|
| `SESSAO_20261009_RISCO_DINHEIRO_ESCADA_E_CONTA_ZERO.md` | Risco em dinheiro (spread, DD realizado, `MinFreeMargin`, SL/TP e gatilhos em dolares), escada de 9 padroes, regra sem stop, os 4 defeitos corrigidos, os 8 erros meus, e a conta que foi a zero por `magic 0` |
| `CONVERSA_20261009_PORTA_CONFIGURAVEL_E_APP.md` | Conflito de porta MT5 x gateway (`WinError 10013`), a opcao (B) que deixa a porta configuravel em Python/Core/Tauri/CSP, e o estado do build interrompido |

As duas sao referencia do estado atual. O `AGENTS.md` continua mandando nas regras.

---

## Regra para o futuro

Um documento de sessão serve para responder "o que aconteceu e por quê".
Ele **não** serve para dizer "como o sistema funciona hoje" — para isso são
as políticas técnicas.

Quando uma sessão gerar documentação nova, ela entra aqui no índice e a
anterior sai da lista de "Referência do estado atual".
