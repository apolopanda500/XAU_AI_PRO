## 8. "Grafico morreu" + "tema claro quebrado" - causas RAIZ medidas (13/11, sessao CMD)

### Causa #1 - o app falava com o gateway errado (estrutural)

O app instalado resolve o gateway HTTP assim (src-tauri/src/main.rs `porta_gateway()`):
le `XAU_GATEWAY_PORT` do ambiente (default 9001). No aparelho do dono:

| .env | porta |
|---|---|
| SO (user env) | **9011** |
| repositorio XAU_AI_PRO/.env | **9027** |
| **`%LOCALAPPDATA%\\XAU AI PRO\\.env`** (o que a app INSTALADA le) | **9027** |

Com 9027 a app fala com o gateway do REPOSITORIO (FastAPI, roda a po ~13:01), que
**nao** tem a rota `/api/publico/ohlc` -> **404**. O frontend caía no fallback
publico ("nenhuma fonte publica respondeu ... binance/yahoo/frankfurter sem
equivalente") e a tela mostrava "Grafico indisponivel" em ambos os temas.

Medido ao vivo: `gateway_autostart.log` mostra `OPTIONS /api/publico/ohlc?... 200`
e `GET /api/publico/ohlc?... 404 Not Found` repetidos. O 9027 responde 401/200
para outras rotas (a app funcionava: conta conectada, WS Online), mas a rota de
ohlc -> 404 -> fallback emudecido pela 404.

**Correcao aplicada pelo CMD**: `%LOCALAPPDATA%\\XAU AI PRO\\.env` ->
`XAU_GATEWAY_PORT=9011` (o bridge embutido, com todos os endpoints).
Backup: `.env.bak_20261113` no mesmo diretorio.
**NUNCA** tocar no 9027 com o mesmo proposito — e o gateway que o EA le (predição).

### Causa #2 - o grafico preso a cores de escuro

`PriceChart.tsx` fixava `layout.textColor='#8b93a7'` e
`grid.horzLines={color:'rgba(139,147,167,.06)'}`. Com o tema **Light**, texto
cinza claro sobre fundo branco = invisivel ("grafico morto"), e a grade sumia.

**Correcao aplicada pelo CMD**: as cores vem do tema via `cssVar('muted')` e
`cssVar('border')` (tokens ja calibrados por tema) + `MutationObserver` em
`data-theme` no `<html>` que reaplica `applyOptions` na troca em runtime.
`vitest`: 8 ficheiros / 120 testes OK; `tsc --noEmit` exit 0.

Medido no Light: grafico visivel (velas vermelhas/verde + Volume + linha 1.29,
legenda legivel). No Dark voltou ao normal (cores = como antes).

### O que continua por ver
- `XAU_GATEWAY_PORT` no `.env` do instalar é INSTALADO PELO APP? Se sim, a
  próxima reinstalação sobrepõe a correção — o instalador precisa escrever 9011
  OU impedir que o app grave outra porta (verificar `main.rs` e o installer NSIS).
- Se o app recriar `.env` com 9027 (bootstrap), reaparece este defeito sem erro
  visivel no log - vigilar apos cada instala/atualizacao.
- `dist/installers/` contem apenas MSI/NSIS 1.2.191 + exe; nada apagado.
- `.env.bak_20261113` (backup do .env da app) foi deixado no aparelho — o
  usuario pode remover quando quiser.

### Layout do ROBO - corte de altura para a dobra (13/11, CMD)

Sintoma: o grafico renderiza (dados e ate screenshots com velas confirmam) mas
a area nasce **abaixo da dobra** e o operador nao a alcanca — no app instalado o
scroll do painel nao avança quando o cursor esta sobre a lista de indicadores
(tela sem scroll naquela zona).

Medido nos screenshots:
- 868px de altura de janela: o grafico so aparece com a janela esticada para
  1900px — lista de indicadores consome ~55-65% da altura (7 itens verticais).

Correcao (so frontend, ssj do painel):
- `indicadores.css`: `.painel-indicadores-lista` passa a grelha de 2 colunas
  (`repeat(2, minmax(0,1fr))`, quebra a 640px), itens com padding 4 px e texto
  11/12px e `.indicador-item-mede` 10px com reticencias. Continua a ser
  texto legivel, so ocupa metade da altura.
- `AcompanharModelos.tsx`: `.grafico-viewport` de `height: calc(100vh - 330px)`
  minHeight 340 para `height: calc(100vh - 470px)` minHeight 250.
- `tsc --noEmit` exit 0; testes de chart/indicadores 123 passed.
- O `overflow-y: auto` de `.content` continua ativo — em telas 1080px o conteudo
  encaixa sem scroll; em telas mais baixas o painel rola normalmente.

Se o resultado nao for suficiente, a proxima iteracao é mover a lista de
indicadores para dentro de `<aside>` fixa lateral (redesign, nao so CSS).

## Estado atual (medido antes de a gente sair)
- App 1.2.191 aberto; WS Online; "EURUSD 16385" como par vivo; ROBO com USDSGD
  configurado; **1 sinais no grafico**; candles desenhando com volume; nenhum
  fallback publico; bridge 9011; custos do tema Light OK.
- Nenhuma alteracao commitada; tree suja multiagente intacta.
