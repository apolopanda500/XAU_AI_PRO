# Índice de Docs — XAU AI PRO

Atualizado em **30/09/2026**. Este mapa existe porque a pasta chegou a ter
61 arquivos com quatro "FINAL" e cinco "HANDOFF" disputando o mesmo assunto.

**Comece por:** [`LEVANTAMENTO_20260930.md`](./LEVANTAMENTO_20260930.md) —
paridade entre corretoras, os dois defeitos que a tela esconde (ativo
inventado e motor que opera a corretora errada) e as etapas propostas.
Depois: [`SESSAO_20260930.md`](./SESSAO_20260930.md) — como o build 1.2.4
foi fechado.

---

## Referência do estado atual

| Documento | Quando | Sobre |
|---|---|---|
| **`MAPEAMENTO_10_10_VERIFICADO_20260930.md`** | 30/09 | **10/10 real, camada por camada, com o comando de cada prova.** Leia primeiro. |
| **`LEVANTAMENTO_20260930.md`** | 30/09 | **Paridade de corretoras + as 5 etapas executadas.** Leia segundo. |
| **`SESSAO_20260930.md`** | 30/09 | Estado verificado do build 1.2.4 assinado |
| `AUDITORIA_20260929.md` | 29/09 | Auditoria de segurança e integridade com comandos reproduzíveis |
| `CORECOES_OPERACAO_20260929.md` | 29/09 | Correções do motor de operação automática |
| `HANDOFF_20260928.md` | 29/09 03:00 | Snapshot do build 1.2.4 anterior (mantido por referência) |
| `MAPEAMENTO_10_10.md` | 28/09 | Avaliação camada por camada com comando de prova |
| `ESTADO_E_PENDENCIAS.md` | 27/09 | Estado e pendências daquele ciclo |

> **Atenção:** os documentos de 27 a 29/09 descrevem ciclos anteriores. Para
> saber o que é verdade **hoje**, o `LEVANTAMENTO_20260930.md` tem precedência.

---

## Políticas técnicas (vigentes)

Estas descrevem regras que **continuam valendo**. Não são registros de sessão.

| Documento | Assunto |
|---|---|
| `risk_control_policy.md` | Política única de risco; regras do Risk Control Center |
| `model_governance_policy.md` | Governança de IA: `min_edge`, `publicable`, reprovação |
| `security_checklist.md` | Checklist de segurança operacional |
| `failover_matrix.md` | Matriz de failover dos 9 cenários |
| `ARCHITECTURE.md` | Arquitetura e decisões técnicas do sistema |

---

## Build, instalação e operação

| Documento | Assunto |
|---|---|
| `INSTALL.md` | Instalação |
| `ACOMPANHAMENTO_OFICIAL_PC_20260921.md` | Acompanhamento do build para PC |
| `TESTE_APK_EMULADOR.md` | Teste do APK no emulador |
| `PRODUCAO_ANDROID.md` | Produção Android |
| `DEPLOY_GATEWAY_REMOTO_ANDROID.md` | Deploy do gateway remoto |
| `VERCEL_INTEGRACAO.md` | Integração Vercel |
| `endurance_test_plan.md` | Plano do teste de endurance |
| `production_readiness.md` | Prontidão para produção |
| `production_gate_etapa24.md` | Gate de produção |

---

## Corretoras e ativos

| Documento | Assunto |
|---|---|
| `MATRIZ_CAPABILIDADES.md` | Capacidades por corretora e ativo |
| `TROUBLESHOOTING_NEW_BROKER.md` | Diagnóstico de corretora nova |
| `MARKET_SYMBOLS` (código) | Símbolos negociáveis — ver `app/market_symbols.py` |

---

## IA e dados

| Documento | Assunto |
|---|---|
| `REFERENCE_NOTES.md` | Notas de referência de treino |
| `ANALISE_ESTRUTURA_20260918.md` | Análise da estrutura do dataset |
| `BUG_HISTORICO_20260916.md` | Histórico de bugs de dados |

---

## Produto e roadmap

| Documento | Assunto |
|---|---|
| `DECISOES_PRODUTO_20260925.md` | Decisões de produto tomadas |
| `STATUS_ATUAL.md` | Status do projeto |
| `PLANO_CORRECAO.md` | Plano de correção |
| `PLANO_EXECUCAO_v1.2.3.md` | Plano de execução da v1.2.3 |
| `PLANO_PRODUTO_VERIFICAVEL_20260923.md` | Plano de produto verificável |
| `RELATORIO_UI_UX_E_NOTAS_PRODUTO_20260925.md` | Relatório de UI/UX |
| `ROADMAP_STORE.md` | Roadmap de publicação |
| `ciclo_guardian_watchdog.md` | Ciclo do Guardian e do watchdog |

---

## MCP e plugins

| Documento | Assunto |
|---|---|
| `MCP_ECOSSISTEMA.md` | Ecossistema MCP |
| `MCP_INTEGRATIONS.md` | Integrações MCP |
| `GITHUB_ISSUES_CONFIG.md` | Configuração de issues no GitHub |
| `PROJECT_PROFILE.md` | Perfil do projeto |
| `PLATFORM_PATTERNS.md` | Padrões de plataforma |

---

## Removidos em 30/09/2026

Treze documentos de julho e agosto, quando o projeto ainda era outra coisa.
Todos estavam versionados e continuam recuperáveis:

```
git show <commit-antigo>:Docs/<arquivo>
```

| Removido | Data original | Motivo |
|---|---|---|
| `AUDITORIA_V1.0.md` | 30/07 | Auditoria de julho, outro produto |
| `AUDITORIA_V1.0_FINAL.md` | 31/07 | Marcada "Bloqueado — falta o código-fonte do EA" |
| `CORRECOES_APLICADAS.md` | 30/07 | Correções de julho |
| `ROADMAP_V1.0.md` | 30/07 | Roadmap substituído pelo atual |
| `ACAO_IMEDIATA.md` | 31/07 | "Aguardando sua ação" de julho |
| `LITELLM_FIX.md` | 02/08 | Correção de um proxy específico |
| `FASE_8_HARDENING.md` | 03/08 | Fase de agosto |
| `MCP_CONFIGURACAO_CLINE.md` | 09/08 | Registro de sessão de agosto |
| `AUDITORIA_V1.2.0.md` | 18/08 | Auditoria feita por "MetaTrader Assistant" |
| `FINAL_RELEASE_etapa25.md` | 24/08 | Release v1.2.0-RC1 |
| `HANDOFF_XAU_AI_PRO_20260923.md` | 23/09 | Substituído pelo handoff de 28/09 |
| `HANDOFF_2026-09-14_XAU_AI_PRO.md` | 14/09 | Sessão antiga |
| `HANDOFF_XAU_AI_PRO_20260925.md` | 25/09 | Substituído pelo handoff de 28/09 |

---

## Regra para o futuro

Um documento de sessão serve para responder "o que aconteceu e por quê".
Ele **não** serve para dizer "como o sistema funciona hoje" — para isso são
as políticas técnicas.

Quando uma sessão gerar documentação nova, ela entra aqui no índice e a
anterior sai da lista de "Referência do estado atual".