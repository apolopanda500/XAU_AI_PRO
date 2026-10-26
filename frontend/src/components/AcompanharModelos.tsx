import { useMemo } from 'react';
import { apiBase } from '../lib/api';
import { useAutoState, useUniversalPositions, usePositions } from '../hooks/queries';
import { useAppStore } from '../hooks/useAppStore';
import { useSinaisModelo } from '../hooks/useSinaisModelo';
import { getCandles, getCandlesLivres, LIMITE_VELAS_GRAFICO, type MarketCandle } from '../lib/marketApi';
import { notify } from '../lib/notify';
import { requestId } from '../lib/format';
import { useEffect, useState, useRef } from 'react';
import PriceChart from './charts/PriceChart';
import { nivelDoValor, linhasDaOrdem, rotuloDoBotao } from '../lib/ordemGrafico';
import { parNaTela } from '../lib/parNaTela';
import { fichaDoAtivo, faixaDoAtivo, mercadoDoAtivo, requisitoDeMargem, unidadeDeVolume, rotuloQuantidade } from '../lib/volumeUnidade';
import { useCatalogoAtivos } from '../hooks/useCatalogoAtivos';
import { useUniversalAccount } from '../hooks/queries';
import { escopoAtivo as contaAtiva } from '../lib/escopoAtivo';
import { TIMEFRAMES } from './charts/PriceChart';

// Acompanhar os modelos operando, ao vivo e com seguranca.
//
// O operador elogiou o grafico tempo real para operar. Faltava ver ONDE o
// modelo decide: o sinal vinha como numero solto no painel, sem contexto de
// preco nem de hora. Aqui cada sinal vira marcador no candle (BUY verde
// abaixo, SELL vermelho acima) com a confianca, e a fita mostra o historico
// com a idade de cada leitura.
//
// SEGURANCA
// =========
// - 1-clique usa LOTE/SL/TP ja configurados no motor, com confirmacao
//   explicita mostrando tudo. Sem config, o botao diz o que falta.
// - Sem resposta, a fita mostra "desatualizado ha Xs" em vez de sumir: sinal
//   velho passado por novo e o modo silencioso de operar no escuro.
// - Sem par configurado no motor, o painel diz isso em vez de adivinhar um.
/**
 * O MOTIVO DA ATUALIZACAO QUE FALHOU, com o que a tela MOSTRA de verdade
 * (11/10/2026).
 *
 * MEDIDO na captura das 12:24, MT5 fechado: 300 candles na tela e, na mesma
 * tela, "Gráfico indisponível: candles ausentes ou inválidos no upstream". O
 * intervalo de 30s falhava e o `erroVelas` ficava gravado por cima do dado que
 * ja estava la — duas telas da mesma tela discordando (AGENTS.md 5), com o
 * agravante de o grafico estar desenhado.
 *
 * Com dado em mao, a falha e da ATUALIZACAO e nao do grafico: o texto diz as
 * duas coisas, o motivo e o que a tela esta mostrando. Sem dado, o motivo vai
 * sem enfeite — e o `PriceChart` e quem coloca "Gráfico indisponível" na
 * frente, que e o caso em que o nome e o certo.
 *
 * Funcao pura de proposito: o `erroVigente` do PriceChart ja trancava o lado
 * de la; esta e a mesma trava deste lado, e ela e medida direto.
 */
export function erroDeVelas(motivo: string, temCandles: boolean): string {
  return temCandles
    ? `Atualização falhou: ${motivo} — mostrando os últimos candles recebidos.`
    : motivo;
}

export default function AcompanharModelos() {
  const autoQ = useAutoState();
  const auto = autoQ.data;
  const parDaTela = useAppStore((s) => s.selectedSymbol);
  /*
    O MESMO PAR, PELOS MESMOTRÔS MOTIVOS DO PAINEL (06/10/2026)
    ============================================================
    MEDIDO no app instalado: a aba mostrava um cartao morto com o titulo
    "Acompanhar modelos" e a frase "Configure o par no motor para ver os sinais
    no grafico" — enquanto a barra inferior, na MESMA tela, ja mostrava `BTCUSD`
    escolhido e o grafico de `OperacaoAutomatica` tinha o par resolvido.

    Este componente lia SO `auto.simbolo`. `OperacaoAutomatica` (linha 179) ja
    resolvia `auto.simbolo || parEscolhido` desde 05/10/2026, porque o motor
    comeca SEM par e so recebe um quando alguem configura. Resultado: dois
    componentes, o mesmo dado, uma versao com reserva e outra sem — e o sintoma
    caia no componente que NAO tinha reserva, com uma mensagem que mandava o
    operador configurar algo que ele ja tinha configurado.

    E o AGENTS.md 5: o defeito e do lado que LE o nome diferente, e o relato
    apontava para o servidor.

    O que entra no `configurado` agora: `timeframe` e `market` sao os unicos que
    continuam sendo exigidos, porque sao o que a consulta precisa. Sem timeframe
    nao ha candles para ler, e sem par nao ha grafico — nesses dois casos a tela
    diz ONDE escolher, e nao promete sinal.
  */
  const simbolo = parNaTela(auto, parDaTela);
  const timeframe = String(auto?.timeframe ?? '').toUpperCase();
  /*
    O PERIODO E O MERCADO PODEM VIR DA FICHA (07/10/2026)
    ====================================================
    MEDIDO no app instalado 00:33, com o build novo:

        Gráfico indisponível: Identidade de mercado inválida.
        BTCUSD sem candles reais para .

    O `para .` com o ponto final e o `timeframe` VAZIO chegando no `PriceChart`,
    e a linha do rodapé dizia `BTCUSD · — ·` (o tracejado no lugar do periodo).

    A CAUSA, e e a mesma que o bloco de `OperacaoAutomatica` documenta com
    40 linhas: este componente lia SO `auto.market` e `auto.timeframe`. O motor
    comeca sem par e so recebe quando alguem liga o automatico — entao, com o
    `Motor desligado` na tela, os dois vinham vazios. O `getCandles` recebia
    `market: ''`, e `normalizeMarketSource` devolvia `null` — o throw de
    `marketApi.ts:1368`, que e a mensagem que o operador leu.

    `configurado` exigia `market` E `timeframe`, entao o `useEffect` nem
    buscava: o `error` vinha do `PriceChart`, que tentava por conta propria.

    A RESERVA, e ela e a mesma do outro componente com a MESMA ressalva: o par
    escolhido na barra (`parDaTela`) ja existia, e so o resto faltava.

    POR QUE NAO E ADIVINHAR O MERCADO
    ===================================
    Nao existe palavra no nome que resolva: `BTCUSD` (cripto), `XAUUSD` (metal) e
    `EURUSD` (forex) terminam igual. A classe vem da HIERARQUIA que a corretora
    publica na ficha, e e a mesma regra do `mercado_do_ativo` do motor
    (AGENTS.md 3). Sem ficha, fica o que veio — e o painel diz o que falta.

    O PERIODO, ao contrario, tem uma unica resposta certa: o MODELO escolhido.
    Ha um seletor de modelo na tela de cima, com `H4 · edge 15,5%`. O periodo
    que o operador escolheu e o que o grafico tem de mostrar; um default fixo
    seria a tela discordando do painel logo acima.
  */
  const { broker: brokerSalvo } = contaAtiva();
  /*
    O PRIMEIRO PERIODO DA LISTA do proprio `PriceChart`, e nao um `'M5'` escrito
    aqui.

    A lista e a que o grafico aceita e a que a barra de tempoframes mostra. Uma
    constante solta aqui passaria o teste e o grafico receberia um periodo que
    o componente nao sabe desenhar — e o sintoma seria a tela vazia de novo,
    agora sem mensagem.
  */
  /*
  O TEMPOFRAME E DO OPERADOR, E O DO MODELO E O PONTO DE PARTIDA (09/10/2026)
  ===========================================================================
  MEDIDO pelo dono: "o grafico esta preso em cada ativo, nao tem como escolher
  timeframes diferentes". E MEDIDO no codigo por que:

      PriceChart.tsx:603   const activeTimeframe = timeframe ?? internalTimeframe;
      PriceChart.tsx:1892  if (onTimeframeChange) onTimeframeChange(next);
                            else setInternalTimeframe(next);

  Este componente passa `timeframe={tempoEscolhido}` e NAO passava
  `onTimeframeChange`. Entao:

    - clicar num timeframe chamava `setInternalTimeframe`, que grava estado
      INTERNO;
    - a linha 603 le `timeframe ?? internalTimeframe`, e `timeframe` estava
      SEMPRE definido — o `??` nunca chegava no lado interno;
    - o clique nao mudava NADA. Nove botoes, um botao decorativo: e o AGENTS.md §9
      ("um controle que nada le e pior que a ausencia dele").

  E o timeframe vinha do MODELO (`auto?.timeframe`), entao o grafico ficava
  preso no periodo do modelo — que era a decisao antiga, documentada nas linhas
  93-96 deste arquivo.

  A DECISAO DO DONO, 09/10/2026: o grafico e LIVRE. O modelo e uma lista
  separada, com os periodos que cada modelo REALMENTE foi treinado. Escolher o
  timeframe para ver o ativo e uma coisa; ligar um modelo para operar e outra.

  O que muda:

    - `periodoDoGrafico` e estado PROPRIO, comecando no periodo do modelo (o
      ponto de partida, nao uma prisao);
    - clicar num timeframe passa a valer;
    - trocar de PAR volta ao periodo do modelo daquele par, porque o periodo do
      modelo anterior nao tem nada a ver com o ativo novo.

  E `null` quando o operador escolheu fora do que o modelo cobre: e assim que o
  painel diz "este modelo nao foi treinado em H1", em vez de o painel afirmar
  que o modelo opera no periodo que so o grafico esta mostrando.
*/
const [periodoDoGrafico, setPeriodoDoGrafico] = useState<string>('');
  /*
    A ORDEM DESTA LINHA ERA O DEFEITO (09/10/2026)
    ==============================================
    MEDIDO pelo dono: "clicar num timeframe nao muda nada". O teste
    `AcompanharModelos.grafico.test.tsx` reprovou com

        o clique no timeframe nao valeu: expected 'M15' to be 'W1'

    A ORDEM era `timeframe || periodoDoGrafico`: o periodo do MODELO vinha
    primeiro e cobria o periodo que o OPERADOR tinha clicado. O estado do
    operador existia, era gravado pelo `onTimeframeChange`, e nunca era lido —
    a barra inteira era decorativa, exatamente como o dono reportou.

    Agora a escolha do operador vem primeiro. O `timeframe` continua sendo o
    periodo do modelo e continua sendo o PONTO DE PARTIDA: o `periodoDoGrafico`
    comeca vazio, e o `useEffect` de troca de par o devolve a vazio para o par
    novo. Quem escolheu por ultimo e quem vale.

    `auto?.timeframe` saiu do meio: `timeframe` (linha 61) ja e esse mesmo valor
    com `.toUpperCase()`, e repetir os dois era a mesma leitura com nomes
    diferentes — o defeito que a regra da secao 5 do AGENTS.md descreve.
  */
  const tempoEscolhido = String(
    periodoDoGrafico || timeframe || (TIMEFRAMES[0] as string),
  ).toUpperCase();
  /*
    O BROKER VEM DA CORRETORA ATIVA, E `??` NAO VIAVA (09/10/2026)
    ==============================================================
    MEDIDO: `auto_engine.motor.snapshot()` com o motor DESLIGADO devolve

        broker = ''   market = ''   simbolo = ''   timeframe = ''

    E a linha era

        const broker = String(auto?.broker ?? brokerSalvo ?? 'mt5').toLowerCase();

    (`??` so pega `null` e `undefined`. `'' ?? brokerSalvo` devolve `''` — o
    operador `??` atravessava a string vazia do motor desligado e o `broker`
    ficava vazio.)

    ATOISS O `normalizeMarketSource('' , ...)` devolvia `null`, e o `getCandles`
    LANCAVA "Identidade de mercado invalida" — com o gateway respondendo 300
    candles (MEDIDO: `_universal_candles('mt5','forex','EURUSD','H1',300)` ->
    ok, count=300). O operador lia um erro de IDENTIDADE e culparia o servidor.

    E o AGENTS.md §5: o defeito e do lado que le o nome diferente.

    `||` em vez de `??`: aqui a diferenca entre "nao informado" e "vazio" e o
    que decide qual das DUAS fontes medidas usar. O mesmo operador que produziu
    o defeito no `market`, na mesma cadeia, na mesma tela.

    MEDIDO NESTA MESMA HORA: o primeiro `edit` desta correcao casou a linha DENTRO
    deste comentario — que e o exemplo do codigo ANTIGO — e deixou a linha de
    codigo com `??`. O comentario dizia `||` e o codigo dizia `??`, e o teste
    reprovava por isso. Um `oldString` sem contexto Finds a primeira ocorrencia, e
    num arquivo com documentacao longa a primeira ocorrencia raramente e a que
    voce queria.
  */
  /*
    SEM CORRETORA MEDIDA, SEM CORRETORA NA TELA (11/10/2026, decisao do dono:
    nada de MT5 fixo). Esta linha era `|| 'mt5'` — e a aba ROBO inteira nascia
    falando MT5 antes de o operador escolher qualquer corretora. Agora vazio e
    vazio: `configurado` fica falso, nada e consultado, e o painel diz para
    escolher a corretora/conta (AGENTS.md 3: recusa com motivo, nunca padrao).
  */
  const broker = String(auto?.broker || brokerSalvo || '').toLowerCase();

  /*
    A PROVA NEGATIVA, E ONDE ELA CAI (09/10/2026)
    ===============================================
    Esta linha e a unica alteracao do `??` para o `||`. Desligada, o teste
    "com o motor desligado, o grafico consulta com o BROKER da conta ativa"
    REPROVA com `expected 0 to be greater than 0` — nenhuma consulta sai, porque
    `configurado` e `false` com `broker` vazio.

    E o primeiro `edit` desta correcao nao a achou: casou a linha do exemplo
    dentro do comentario acima. O comentario passou a dizer `||`, o codigo
    continuou `??`, e o teste reprovava por isso — o defeito do CODIGO
    escondido dentro da DOCUMENTACAO do defeito.
  */

  /*
    `pronto1Clique` E `limites` SAIRAM (06/10/2026)

    Eles existiam SO para decidir se os botoes "1-clique" podiam enviar, e os
    botoes sairam a pedido do dono. Deixar o calculo seria um controle sem
    consumidor — o AGENTS.md 9: "um controle que nada lê é pior que a ausência
    dele, porque o usuário acredita que está protegido".

    Os limites continuam sendo lidos pelo MOTOR, na tela de operação automática.
    Esta tela passou a mostrar o que o modelo decide e a permitir operar pelo
    grafico.
  */
  const positionsQ = usePositions();
  const [verEma, setVerEma] = useState(true);

  /*
    A FICHA DO ATIVO, e por que ela e obrigatoria
    =============================================
    O modo em DINHEIRO (padrao da XM) so existe com `contract_size`: sem ele nao
    ha conversao entre dinheiro e preco, e o nivel sairia 100.000 vezes errado em
    forex. `nivelDoValor` devolve `null` nesse caso — recusa, nunca estimativa
    (AGENTS.md 3).

    O CATALOGO vem de `useCatalogoAtivos`, o mesmo hook que `OperacaoAutomatica`
    e `SeletorModelo` leem — e nao de um `getAssets` proprio deste componente.
    MEDIDO ao escrever este codigo: `getAssets` normaliza o payload e devolve
    `MarketAsset`, que NAO tem o campo `contract_size` (ver `marketApi.ts`),
    enquanto `parseAssetCatalog` le o campo do payload CRU. Passar a resposta
    normalizada para o parser dava `contractSize: null` sem erro nenhum: a tela
    dizia "depende do contrato" para um ativo que a corretora ja tinha
    publicado, e o painel ficava travado sem o operador ter feito nada de
    errado. E a regra do AGENTS.md 5 pelo outro lado: o produtor e o consumidor
    discordando do nome, e o sintoma cairia em quem WRITOU a tela.

    `null` e a resposta correta quando a corretora nao devolveu. Nao ha default.
  */
  const catalogo = useCatalogoAtivos(
    (broker || '') as Parameters<typeof useCatalogoAtivos>[0],
    String(auto?.market || '').toLowerCase(),
  );
  const ficha = useMemo(() => fichaDoAtivo(catalogo, simbolo), [catalogo, simbolo]);

  /*
    O MERCADO DA CONSULTA, derivado da classe que a CORRETORA publicou.

    `mercadoDoAtivo` e o mesmo que `OperacaoAutomatica` usa, e o mesmo que
    `mercado_do_ativo` usa no motor: os tres lados falando a mesma lingua, ou o
    sintoma volta a parecer "nao tem preco" — que e o AGENTS.md 5.

    `null` sem ficha: nao ha conversao possivel, e escolher um mercado seria a
    presuncao que a regra proibe.
  */
  const mercadoDaFicha = mercadoDoAtivo(ficha?.assetClass);
  /*
    `marketSalvo` NAO ENTRA NESTA CADEIA, e a razao e o defeito.

    Antes `escopoAtivo()` devolvia `mt5:forex` sem a chave gravada — um DEFAULT,
    nao uma medida (desde 11/10/2026 ele devolve vazio: nada de MT5 fixo). Usar
    um default como mercado de consulta faz o gateway responder vazio para um
    par de cripto, e o sintoma vira "a corretora nao devolve candles". E `OperacaoAutomatica` usa `marketSalvo` como ultimo
    recurso porque ele TEM a ficha antes: ali o fallback so roda com ficha
    carregada, e sem ficha o `configurado` dele ja e falso por outro caminho.

    Aqui o `configurado` NAO pode aceitar `forex` como resposta: sem classe
    publicada nao ha mercado medido, e o painel avisa em vez de consultar.
  */
  const market = String(mercadoDaFicha ?? auto?.market ?? '').toLowerCase();
  const configurado = Boolean(broker && market && simbolo);

  /*
    POSIÇÕES DA CORRETORA ATIVA, SEM MT5 FIXO (12/10/2026).
    MEDIDO nas capturas MT5 do dia: posição sell 0.01 com SL/TP desenhados
    no gráfico e faixa de conta embaixo. O hook legado (`/api/positions`)
    só responde com o terminal aberto; o universal responde pela corretora
    do escopo (MT5 aberto ou não). A lista usada é a que tem dado; com as
    duas respondendo, o universal da conta ativa vence, sem duplicar linha.
  */
  const uniPositionsQ = useUniversalPositions(String(broker || ''), String(market || ''));
  const uniLista = Array.isArray(uniPositionsQ.data?.positions) ? uniPositionsQ.data!.positions! : [];
  const legadoLista = Array.isArray(positionsQ.data?.positions) ? positionsQ.data.positions : [];
  const posicoes = (uniLista.length ? uniLista : legadoLista) as Array<Record<string, unknown>>;

  /*
    A ORDEM ARMADA (06/10/2026)
    ==========================
    MEDIDO nas capturas da XM: o clique ARMA, o painel mostra tudo, e o botao
    `Colocar ordem a <preco>` envia. O estado vive aqui, no pai, porque e o pai
    que tem a ficha do ativo e quem envia — o grafico so devolve o preco.

    `preco` e o que o operador CLIQUEU, e nao o ultimo fechamento. Um clique no
    meio do candle e um preco escolhido: e o que substitui a ordem a mercado do
    motor, que era o defeito do 1-clique removido.

    `papelApagado` guarda o `x`: apagado o stop, a linha some e o painel diz que
    falta stop. `null` e ausencia de linha, e o motivo da recusa — nao um preco
    zero, que o gateway rejeitaria com outra mensagem e outra camada de causa.
  */
  const [precoArmado, setPrecoArmado] = useState<number | null>(null);
  /*
    `descartado` e a resposta a uma REGRESSAO que este ciclo mediu.

    O preco passou a vir do ultimo fechamento (o dono mandou remover o caminho de
    1-clique). O efeito que preenche so age enquanto `precoArmado` e `null` — e
    `Descartar` FAZ ele virar `null`. Resultado: o operador clicava Descartar e
    o painel voltava sozinho, no mesmo tique. O teste `o painel aceita DESCARTER
    sem enviar` reprovou e tinha razao.

    Descartar e um gesto do operador e significa "esta ordem nao existe". Entao
    ele tambem desliga o preenchimento automatico, ate o par ou o periodo mudar —
    que e quando o operador esta olhando outra coisa e espera o painel de novo.
  */
  const [descartado, setDescartado] = useState(false);
  const [volumeArmado, setVolumeArmado] = useState('0.01');
  const [riscoArmado, setRiscoArmado] = useState('2.00');
  const [alvoArmado, setAlvoArmado] = useState('2.00');
  const [enviando, setEnviando] = useState(false);
  const [erroEnvio, setErroEnvio] = useState('');

  const faixa = faixaDoAtivo(ficha);
  const unidade = unidadeDeVolume(ficha?.assetClass);

  /*
    A REQUISITO DE MARGEM (06/10/2026)
    ==================================
    MEDIDO na captura da XM (20:43): `Quantidade 0,01 lotes` ·
    `Requisito de margem $0.85` · barra em `8,01%`.

    O ciclo anterior recusou este numero por causa certa — nao se escreve
    estimativa num painel onde o numero vira limite — e chegou a conclusao
    errada: escreveu que a alavancagem "e um numero que a corretora calcula e
    que o app nao tem de onde ler". **A corretora publica.** MEDIDO no painel
    `Gerir` da XM: `Alavancagem 1000:1`; MEDIDO em `account_info().leverage`:
    `1000`. O gateway agora traz o campo.

    E o numero confere com a conta, o que e o que autoriza a tela a exibi-lo:
    `0,01 x contract_size 1,0 x 85.376,63 = 853,77` de nocional, e
    `853,77 / 1000 = 0,85`. A XM escreve `$0.85`. (Teste:
    `requisitoMargem.test.ts`.)

    A BARRA de margem, essa sim, fica de fora: e `requisito / margem livre`, e a
    margem livre muda a cada tique. Um percentual guardado no painel seria um
    numero que muda sozinho sem ninguem ler.
  */
  const contaQ = useUniversalAccount(String(broker || ''), String(market || ''));
  const conta = (contaQ.data?.account ?? null) as { leverage?: number | null } | null;

  const contrato = ficha?.contractSize;
  const contratoOk = typeof contrato === 'number' && Number.isFinite(contrato) && contrato > 0;

  const requisito = useMemo(
    () => requisitoDeMargem(Number(volumeArmado), precoArmado ?? 0, contrato, conta?.leverage),
    [volumeArmado, precoArmado, contrato, conta?.leverage],
  );

  const volumeNum = Number(volumeArmado);
  const riscoNum = Number(riscoArmado);
  const alvoNum = Number(alvoArmado);
  const precoCasa = ficha?.point ?? null;
  const casa = precoCasa && precoCasa > 0 ? precoCasa : 0.01;
  const arredondar = (p: number) => Math.round(p / casa) * casa;

  /*
    Os NIVEIS derivados do dinheiro.

    O LADO vem do botao do painel, e nao do clique: o grafico mostra um preco, e
    um preco nao diz se o operador esta comprando ou vendendo. Sem o lado, `nivelDoValor`
    nao sabe de que lado botar o stop, e o painel mostraria os dois — que e o que
    `OperacaoAutomatica` faz quando nao sabe o lado, e aqui sabemos.
  */
  const [lado, setLado] = useState<'BUY' | 'SELL'>('BUY');
  const slPreco =
    precoArmado !== null && contratoOk && riscoNum > 0
      ? nivelDoValor(precoArmado, riscoNum, volumeNum, lado, contrato!, 'stop')
      : null;
  const tpPreco =
    precoArmado !== null && contratoOk && alvoNum > 0
      ? nivelDoValor(precoArmado, alvoNum, volumeNum, lado, contrato!, 'alvo')
      : null;

  const linhasOrdem = useMemo(() => {
    if (precoArmado === null) return [];
    return linhasDaOrdem({
      entrada: precoArmado,
      lado,
      volume: Number.isFinite(volumeNum) ? volumeNum : 0,
      contrato: contratoOk ? contrato! : null,
      riscoValor: riscoNum > 0 ? riscoNum : null,
      alvoValor: alvoNum > 0 ? alvoNum : null,
      slPreco,
      tpPreco,
    });
  }, [precoArmado, lado, volumeNum, riscoNum, alvoNum, contratoOk, contrato, slPreco, tpPreco]);

  /*
    POR QUE O PAINEL RECUSA, E CADA MOTIVO TEM UM NOME

    A rota `/api/trade/order` (medida em `backend/mt5_gateway.py`, `_trade_order`)
    exige `symbol`, `side` e `volume` em (0, 0.10]. Sem nenhum destes, o gateway
    responde 403/400 com o motivo DELE — que e generico e nao diz qual faltou.

    Recusar aqui, com o campo nomeado, e a diferenca entre o operador corrigir o
    campo e o operador ficar procurando defeito na corretora (AGENTS.md 5).

    SL E TP NAO RECUSAM MAIS (decisao do dono, 07/10/2026)
    ----------------------------------------------------
    MEDIDO nas capturas de 22:01 e no historico: o painel escrevia "Preencha SL
    e TP para ligar o AUTO" e recusava sem os dois campos, enquanto as colunas
    S/L e T/P do historico saiam VAZIAS nas 10 operacoes. O acoplamento nao
    existia — o painel exigia e o que saia era ordem a mercado sem os dois.

    O risco passou a ser do operador, e da IA quando ela sugere. Os botoes de
    preset (1:1, 1:2, 1:3, 1:4) continuam preenchendo, entao quem quer
    protecao clica uma vez; quem nao quer envia sem.

    Quando o valor NAO e informado, ele nao vai no corpo: nao mandar `sl: 0`,
    porque zero e um numero, e o gateway so pode distinguir "ausente" de
    "invalido" pelo nome do campo, nao pelo valor.
  */
  const semStop = riscoNum <= 0 || !Number.isFinite(riscoNum);
  const semAlvo = alvoNum <= 0 || !Number.isFinite(alvoNum);
  /*
    DE ONDE VIERAM AS VELAS DA TELA (12/10/2026, grafico sempre vivo).
    Declarado AQUI (e nao junto do efeito que preenche, la embaixo) porque
    o `motivoRecusa` logo abaixo ja le `velasPublicas` — e o TypeScript barra
    uso antes da declaracao. Ver o comentario completo junto das velas.
  */
  const [fonteVelas, setFonteVelas] = useState<string | null>(null);
  const [velasPublicas, setVelasPublicas] = useState(false);
  const motivoRecusa = useMemo(() => {
    /*
      PRECO PUBLICO NAO ARMA ORDEM (12/10/2026, grafico sempre vivo). E a
      regra do modulo de fonte publica: preco de terceiro nao vira execucao.
      Sem esta guarda, o preco do ultimo fechamento publico armaria a ordem
      e o operador enviaria sobre um numero que a corretora dele nao tem.
    */
    if (velasPublicas)
      return 'Preço de fonte pública (sem execução): escolha a conta em Configurações → Conexões para operar.';
    if (precoArmado === null) return '';
    if (!simbolo) return 'Sem par configurado no motor. O símbolo vazio é recusa, nunca um ativo padrão.';
    if (!contratoOk)
      return 'A corretora não devolveu o tamanho do contrato deste ativo: dinheiro não vira preço sem ele.';
    if (!Number.isFinite(volumeNum) || volumeNum <= 0) return 'Informe a quantidade.';
    if (volumeNum > 0.1) return `Quantidade ${volumeNum} acima do máximo aceito: 0,10.`;
    return '';
  }, [velasPublicas, precoArmado, simbolo, contratoOk, volumeNum]);

  const enviarOrdem = async () => {
    if (motivoRecusa) {
      setErroEnvio(motivoRecusa);
      return;
    }
    setEnviando(true);
    setErroEnvio('');
    try {
      // SL e TP so entram no corpo quando TEM VALOR. `sl: 0` seria um numero
      // - e nao uma ausencia - e o gateway so distingue os dois pelo nome do
      // campo. Sem o campo, `_trade_order` le 0 e a ordem segue sem protecao.
      const corpo: Record<string, unknown> = {
        symbol: simbolo,
        side: lado,
        volume: volumeNum,
        confirm: true,
        request_id: requestId(),
      };
      if (!semStop && slPreco !== null) corpo.sl = arredondar(slPreco);
      if (!semAlvo && tpPreco !== null) corpo.tp = arredondar(tpPreco);
      const resposta = await fetch(`${apiBase()}/api/trade/order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo),
        signal: AbortSignal.timeout(15000),
      });
      const d = (await resposta.json().catch(() => ({}))) as { ok?: boolean; error?: string };
      const ok = resposta.ok && d.ok !== false;
      notify(
        ok ? 'Ordem enviada' : 'Ordem recusada',
        ok
          ? `${lado} ${volumeNum} em ${simbolo}.`
          : String(d.error ?? `HTTP ${resposta.status}`),
      );
      if (ok) {
        setPrecoArmado(null);
        void positionsQ.refetch();
      } else {
        setErroEnvio(String(d.error ?? `HTTP ${resposta.status}`));
      }
    } catch (e) {
      setErroEnvio(e instanceof Error ? e.message : 'Gateway indisponível.');
      notify('Gateway indisponível', e instanceof Error ? e.message : 'erro');
    } finally {
      setEnviando(false);
    }
  };

  const { sinais, idadeSeg } = useSinaisModelo(simbolo, tempoEscolhido, configurado);
  const [candles, setCandles] = useState<MarketCandle[] | undefined>(undefined);
  const [erroVelas, setErroVelas] = useState('');
  /* `fonteVelas`/`velasPublicas` declarados acima, junto do `motivoRecusa`. */
  /*
    A REFERÊNCIA DOS CANDLE QUE JÁ ESTÃO NA TELA (11/10/2026)
    =========================================================
    O intervalo de 30s precisa saber se AINDA HÁ dado em mãos quando a
    atualização falha — e o `candles` do estado não pode ser lido dentro do
    `catch`: o closure fica com o valor de quando o efeito montou.

    MEDIDO na captura das 12:24, MT5 fechado: o gráfico mostrava 300 candles e,
    na mesma tela, "Gráfico indisponível: candles ausentes ou inválidos no
    upstream". Duas telas da mesma tela discordando — e o AGENTS.md 5 diz o
    que o operador faz: culpa o servidor, que estava com o dado na mão.
  */
  const candlesRef = useRef<MarketCandle[]>([]);

  useEffect(() => {
    if (!configurado) return undefined;
    let vivo = true;
    /*
      MUDOU O PAR OU O PERIODO, ZERA: o que está na tela é do ativo de antes,
      e uma falha daqui não pode dizer "mostrando os últimos candles" apontando
      para o gráfico do ativo errado. O `vivo=false` do efeito anterior já
      impede a resposta antiga de gravar; o zêro impede a REFERÊNCIA de mentir.
    */
    candlesRef.current = [];
    setCandles(undefined);
    setFonteVelas(null);
    setVelasPublicas(false);
    const carregar = async () => {
      try {
        const r = await getCandles({ broker: broker as never, market: market as never, symbol: simbolo }, tempoEscolhido, LIMITE_VELAS_GRAFICO);
        if (vivo) {
          candlesRef.current = r.candles;
          setCandles(r.candles);
          setErroVelas('');
          setFonteVelas(r.fonte ?? null);
          setVelasPublicas(r.fallback_publico === true);
        }
      } catch (e) {
        if (!vivo) return;
        const motivo = e instanceof Error ? e.message : 'Candles indisponíveis.';
        setErroVelas(erroDeVelas(motivo, candlesRef.current.length > 0));
      }
    };
    void carregar();
    const t = window.setInterval(carregar, 30_000);
    return () => {
      vivo = false;
      window.clearInterval(t);
    };
  }, [broker, market, simbolo, tempoEscolhido, configurado]);

  /*
    VELAS LIVRES SEM CORRETORA (12/10/2026, grafico sempre vivo).
    ==============================================================
    Decisao do dono: sem MT5 e sem chave, o grafico continua vivo com valores
    reais de fonte publica. Quando ha corretora, o efeito acima manda (dado
    da conta); sem ela, este pede `/api/publico/ohlc` — que nao recebe broker
    e declara `fonte` + `execucao: False`.

    A CONDICAO E `!configurado`, E NAO `!broker` (12/10/2026, 0 candles).
    =======================================================================
    MEDIDO no app instalado, MT5 fechado: par escolhido, corretora escolhida
    (`mt5`), mas `market === ''` — sem catalogo (o terminal nao lista ativos
    fechado) nao ha ficha, sem ficha nao ha mercado, sem mercado o
    `configurado` e falso. O efeito com conta pulava (sem mercado) E este
    pulava (com broker): par + corretora e ZERO consultas — "0 candles" sem
    erro e sem aviso. Dois guardas que juntos cobriam tudo menos o caso real.

    Agora: configurado manda; sem configuracao e com par, o livre manda. O
    PRECO PUBLICO NUNCA ARMA ORDEM: `precoArmado` continua `null` (ver o
    guarda no efeito do preco e no `motivoRecusa`), entao o painel mostra os
    niveis derivados? NAO — sem preco armado nao ha `slPreco`/`tpPreco`, e o
    envio recusa nomeando a conta. Ver grafico e uma coisa; operar e outra.
  */
  useEffect(() => {
    if (configurado || !simbolo) return undefined;
    let vivo = true;
    // Saiu a configuracao no meio da sessao: o que esta na tela era dela, e
    // dado publico por cima de dado de conta seria o AGENTS.md 5 (mesma regra
    // do zera da troca de par, acima).
    candlesRef.current = [];
    setCandles(undefined);
    setFonteVelas(null);
    setVelasPublicas(false);
    const carregar = async () => {
      try {
        const r = await getCandlesLivres(simbolo, tempoEscolhido, LIMITE_VELAS_GRAFICO);
        if (vivo) {
          candlesRef.current = r.candles;
          setCandles(r.candles);
          setErroVelas('');
          setFonteVelas(r.fonte);
          setVelasPublicas(true);
        }
      } catch (e) {
        if (!vivo) return;
        const motivo = e instanceof Error ? e.message : 'Candles indisponíveis.';
        setErroVelas(erroDeVelas(motivo, candlesRef.current.length > 0));
      }
    };
    void carregar();
    const t = window.setInterval(carregar, 30_000);
    return () => {
      vivo = false;
      window.clearInterval(t);
    };
  }, [broker, market, simbolo, tempoEscolhido, configurado]);

  /*
    TROCOU O PAR, VOLTA AO PERIODO DO MODELO DESTE PAR (09/10/2026)
    ================================================================
    Sem isto, o operador escolhe BTCUSD em M15, troca para EURUSD — e o grafico
    continua em M15, que e o periodo do modelo de BTCUSD. O periodo escolhido na
    barra pertence ao par escolhido na barra.

    E o que o proprio componente ja faz em outro lugar: quando o par ou o
    periodo muda, o "Descartar" da ordem vale para AQUele ativo e nao para o
    seguinte. Aqui e a mesma regra, aplicada ao timeframe.
  */
  useEffect(() => {
    setPeriodoDoGrafico('');
  }, [simbolo]);

  /*
    O PRECO DA ORDEM E O ULTIMO FECHAMENTO (decisao do dono, 08/10/2026)
    =====================================================================
    Antes o preco vinha de `onArmarOrdem`, e o clique no grafico era o caminho
    de 1-clique que o dono mandou remover. MEDIDO em 08/10 19:35, conta real:
    dois cliques criaram tres linhas de ordem a 75670,29 / 75470,29 /
    75270,29 — a um clique do botao `Colocar ordem`. Nenhuma ordem saiu
    (`Orders=0 | Exec=0`), mas a ordem FICAVA MONTADA.

    Entao o preco nasce do dado que a corretora ja mandou: o ultimo fechamento
    do ultimo candle. Nao e escolha do operador — e leitura, e por isso nao
    precisa de clique nenhum. O que o operador ESCOLHE continua sendo o nivel:
    arrastando a ponta do stop ou do alvo, que recalcula o dinheiro em
    `onMoverLinhaOrdem`.

    So preenche uma vez, enquanto `precoArmado` for `null`: um efeito que
    reescrevesse o preco a cada tique transformaria a ordem num preco movel, e
    o painel mostraria um numero que muda sozinho sem ninguem ler.
  */
  useEffect(() => {
    if (precoArmado !== null || descartado) return;
    // Sem preco publico armado (12/10/2026): o motivoRecusa ja barra o envio,
    // mas o preco nem pode NASCER de vela publica — senao o painel mostraria
    // stop/alvo "prontos" sobre um numero que nao executa.
    if (velasPublicas) return;
    const ultimo = candles?.[candles.length - 1];
    if (!ultimo) return;
    const fechamento = Number(ultimo.close);
    if (!Number.isFinite(fechamento) || fechamento <= 0) return;
    setPrecoArmado(arredondar(fechamento));
  }, [candles, precoArmado, descartado, velasPublicas]);

  // Mudou o par ou o periodo: o gesto de Descartar valeu para AQUele ativo.
  useEffect(() => {
    setDescartado(false);
  }, [simbolo, tempoEscolhido]);

  // Cada sinal ancora no candle fechado mais recente ate a hora do sinal.
  const markers = useMemo(() => {
    if (!candles?.length) return [];
    return sinais
      .map((s) => {
        let alvo = 0;
        for (const c of candles) {
          if (c.time <= s.time) alvo = c.time;
          else break;
        }
        if (!alvo) return null;
        return {
          time: alvo,
          signal: s.signal,
          text: `${s.signal} ${s.confidence ?? '--'}%`,
        };
      })
      .filter((m): m is { time: number; signal: string; text: string } => m !== null);
  }, [candles, sinais]);

  /*
    O ESTADO SEM PAR fica la embaixo, colado no `return` principal (11/10/2026).
    ============================================================================
    MEDIDO no app instalado (captura 20:37, Modelos): "Gráfico ao vivo
    indisponível / Minified React error #310". A #310 e "mais hooks que no
    render anterior": este `if (!simbolo) return` estava ANTES do `useMemo`
    das linhas de posicao (e de todo o resto abaixo). Com par sempre
    preenchido o defeito dormia; sem par presumido (decisao do dono: nada de
    BTCUSD fixo) o `simbolo` alterna entre `''` e valor, a contagem de hooks
    muda, e o React derruba a secao inteira no ErrorBoundary.

    Regra: nenhum `return` condicional antes do ultimo hook. O bloco desceu
    para depois de todos eles.
  */

  /*
    A IDADE DA LEITURA FOI PARA O CHIP DE SINAIS (09/10/2026)
    ==========================================================
    MEDIDO: a faixa `symbol · H1 · MT5 · desatualizado ha Xs` do cabecalho do
    PAI saiu — o `PriceChart` ja mostra simbolo, periodo e corretora no
    cabecalho dele, e repetir aqui era o excedente que o dono pediu para tirar
    ("e so tres coisas, entao tire o excedente").

    A IDADE nao foi perdida: ela passou a valer no chip de sinais, que ȩ o dado
    que ela qualifica. "3 sinais no grafico" nao diz ha quanto tempo eles foram
    lidos, e com a cotacao parada o numero envelhece sem aviso. Agora o chip
    fica amarelo e diz a idade. Ver a fita em `useSinaisModelo`.
  */
  const sinaisVelhos = idadeSeg !== null && idadeSeg > 150;

  // Posicoes do par desenhadas no grafico: entrada, SL e TP. SL/TP com
  // ticket arrastam e aplicam ao soltar (estilo MT5).
  const linhas = useMemo(() => {
    const lista: Array<{ price: number; color: string; title: string; ticket?: number | string; kind?: 'sl' | 'tp' | 'entrada' }> = [];
    for (const p of posicoes as Array<Record<string, unknown>>) {
      if (String(p.symbol ?? '').toUpperCase() !== simbolo) continue;
      const abertura = Number(p.open_price ?? p.price_open);
      const sl = Number(p.sl);
      const tp = Number(p.tp);
      const ticket = (p.ticket ?? '') as number | string;
      if (Number.isFinite(abertura)) lista.push({ price: abertura, color: '#4f7cff', title: 'entrada' });
      if (Number.isFinite(sl) && sl > 0)
        lista.push({ price: sl, color: '#ef4444', title: `SL ${ticket}`, ticket, kind: 'sl' });
      if (Number.isFinite(tp) && tp > 0)
        lista.push({ price: tp, color: '#22c55e', title: `TP ${ticket}`, ticket, kind: 'tp' });
    }
    return lista;
  }, [posicoes, simbolo]);

  // Soltou a linha: aplica na hora (MT5 nao pergunta). Erro volta sozinho
  // no proximo refresh das posicoes — a linha mentirosa nao fica.
  const moverLinha = async (ticket: number | string, kind: 'sl' | 'tp', price: number) => {
    try {
      const corpo: Record<string, unknown> =
        kind === 'sl' ? { sl: price } : { tp: price };
      const r = await fetch(`${apiBase()}/api/trade/modify-position`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticket, ...corpo, request_id: requestId(), confirm: true }),
        signal: AbortSignal.timeout(15000),
      });
      const d = (await r.json().catch(() => ({}))) as { ok?: boolean; error?: string };
      notify(
        r.ok && d.ok !== false ? 'Proteção movida' : 'Movimento recusado',
        r.ok && d.ok !== false
          ? `${kind.toUpperCase()} do ticket ${ticket} em ${price}.`
          : String(d.error ?? `HTTP ${r.status}`),
      );
      void positionsQ.refetch();
    } catch (e) {
      notify('Gateway indisponível', e instanceof Error ? e.message : 'erro');
      void positionsQ.refetch();
    }
  };

  /*
    OS BOTOES "1-CLIQUE" SAIRAM (06/10/2026)
    =========================================
    O dono pediu: "remover botao 1 clique deixar apenas selecionar modelos e
    periodos treinados". E o proprio pedido anterior ja dizia: "remover botao 1
    clique" junto com "grafico operacional".

    O QUE ERA O 1-CLIQUE, E POR QUE SUMIU
    =======================================
    Dois botoes que enviavam ordem A MERCADO com LOTE/SL/TP do motor e uma
    confirmacao. O problema nao e o preco — e que o preco nao era escolhido pelo
    operador: ele mandava o que o motor tinha, e o unico lugar onde o preco e o
    SL e o TP sao escolhidos COM VER e sao arrastados no grafico e o proprio
    grafico.

    Entao a ordem pelo mouse SUBSTITUI o 1-clique, em vez de ficar ao lado dele.
    Dois caminhos para a mesma ordem, com nomes diferentes, sao duas chances de o
    operador mandar o que nao queria — e o dono pediu "tudo limpo".

    A funcao `umClique` inteira saiu, com o envio a `/api/trade/order`. A rota
    continua no gateway e passa a ser chamada pelo clique no grafico, com
    `confirm` e `request_id` como sempre (AGENTS.md 4).
  */
  /*
    O ESTADO SEM PAR: A MENSAGEM DIZ ONDE ESCOLHER (06/10/2026, movido para
    ca em 11/10/2026 — ver o comentario acima: `return` condicional antes do
    ultimo hook quebrava o React #310).

    O titulo "Acompanhar modelos" saiu a pedido do dono, e junto com ele a
    frase que mandava configurar o motor. A mensagem aponta para o lugar onde
    o controle ESTA — "Par para operar", no topo da operacao automatica.

    So aparece quando NAO ha par. Com par na barra e motor sem timeframe, o
    grafico entra e mostra o que tem, em vez de um cartao que nao ajuda.
  */
  if (!simbolo) {
    return (
      <section className="card compact-card" aria-label="Gráfico ao vivo">
        <div className="section-head">
          <div>
            <h2>Gráfico ao vivo</h2>
            <span className="muted">
              Escolha o par em &quot;Par para operar&quot;, no topo da operação automática, para
              ver o gráfico.
            </span>
          </div>
        </div>
      </section>
    );
  }
  return (
    <section className="card robo-grafico" aria-label="Gráfico operacional ao vivo">
      {/*
        O CABECALHO DO PAI SAIU (09/10/2026)
        =====================================
        MEDIDO na captura de 20:16 e na tela ao vivo: o painel mostrava DOIS
        cabecalhos empilhados — o daqui (`Gráfico ao vivo` + `BTCUSD · H1 · MT5 ·
        ao vivo`) e o do proprio `PriceChart` (<h2>BTCUSD</h2> + a faixa OHLC com
        o timeframe). O dono resumiu: "e so tres coisas, entao tire o excedente,
        deixa apenas mesmos itens".

        O que ficou: o chip dos sinais, que e a UNICA informacao que o grafico
        nao tem. Simbolo, periodo, corretora e estado da cotacao ja estao todos
        no cabecalho do `PriceChart`, que ȩ quem tem o dado — repetir aqui seria
        duas versoes do mesmo numero na mesma tela, e a regra 5 do AGENTS.md
        sobre dois lados do mesmo dado.

        O `section-head` vazio nao: quando nao ha chip ainda (carregando), o
        espaco do cabecalho tambem nao aparece.
      */}
      {sinais.length > 0 && (
        <div className="section-head robo-grafico-cabeca">
          <span
            className={`chip ${sinaisVelhos ? 'warn' : sinais.length ? 'ok' : 'warn'}`}
            title={
              sinaisVelhos && idadeSeg !== null
                ? `Leitura de ha ${idadeSeg}s — a cotacao pode estar parada`
                : 'Leitura ao vivo'
            }
          >
            {sinais.length} sinais no gráfico
            {sinaisVelhos && idadeSeg !== null ? ` · há ${idadeSeg}s` : ''}
          </span>
        </div>
      )}
      {/*
        SEM CORRETORA, O GRAFICO DIZ ISSO (11/10/2026, decisao do dono: nada de
        MT5 fixo). Sem este aviso o grafico nasceria vazio com "Candles reais
        indisponíveis para esta fonte" — e o operador culparia a fonte por uma
        escolha que ele ainda nao fez. Vazio aqui e "escolha a corretora/conta
        na barra inferior ou em Conexões", nunca um grafico de outra corretora.
      */}
      {!broker && (
        <p className="hint" role="status">
          Sem corretora escolhida. Escolha a conta em Configurações → Conexões
          (botão Ativar da conexão) para ver o gráfico.
        </p>
      )}
      <PriceChart
        symbol={simbolo}
        broker={broker as never}
        market={market as never}
        timeframe={tempoEscolhido as never}
        onTimeframeChange={(periodo) => setPeriodoDoGrafico(String(periodo).toUpperCase())}
        candles={candles}
        markers={markers}
        lines={linhas}
        ema={verEma}
        onIndicadoresChange={(estado) => setVerEma(estado.ema)}
        onMoveLine={(ticket, kind, price) => void moverLinha(ticket, kind, price)}
        modoOrdem
        ordem={linhasOrdem}
        /*
          SEM `onArmarOrdem` — decisao do dono, 08/10/2026.
          O clique no grafico nao arma mais ordem. O preco vem do ULTIMO
          FECHAMENTO, abaixo, e o operador ajusta o nivel arrastando a ponta do
          stop ou do alvo. Ver `PriceChart` no efeito do clique.
        */
        onMoverLinhaOrdem={(papel, preco) => {
          /*
            ARRASTAR A LINHA E RECONFIGURAR O DINHEIRO, e nao mover o preco.

            MEDIDO na XM: o `x` apaga a linha, e arrastar ajusta o nivel. O
            operador que escolheu "aceito perder 2,00" espera ver 2,00 depois de
            arrastar. Mover o preco em silencio e trocar o dinheiro que ele
            escreveu — e o app decidindo o risco por ele.

            O dinheiro e o inverso da conta que ja existe e esta testada em
            `risco.ts`: `distancia * volume * contract_size`. Arredondar para
            baixo deixa o risco digitado como teto, nunca acima.
          */
          if (!contratoOk || !Number.isFinite(volumeNum) || volumeNum <= 0) return;
          const distancia = Math.abs(preco - (precoArmado ?? preco));
          const risco = Math.floor(distancia * volumeNum * contrato! * 100) / 100;
          if (papel === 'sl') setRiscoArmado(risco.toFixed(2));
          else setAlvoArmado(risco.toFixed(2));
        }}
        onRemoverLinha={(papel) => {
          /*
            O `x` APAGAR A LINHA, e nao zerar o dinheiro.

            `sl: 0` no payload seria enviado ao gateway e recusado com um motivo
            generico; apagar o stop e um ato do operador que o painel precisa
            mostrar como ausencia. Por isso o dinheiro vai a zero e o
            `motivoRecusa` assume — com o campo nomeado.
          */
          if (papel === 'sl') setRiscoArmado('0');
          else setAlvoArmado('0');
        }}
        error={erroVelas}
        /*
          O NOME E DE QUEM MANDOU AS VELAS (12/10/2026, grafico sempre vivo).
          Com fallback publico, `fonteVelas` traz a venue real ("binance",
          "yahoo") e o rotulo diz "dados publicos (sem execucao)" — porque
          preco de terceiro nao arma ordem. Sem fallback, o rotulo e o de
          sempre (corretora + sinais do modelo). Sem corretora, `undefined`
          esconde a linha (ver `fonteDoGrafico` no PriceChart).
        */
        sourceLabel={
          velasPublicas && fonteVelas
            ? `${fonteVelas} · dados públicos (sem execução)`
            : broker
              ? `${broker.toUpperCase()} · sinais do modelo`
              : undefined
        }
        /*
          COMPRAR E VENDER PELO MENU DO BOTAO DIREITO (09/10/2026)
          ==========================================================
          MEDIDO na captura da XM (`Screenshot 2026-10-09 201959.png`): o menu
          direito do grafico tem TRADE no topo, com compra e venda. O dono pediu:
          "quando tem direito tem que abrir todas funcoes do menu".

          NAO envia ordem e NAO cria linha. Recebe o lado e o PRECO onde o
          operador clicou, e so escolhe o lado da ordem que o painel abaixo
          mostra. O que manda continua sendo o botao `Colocar ordem`.

          E a mesma regra de 08/10/2026: o clique sozinho nao pode montar uma
          ordem a um clique do envio (MEDIDO entao: dois cliques criaram tres
          linhas montadas na conta real). O menu direito e o mesmo perigo por
          outro caminho, e por isso ele so CHEGA AQUI — na escolha do lado, com
          o preco para a mesa conferir.
        */
        onOperarNoMenu={(escolhido) => setLado(escolhido === 'compra' ? 'BUY' : 'SELL')}
        onEscolherPreco={(papel, precoNoPonto) => {
          /*
            O stop e o alvo nascem no PRECO onde o operador apontou, e nao no
            meio do grafico — que e o que um clique em qualquer pixel daria.

            O valor ȩ DISTANCIA em dinheiro, porque ȩ assim que o painel pense
            e que o dono descreveu: quem aceita perder 2,00 ve 2,00. O calculo
            ȩ o mesmo do arraste (`risco.ts`), pela mesma razao: dois lugares
            com a mesma conta ȉ dois lugares para divergir.
          */
          if (precoNoPonto === null) return;
          const referencia = precoArmado ?? precoNoPonto;
          const distancia = Math.abs(precoNoPonto - referencia);
          const risco = Math.floor(distancia * volumeNum * (contratoOk ? contrato! : 1) * 100) / 100;
          if (papel === 'sl') setRiscoArmado(risco.toFixed(2));
          else setAlvoArmado(risco.toFixed(2));
        }}
      />
      {/*
        O PAINEL DE CONFIRMACAO
        =======================
        MEDIDO na captura da XM: `Quantidade 0.01 lotes` · `Requisito de
        margem $0.85` · `Vender quando preço atingir` · `TP/SL` · `Colocar
        ordem a 85.510.25`.

        O BOTAO E O QUE MANDA, e ele mostra o preco que vai ser enviado. Sem a
        ordem armada nao ha painel: um painel vazio com botao desabilitado
        seria um controle que o operador acredita ter e nao tem.

        O REQUISITO DE MARGEM ENTROU NESTE CICLO, e a correcao do ciclo
        anterior: ele NAO entrava por "o app nao tem de onde ler" — a
        corretora PUBLICA a alavancagem, e o gateway agora traz `leverage` do
        `account_info()`. O numero que sai da conta foi conferido com a conta
        da XM antes de a tela escrever. Ver o bloco do calculo, abaixo.
      */}
      {precoArmado !== null && (
        <div className="robo-ticket robo-ordem-painel" aria-label="Ordem armada">
          <div className="robo-ticket-preco" role="status" aria-live="polite" title="Preço clicado no gráfico">
            {precoArmado}
          </div>

          <div className="robo-ticket-modo" role="group" aria-label="Lado da ordem">
            <button
              type="button"
              className={`btn sm ${lado === 'BUY' ? 'primary' : 'ghost'}`}
              aria-pressed={lado === 'BUY'}
              onClick={() => setLado('BUY')}
            >
              Comprar
            </button>
            <button
              type="button"
              className={`btn sm ${lado === 'SELL' ? 'primary' : 'ghost'}`}
              aria-pressed={lado === 'SELL'}
              onClick={() => setLado('SELL')}
            >
              Vender
            </button>
          </div>

          <label className="field robo-ticket-lote" style={{ marginBottom: 0 }}>
            <span>{unidade ?? 'Lote'}{faixa.assumido ? '*' : ''}</span>
            <input
              type="number"
              step={faixa.passo}
              min={faixa.minimo}
              value={volumeArmado}
              onChange={(e) => setVolumeArmado(e.target.value)}
              aria-label={rotuloQuantidade(unidade, faixa.passo)}
              title={
                faixa.assumido
                  ? 'Faixa assumida: a corretora não devolveu volume_min/volume_max deste ativo'
                  : `min ${faixa.minimo} · passo ${faixa.passo} (da corretora)`
              }
            />
          </label>

          {/*
            O STOP E O ALVO EM DINHEIRO, e o PRECO DERIVADO ao lado.

            O dinheiro e a entrada do operador; o preco e o que a corretora vai
            entender. Mostrar so o preco deixaria o operador calibrando risco
            sem saber quanto esta arriscando.
          */}
          <div className="robo-ticket-protecao">
            <label className="field" style={{ marginBottom: 0 }}>
              <span>Stop loss (−{riscoArmado || '0,00'} USD)</span>
              <input
                type="number"
                min={0}
                step={0.01}
                value={riscoArmado}
                onChange={(e) => setRiscoArmado(e.target.value)}
                aria-label="Quanto aceita perder no stop loss"
                title="Quanto você aceita perder. O preço do stop é derivado."
              />
            </label>
            <label className="field" style={{ marginBottom: 0 }}>
              <span>Alvo (+{alvoArmado || '0,00'} USD)</span>
              <input
                type="number"
                min={0}
                step={0.01}
                value={alvoArmado}
                onChange={(e) => setAlvoArmado(e.target.value)}
                aria-label="Quanto espera ganhar no alvo"
                title="Quanto você espera ganhar. O preço do alvo é derivado."
              />
            </label>
          </div>

          {/*
            O REQUISITO DE MARGEM E O NOCIONAL, lado a lado.

            Sao os dois numeros que o operador precisa antes de confirmar, e o
            nocional e o que oeye le: `$0.85` de margem parece pouco, e
            `$853.77` de dinheiro exposto diz o que a alavancagem faz.

            Quando falta insumo, o texto DIZ O QUE FALTA em vez de mostrar
            `$0,00`. `0,00` de requisito lido como "de graca" e a leitura que
            leva o operador a abrir uma ordem que a corretora recusa.
          */}
          <div className="robo-ticket-requisito" role="status" aria-live="polite">
            {requisito.valor !== null ? (
              <>
                <span>
                  Requisito de margem <b>{requisito.valor.toFixed(2)} USD</b>
                </span>
                <span className="muted">
                  nocional {requisito.nocional!.toLocaleString('pt-BR', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}{' '}
                  USD{conta?.leverage ? ` · alavancagem ${conta.leverage}:1` : ''}
                </span>
              </>
            ) : (
              <span className="muted">
                Requisito de margem indisponível — {requisito.motivo}.
              </span>
            )}
          </div>

          <div className="robo-ticket-niveis" role="status" aria-live="polite">
            {slPreco !== null && (
              <span className="mono">
                Stop em <b>{arredondar(slPreco).toPrecision(8)}</b>
              </span>
            )}
            {tpPreco !== null && (
              <span className="mono">
                Alvo em <b>{arredondar(tpPreco).toPrecision(8)}</b>
              </span>
            )}
            {slPreco === null && riscoNum <= 0 && (
              <span className="muted">Stop apagado. Clique numa linha e arraste, ou escreva o valor.</span>
            )}
          </div>

          {/*
            ORDEM SEM PROTECAO, DITA ANTES DE ENVIAR.

            A obrigatoriedade saiu (decisao do dono, 07/10/2026). O que fica e a
            VISIBILIDADE: quem manda sem stop e sem alvo ve isso escrito, porque
            a ordem segue viva na conta sem limite de perda. O risco e do
            operador — e da IA quando ela sugere — mas o operador precisa saber
            em que situacao esta clicando.
          */}
          {(semStop || semAlvo) && !motivoRecusa && (
            <p className="hint" role="alert">
              Esta ordem vai{' '}
              <b>sem {semStop ? 'stop' : ''}{semStop && semAlvo ? ' e sem ' : ''}{semAlvo ? 'alvo' : ''}</b>
              . Ela fica aberta na conta sem limite de perda definido pelo app — o
              risco é seu, e o da IA quando ela sugere. Clique num preset de risco
              ou arraste a linha se quiser proteção.
            </p>
          )}

          {/* Botao explicito para quem QUER enviar sem, e nao por engano.

              Classe propria, e NAO `.robo-ticket-presets`: aquela area do grid
              (`grid-area: presets`) ja e dos botoes 1:1 a 1:4 em
              `OperacaoAutomatica.tsx`, e dois elementos na mesma area do grid se
              sobrepoem em vez de ficarem lado a lado. */}
          <div className="robo-ticket-sem-protecao" role="group" aria-label="Proteção da ordem">
            <button
              type="button"
              className="btn ghost"
              aria-pressed={semStop && semAlvo}
              onClick={() => {
                setRiscoArmado('0');
                setAlvoArmado('0');
              }}
              title="Deixa a ordem sem stop e sem alvo, de propósito"
            >
              {semStop && semAlvo ? 'Sem SL/TP ✓' : 'Enviar sem SL/TP'}
            </button>
          </div>

          {motivoRecusa && (
            <p className="hint" role="alert">
              {motivoRecusa}
            </p>
          )}
          {erroEnvio && (
            <p className="hint" role="alert">
              {erroEnvio}
            </p>
          )}

          <button
            type="button"
            className="btn primary"
            onClick={() => void enviarOrdem()}
            disabled={Boolean(motivoRecusa) || enviando}
            title={
              motivoRecusa
                ? motivoRecusa
                : `Envia ${lado} ${volumeArmado} em ${simbolo} com confirm e request_id`
            }
          >
            {enviando ? 'Enviando…' : rotuloDoBotao(precoArmado)}
          </button>

          <button
            type="button"
            className="btn ghost"
            onClick={() => {
              setDescartado(true);
              setPrecoArmado(null);
              setErroEnvio('');
            }}
          >
            Descartar
          </button>
        </div>
      )}
      {/*
        A BARRA DE OPERAR SAIU INTEIRA (06/10/2026)
        ============================================
        Os botoes "Comprar 1-clique" e "Vender 1-clique" saíram a pedido do dono:
        "remover botao 1 clique deixar apenas selecionar modelos e periodos
        treinados".

        O caminho que os substitui e o PROPRIO GRAFICO: clicar nele arma a ordem
        no preco clicado, com stop e alvo em dinheiro arrastaveis, e a confirmacao
        mostra tudo antes de enviar. Ver `PriceChart` (`modoOrdem`).

        E o checkbox "EMA 12/26" que estava aqui tambem saiu: o botao `EMA` do
        topo do grafico e o que manda agora, por `onIndicadoresChange`. Eram dois
        controles para um dado, e o de cima era decorativo — o defeito que o dono
        reportou como "botao EMA travado de cima azul".
      */}
      {/*
        A TABELA DE SINAIS FOI REMOVIDA.
        ======================================
        O dono: "nada de prever tabela de previsao — isso nao ajuda em nada, o
        que importa e operar, ordens ao vivo, grafico operacional".

        Os sinais NAO sumiram: eles continuam desenhados como MARCADORES no
        candle (BUY verde abaixo do preco, SELL vermelho acima), que e onde o
        operador olha o preco de qualquer forma. A tabela repetia os mesmos
        numeros em texto — hora, sinal, confianca, preco, modelo — num bloco que
        ocupava a tela abaixo dos botoes de operar.

        Um dado mostrado em dois lugares faz o operador desconfiar dos dois.
        Agora o sinal existe em um lugar so, e a tela inteira e para operar.
      */}
    </section>
  );
}
