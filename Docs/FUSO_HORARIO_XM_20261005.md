# FUSO HORARIO — O QUE A CAPTURA XM PROVOU (05/10/2026, 21:01)

## A medicao

`Screenshot 2026-10-05 210126.png` mostra o seletor de fuso da XM aberto. Tres
fatos, lidos da tela:

1. **A lista e de CIDADES com o offset entre parenteses**, nao uma lista de
   fusos tecnicos: `(UTC-6) Chicago`, `(UTC-5) Lima`, `(UTC-4) Caracas`,
   `(UTC-4) Nova York`, `(UTC-3) Buenos Aires`, `(UTC-3) Santiago`,
   `(UTC-3) Sao Paulo` (marcado com tick), `(UTC) Acores`, `(UTC) Reykjavik`,
   `(UTC+1) Casablanca/Dublin/Lagos/Lisboa/Londres/Tunis`,
   `(UTC+2) Amsterdam/Belgrado/Budapeste`.

2. **O rodape mostra `21:01:24 UTC-3`** — o OFFSET, nao a cidade. A cidade e o
   item do menu; o relogio mostra o numero.

3. **`auto` aparece em AZUL**, ou seja, o modo automatico e o padrao e a lista e
   a excecao. **Nao e um seletor de fuso: e um override sobre um fuso derivado.**

## Consequencia medida no grafico

Na captura anterior (`Screenshot ... 20:47`) o rodape era `02:47:49 UTC+3`. Na de
21:01 e `21:01:24 UTC-3`. Os candles foram redesenhados no fuso escolhido e o
cabecalho mudou de `-189,50 (-0,22%)` para `+42,50 (+0,05%)`.

Trocar de fuso **mexe no grafico**. Nao e so rotulo.

## O que foi feito neste ciclo

- `frontend/src/lib/fuso.ts` — catalogo de cidades com zona IANA, offset lido do
  `Intl` na data pedida, `rotuloOffset`, `listaOrdenada`, `horaNaZona`,
  `fusoAutomatico`, `ehConhecida`.
- `frontend/src/lib/fuso.test.ts` — 18 testes.

## Decisoes e por que

**Offset sem tabela.** O Brasil nao tem horario de verao desde 2019, e Buenos
Aires (2015) e Santiago (2016) tambem nao. Mas Londres muda: UTC+0 em janeiro,
UTC+1 em outubro. Numero fixo em tabela fica errado na virada, e o operador
leria um relogio que mente sem aviso. O caminho do teste prova que le o `Intl`:
`Europe/London` devolve 0 em janeiro e 60 em outubro na mesma funcao.

**Chave e a ZONA, nao o offset.** Sao Paulo e Santiago tem o mesmo offset em
outubro e nao sao o mesmo fuso. Quem escolhe Santiago precisa receber a regra de
Santiago. Trocar os dois pelo offset seria trocar fuso por numero.

**Zona invalida lanca.** `RangeError` em vez de offset silencioso: e melhor o
operador ver o erro do que ver um relogio errado sem origem.

**`auto` nao vira item da lista.** MEDIDO nesta maquina: o fuso do navegador e
`America/Sao_Paulo`, que ESTA no catalogo — e o comportamento desejado, porque o
operador quer poder escolher a propria cidade. O que e proibido e `auto`
aparecer como mais uma cidade, duplicando a escolha. O teste mede a lista, nao a
comparacao de strings.

## O QUE NAO ESTA FEITO

Este ciclo entregou o **nucleo de dados**. Faltam tres consumidores, e sao eles
que dao o item ao dono:

1. **O seletor na tela.** O componente com a lista, o tick, e o item `auto`.
2. **`QuantumClock` nao le a escolha.** Hoje usa
   `Intl.DateTimeFormat().resolvedOptions().timeZone` implicitamente, via
   `toLocaleDateString('pt-BR')` — ou seja, fuso do navegador e nada mais.
3. **O calendario continua com `tz=BRT` FIXO na URL** (`useEconomicData.ts:256`).
   Se o operador trocar o fuso, o grafico acompanha e o calendario nao.

E o grafico: `lightweight-charts` 4.2.3 desenha o eixo no fuso do BROWSER e nao
aceita troca. Fuso de exibição no grafico é mudanca de dado (timestamp
convertido), nao de rotulo — item proprio, com medicao propria.