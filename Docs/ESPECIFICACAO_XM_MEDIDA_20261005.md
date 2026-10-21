# ESPECICAÇÃO MEDIDA — gráfico XM Global (`my.xm.com/pt/symbol-info/BTCUSD`)

Medido nas duas capturas de tela em `C:\Users\Micro\Pictures\Screenshots` de
05/10/2026. As duas mostram o **mesmo** gráfico em dois estados: uma com o
painel de ferramentas aberto, outra fechado. Isso é útil porque dá a
**posição de repouso** e a **posição de trabalho** da mesma tela.

Proporções medidas na captura de 1440×900 (a janela do browser ocupa ~1440×830):
barra lateral esquerda **≈60 px**, painel de ferramentas **≈320 px**,
painel de ordem **≈250 px**, barra vertical direita **≈40 px**, gráfico no meio.

---

## 1. BARRA VERTICAL ESQUERDA — Permanentemente visível, dois grupos

**Grupo de navegação** (ícones de ~24 px, com separador depois):
início · caixa de entrada · calendário · carteiras · cópia de operação ·
prêmio · foguete (sinais) · histórico

**Grupo de ferramentas** (separado por um separador visível):
cursor/cruz · linha de tendência · linhas horizontais · retratação/Fibonacci ·
mrore/forma · caneta · caneta com cadeado · ímã · texto `T` · emoji ·
régua · círculo · zoom `+` ·_SETTINGS_

No rodapé da mesma coluna: um ícone de **lixeira** (descartar desenho).

**Regra de projeto:** a barra é **sempre visível** e só o painel lateral abre e
fecha. Ferramenta escondida atrás de menu é ferramenta que ninguém usa.

## 2. PAINEL LATERAL ESQUERDO — Abre por cima, agrupado e com atalho

Abre **sobre o gráfico**, com o timeframe (`1h`) no topo, e é dividido em grupos
com título em caixa alta:

- **LINHAS**: Linha de Tendência `Alt+T` · Retas · Linha com Informações ·
  Linha Estendida · Ângulo de Tendência · Linha Horizontal `Alt+H` ·
  Raio Horizontal `Alt+J` · Linha Vertical `Alt+V` · Linha Cruzada `Alt+C`
- **CANAIS**: Canal Paralelo · Tendência de Regressão · Topo/Fundo Plano ·
  Canal Não-Paralelo
- **GARFO**: começa logo abaixo do corte da captura
- Cada item: **ícone à esquerda · nome · atalho à direita**
- O item sob o cursor abre um **tooltip com o nome** ("Ferramentas de Linhas de
  Tendência")

**Atalho de teclado visível em cada linha é o detalhe que importa**: o operador
descobre a função sem tirar o olho do gráfico.

## 3. BARRA HORIZONTAL DO GRÁFICO — Só aparece quando o painel fecha

Esta é a diferença entre as duas capturas, e é a informação mais útil:

`1h` · ícone de candle (tipo de gráfico) · **Indicadores** · ícone de grade
(layout) · `+` · **desfazer** · **refazer**

Em seguida, à direita do gráfico: checkbox · **Salvar** · `Bolivar` (dropdown) ·
engrenagem · câmera.

E na base do gráfico: **pills de timeframe** `1H 1D 1W 1M 3M 1Y MAX` à esquerda;
**relógio** `01:10:37 UTC+3` e os toggles `%` · `log` · `auto` + engrenagem à
direita.

Rodapé da janela: `Saldo $7.63 · Capital $13.25 · Margem Livre $13.25 · Margem ·
Nível de Margem ·`

## 4. BARRA VERTICAL DIREITA — Navegação

expandir · **IA (sparkle)** · transmissão/sinal · gráfico com lupa ·
calendário · câmera · grupos · lupa

## 5. PAINEL DE ORDEM (direita) — Ordem de leitura, medida

1. **"ordem com 1 clique"** com interruptor + dois botões grandes:
   **VENDER 85.886,65** (rosa, com contador) e **COMPRAR 85.928,65**
2. Abas **Quantidade | Lotes**
3. **Quantidade** `0.01 lote(s)`
4. **Requisito de margem $0.86** + **slider** mostrando **6.49%**
5. Interruptor **"Vender quando preço atingir"**
6. Interruptor **"TP / SL"** (ligado, verde)
7. Segmentado **Preço | Quantidade**
8. Aviso: *"Os montantes finais podem diferir dos valores introduzidos."*
9. **Montante take profit 2.00 USD**
10. **Nível do preço equivalente: 85.670,25**
11. **Montante stop loss**
12. Botão grande: **"Colocar ordem a 85.886,65"**
13. Selo acima do gráfico: **"Acima do preço de mercado"**

## 6. CABEÇALHO

`Real | $13.25` (conta real + saldo, com dropdown) · **BTCUSD** +1244.30 ↑1.47%
· 1 semana · à direita: sino (notificações) · carteira · perfil.

---

## O QUE ISSO MUDA NO ROBÔ, EM ORDEM DE IMPORTE

1. **Ferramentas em barra vertical sempre visível** (item 1), e o painel
   agrupado **abrindo por cima** com **atalho visível** (item 2). Hoje o Robô não
   tem nenhum dos dois.
2. **Barra horizontal do gráfico** com `Indicadores` · `+` · desfazer · refazer
   (item 3) — é o que falta para os indicadores que você pediu.
3. **Pills de timeframe** e **relógio com fuso** (`01:10:37 UTC+3`) na base do
   gráfico (item 3).
4. **Faixa de conta e saldo** (`Real | $13.25`) no cabeçalho (item 6).
5. **Slider de requisito de margem** e **"nível de preço equivalente"** no painel
   de ordem (item 5) — o量 do risco em dinheiro, não só em pontos.

**O que NÃO muda:** a regra do projeto de que nenhuma ordem sai sem `confirm`
e `request_id`. A XM pede 1 clique; este app pede confirmação. Isso é
intencional e não é uma falha a ser corrigida copiando a tela.