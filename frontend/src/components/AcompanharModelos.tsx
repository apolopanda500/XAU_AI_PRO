import { useMemo } from 'react';
import { apiBase } from '../lib/api';
import { useAutoState, usePositions } from '../hooks/queries';
import { useAppStore } from '../hooks/useAppStore';
import { useSinaisModelo } from '../hooks/useSinaisModelo';
import { getCandles, type MarketCandle } from '../lib/marketApi';
import { notify } from '../lib/notify';
import { requestId } from '../lib/format';
import { useEffect, useState } from 'react';
import PriceChart from './charts/PriceChart';
import { nivelDoValor, linhasDaOrdem, rotuloDoBotao } from '../lib/ordemGrafico';
import { fichaDoAtivo, faixaDoAtivo, mercadoDoAtivo, requisitoDeMargem, unidadeDeVolume, rotuloQuantidade } from '../lib/volumeUnidade';
import { useCatalogoAtivos } from '../hooks/useCatalogoAtivos';
import { useAccount } from '../hooks/queries';
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
  const simbolo = String(auto?.simbolo || parDaTela || '').toUpperCase();
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
  const tempoEscolhido = String(timeframe || auto?.timeframe || (TIMEFRAMES[0] as string)).toUpperCase();
  const broker = String(auto?.broker ?? brokerSalvo ?? 'mt5').toLowerCase();

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
  const posicoes = Array.isArray(positionsQ.data?.positions) ? positionsQ.data.positions : [];
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
    (broker || 'mt5') as Parameters<typeof useCatalogoAtivos>[0],
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

    `escopoAtivo()` devolve `mt5:forex` quando a chave nao esta gravada — um
    DEFAULT, nao uma medida. Usar esse valor como mercado de consulta faz o
    gateway responder vazio para um par de cripto, e o sintoma vira "a corretora
    nao devolve candles". E `OperacaoAutomatica` usa `marketSalvo` como ultimo
    recurso porque ele TEM a ficha antes: ali o fallback so roda com ficha
    carregada, e sem ficha o `configurado` dele ja e falso por outro caminho.

    Aqui o `configurado` NAO pode aceitar `forex` como resposta: sem classe
    publicada nao ha mercado medido, e o painel avisa em vez de consultar.
  */
  const market = String(mercadoDaFicha ?? auto?.market ?? '').toLowerCase();
  const configurado = Boolean(broker && market && simbolo);

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
  const contaQ = useAccount();
  const conta = (contaQ.data ?? null) as { leverage?: number | null } | null;

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
  const motivoRecusa = useMemo(() => {
    if (precoArmado === null) return '';
    if (!simbolo) return 'Sem par configurado no motor. O símbolo vazio é recusa, nunca um ativo padrão.';
    if (!contratoOk)
      return 'A corretora não devolveu o tamanho do contrato deste ativo: dinheiro não vira preço sem ele.';
    if (!Number.isFinite(volumeNum) || volumeNum <= 0) return 'Informe a quantidade.';
    if (volumeNum > 0.1) return `Quantidade ${volumeNum} acima do máximo aceito: 0,10.`;
    return '';
  }, [precoArmado, simbolo, contratoOk, volumeNum]);

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

  useEffect(() => {
    if (!configurado) return undefined;
    let vivo = true;
    const carregar = async () => {
      try {
        const r = await getCandles({ broker: broker as never, market: market as never, symbol: simbolo }, tempoEscolhido, 300);
        if (vivo) {
          setCandles(r.candles);
          setErroVelas('');
        }
      } catch (e) {
        if (vivo) setErroVelas(e instanceof Error ? e.message : 'Candles indisponíveis.');
      }
    };
    void carregar();
    const t = window.setInterval(carregar, 30_000);
    return () => {
      vivo = false;
      window.clearInterval(t);
    };
  }, [broker, market, simbolo, tempoEscolhido, configurado]);

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
    O ESTADO SEM PAR: A MENSAGEM DIZ ONDE ESCOLHER (06/10/2026)
    ==========================================================
    O titulo "Acompanhar modelos" saiu a pedido do dono, e junto com ele a
    frase que mandava configurar o motor. O nome saia porque o bloco e o
    GRAFICO, e nao um "acompanhamento" de nada.

    A mensagem agora aponta para o lugar onde o controle ESTA — "Par para
    operar", no topo da operacao automatica, logo acima na mesma pagina. A frase
    antiga mandava configurar algo que o operador nao ve na tela, que e o
    "NUNCA va para outra aba" que o painel de cima ja registrava em
    `OperacaoAutomatica.tsx` pelo mesmo motivo.

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

  const desatualizado = idadeSeg !== null && idadeSeg > 150;

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
  return (
    <section className="card robo-grafico" aria-label="Gráfico operacional ao vivo">
      <div className="section-head">
        <div>
          <h2>Gráfico ao vivo</h2>
          <span className="muted">
            {simbolo} · {tempoEscolhido} · {broker.toUpperCase()}
            {desatualizado ? ` · desatualizado há ${idadeSeg}s` : ' · ao vivo'}
          </span>
        </div>
        <span className={`chip ${desatualizado ? 'warn' : 'ok'}`}>
          {sinais.length ? `${sinais.length} sinais no gráfico` : 'aguardando sinal'}
        </span>
      </div>
      <PriceChart
        symbol={simbolo}
        broker={broker as never}
        market={market as never}
        timeframe={tempoEscolhido as never}
        candles={candles}
        markers={markers}
        lines={linhas}
        ema={verEma}
        onIndicadoresChange={(estado) => setVerEma(estado.ema)}
        onMoveLine={(ticket, kind, price) => void moverLinha(ticket, kind, price)}
        modoOrdem
        ordem={linhasOrdem}
        onArmarOrdem={(p) => {
          setErroEnvio('');
          setPrecoArmado(arredondar(p));
        }}
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
        sourceLabel={`${broker.toUpperCase()} · sinais do modelo`}
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
