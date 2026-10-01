# Progressão VIP por volume — o que as corretoras fazem de verdade

> Pesquisa de 01/10/2026 para desenhar a escada VIP. O código está em
> `backend/vip_progress.py`.

## O problema que motivou

O projeto tinha três nomes de plano (Free / VIP / VIPS) e **nenhuma relação
entre operar e subir de nível**. O plano era uma etiqueta: você ativava
"Business" e pronto. Nas corretoras reais é o contrário — o nível é
conquistado por **volume**, e a corretora mostra quanto falta.

## As duas referências

### PrimeXBT — "How VIP Tiers Work"

Cinco níveis acima do Regular. O que muda por nível:

| Tier | Taker fee | Desconto spread | Desconto exchange | Cashback |
|---|---|---|---|---|
| Regular | 0,045% | — | 1% | — |
| VIP1 | 0,044% | 2% | 5% | 1% |
| VIP2 | 0,042% | 5% | 7% | 2% |
| VIP3 | 0,04% | 10% | 8% | 5% |
| VIP4 | 0,03% | 15% | 10% | 10% |
| VIP5 | 0,015% | 25% | 15% | 10% |

**Maker fee não muda** em nenhum nível.

Volume necessário em 30 dias — e o detalhe que mais importa:

| Tier | Cripto | Forex e CFD |
|---|---|---|
| VIP1 | 10.000 USD | 100.000 USD |
| VIP2 | 100.000 USD | 1.000.000 USD |
| VIP3 | 1.000.000 USD | 10.000.000 USD |
| VIP4 | 5.000.000 USD | 45.000.000 USD |
| VIP5 | 25.000.000 USD | 90.000.000 USD |

Duas regras que só a leitura da tabela revela:

1. **O volume é contado por grupo de instrumento.** Cripto e forex têm limiares
   diferentes — 10x. Isso porque cripto é mais líquido: o mesmo volume em
   USD compra muito mais volume contratual.
2. **O nível trava por 30 dias ao ser alcançado.** Sem isso, um mês fraco
   tiraria o cliente do nível no meio do ciclo, e ele perderia um desconto
   pelo qual já pagou para entrar.

Existe ainda um caminho paralelo: comprar o nível com saldo do *Reward
Center*, sem operar.

### IC Markets — "Raw Spread Account"

O extremo oposto: **não há nível nenhum.** Há um único tipo de conta com
spread a partir de 0,0 pips e comissão de **US$ 3,50 por lote, por lado**.
Média de 0,1 pips em EUR/USD. Servidores em Equinix NY4. Alavancagem 1:5000.

É a mesma lógica vista pelo outro lado: o que o cliente negocia é o **custo
total** (spread + comissão), e a conta existe para quem opera volume alto.

## O que foi construído

`backend/vip_progress.py` implementa a estrutura do PrimeXBT sobre o
`audit.jsonl` real do produto:

- **6 níveis** (Regular + VIP1..VIP5) com os limiares da tabela.
- **Janela de 30 dias**, com `trava_dias` declarado — a regra do "não cai de
  nível no meio do ciclo".
- **Volume contado separado por grupo** (cripto / forex_cfd), porque o
  limiar muda.
- **Nível exige que TODOS os grupos passem.** Sem isso, quem tivesse 500.000 em
  cripto e 20.000 em forex subiria olhando só para o cripto.
- **`proximo` é o primeiro nível NÃO alcançado** — não o primeiro da lista.
  Pular direto daria "falta 0" para quem já passou.

Estado real desta máquina: `Regular`, volume 0 nos dois grupos, `live_execution: False`.

## Limite explícito

Os limiares em código são **estrutura, não promessa comercial**. O desconto
que cada nível concede depende de acordo com a corretora e **não está no
código** — inventar esses números seria a tela mintindo, que é o defeito que
o projeto registrou três vezes (metadados apagados por script legado,
`install_app.bat` apontando para caminho inexistente, plano salvo perdendo-se
no renome).

Nenhuma regra aqui altera plano, libera saque ou habilita dinheiro real.

## Referência

- primexbt.help — "How VIP Tiers Work" (14/07/2026)
- ic.com — "Raw Spread Account"

