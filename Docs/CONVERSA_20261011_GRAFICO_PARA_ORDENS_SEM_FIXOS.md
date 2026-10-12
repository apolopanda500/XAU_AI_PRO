# Conversa 11/10/2026 (noite) — gráfico para ordens, sem MT5/BTCUSD fixos

> Estado medido ao fim do ciclo. Se um número aqui divergir do que o comando
> mostrar, o comando vence.

## O que o dono mandou (respostas às 2 perguntas + lista)

1. **Edição indo para fora do gráfico** — confirmado: segmento azul com pontas
   flutuando no cabeçalho (captura 12:29), horizontal riscando a página.
2. **Ferramentas genéricas** — resposta: NÃO existir barra inferior ou lateral
   no gráfico para editar/estudar/analisar; **o gráfico é para colocar ordens**.
   (Referência XM verificada em `Pictures\Screenshots\XM GLOBAL` — 25 capturas,
   `202814` com a lateral de desenho e `141407` com as linhas de ordem.)
3. **Falta de tabela no gráfico operacional** — travada com teste.
4. **BTCUSD/MT5 fixos** — resposta: na ROBÔ, partes de cima e gráfico com "MT5"
   fixo não pode; modelo/par BTCUSD fixo não pode.
5. App limpo, 0 duplicatas, validação 10/10.

## O que saiu do gráfico (decisão do dono)

Barra de ferramentas (cursor, tendência, horizontal, apagar, limpar,
desfazer/refazer de desenho), fileira de estilo (cor, espessura, opacidade,
cadeado), camada SVG, desenho por clique, arraste de pontas, `Ctrl+Z` de
desenho, itens DESENHAR/LIMPAR/grade do menu de contexto, dica de ferramenta.

O QUE FICA (é ordem): arrastar stop/alvo, `x` de stop/alvo, timeframe, tipo de
gráfico, indicadores, zoom do menu, tabela de dados. Clique continua sem armar.

Arquivos APAGADOS: `charts/BarraFerramentas.tsx`, `charts/IconesGrafico.tsx`,
`charts/desenhos.ts`, `charts/PriceChart.desenhos.test.tsx`,
`charts/desenhos.test.ts`. Regras CSS mortas removidas de `market.css`.
`MenuGrafico` ficou só com TRADE + VER. Zoom restante: roda do mouse + menu.

## Sem MT5/BTCUSD fixos

- `escopoAtivo()`: sem chave gravada → `{broker:'', market:''}` (era
  `mt5:forex`). Novo `lib/escopoAtivo.test.ts` (4/4).
- Leitores sem fallback: `AcompanharModelos` (+aviso "Sem corretora escolhida"),
  `OperacaoAutomatica` (cabeçalho "sem corretora", ligar recusa nomeando a
  barra inferior, sem consulta de quotes), `SeletorModelo` (catalogo vazio),
  `RobotMarketBar` ("sem corretora — escolha a conta"), `UniversalLiveTerminal`
  (fechamento sem conta nomeia Conexões), `useCatalogoAtivos` (sem broker, sem
  fetch), `PriceChart` (`defaultMarket('')=''`, fonte some do cabeçalho).
- `SeletorModelo`: sem par → placeholder "Escolha o par…" (era o primeiro
  modelo publicável = BTCUSD, GRAVADO no store); sem modelo → "Escolha o
  modelo…"; mensagem de vazio aponta o seletor ao lado.
- `mercadoParaConsulta(undefined, '') === ''` (regra pura + teste).

## Validação (11/10, ~19:00)

- `pytest -q tests`: **1330 passed, 2 skipped**.
- `npx vitest run`: **844 passed, 10 failed** — só `EconomicCalendarTab`
  (pré-existentes, de outro ciclo). `ListaModelos` voltou a passar.
- `npx tsc --noEmit`: limpo. `git diff --check`: limpo.
- `build_app.bat`: completo. Instalação com `bridge` apagado, hash
  instalado = repo. App no ar (3 processos), portas 9011/9002/9003, 401 sem
  token (fail-closed correto). `preflight app-rodando`: sem falha bloqueante.

## NÃO feito / perguntas

1. Indicadores (EMA/RSI/MACD) ficaram como opção de VISÃO. Se "estudar/
   analisar" incluía eles, é mais um corte — confirmar.
2. As 10 falhas do EconomicCalendarTab são de outro ciclo — têm dono?
3. EA: nada `.mq5` tocado; os 21 declarados seguem exigindo MetaEditor64 +
   reanexar (§7). MT5 segue fechado — validação em tela com ele aberto fica
   para o dono.

## Adendo 20:40 — aba Plano lia "Failed to fetch" no app instalado

MEDIDO nas capturas 19:41 (Configurações → Plano): "Assinatura indisponível:
Failed to fetch" + "Catálogo indisponível: Failed to fetch", com o resto do
app funcionando. Causa: `backend.planos.subscriptions` (e `caminhos`,
`social_paper`) nunca entraram no `hiddenimports` do `mt5-gateway.spec` —
nenhum import de topo os alcança (`__init__.py` vazio, imports dentro de
função) — e o teste-guarda só varria `backend/*.py`, nunca `planos/`. No
`.exe` congelado a rota cai a conexão sem resposta (TypeError, não 401).

Correção: 3 entradas no spec + teste-guarda estendido
(`test_nenhum_modulo_do_planos_fica_de_fora_do_bundle`,
`test_modulos_das_assinaturas_estao_declarados` — ambos REPROVARAM antes do
fix, 15/15 depois). Rebuild + reinstalação: `/api/subscriptions/plans`,
`/me`, `/api/social/strategies`, `/api/vip/progress`, `/api/acesso` respondem
401 sem token (rota viva, fail-closed correto) em vez de derrubar a conexão.

Script novo: `scripts/capturar_tela.ps1` (foto única ou intervalada, sem
interferir; CRLF por `test_scripts_windows_crlf.py`).

Validação final: pytest **1333 passed, 2 skipped** (era 1330; +3 do spec...
na verdade +2 planos + CRLF coberto); vitest **844 passed, 10 failed** (só
EconomicCalendar, pré-existentes); tsc limpo; diff-check limpo.

## Adendo 21h — 20 capturas revisadas + segunda leva de fixes

- Plano FUNCIONANDO no instalado (VIPS ativo) — fix do hiddenimports confirmado em tela.
- Crash React #310 no Grafico ao vivo: if (!simbolo) return antes do ultimo hook — movido para depois; teste de alternancia.
- Fonte vazia 'Candles OHLC reais · · sinais do modelo' — sourceLabel agora undefined sem corretora.
- Beco sem saida: Sincronizar/Ativar gravam a conta ativa; Desativar limpa; refusas apontam Conexoes.
- Botao recolher/expandir cortado com sidebar minimizada — topo empilha (teste Sidebar).
- 1 grafico so, na Operacao (RobotTabs + 6 testes).
- Validacao: pytest 1333/0, vitest 857 passed + 10 pre-existentes (EconomicCalendar), tsc limpo.
- Rebuild + reinstalacao OK (hash igual), rotas 401, preflight sem bloqueio.

## Adendo 12/10 — comparacao MT5 aberto x fechado + motor universal

- Com MT5 ABERTO e escopo MEXC (sem credenciais validas): graficos de forex vazios + motor em loop 'mercado nao suportado para mexc'. Causa: escopo errado, nao codigo morto.
- MotorAuto.ligar() agora recusa par (corretora, mercado) nao suportado NA PORTA (mesma regra do roker_registry), com 3 testes. Fim do erro-em-loop.
- Planos NAO dependem do MT5: ackend/planos/*.py sem uma referencia a MT5; catalogo carregou com MT5 fechado (captura 20:39).
- WARN 'Spot/Futuros indisponivel' agora traz o motivo (CryptoAccount.error, cortado em 90) — rede OK (mexc/binance ping 200), falta a credencial valer.
- Instalacao: NSIS /S com mesma versao pode DESINSTALAR em vez de instalar (pasta sumiu); reinstalado do zero, hash igual.
- Commit 1f76d93 push origin/develop. Validacao: pytest 1336/0, vitest 857+10 pre-existentes, tsc limpo.
