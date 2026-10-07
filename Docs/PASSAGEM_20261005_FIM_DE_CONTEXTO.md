# PASSAGEM DE ESTADO — 05/10/2026, fim de contexto

Numbers measured at the moment of writing. **If a number here disagrees with a
command, the command wins** — and fix this file.

## VALIDACAO MEDIDA

```
frontend: npx tsc --noEmit        -> limpo
frontend: npm run build           -> ok, 195 modulos
frontend: npx vitest run          -> 37 arquivos, 524 passed
python:   pytest -q tests         -> 1191 passed, 1 failed
```

A unica falha do Python e `test_bundle_gateway_artefato`: ela olha o executavel
existente, compilado antes de `backend/alvo_risco.py` existir. **Fecha no build,
nao antes.** Nao e defeito.

## A CAPTURA DO MT5 — ONDE ESTAVA

A referencia do item 1 estava em
`C:\Users\Micro\Pictures\Screenshots\Screenshot 2026-10-05 224845.png`.
Aba Historico do MT5 terminal, conta **391773676** (XMGlobal-MT5 14), com o deal
24503922 aberto. As 4 linhas, literais:

```
2026.10.04 21:53:54   —  260002613 balance CD-AST-PIC 265376085              5,52
2026.10.04 21:53:54   —  260002614 balance EXP05-AST-PIC 265376085             0,10
2026.10.04 21:53:55   —  260002615 credit  Credit-In-100%-$100-NewClients     5,62
2026.10.05 01:46:43  btcusd 24503922 buy 0,01 86394,85 86594,50
                        2026.10.05 02:12:25 86585,35  2,01  0,23%

Lucro: 2,01  Crédito: 5,62  Recarregar: 5,62  Retirada: 0,00  Saldo: 13,25
```

## BLOQUEADOR DE BUILD — RESOLVIDO

`backend/alvo_risco.py` incluido em `mt5-gateway.spec` com o motivo escrito.
`test_spec_gateway.py` passa.

## O QUE ESTA PRONTO E NAO PRECISA SER REFEITO

- D1 horario do evento, D2 dias vazios (`limit=50` -> `200`), D3 bandeira
  (quadrado com sigla; Windows nao desenha bandeira emoji), D4 `--` (celula
  vazia + motivo no `title`).
- Erro do "Valor no risco": era `preco * volume * distancia`, exagerava
  85.865x. Agora e `distancia * volume * contract_size`.
- Trava sem conexao: o botao AUTO desabilita e o handler recusa.
- Unidade `Token(s)`/`Lote(s)` vinda de `asset_class`, faixa de volume da ficha.
- `lib/fuso.ts` (18 testes), `lib/risco.ts` (14), `lib/historicoMt5.ts` (34),
  `lib/volumeUnidade.ts` (13), `backend/alvo_risco.py` (18),
  `tests/test_fuso_calendario.py` (18).
- `backend/planos/economic_calendar.py`: `convert_to_tz` aceita zona IANA
  (antes fuso desconhecido virava UTC **sem erro**), `tz_desconhecida()`.
- `lib/grafico-indicadores`: `rsiValores`, `macdValores` puros e testados.
- Server: `limit=200` no calendario; `useEconomicData.test.ts` (7 testes do
  caminho inteiro — o arquivo **nao existia** antes).

**REMOVIDO NESTE CICLO, E POR QUE** — `HistoryTab.tsx` tinha `resumirPorOperacao`
(21 linhas de agrupamento) e `LinhaResumo`. Substituidos por `linhasMt5`, que
faz o mesmo agrupamento e ainda tem a linha de resumo do MT5. Os testes que
fixavam "uma linha por posicao" foram reescritos **contra os numeros da captura**
em vez de apagados, e os casos que a captura nao tem (fechamento parcial,
`position_id`, corretoras diferentes) continuam com prova negativa em
`historicoMt5.test.ts`.

`formaMovimentacao` ficou **sem consumidor** quando as duas tabelas viraram uma.
Como voce pediu "identificar formas de depositos e saques", ela voltou como
prefixo na propria celula do comentario — e nao numa coluna nova, porque e uma
LEITURA desse texto e duas colunas para o mesmo dado sao dois lugares para
divergirem.

## FILA — 13 ITENS, COM O PONTO EXATO

### 1. ~~D7+D8 Historico MT5~~ **FEITO (05/10/2026) — uma tabela, como a captura**

A tela era DUAS tabelas e na de Operacoes as tres movimentacoes de saldo
apareciam como operacao (`CREDIT`/`BALANCE`, ativo `—`, resultado de deposito).
Agora e **UMA tabela**, e o que separa e o TIPO, como no MT5.

`frontend/src/lib/historicoMt5.ts` — `linhasMt5()` agrupa entrada e fechamento
da MESMA posicao numa linha so, com as colunas na ordem da captura:
`Horario | Ativo | Bilhete | Tipo | Comentario | Volume | Preco | S/L | T/P |
Horario | Preco | Lucro | Mudanca`, mais a linha de resumo em `tfoot`.
`frontend/src/theme/history-grid.css` — `.hist-resumo*`, `.hist-forma*`,
`.hist-comentario`.

**O QUE A CAPTURA CORRIGIU, E O QUE O CODIGO AFIRMAVA ERRADO**

1. O codigo afirmava que "o MT5 mostra entrada e saida em DUAS linhas". **Falso**:
   a captura mostra UMA linha com os dois pares `Horario | Preco` lado a lado.
2. `Credito: 5,62` e `Recarregar: 5,62` sao o **mesmo numero** na captura — os
   dois `balance` (5,52 + 0,10) somam 5,62. Sao coisas diferentes por regra:
   `balance` = deposito do operador, `credit`/`bonus` = concession da corretora.
   Divergem com outros valores, e ha prova negativa para isso.
3. `Tipo` e o lado da **ABERTURA**: a operacao 24503922 e `buy` e o deal de
   saida e `SELL`. Ler o do fechamento escreveria "venda" numa compra.
4. `Bilhete` e o ticket do **FECHAMENTO** (24503922). Com a posicao aberta e o
   ticket da abertura (24503921), que e o unico que existe.
5. `Saldo: 13,25` e o **capital** da conta (o painel XM mostra Saldo $7,63 e
   Capital $13,25) e a soma das movimentacoes do dia da 11,24. O historico nao
   tem como saber qual o operador quer, entao a celula fica `—` e o `title`
   manda para a Carteira.
6. `Mudanca`: a captura escreve `0,23%` e o calculo da `0,22%`
   (86585,35 contra 86394,85 = 0,2205%). O MT5 arredonda por dentro. A
   diferenca esta escrita no teste, e o codigo NAO foi ajustado para "bater".

**ARMADILHA MEDIDA NESTE ITEM:** os comentarios reais da XM sao `CD-AST-PIC` e
`EXP05-AST-PIC` — **PIC**, nao PIX. `formaMovimentacao` casa `\bpix\b` e nao
`pic`, e por isso as tres movimentacoes da conta saem `nao informada`. Um teste
meu esperava `PIX` e reprovou: eu tinha escrito o que SUPOSTO, nao o que a
corretora escreve. Tratar `PIC` como Pix brasileiro seria o app inventando o
metodo de um deposito.

### 2. A6 parte 1 — provedor de contrato no gateway

`MotorAuto.contract_size` e `asset_digits` sao `staticmethod(lambda: None)`.
Ligar em `backend/mt5_gateway.py` lendo `asset_registry` (`trade_contract_size`,
`digits`). Sem isso o modo dinheiro **recusa** (fail-closed, certo) mas nao
opera.

### 3. A6 parte 2 — a tela manda dinheiro

`OperacaoAutomatica` tem a aba `Quantidade` e mostra os DOIS niveis (acima e
abaixo), porque o painel **nao sabe o lado** — o botao diz "a direcao e do
modelo" e o preco e um so (`price ?? last ?? bid ?? ask`). Falta mandar
`sl_valor`/`tp_valor` no `ligar()`.

### 4. A6 parte 3 — botao de IA para risco ao vivo

### 5. A2 — barra horizontal do grafico

`1h · tipo de grafico · Indicadores · layout · + · desfazer · refazer`

### 6. A3 — botao que liga RSI/MACD

A matematica (`rsiValores`/`macdValores`) e os paineis (`GraficoIndicador.tsx`)
**ja existem e tem teste**. Falta o controle na tela: `PriceChart` aceita `rsi` e
`macd` como props, default `false`, e **nenhum consumidor os passa**.

### 7. A1 — ferramentas XM (maior volume)

Barra vertical sempre visivel + painel agrupado com **atalho visivel por linha**.

### 8. A4 — mini barras do grafico, com funcao real

### 9. A5 — precos na tabela de operacao automatica + compactar

### 10. A7 — abas por par treinado

### 11. A8 — sub-aba de acessibilidade (zoom/fonte). Decimais ja existem.

### 12. D5 — a IA roda ao ligar?

`useInferenciaIA` expoe `inferir`, mas `OperacaoAutomatica` chama so `ativar`.
**O botao hoje muda estado; nao se sabe se a inferencia roda.**

### 13. Fuso do eixo do grafico

`lightweight-charts` 4.2.3 desenha no fuso do **browser** e nao aceita troca.
Trocar e **converter timestamp** — muda dado, nao rotulo.

## ARMADILHAS MEDIDAS NESTE CICLO

1. **`tsc` nao resolve import de CSS.** Ele passou enquanto o Vite reprovava, no
   mesmo minuto, com `../theme/` em vez de `../../theme/`. "tsc limpo" NAO
   significa que o build passa.
2. **Teste decorativo:** `monkeypatch.setenv("TZ")` nao troca fuso no Windows
   (nao existe `time.tzset()`). Passava com o bug de volta. Os detectores reais
   sao os que fixam numeros esperados.
3. **Botao `disabled` nao dispara `click`** em jsdom nem em navegador. A guarda
   dentro do handler cobre so o caminho que o `disabled` nao cobre.
4. **Quatro testes meus gravavam o bug do `papel` no motor** (stop de compra em
   105 em vez de 95). Corrigidos, com o motivo escrito em cada.
5. **Brasil nao tem horario de verao desde 2019.** Sao Paulo e UTC-3 o ano
   inteiro. Buenos Aires (2015) e Santiago (2016) tambem nao.
6. **Commit nenhum foi feito.** Arquivos pendentes no git.