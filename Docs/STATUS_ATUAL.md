# STATUS ATUAL DO PROJETO

**Data:** 11/10/2026
**Versão:** 1.2.4
**Status:** app novo **instalado e rodando** pelo atalho; todas as telas validadas;
`0 falhas bloqueantes`. Pendências são **ação do dono** (ver §ABERTO).

---

## LEIA PRIMEIRO

**→ [`Docs/CONVERSA_20261011_TEMAS_RENOMEADOS_E_ESTADO_MEDIDO.md`](CONVERSA_20261011_TEMAS_RENOMEADOS_E_ESTADO_MEDIDO.md)**

Diz o que fazer, o que medir e o que está aberto, com o estado de agora.
Este arquivo é o resumo.

---

## OS NÚMEROS (medidos em 11/10/2026)

| | |
|---|---|
| `preflight --etapa app-rodando` | **0 falhas**, 2 avisos (MQL5 + git pendente) |
| `tsc --noEmit` | **exit 0** |
| app em execução | `XAU AI PRO` + `mt5-gateway` + `xau-ai-pro-core` |
| portas escutando | **9011** (gateway), **9002**/**9003** (core) — ocupadas |
| `frontend/src` com nome de ativo no código | **0** (com comentário/docstring removidos) |
| disco C: livre | **8,99 GB** |
| branch | `develop`, 2 commits à frente de `origin/develop` |
| arquivos pendentes no git | **108** |

Números da suíte completa vêm do ciclo de 10/10 (`1315 passed`, `874 vitest`);
não foram re rodados em 11/10 porque a mudança deste ciclo foi **só documentação**
— nenhum fonte foi tocado, e o `tsc --noEmit` de agora confirma o frontend limpo.

---

## O QUE FOI FEITO NO CICLO DE 11/10

| item | antes | agora |
|---|---|---|
| pergunta de temas com nome de ativo | em aberto (`xau_dark`/`btc_dark`) | **resolvida no código** e **documentada** (`dourado_dark`/`laranja_dark`, com migração da preferência salva) |
| deploy do `.ex5` para o terminal | inexistente (reanexar não copiava) | **`backend/ea_deploy.py`** copia só o `.ex5` (com backup, atômico, `XAU_ALLOW_EA_DEPLOY=1`) + **12 testes** (prova positiva e negativa) |

A renomeação dos temas já estava pronta no fonte; este ciclo **fechou a lacuna de
documentação** e **mediu o estado**.

### ⚠️ Descoberta: o EA no terminal está defasado e operando a conta real

MEDIDO (hash, não data):

| Onde | Hash (12) | Modificado |
|---|---|---|
| repo `XAU_AI_PRO.ex5` | `dc115aecc4df` | 10/10 21:00 |
| terminal `XAU_AI_PRO.ex5` | `6f86cd6e37cd` | **08/10 23:03** |

Compilar no MetaEditor gera o `.ex5` **ao lado do `.mq5`, no repo** — mas o
gráfico carrega de `MQL5/Experts` do **terminal**. Reanexar não copia. O journal
de 11/10 (domingo) mostra o EA **velho** operando a conta 391773676: 1132 vendas
de EURUSD, 566 com `[Market closed]`. Opera EURUSD, não o BTCUSD do app.

**Fechado a ferramenta, não o deploy.** `ea_deploy.py` está pronto e testado,
mas **não copiei** — exige `XAU_ALLOW_EA_DEPLOY=1` e mexe no binário da conta
real. Decisão do dono.

---

## O QUE ESTÁ ABERTO (ação do dono, não do ciclo)

1. **Reanexar o EA ao gráfico.** Compilar não reanexa; 21 arquivos MQL5 estão com
   autorização declarada no preflight. O EA anexado ao terminal é mais antigo que
   o do repo.
2. **Confirmar o AutoTrading do terminal.** A validação do app é só em leitura:
   motor e IA ficam desligados.
3. **Commit dos 108 arquivos** — decisão do dono.
4. **Fechamento espontâneo do app** em sessão longa: medido, sem log nem stack.
   Se repetir, rodar com o console aberto para ter o rastro.

---

**Um documento antigo neste `Docs/` não está desatualizado por estar no fim da
lista — e sim por ser de um ciclo anterior. O `command` vence o número; o
documento mais recente manda.** Ver `CONVERSA_20261011_TEMAS_RENOMEADOS_E_ESTADO_MEDIDO.md` §7.
