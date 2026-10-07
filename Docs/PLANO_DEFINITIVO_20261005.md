# PLANO DEFINITIVO — 05/10/2026

Este é o plano certo. Nasce de três fontes, todas medidas, nenhuma de memória:

1. **As telas do app** (`C:\Users\Micro\Pictures\Screenshots`, 15 capturas).
2. **O MT5 real** com a conta `391773676` aberto, aba Histórico com os deals.
3. **A referência da XM** (`my.xm.com/pt/symbol-info/BTCUSD`), nos dois estados
   da tela: painel de ferramentas aberto e fechado.

Regra da fase: **um item por vez**, `tsc` a cada passo, **suíte completa e build
só no fim**. Motivo escrito: cada ciclo anterior empilhou seis ou sete mudanças e
só validou no fim — foi assim que passaram o gráfico preto, a trava do AUTO, o
par que não trocava, o "Acompanhar modelos" sem gráfico e a latência invisível.

---

## PARTE 1 — JÁ CONCLUÍDO (não refazer)

| Item | Estado medido |
|---|---|
| Auditoria dos "fixos" | instalador sem `.env`, sem chave; `selectedSymbol: ''`; sem caminho de terminal fixo |
| Histórico: período padrão 30 dias | causa raiz: os 5 deals eram de 04/10 e a aba abria em "Hoje" |
| Calendário 100% PT-BR | cobertura **16% → 100%** contra o feed real (82 eventos) |
| Bandeira quadrada com nome do país | CSS + nome do país escrito ao lado da sigla |
| Navegação: botão "Ontem" | só aparece quando existe evento naquele dia |
| Causa da latência | 401/429/sem corretora colapsavam no mesmo vazio; agora cada estado tem sua frase |
| Servidores MT5 como contas distintas | campo editável + servidor no rótulo + aviso de divergência |
| Fonte pública de preço | Binance 368 ms · Yahoo 578 ms · Frankfurter 77 ms · sem chave |
| Especificação XM gravada | `Docs/ESPECIFICACAO_XM_MEDIDA_20261005.md` |

**Nenhuma dessas está no app instalado** — o build está pendente, por decisão sua.

---

## PARTE 2 — DEFEITOS PROVADOS PELA TELA, em ordem

### D1. Todos os eventos do calendário mostram **19:13**
A coluna Horário é idêntica em 50 linhas. O tempo vem de "agora" em vez do
horário do evento. **É o defeito mais visível do calendário.**
**Aceite:** dois eventos do mesmo dia, em horários diferentes, mostram horários
diferentes — e o teste reprova se todos derem o mesmo minuto.

### D2. Só "Hoje" tem eventos; os outros seis dias mostram **0**
O feed medido cobre **04/10 a 11/10**. Amanhã a domingo, dentro da semana
corrente, vêm vazios. Precisa:_BACKFILL por data real do feed_ e estimativa
para as semanas seguintes, sempre rotulada.
**Aceite:** navegar para amanhã mostra eventos, e o dia sem dado diz por quê.

### D3. As bandeiras **não renderizam**
Aparecem como quadrados brancos, e o chip repete o código ("EU EU").
**Aceite:** a bandeira quadrada mostra a cor e o nome do país; nenhum quadrado
branco em nenhum evento.

### D4. `--` nas colunas Anterior/Real do calendário
Vazio renderizado como trace, a mesma classe de defeito do gráfico preto.
**Aceite:** ausência = célula vazia com rótulo em tooltip, nunca `--`.

### D5. **AI: Inativo** no cabeçalho, em todas as telas
O `MULTI_METALS` tem o melhor edge da lista (25,0%) e não opera porque a IA
está desligada. **É o botão "ativar IA" que você pediu nos comandos.**
**Aceite:** o interruptor liga a IA, o estado muda para "IA ativa" no cabeçalho,
e a inferência passa a alimentar o motor.

### D6. **EA: Desconectado**
Encerrar com真相: o EA precisa ser anexado ao gráfico e reconectado. Não é
código — é passo fora do repositório (AGENTS.md §7).

### D7. Movimentações em tabela separada; o MT5 usa **uma tabela só**
O MT5 puxa `balance`/`credit` como **Tipo**, deixa Volume/Preço/S/L/T/P em
branco e põe o comentário na coluna **Bilhete**. E tem **dois campos Horário**:
o do registro e o de **fechamento** da posição.
**Aceite:** a tabela reproduz a linha do MT5, e a barra de resumo mostra os
cinco números — `Lucro · Crédito · Recarregar · Retirada · Saldo`.

### D8. `Crédito` e `Recarregar` são números diferentes
Medido no MT5: `credit` entra em Crédito (5,62) e `balance` em Recarregar
(5,62). Somados, 11,24 — que é o número que antes aparecia como "SELL".

---

## PARTE 3 — ADIÇÕES PEDIDAS, do mais visível ao menos

### A1. Ferramentas do gráfico (referência XM medida)
- **Barra vertical esquerda sempre visível**, dois grupos separados: navegação
  (início, caixa, calendário, carteiras, cópia, prêmio, foguete, histórico) e
  ferramentas (cruz, tendência, horizontais, Fibonacci, caneta, caneta com
  cadeado, ímã, texto, régua, círculo, zoom), **lixeira no rodapé**.
- **Painel lateral que abre por cima do gráfico**, agrupado — **LINHAS** (com
  `Alt+T`, `Alt+H`, `Alt+J`, `Alt+V`, `Alt+C` visíveis), **CANAIS**, **GARFO** —
  ícone, nome, atalho à direita, tooltip no item sob o cursor.
**Aceite:** a barra existe sem abrir nada; o painel abre e fecha sobre o gráfico;
cada linha mostra o atalho.

### A2. Barra horizontal do gráfico
`1h` · tipo de candle · **Indicadores** · grade · `+` · desfazer · refazer;
à direita: Salvar · dropdown · engrenagem · câmera. Na base: **pills
`1H 1D 1W 1M 3M 1Y MAX`** à esquerda e **relógio com fuso** (`01:10:37 UTC+3`) +
toggles `%` `log` `auto` à direita.

### A3. Indicadores com liga/desliga e valores
RSI, volume, EMA, MACD. Cada um: **liga/desliga** e **período configurável**.
**Aceite:** desligado não desenha nada e não aparece na lista; ligado desenha e
o valor é lido da série real, não fixado.

### A4. Mini barras do gráfico, com função real
Inferior e lateral, e **todo botão executa algo**. Botão sem função não entra
(regra 9 do AGENTS.md: controle sem consumidor é pior que ausência).

### A5. Preços na tabela de operação automática + compactar
Preço **ao vivo** na linha do par, e a tabela mais densa — linha de **22 px**.

### A6. Botão de IA para configurar risco ao vivo
Um clique calcula os limites a partir do que a IA está lendo. **Regra:** o valor
calculado é **mostrado e editável** antes de ser enviado. Nenhum número vai
para o motor sem o operador ver.

### A7. Abas por par treinado
O MT5 tem uma aba por par: `BTCUSD,M5` · `ETHUSD,H1` · `GOLD,H1` · `USDJPY,H1`
· `USDCHF,H1` · `USDCNH,H1` · `USDSEK,H1` · `GBPUSD,H1` · `EURUSD,H1` ·
`AUDUSD,H1`, com `SYM,TF` e o relógio à direita.

### A8. Acessibilidade (sub-aba)
Zoom e tamanho de fonte. **Casas decimais de 1 a 5 já existe** em
Geral/Interface, com slider — não criar um segundo.

---

## PARTE 4 — ORDEM DE EXECUÇÃO

```
 1. D1 horário do evento        (defeito, visível)
 2. D2 dias vazios             (defeito, visível)
 3. D3 bandeira não renderiza  (defeito, visível)
 4. D4 trace no calendário     (defeito, visível)
 5. D7 + D8 histórico MT5      (defeito, medido na tela)
 6. D5 botão de IA             (defeito, visível)
 7. A2 barra horizontal        (base dos indicadores)
 8. A3 indicadores             (depende de 7)
 9. A1 ferramentas + painéis   (maior volume)
10. A4 mini barras com função
11. A5 preços na tabela
12. A6 risco pela IA
13. A7 abas por par
14. A8 acessibilidade
15. VALIDAÇÃO COMPLETA
16. BUILD + INSTALAÇÃO
```

Cada item: implementa → `tsc` → suíte do item → **compara com a tela**.

---

## PARTE 5 — VALIDAÇÃO E BUILD (o fim, e só o fim)

```
1. npx tsc --noEmit
2. npx vitest run
3. .venv\Scripts\python.exe -m pytest -q tests
4. .venv\Scripts\python.exe -m pytest -q tests\test_mql5_compila.py
5. .venv\Scripts\python.exe scripts\preflight.py --etapa app-rodando
6. scripts\build_app.bat
7. scripts\conferir_bundle_gateway.py
8. Desinstalar → instalar o NSIS → abrir pelo atalho → medir processos e portas
9. CONFERIR CONTRA AS 15 CAPTURAS
```

**O passo 9 é o que faltou sempre.** Depois do build, abrir o app e comparar
tela a tela com as capturas: nenhum `--`, nenhum quadrado branco, nenhum 19:13,
IA ativa, latência com número, histórico no formato MT5.

---

## PARTE 6 — O QUE NÃO SE FAZ

- **Nada de ordem real.** `XAU_ENABLE_REAL_ORDERS` fica em `0`; nenhuma flag de
  execução é ligada. Toda ordem continua exigindo `confirm` e `request_id`.
- **Nada de saque ou transferência.** `withdrawals_enabled` e `transfers` seguem
  `False` (AGENTS.md §2).
- **Nenhuma chave no código.** As fontes públicas não precisam de chave; se
  alguma precisar, ela entra em campo de configuração do operador.
- **Nenhuma credencial de terminal.** Os servidores são nomes; a autenticação
  acontece no MT5.
- **Nenhum controle sem consumidor.** Cada botão novo executa algo, e o que não
  tem uso sai com o motivo escrito no código.
- **Nenhum `xfail`.** Onde existe compilador e código, erro reprova.

---

## PARTE 7 — PERGUNTAS QUE MUDAM O PLANO

1. **O EA precisa ser reanexado** ao gráfico do `[BTCUSD,M5]` para sair de
   "EA: Desconectado". Você faz esse passo no terminal?
2. **A IA ligada deve operar sozinha**, ou só出来后 suggestion e você confirma
   antes de enviar? A segunda é a que o projeto já exige; a primeira é
  SAMO com `XAU_ENABLE_DEMO_ORDERS` ligado.
3. **Ferramentas de desenho: precisam persistir?** Salvo no MT5 elas sobrevivem
   à sessão; aqui, sem `.ex5` versionado, a persistência é decisão sua.