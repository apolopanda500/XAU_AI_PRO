# Sessão 05/10/2026 — o que foi feito e o que foi medido

Documento escrito durante a sessão, com o estado medido por comando. Onde a
leitura anterior estava errada, está marcado como **corrigido**.

Vale a regra que vale para o resto do repositório: o que está aqui sem número
de comando não foi medido, foi herdado de relato.

---

## 1. O pedido, na ordem em que chegou

1. Aba Configuração: "não tem como digitar ou modificar as chaves".
2. Pesquisar APIs públicas para calendários e ferramentas que precisam se
   manter vivas.
3. Aba Calendário: reconstruir, copiando o padrão do MT5.
4. Aba Histórico: remover duplicidades.
5. Aba VIPS: não carrega volume.
6. Robô: remover a Mesa, deixar só operação automática + gráfico XM Global +
   MiniTerminal com posições abertas.
7. Barra inferior do app, lado direito, estilo MT5, com latência ao vivo e
   seletor de timeframe.
8. "Temas mais fluidos, abas mais leves".
9. "Ciclos limpos, 0 erros", build final.

---

## 2. Causas raiz encontradas (medidas, não inferidas)

### 2.1 VIPS: o volume nunca foi medido

`audit_log.record()` gravava um conjunto **fixo** de campos:

```
at, action, request_id, account_id, broker, market, symbol, status
```

`volume` não estava entre eles. Mas `vip_progress.volume_por_grupo()` lê
exatamente `evento["volume"] or evento["quantity"]`.

Medido no `audit.jsonl` real (6 ordens `executed` na janela, todas do MT5):
todas sem `volume`. O `float(None)` caía no `continue` e a soma era **zero**.

A tela mostrava `0` como se o cliente não tivesse operado. Ele operou.

**A parte que importa**: `tests/test_vip_progress.py` passava. Os testes
fabricavam um evento **com** `volume`, um formato que o produtor real nunca
gerava. O teste media o formato imaginado, não o formato emitido.

Corrigido em `backend/audit_log.py`, `backend/vip_progress.py` e na tela, com 15
testes Python e 4 de vitest. O teste novo monta o evento passando pelo
`audit_log.record()` de verdade.

Também: `notional` tem precedência sobre `volume` na soma, porque a escada é
medida em **dinheiro** e `volume` de MT5 é **lote**. 0,10 lote de ouro é
~US$ 3.350; somar 0,10 contra um limiar de US$ 10.000 dá o nível errado em três
ordens de grandeza.

### 2.2 Configuração: não existia caminho para trocar uma chave

A tela só sabia **criar** conexão. Trocar a chave significava excluir e cadastrar
outra com o mesmo nome — dois cliques, com a conta sem credencial no meio, e sem
volta se o cadastro novo falhasse.

Faltava no backend: `PUT /api/connections/{id}`. Campo em branco significa
**manter** o que está gravado, o que permite rotacionar a chave sem ler a atual
de volta (a listagem nunca devolve credencial, e com razão).

### 2.3 Calendário: três colunas que nunca podiam ter dado

A tela tinha Anterior / Previsão / Real e as três ficavam permanentemente em
`--`. A fonte era `planos/economic_calendar.py`, que é uma **tabela local de
horários recorrentes**: sabe QUANDO o evento acontece e nada mais.

Coluna morta é pior que coluna ausente — faz o operador desconfiar do resto.

Pesquisa de fonte pública sem chave: `nfs.faireconomy.media/ff_calendar_thisweek.json`.
Medido: 79 eventos na semana, 39 com previsão, 57 com anterior. Limite medido:
`ff_calendar_nextweek.json` e `ff_calendar_lastweek.json` respondem **404**.

Então: semana corrente com número de verdade, semanas seguintes como estimativa
— **cada evento rotulado**, `fonte` e `estimado`, e a tela mostra. Nunca
misturado sem aviso.

O feed respondeu **HTTP 429** durante a sessão. Virou `CalendarUnavailable` com o
código na mensagem (não "indisponível" genérico, que culpa o gateway local) e
cache de 30 min em disco.

### 2.4 Histórico: uma operação aparecia como duas

A tabela listava **deal** por deal. Uma posição que abre às 10:00 e fecha às
14:00 vira dois deals no MT5, e a tela mostrava duas linhas para uma operação.
Somando a coluna Resultado, o operador lia duas operações onde houve uma.

Corrigido por agrupamento: `position_id` quando existe, e
`corretora|ativo` no primeiro deal livre quando não existe — duas ordens
realmente distintas no mesmo par continuam em linhas separadas.

### 2.5 Endpoint morto (achado pelo teste novo)

`DeclaracoesConfianca.tsx` chamava `/api/mt5/account`, que **nenhuma camada do
backend trata**. O `.catch(() => {})` engolia o 404 e a tela mostrava "nenhuma
conta" mesmo com o terminal logado. Falha silenciosa: a tela parecia funcionar.

Corrigido para `/api/status`, que devolve `account`.

### 2.6 Bundle do instalador

`backend/economic_calendar_publica.py` é importado **dentro** de
`_economic_calendar`, e o PyInstaller só enxerga import de topo. Sem declarar no
`hiddenimports`, o gateway congelado sobe normal e a rota responde "agenda
indisponível" — sem exceção e sem log. `tests/test_spec_gateway.py` reprovou e
avisou. Mesmo modo de falha do VIP, que já tem trava própria.

---

## 3. O que mudou na tela

**Robô** — página única, sem sub-aba, na ordem em que se opera:
1. Operação automática (ativo, lote, SL, TP, `AUTO SIM/NÃO`)
2. Modelos e sinais
3. Gráfico XM Global (1 clique, arrastar TP/SL)
4. MiniTerminal (posições abertas)

A Mesa manual saiu. Ordem manual continua existindo no **gráfico**, em 1 clique,
com o mesmo LOTE/SL/TP. O lado BUY/SELL saiu do painel porque é decisão do
**modelo**, não do painel: um toggle ali prometeria algo que o painel não decide.

**Barra inferior** — nova, filha de `.main`, fora do scroll: ativo + timeframe à
esquerda, estado do tempo real e latência por corretora à direita. O seletor de
timeframe marca `M1`/`M30`/`D1` como **só gráfico**, porque
`TIMEFRAMES_VALIDOS` do modelo aceita só M5, M15, H1 e H4. Escolher D1 sem aviso
ligaria um motor que não infere.

**Calendário** — abas por dia, navegação por semana, colunas na ordem do MT5,
importância em três estrelas, detalhe por evento.

---

## 4. Fluidez: o que era enfeite e o que era peso

Transição curta onde a mudança de estado parece erro. E, mais importante, o que
estava gastando quadro sem retorno:

- **Fundo animado**: era o maior custo de repintura do app — tela inteira, DPR
  até 2, 60 partículas, O(n²) pelas linhas de energia, a 60 fps **em todas as
  abas**. Agora: 30 fps, DPR até 1,5, 34 partículas (um terço das comparações),
  e **para fora do foco**.
- **Barra de latência**: `transform: scaleX` em vez de `width`. `width` é
  propriedade de layout; animar reflowa a linha a cada quadro.
- **Números nunca animam**: cotação, PnL e latência sem transição. Um número
  atrasado em relação ao dado é pior do que um número sem animação.
- **`prefers-reduced-motion`** em um bloco único, no fim, com `!important`.

Ganho de FPS no fundo: **60 → 30** (metade dos quadros), **DPR 2 → 1,5**
(44% menos pixels), **partículas 60 → 34** (1770 → 561 comparações por quadro),
e zero trabalho quando a janela não está em foco.

---

## 5. Estado medido no fim da sessão

| Medida | Comando | Resultado |
|---|---|---|
| Python | `pytest -q tests` | **1113 passed**, 1 warning |
| Frontend | `npx vitest run` | **283 passed** em 26 arquivos |
| Tipos | `npx tsc --noEmit` | limpo |
| MQL5 | `pytest -q tests/test_mql5_compila.py` | 2 passed (MetaEditor real) |
| Bundle | `tests/test_spec_gateway.py` | 12 passed |
| Preflight | `scripts/preflight.py` | **BLOQUEADO** — ver §6 |

O único warning é `StarletteDeprecationWarning` do `fastapi.testclient`, de
dependência externa.

### Comparação com o estado anterior do AGENTS.md

| Antes | Agora |
|---|---|
| 1030 passed | 1113 passed (+83) |
| 217 frontend | 283 frontend (+66) |
| 25 arquivos de teste | 26 arquivos |

---

## 6. O que está bloqueado agora

**Preflight: portas 9002 e 9003 ocupadas** pelo processo `xau-ai-pro-core`
(PID 10160) — é o app instalado, rodando.

```
porta 9003 -> PID 10160 : xau-ai-pro-core
porta 9002 -> PID 10160 : xau-ai-pro-core
```

O build final exige essas portas. **Não encerrei o processo**: o dono não pediu, e
há outro agente trabalhando no MT5 nesta máquina. Fechar o app é decisão de quem
está na frente dele.

`[ !! ] 53 arquivos pendentes no git` — 35 modificados, 2 removidos, 16 novos.
Quatro deles (`pytest.ini`, `scripts/endurance_test.py`,
`frontend/src/lib/historico.test.ts`, `tests/test_mql5_compila.py`) **não são
desta sessão**; estavam modificados quando ela começou.

---

## 7. Regras que valem para a continuação

- Nenhuma ordem real foi enviada nesta sessão. Os testes usam `order_check` e
  dublês.
- Nenhum arquivo do build foi apagado com teste no ar.
- `MQL5/Experts` está intacto: `guarda MQL5 [ ok ]`.
- `withdrawals_enabled` continua `False` fixo, agora com teste que varre o
  código inteiro procurando `True`.
