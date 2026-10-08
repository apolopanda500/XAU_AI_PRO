// OPERAÇÃO AUTOMÁTICA — os comandos do motor (05/10/2026, reconstruída)
//
// O DONO PEDIU
// ============
// "deletar aba e reconstruir sem mesa apenas:
//    CABECALHO EM CIMA, OPERACAO AUTOMATICO COMANDOS,
//    GRAFICO OPERACIONAL AO VIVO EMBAIXO, MINITERMINAL AO VIVO"
//
// O QUE ESTE COMPONENTE É, E O QUE NÃO É
// ======================================
// É o painel que LIGA e DESLIGA o motor: ativo, lote, proteção, presets.
//
// NÃO é um ticket de ordem. Não tem Comprar/Vender, não tem lado BUY/SELL, não
// tem confirmação. Três motivos, todos medidos:
//
// 1. O LADO É DO MODELO. Um toggle de lado aqui prometeria algo que este painel
//    não decide: o operador marcava "vender" e o motor comprava, porque quem
//    decide é o sinal.
//
// 2. ORDEM MANUAL EXISTE NO GRÁFICO, em 1 clique, com o mesmo LOTE/SL/TP. Ter
//    as duas coisas era duplicação: dois caminhos para a mesma ordem, com risco
//    de mandarem lotes diferentes.
//
// 3. A tela ficou desconfigurada quando a `MesaXM` foi removida. Este arquivo
//    não usa mais nenhuma classe `mesa-`: as classes são `robo-` e vivem em
//    `theme/robo.css`, que ESTE arquivo importa. Nada depende de outro
//    componente carregar a folha.
import { useEffect, useMemo, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';
import { useAutoState } from '../hooks/queries';
import { notify } from '../lib/notify';
import { escopoAtivo as contaAtiva } from '../lib/escopoAtivo';
import { unidadeDeVolume, fichaDoAtivo, faixaDoAtivo, rotuloQuantidade, mercadoDoAtivo } from '../lib/volumeUnidade';
import { valorDoNivel, nivelParaValor, contratoUtilizavel, SEM_CONTRATO } from '../lib/risco';
import { useCatalogoAtivos } from '../hooks/useCatalogoAtivos';
import SeletorModelo from './SeletorModelo';
import ListaModelos from './ListaModelos';
import { useInferenciaIA } from '../hooks/useAICommunication';

/**
 * OS LIMITES QUE O MOTOR JA ACEITA E QUE NAO TINHAM BOTÃO.
 *
 * A lista vem do `LimitesAuto` do backend — nome, tipo e regra de validação
 * included. Declarar aqui um campo que o motor não aceita seria o painel
 * mentindo sobre o que ele configurou: o `POST` volta com "valor invalido para
 * X" e o operador não sabe de onde.
 *
 * `zerado` é o texto de campo vazio. Vazio significa **não declarado**: o motor
 * tem limite próprio para cada um (é o `risk_gate` que protege de verdade), e
 * o painel não inventa número que vira regra.
 */
const LIMITES: Array<{
  chave: string;
  rotulo: string;
  ajuda: string;
  passo: number;
  minimo: number;
  zerado: string;
}> = [
  {
    chave: 'confianca_minima',
    rotulo: 'Confiança mínima (%)',
    ajuda: 'Probabilidade real mínima do modelo para abrir operação. O motor aceita 0 a 100.',
    passo: 1,
    minimo: 0,
    zerado: 'não declarada',
  },
  {
    chave: 'edge_minimo',
    rotulo: 'Edge mínimo',
    ajuda: 'Edge do modelo medido no treino. Abaixo disso, o modelo não decide.',
    passo: 0.01,
    minimo: 0,
    zerado: 'não declarado',
  },
  {
    chave: 'banca',
    rotulo: 'Banca',
    ajuda: 'Saldo declarado da conta, usado para calcular o risco por operação.',
    passo: 10,
    minimo: 0,
    zerado: 'não declarada',
  },
  {
    chave: 'risco_por_trade_pct',
    rotulo: 'Risco por operação (%)',
    ajuda: 'Percentual da banca que uma operação pode perder.',
    passo: 0.1,
    minimo: 0,
    zerado: 'não declarado',
  },
  {
    chave: 'max_posicoes',
    rotulo: 'Máximo de posições',
    ajuda: 'Quantas posições podem ficar abertas ao mesmo tempo.',
    passo: 1,
    minimo: 0,
    zerado: 'sem limite próprio',
  },
  {
    chave: 'max_operacoes_dia',
    rotulo: 'Operações por dia',
    ajuda: 'Teto de aberturas por dia. Sem isso, o motor pode repetir o mesmo sinal o dia inteiro.',
    passo: 1,
    minimo: 0,
    zerado: 'sem teto',
  },
  {
    chave: 'perda_diaria_max_pct',
    rotulo: 'Perda diária máxima (%)',
    ajuda: 'Ao atingir esse percentual da banca, o motor para sozinho.',
    passo: 0.5,
    minimo: 0,
    zerado: 'sem teto',
  },
  {
    chave: 'intervalo_minutos',
    rotulo: 'Intervalo entre avaliações (min)',
    ajuda: 'Tempo mínimo entre duas avaliações do mesmo par.',
    passo: 1,
    minimo: 0,
    zerado: 'sem intervalo próprio',
  },
];
// A FOLHA DA PÁGINA. Este import é o que torna o painel operável: sem ele
// nenhuma regra `.robo-*` existe e o ticket aparece desmontado.
import '../theme/robo.css';

/*
  FAixa de volume: REMOVIDA daqui em 05/10/2026.

  Eram `LOTE_MIN = 0.01` e `LOTE_MAX = 10.0`, constantes aplicadas a TODOS os
  ativos. MEDIDO nas capturas da XM: a unidade muda com a classe do ativo
  ("0,01 Lote(s)" em Bolivar/forex, "0,01 Token(s)" em BTCUSD/crypto), e
  `asset_registry.discover_assets` ja devolve `volume_min`, `volume_max` e
  `volume_step` lidos do item da corretora.

  Medir o uso antes de remover: os dois valores eram lidos em 2 lugares, o
  `min`/`max` do input e a validacao antes do gateway. Os dois agora leem
  `faixaVolume`, que vem da ficha do ativo.

  O fallback (0,01 a 10,00, marcado com `assumido: true`) passou a viver em
  `lib/volumeUnidade.ts`, num lugar so, e a tela mostra o asterisco quando ele
  esta em uso — faixa assumida nao pode parecer faixa da corretora.
*/
// Presets SL:TP. O passo sai da escala do preço (0,1%): igual para ouro e
// forex, sem número fixo. O botão PREENCHE, não trava.
const PRESETS: Array<{ nome: string; risco: number; alvo: number }> = [
  { nome: '1:1', risco: 1, alvo: 1 },
  { nome: '1:2', risco: 1, alvo: 2 },
  { nome: '1:3', risco: 1, alvo: 3 },
  { nome: '1:4', risco: 1, alvo: 4 },
];

const num = (v: string) => Number(String(v).replace(',', '.'));

export default function OperacaoAutomatica() {
  const autoQ = useAutoState();
  const wsConnected = useAppStore((s) => s.wsConnected);
  const parEscolhido = useAppStore((s) => s.selectedSymbol);
  const auto = autoQ.data;
  /*
    O PAR: o motor quando ele tem, o escolhido na tela quando não tem.

    MEDIDO (05/10/2026): lia só `auto.simbolo`. O motor começa SEM par — ele só
    recebe um quando alguém configura. Então o painel mostrava "sem par" e o
    botão recusava com "ESCOLHE O PAR EM 'PAR PARA OPERAR'..." mesmo com o
    seletor logo ACIMA mostrando um par escolhido.

    Era uma trava em círculo: o par vinha da tela, a tela exigia o par do motor,
    e o motor só recebia o par passando pela tela. Um botão que não liga porque
    o valor que o operador acabou de escolher não chegou nele.

    Ordem: motor primeiro (quando ele tem par, é o que ele opera), e a escolha
    da tela como reserva. O payload de `ligar` já manda `simbolo`, então o
    motor passa a ter o mesmo par ao ligar.
  */
  const simbolo = String(auto?.simbolo || parEscolhido || '').toUpperCase();
  const timeframe = String(auto?.timeframe ?? '').toUpperCase();

  const [lote, setLote] = useState('0.01');
  const [sl, setSl] = useState('');
  const [tp, setTp] = useState('');

  /*
    SL/TP POR PRECO OU POR DINHEIRO (05/10/2026)
    ============================================
    MEDIDO na captura da XM: o `TP/SL` tem DUAS abas, `Preco` e `Quantidade`.
    Na `Quantidade` o operador escreve `Montante take profit 2.00 USD` e a tela
    mostra `Nivel de preco equivalente: 86,105.85` — o valor e do operador e o
    preco e derivado.

    NO MODO DINHEIRO O NIVEL SEGUE O PRECO E O VALOR NAO: e exatamente o que o
    dono pediu ("configurar tp e sl ao vivo, mantendo o valor predeterminado").
    O nivel e recalculado a cada tick para que o dinheiro continue sendo o que o
    operador escreveu.

    O LADO NAO ESTA DEFINIDO AQUI, e por isso a tela mostra os DOIS niveis.
    MEDIDO: este painel nao sabe compra ou venda — o comentario do proprio botao
    diz "A direcao e do modelo", e o preco que chega e um so
    (`price ?? last ?? bid ?? ask`), sem o lado. Inventar um lado aqui seria
    mostrar o nivel de stop de uma venda no campo de stop de uma compra.
  */
  const [modoProtecao, setModoProtecao] = useState<'preco' | 'quantidade'>('preco');
  const [valorSl, setValorSl] = useState('');
  const [valorTp, setValorTp] = useState('');
  const [preco, setPreco] = useState<number | null>(null);
  const [limites, setLimites] = useState<Record<string, string>>({});
  /*
    INTERRUPTOR DA IA (05/10/2026).

    Começa DESLIGADA de propósito: inferência consome CPU e escreve estado, e
    fazer isso sem o operador pedir é decidir por ele. Ligar é um clique, e o
    botão diz o que a ligação faz — "IA ligada" não é "ordem liberada".
  */
  const [iaLigada, setIaLigada] = useState(false);
  const { ativar: ativarIA } = useInferenciaIA(timeframe, iaLigada);
  const [ocupado, setOcupado] = useState(false);
  const [status, setStatus] = useState('');

  /*
    O ESCOPO VEM DO MOTOR, e nao do `localStorage` (06/10/2026)
    ==========================================================
    MEDIDO no app instalado: par `BTCUSD` escolhido na barra, e a tela com
    `passo --`, `Valor no risco (SL) 0`, SL/TP vazios e `AUTO NAO` recusando
    com "Preencha SL e TP para ligar o AUTO".

    A CAUSA: `escopoAtivo()` le `localStorage` e, sem a chave gravada, devolve
    o default `mt5:forex`. O preco era pedido assim:

        /api/universal/quotes?broker=mt5&market=forex&symbols=BTCUSD

    BTCUSD em FOREX nao existe. A resposta vinha vazia, `preco` ficava `null`,
    `passo` ficava 0, o preset 1:1 nao tinha como calcular distancia — e sem
    SL/TP o botao AUTO recusava. O operador via "preencha SL e TP" num painel
    que nao tinha como saber o preco, e a culpa caia nele.

    E o AGENTS.md 5 pelo lado do PRODUTOR: o grafico (`AcompanharModelos` ->
    `PriceChart`) usava `auto.market`, que esta CORRETO, e por isso os candles
    apareciam normalmente na mesma tela. Dois componentes, o mesmo dado, uma
    versao lendo o motor e outra lendo o navegador — e so a que lia errado
    aparecia quebrada.

    POR QUE ISTO AINDA NAO BASTA (medido no app instalado, 19:56)
    ===========================================================
    Preferir `auto.market`irks o defeito para dentro: o motor tinha `forex`
    gravado, e um valor gravado e lido de volta. A tela ficava fiel a um valor
    errado — fiel e errada.

    A resposta nao e escolher melhor entre dois valores guardados: e DERIVAR o
    mercado do ATIVO, pela classe que a CORRETORA publica na ficha. `crypto`
    e cripto spot; `metal`, `metals`; `forex`, forex. E a mesma hierarquia do
    `mercado_do_ativo` do motor, pelos dois lados falando a mesma lingua.

    E o AGENTS.md 3: nada aqui e adivinhado pelo nome do simbolo. `ETHUSD`
    entrou como cripto pela ficha, e nao porque tem as letras de cripto.

    SEM FICHA, FICA O QUE VEIO. Nao ha conversao possivel e inventar
    mercado seria a presuncao que a regra proibe.
  */
  const { broker: brokerSalvo, market: marketSalvo } = contaAtiva();
  const broker = String(auto?.broker || brokerSalvo || 'mt5').toLowerCase();

  /*
    O CATALOGO ANTES DO MERCADO, E POR QUE ISSO NAO E CIRCULAR
    ==========================================================
    `useCatalogoAtivos` precisa de um `market` para montar a URL, e o mercado
    que interessa e o do ATIVO — que so se descobre depois do catalogo.

    Nao e circular porque o MT5 responde o catalogo INTEIRO: `discover_assets`
    le o terminal, e nao um mercado pedido. O parametro da URL e o escopo
    guardado, e o que o motor devolve e a ficha real de cada simbolo. Aplica-se
    a mesma logica do motor (`mercado_do_ativo`, em `backend/auto_engine.py`):
    a consulta vem pelo escopo guardado, e a CLASS decide o mercado usado na
    cotacao.
  */
  const catalogo = useCatalogoAtivos(
    broker as Parameters<typeof useCatalogoAtivos>[0],
    String(auto?.market || marketSalvo || '').toLowerCase(),
  );
  const ficha = fichaDoAtivo(catalogo, simbolo);
  const unidade = unidadeDeVolume(ficha?.assetClass);
  const faixaVolume = faixaDoAtivo(ficha);
  /*
    O MERCADO DA COTACAO, derivado da classe que a corretora publicou.
    `null` sem ficha: nao ha conversao possivel, e o que veio antes e melhor do
    que um palpite.
  */
  const mercadoDaFicha = mercadoDoAtivo(ficha?.assetClass);
  const market = String(
    mercadoDaFicha ?? auto?.market ?? marketSalvo ?? '',
  ).toLowerCase();

  /*
    A UNIDADE E A FAIXA DO ATIVO (05/10/2026)
    ==========================================
    MEDIDO nas capturas da XM: Bolivar (forex) escreve "0,01 Lote(s)" e BTCUSD
    (crypto) escreve "0,01 Token(s)". A tela mantinha "Lote" e a faixa 0,01-10,00
    para TODO ativo - o que e presumir classe, e rejeitar/aceitar ordens validas
    conforme o par.

    `unidade`, `faixaVolume` e `ficha` sao calculados ACIMA, junto do catalogo:
    o mercado da cotacao depende da ficha, e a ficha depende do catalogo. Ver a
    nota do ciclo quebrado logo acima.
  */

  /*
    O VALOR DO SL EM DINHEIRO.
  */
  const entrada = preco ?? null;
  const volumeAtual = num(lote);
  /*
    `sl` E PRECO (06/10/2026), e nao distancia. Ver o bloco de `ligar()`.

    Antes era `entrada - num(sl)`, que so fazia sentido com distancia. Com o
    campo em preco, `num(sl)` ja e o nivel — e subtrair de novo daria um valor
    sem significado nenhum, que apareceria em `Valor no risco (SL)`.

    E `Valor no risco` e dinheiro REAL, calculado com `contract_size` da ficha
    (`lib/risco.ts`). O defeito medido antes: a tela afirmava 7.255,62 USD num
    risco de 0,08 USD, multiplicando pelo preco em vez da distancia.
  */
  const nivelSl = entrada === null ? null : num(sl) > 0 ? num(sl) : null;
  const valorRiscoBruto =
    entrada === null || nivelSl === null
      ? null
      : valorDoNivel(entrada, nivelSl, volumeAtual, ficha);
  const valorRisco =
    valorRiscoBruto === null ? null : Number(valorRiscoBruto.toPrecision(4));

  /*
    OS DOIS NIVEIS EQUIVALENTES, no modo dinheiro.

    `acima` e o alvo de uma VENDA e o stop de uma COMPRA; `abaixo` e o stop de
    uma VENDA e o alvo de uma COMPRA. Mostrar os dois e o que nao presume o
    lado que o painel nao tem.
  */
  const entradaOuNula = preco ?? null;
  const volumeOuNula = num(lote) > 0 ? num(lote) : null;
  const slValorN = valorSl.trim() === '' ? null : num(valorSl);
  const tpValorN = valorTp.trim() === '' ? null : num(valorTp);
  const slAcima =
    entradaOuNula === null || volumeOuNula === null || slValorN === null
      ? null
      : nivelParaValor(entradaOuNula, slValorN, volumeOuNula, 'venda', ficha);
  const slAbaixo =
    entradaOuNula === null || volumeOuNula === null || slValorN === null
      ? null
      : nivelParaValor(entradaOuNula, slValorN, volumeOuNula, 'compra', ficha);
  const tpAcima =
    entradaOuNula === null || volumeOuNula === null || tpValorN === null
      ? null
      : nivelParaValor(entradaOuNula, tpValorN, volumeOuNula, 'venda', ficha);
  const tpAbaixo =
    entradaOuNula === null || volumeOuNula === null || tpValorN === null
      ? null
      : nivelParaValor(entradaOuNula, tpValorN, volumeOuNula, 'compra', ficha);
  const autoAtivo = Boolean(auto?.ativo);

  // Preço ao vivo do ativo do motor. Sem side, o preço de referência é o
  // último: serve para calcular a distância dos presets e para o operador ver o
  // número antes de ligar.
  useEffect(() => {
    if (!simbolo) return undefined;
    let vivo = true;
    const ler = async () => {
      try {
        const r = await fetch(
          `${apiBase()}/api/universal/quotes?broker=${broker}&market=${market}&symbols=${encodeURIComponent(simbolo)}`,
          { signal: AbortSignal.timeout(10000) },
        );
        const d = (await r.json()) as {
          quotes?: Array<{ price?: number; last?: number; bid?: number; ask?: number }>;
        };
        const q = d.quotes?.[0];
        const p = q?.price ?? q?.last ?? q?.bid ?? q?.ask ?? null;
        if (vivo && typeof p === 'number') setPreco(p);
      } catch {
        /* mantém o último preço; o motor revalida no gateway */
      }
    };
    void ler();
    const t = window.setInterval(ler, 5_000);
    return () => {
      vivo = false;
      window.clearInterval(t);
    };
  }, [broker, market, simbolo]);

  // PASSO DO ATIVO, em preço. 0,1% arredondado na escala que o ativo usa.
  const passo = useMemo(() => {
    const p = preco ?? 0;
    if (!(p > 0)) return 0;
    const bruto = p * 0.001;
    const escala = bruto >= 100 ? 1 : bruto >= 10 ? 0.1 : bruto >= 1 ? 0.01 : 0.0001;
    return Math.max(escala, Math.round(bruto / escala) * escala);
  }, [preco]);

  const aplicarPreset = (p: { nome: string; risco: number; alvo: number }) => {
    if (!(passo > 0) || entrada === null) {
      setStatus('Aguardando o preço ao vivo para calcular o nível.');
      return;
    }
    const slPreco = Number((entrada - passo * p.risco).toPrecision(6));
    const tpPreco = Number((entrada + passo * p.alvo).toPrecision(6));
    setSl(String(slPreco));
    setTp(String(tpPreco));
    setStatus(`1:${p.alvo / p.risco} · SL ${slPreco} · TP ${tpPreco} sobre o preço ${entrada}.`);
  };

  /*
    O PADRAO 1:1 NASCE SOZINHO, ASSIM QUE O PRECO CHEGA (06/10/2026)
    ================================================================
    O DONO PEDIU: "IA tem que ajudar a configurar em tempo real, preço do
    mercado ao vivo e com padrao 1:1 TP SL".

    MEDIDO: o painel nascia com SL e TP VAZIOS, e `ligar()` recusava com
    "Preencha SL e TP para ligar o AUTO". O operador tinha de: escolher um par,
    esperar a cotacao, clicar num preset e so entao ligar. No caminho a tela
    afirmava "AUTO NAO" sem dizer o que faltava.

    PREENCHE SO QUANDO ESTAO VAZIOS. Um preset que reescreve o que o operador ja
    digitou e o app decidindo o risco pelo dono. Este efeito so age em campo
    vazio, e o valor preenchido fica VISIVEL no input: o operador ve 85564,55 e
    pode trocar por qualquer outro numero.

    POR QUE 1:1 E O PADRAO
    =====================
    MEDIDO nas capturas da XM: a primeira tinha `−2,00 USD` no stop e `+2,00
    USD` no alvo — simetrico. A assimetria 1:2, 1:3 e 1:4 fica nos botoes
    PRESETS, que existem para quem quer.

    NAO PREENCHE SEM PRECO. Sem preco ao vivo nao existe nivel, e um SL
    inventado e o "numero inventado no painel vira limite real" que o AGENTS.md
    proibe — e pior: SL errado manda ordem errada.
  */
  useEffect(() => {
    if (!(passo > 0) || entrada === null) return;
    if (sl.trim() !== '' || tp.trim() !== '') return;
    const slPreco = Number((entrada - passo).toPrecision(6));
    const tpPreco = Number((entrada + passo).toPrecision(6));
    setSl(String(slPreco));
    setTp(String(tpPreco));
    setStatus(`1:1 padrão · SL ${slPreco} · TP ${tpPreco} sobre o preço ${entrada}.`);
  }, [passo, entrada, sl, tp]);

  const parar = async () => {
    if (ocupado) return;
    setOcupado(true);
    try {
      const r = await fetch(`${apiBase()}/api/auto/stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
        signal: AbortSignal.timeout(10000),
      });
      const d = (await r.json().catch(() => ({}))) as { ok?: boolean; error?: string };
      const ok = r.ok && d.ok !== false;
      setStatus(ok ? 'Motor parado.' : String(d.error ?? `HTTP ${r.status}`));
      notify(ok ? 'Motor parado' : 'Não parou', ok ? 'Automático desligado.' : String(d.error ?? ''));
    } catch (e) {
      setStatus(`Gateway indisponível: ${e instanceof Error ? e.message : 'erro'}`);
    } finally {
      setOcupado(false);
    }
  };

  /*
    Os limites declarados, SÓ os declarados.

    Campo vazio não vai no payload. Enviar `''` faria o backend rodar
    `type(valor)('')` — e `float('')` levanta `ValueError`, que o
    `configurar()` transforma em "valor invalido para confianca_minima". O
    operador preencheria três campos e receberia erro no quarto, que ele não
    preencheu.

    Então: vazio = ausente do payload = "não declarado", que é o que o texto do
    campo promete.
  */
  const limitesNumericos = (): Record<string, number> => {
    const saida: Record<string, number> = {};
    for (const item of LIMITES) {
      const bruto = (limites[item.chave] ?? '').trim();
      if (!bruto) continue;
      const n = Number(bruto);
      if (Number.isFinite(n)) saida[item.chave] = n;
    }
    return saida;
  };

  const ligar = async () => {
    if (ocupado) return;
    if (!simbolo) {
      // NUNCA "vá para outra aba".
      //
      // MEDIDO (05/10/2026): a mensagem mandava escolher o ativo na aba
      // Inteligência Artificial, e o bloco que fazia essa escolha tinha sido
      // removido a pedido do dono. O operador recebia uma instrução impossível
      // de seguir e o Robô virava beco sem saída.
      //
      // A escolha do par está AQUI, no topo desta mesma seção ("Par para
      // operar", alimentado pelo catálogo da corretora). A mensagem aponta para
      // o lugar certo porque é o lugar onde o controle está.
      setStatus('Escolha o par em "Par para operar", logo acima, antes de ligar o AUTO.');
      return;
    }
    const loteN = num(lote);
    const slN = num(sl);
    const tpN = num(tp);
    const slValorN = valorSl.trim() === '' ? 0 : num(valorSl);
    const tpValorN = valorTp.trim() === '' ? 0 : num(valorTp);
    /*
      A FAIXA VALIDA E A DO ATIVO, e a mesma do `min`/`max` do input.

      MEDIDO (05/10/2026): antes estas duas coisas podiam divergir, e a forma
      pior dessa divergencia e a tela ACEITAR e o gateway RECUSAR. Agora as duas
      leem `faixaVolume`, que veio da ficha que a corretora devolveu.
    */
    if (!(loteN >= faixaVolume.minimo) || !(loteN <= faixaVolume.maximo)) {
      setStatus(
        `Volume entre ${faixaVolume.minimo} e ${faixaVolume.maximo} para ${simbolo || 'este ativo'}.`,
      );
      return;
    }
    /*
      A VALIDAÇÃO SEGUE O MODO, E O QUE MANDA É O LADO QUE LÊ (05/10/2026)
      =======================================================================
      MEDIDO: `ligar()` mandava `sl_preco`/`tp_preco` sempre. Em modo
      `quantidade` o operador escreve o VALOR em dinheiro, e esse valor chegava
      a lugar nenhum — o painel aceitava, a tela mostrava os dois niveis
      derivados, e o motor recebia precos vazios.

      O que decide e o motor: `MotorAuto.modo_preco_do_lote` devolve verdadeiro
      quando `sl_preco` E `tp_preco` estao preenchidos, e nesse caso o PRECO
      tem prioridade — derivar de dinheiro ignoraria o nivel que o operador
      escolheu. Entao em modo dinheiro a tela nao pode mandar preco nenhum: se
      mandasse, o motor usaria o preco e o valor em dinheiro seria decorativo.

      E o motivo de recusar AQUI, e nao deixar o gateway recusar: a recusa
      chega com o nome do campo certo, que e o que o operador ve.
    */
    /*
      `sl` E `tp` SAO PRECOS, E NAO DISTANCIAS (06/10/2026)
      ====================================================
      MEDIDO: o campo aceitava os DOIS sentidos ao mesmo tempo. O placeholder
      dizia "preço ou distância", o operador digitava um preço (o teste medido
      digita `4130` em ouro a `4140,6`), e o `aplicarPreset` preenchia uma
      DISTANCIA (`passo * risco`, uns 4,14). O mesmo campo com dois sentidos e
      o AGENTS.md 5: o produtor e o consumidor discordam do significado, e o
      sintoma cai em quem le — aqui, o motor receberia `sl_preco: 4,14` num
      ativo que custa 4.140, e o `order_check` recusaria por stop invalido.

      Agora o campo e PRECO, e o preset faz a conta:

          SL = entrada − passo x risco
          TP = entrada + passo x alvo

      Preco e o certo porque e o que o motor le (`auto_engine.py:152`,
      `"sl_preco": "stop loss (preco)"`, usado direto na linha 757), e e o que
      o operador compara com o grafico. No modo `Quantidade` o preco ja era
      derivado do dinheiro, entao os dois modos falam a mesma lingua.

      A conversao distancia -> preco saiu de `ligar()`: com o campo em preco,
      ela viraria uma subtracao que o motor receberia duas vezes.
    */
    const modoDinheiro = modoProtecao === 'quantidade';
    // SL E TP NAO SAO MAIS OBRIGATORIOS PARA LIGAR O MOTOR (decisao do dono,
    // 07/10/2026). MEDIDO na captura de 22:01: o painel recusava com "Preencha
    // SL e TP para ligar o AUTO", e as colunas S/L e T/P do historico saiam
    // VAZIAS nas operacoes que ele mesmo produzia. O acoplamento nao existia.
    //
    // O risco passa a ser do operador e da IA. QUEM QUER protecao clica um
    // preset (1:1 a 1:4) ou escreve o valor; quem nao quer liga sem.
    //
    // Sem sl/tp o motor NAO recebe os campos: `limitesNumericos()` ja devolve
    // `sl_preco`/`tp_valor` como 0 quando o operador nao escreve nada, e o
    // corpo abaixo so os inclui com valor > 0 — mandar zero seria pedir uma
    // protecao de preco zero, que o motor leria como nivel invalido.
    setOcupado(true);
    try {
      /*
        O CORPO SEGUE O MODO.

        `sl_valor`/`tp_valor` sao os nomes que `MotorAuto.configurar` LE, porque
        `configurar` grava o que veio em `asdict(self.limites)` e `Limites`
        declara exatamente esses campos. Mandar `valor_sl` seria recusa com
        "defina lote, stop loss e take profit" — sintoma de nome, defeito do
        cliente (AGENTS.md 5).

        Em modo dinheiro NAO mandamos `sl_preco`/`tp_preco`: se viessem
        preenchidos, `modo_preco_do_lote` devolveria verdadeiro e o motor
        usaria o preco — e o valor em dinheiro que o operador escreveu seria
        ignorado em silencio.
      */
      const corpo: Record<string, unknown> = {
        lote: loteN,
        simbolo,
        timeframe,
        broker,
        market,
        ...limitesNumericos(),
      };
      if (modoDinheiro) {
        if (slValorN > 0) corpo.sl_valor = slValorN;
        if (tpValorN > 0) corpo.tp_valor = tpValorN;
      } else {
        if (slN > 0) corpo.sl_preco = slN;
        if (tpN > 0) corpo.tp_preco = tpN;
      }
      const cfg = await fetch(`${apiBase()}/api/auto/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo),
        signal: AbortSignal.timeout(10000),
      });
      const dCfg = (await cfg.json().catch(() => ({}))) as { ok?: boolean; error?: string };
      if (!cfg.ok || dCfg.ok === false) {
        setStatus(String(dCfg.error ?? `HTTP ${cfg.status}`));
        notify('Configuração recusada', String(dCfg.error ?? ''));
        return;
      }
      const ini = await fetch(`${apiBase()}/api/auto/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
        signal: AbortSignal.timeout(10000),
      });
      const dIni = (await ini.json().catch(() => ({}))) as { ok?: boolean; error?: string };
      const ok = ini.ok && dIni.ok !== false;
      setStatus(ok ? 'Motor ligado.' : `Configurado, mas não ligou: ${dIni.error ?? ''}`);
      notify(
        ok ? 'Motor ligado' : 'Não ligou',
        ok ? `Operando ${simbolo}.` : String(dIni.error ?? ''),
      );
    } catch (e) {
      setStatus(`Gateway indisponível: ${e instanceof Error ? e.message : 'erro'}`);
    } finally {
      setOcupado(false);
    }
  };

  /*
    SEM CONEXAO, NAO MANDA ORDEM (05/10/2026)
    =======================================
    MEDIDO na captura da XM, 21:27: apareceu "Ligacao perdida, estamos a tentar
    reconectar" e o painel inteiro ficou CINZA — `0,01 Lote(s)`, os montantes,
    o toggle e o botao `Colocar ordem` desabilitados. O grafico continuava
    desenhando, e a XM **recusa** a ordem.

    MEDIDO aqui: o botao AUTO so desabilitava com `ocupado` (requisicao em
    voo). Com o websocket caido ele continuava clicavel, e o operador podia
    ligar o motor sem linha.

    A guarda esta em DOIS lugares de proposito. `disabled` no botao e o que o
    operador ve; a recusa dentro de `alternar` e o que impede a chamada mesmo que
    o botao seja acionado por teclado, por teste ou por codigo. Botao
    desabilitado sozinho nao e garantia de que a ordem nao sai.
  */
  const semConexao = !wsConnected;

  const alternar = () => {
    if (semConexao) {
      setStatus('Sem conexao com o gateway: a ordem nao foi enviada.');
      notify('Ligacao perdida', 'Reconectando. Nenhuma ordem foi enviada.');
      return;
    }
    void (autoAtivo ? parar() : ligar());
  };

  return (
    <section className="card robo-comandos" aria-label="Operação automática">
      <div className="section-head">
        <div>
          <h2>Operação automática</h2>
          <span className="muted">
            {simbolo ? `${simbolo} ${timeframe}`.trim() : 'Sem par escolhido'} · {broker.toUpperCase()}
          </span>
        </div>
        <div className="btn-row">
          {/*
            O AUTO SUBIU PARA O TOPO (06/10/2026)
            ========================================
            MEDIDO na captura do app instalado: o botao vivia no RODAPE do
            ticket, embaixo de `passo`, dos quatro presets e dos campos de SL e
            TP. Ligar e desligar o motor e a acao principal da pagina, e ela
            ficava a ultima coisa antes de rolar a tela.

            Ele fica aqui, ao lado do titulo `Operação automatica` e dos
            indicadores de estado (`Tempo real`, `Ligado`/`Parado`), que e onde
            o operador olha primeiro para saber se o motor esta rodando.

            O BOTAO CONTINUA MOSTRANDO O ESTADO, nao o lado. A direcao e do
            modelo: um botao que dissesse "comprar" prometeria algo que este
            painel nao decide.

            `role="switch"` com `aria-checked` e o que um leitor de tela anuncia
            como liga/desliga. O texto `AUTO SIM`/`AUTO NAO` e o reinforcement
            visual para quem nao usa leitor de tela.
          */}
          <button
            type="button"
            role="switch"
            aria-checked={autoAtivo}
            aria-label="Operação automática"
            className={`robo-ticket-enviar robo-auto-topo ${autoAtivo ? 'is-on' : 'is-off'}`}
            onClick={alternar}
            disabled={ocupado || semConexao}
            aria-disabled={ocupado || semConexao}
            title={
              semConexao
                ? 'Ligacao perdida com o gateway: a ordem nao e enviada. A XM tambem recusa neste estado.'
                : autoAtivo
                  ? 'Desligar o motor'
                  : 'Aplicar LOTE/SL/TP e ligar o motor'
            }
          >
            {ocupado
              ? 'Aplicando.'
              : semConexao
                ? 'SEM CONEXAO'
                : `AUTO ${autoAtivo ? 'SIM' : 'NÃO'}`}
          </button>

          {/*
            O INTERRUPTOR DA IA (05/10/2026).

            O dono pediu: "ativar IA nos comandos também e na aba ao todo".

            MEDIDO: a IA estava implementada e desligada por ausência de botão.
            `useInferenciaIA(timeframe, enabled)` recebia `enabled` e **não o
            usava** — inferia sempre; e como ninguém chamava o hook, o
            cabeçalho ficava em "AI: Inativo", o valor inicial do store, com o
            EA inteiro (`AIConnector`, `AIEngine`, `ModelGovernance`) ligado do
            outro lado.

            Aqui o interruptor manda no `enabled` de verdade. E é **inferência**,
            não ordem: ligar a IA faz o modelo dizer o que acha, e continua
            exigindo `confirm` e `request_id` para qualquer envio — a regra do
            projeto não muda porque apareceu um interruptor na tela.
          */}
          <button
            type="button"
            className={`btn sm ${iaLigada ? 'success' : 'ghost'}`}
            onClick={() => {
              const proximo = !iaLigada;
              setIaLigada(proximo);
              ativarIA(proximo);
            }}
            aria-pressed={iaLigada}
            title={
              iaLigada
                ? 'IA ligada: o modelo lê os candles e informa o sinal. A ordem ainda exige confirmação.'
                : 'IA desligada: nenhum modelo é lido e o motor não decide.'
            }
          >
            {iaLigada ? 'IA ligada' : 'Ligar IA'}
          </button>
          <span className={`chip ${wsConnected ? 'ok' : 'warn'}`}>
            {wsConnected ? 'Tempo real' : 'Reconectando…'}
          </span>
          <span className={`chip ${autoAtivo ? 'ok' : 'neutral'}`}>
            {autoAtivo ? 'Ligado' : 'Parado'}
          </span>
        </div>
      </div>

      {/*
        O MODELO, DENTRO DA OPERAÇÃO AUTOMÁTICA (05/10/2026).

        Ele era um bloco separado, chamado "Ativo e Período". O dono pediu para
        remover, e o que sobra dessa decisão é este seletor: "operação automática
        COMPLETA com modelos" exige que a escolha do modelo esteja onde o
        automático é ligado — não numa seção que o operador precisa achar.

        O PAR foi para a barra inferior; aqui ele é apenas LIDO.
      */}
      <SeletorModelo />

      {/*
        A LISTA DOS MODELOS TREINADOS (05/10/2026).

        O dono pediu: "tem que ter lista dos modelos treinados, eles vão operar
        automáticos". MEDIDO: 39 modelos, 28 publicáveis. O par vem do catálogo
        da corretora; o MODELO que decide por ele vem daqui — e é esta lista
        que diz ao operador com que acerto e que edge ele vai operar.
      */}
      <ListaModelos />

      {/* TICKET DE COMANDOS — uma faixa, na ordem em que se opera.
          Preço e lote à esquerda (o que se olha e o que se decide), proteção no
          meio, presets e botão à direita. */}
      {/*
        OS COMANDOS QUE FALTAVAM PARA OPERAR COMPLETO (05/10/2026).

        MEDIDO em `backend/auto_engine.py::LimitesAuto`: o motor aceita e VALIDA
        `banca`, `risco_por_trade_pct`, `confianca_minima`, `edge_minimo`,
        `max_posicoes`, `max_operacoes_dia`, `perda_diaria_max_pct`,
        `intervalo_minutos`, `sl_atr` e `tp_atr`. Nenhum deles tinha botao na
        tela: o operador so podia ligar o AUTO com lote, SL e TP.

        Isso nao e campo sobrando: e o que impede a estrategia de operar. Sem
        `confianca_minima`, o motor aceita sinal de 51% como sinal de 90%; sem
        `max_operacoes_dia`, ele pode abrir vinte operacoes no mesmo dia; sem
        `perda_diaria_max_pct`, a perda diaria nao tem teto.

        Ficam em `<details>`, porque sao limite de risco e o primeiro uso e
        lote + SL + TP. Esconder em gaveta e organizar, nao remover: os botoes
        existem e o valor que o motor usa e o que o operador digitou.

        VAZIO = "nao declarado" no motor, e a validacao do backend aceita. Nao
        preenchemos nada aqui: numero inventado no painel vira limite real.
      */}
      <details className="robo-limites">
        <summary>
          Limites de risco{' '}
          <span className="muted">(confianca, posicoes por dia, perda maxima)</span>
        </summary>
        <div className="robo-limites-grade">
          {LIMITES.map((item) => (
            <label className="field" key={item.chave}>
              <span title={item.ajuda}>{item.rotulo}</span>
              <input
                type="number"
                step={item.passo}
                min={item.minimo}
                value={limites[item.chave] ?? ''}
                placeholder={item.zerado}
                onChange={(e) =>
                  setLimites((atual) => ({ ...atual, [item.chave]: e.target.value }))
                }
                aria-label={item.rotulo}
              />
            </label>
          ))}
        </div>
        <p className="hint">
          Campo vazio = nao declarado, e o motor usa o limite proprio do risk_gate.
          Preencher e declarar quanto voce aceita perder.
        </p>
      </details>

      <div className="robo-ticket">
        <div className="robo-ticket-preco" role="status" aria-live="polite" title="Preço ao vivo">
          {preco != null ? preco : '--'}
        </div>

        <label className="field robo-ticket-lote" style={{ marginBottom: 0 }}>
          <span>
            {unidade ?? 'Lote'}{faixaVolume.assumido ? '*' : ''}
          </span>
          <input
            type="number"
            step={faixaVolume.passo}
            min={faixaVolume.minimo}
            max={faixaVolume.maximo}
            value={lote}
            onChange={(e) => setLote(e.target.value)}
            aria-label={rotuloQuantidade(unidade, faixaVolume.passo)}
            title={
              faixaVolume.assumido
                ? 'Faixa assumida: a corretora nao devolveu volume_min/volume_max para este ativo'
                : `min ${faixaVolume.minimo} · max ${faixaVolume.maximo} · passo ${faixaVolume.passo} (da corretora)`
            }
          />
        </label>

        {/*
          O RISCO EM DINHEIRO (05/10/2026)
          ================================
          MEDIDO: esta tela calculava `preco * lote * distancia`. Com BTCUSD a
          85.865,35, lote 0,01 e distancia 8,45, devolvia 7.255,62 USD quando o
          risco real e 0,08 USD — exagero de 85.865x, que era exatamente o preco.
          Numa conta de 13,25 USD a tela afirmava risco de 7.255 USD.

          A conta certa e `distancia * volume * contract_size`, e o
          `contract_size` e o que separa crypto de forex: 1 em BTCUSD, 100.000 em
          EURUSD. Sem ele, "lote" nao significa nada de dinheiro.

          Sem contrato, o campo mostra "depende do contrato" e nao um numero.
        */}
        <label className="field robo-ticket-volume" style={{ marginBottom: 0 }}>
          <span>Valor no risco (SL)</span>
          <input
            value={valorRisco ?? ''}
            readOnly
            placeholder={preco && num(sl) > 0 ? SEM_CONTRATO : 'depende do SL'}
            aria-label="Valor da perda se o stop for tocado"
            title={
              valorRisco === null && preco && num(sl) > 0
                ? 'A corretora nao devolveu o tamanho do contrato deste ativo: nao da para dizer o valor em dinheiro.'
                : 'Distancia ate o SL x volume x tamanho do contrato.'
            }
          />
        </label>

        {/*
          AS DUAS ABAS DA XM (05/10/2026)
          ===============================
          `Preco` e o que existia. `Quantidade` e o que o dono pediu: o valor em
          dinheiro e do operador, e o preco e derivado, se recalculando a cada
          tick para o dinheiro continuar sendo o mesmo.

          O botao `Quantidade` fica desabilitado sem `contract_size`: sem o
          tamanho do contrato nao ha conversao possivel, e oferecer o campo e
          oferecer uma conta que da numero errado.
        */}
        <div className="robo-ticket-modo" role="group" aria-label="Como definir a protecao">
          <button
            type="button"
            className={`btn sm ${modoProtecao === 'preco' ? 'primary' : 'ghost'}`}
            aria-pressed={modoProtecao === 'preco'}
            onClick={() => setModoProtecao('preco')}
          >
            Preco
          </button>
          <button
            type="button"
            className={`btn sm ${modoProtecao === 'quantidade' ? 'primary' : 'ghost'}`}
            aria-pressed={modoProtecao === 'quantidade'}
            onClick={() => setModoProtecao('quantidade')}
            disabled={contratoUtilizavel(ficha) === null}
            title={
              contratoUtilizavel(ficha) === null
                ? 'A corretora nao devolveu o tamanho do contrato deste ativo: dinheiro e preco nao converte'
                : 'Definir o risco e o alvo em dinheiro; o preco e derivado'
            }
          >
            Quantidade
          </button>
        </div>

        <div className="robo-ticket-protecao">
          <label className="field" style={{ marginBottom: 0 }}>
            <span>Stop Loss</span>
            <input
              value={sl}
              onChange={(e) => setSl(e.target.value)}
              placeholder="preço ou distância"
              aria-label="Stop loss"
            />
          </label>
          <label className="field" style={{ marginBottom: 0 }}>
            <span>Take Profit</span>
            <input
              value={tp}
              onChange={(e) => setTp(e.target.value)}
              placeholder="preço ou distância"
              aria-label="Take profit"
            />
          </label>
        </div>

        {/* Presets 1:1 a 1:4 preenchem os campos. O passo sai da escala do
            ativo: um "10" fixo seria 0,2% no ouro e 900% no EURUSD. */}
        <div className="robo-presets robo-ticket-presets" role="group" aria-label="Presets de distância SL TP">
          <span className="robo-presets-passo" title="Passo da distância: 0,1% do preço ao vivo">
            passo {passo > 0 ? passo : '--'}
          </span>
          {PRESETS.map((p) => (
            <button
              key={p.nome}
              type="button"
              className="btn sm ghost"
              onClick={() => aplicarPreset(p)}
              title={`SL ${p.risco}x passo · TP ${p.alvo}x passo`}
            >
              {p.nome}
            </button>
          ))}
        </div>

        {modoProtecao === 'quantidade' && (
          <div className="robo-ticket-dinheiro">
            <label className="field" style={{ marginBottom: 0 }}>
              <span>Valor do stop loss</span>
              <input
                type="number"
                min={0}
                step={0.01}
                value={valorSl}
                onChange={(e) => setValorSl(e.target.value)}
                aria-label="Valor do stop loss em dinheiro"
                title="Quanto voce aceita perder. O preco do stop e derivado."
              />
            </label>
            <label className="field" style={{ marginBottom: 0 }}>
              <span>Valor do alvo</span>
              <input
                type="number"
                min={0}
                step={0.01}
                value={valorTp}
                onChange={(e) => setValorTp(e.target.value)}
                aria-label="Valor do alvo em dinheiro"
                title="Quanto voce espera ganhar. O preco do alvo e derivado."
              />
            </label>

            {/*
              OS NIVEIS DERIVADOS, dos dois lados.

              Este painel nao sabe o lado: o proprio botao diz "a direcao e do
              modelo", e o preco que chega e um so, sem bid/ask. Por isso os DOIS
              niveis aparecem. O que NAO aparece e um nivel unico escolhido por
              conta propria — seria mostrar o stop de uma venda no campo de stop
              de uma compra, e o operador nao teria como saber qual dos dois o
              motor vai usar.
            */}
            <div className="robo-ticket-niveis" role="status" aria-live="polite">
              {(slValorN === null || tpValorN === null) && (
                <span className="muted">Informe o valor do stop e do alvo.</span>
              )}
              {slValorN !== null && (
                <span className="mono">
                  Stop {slValorN}:{' '}
                  <b>{slAbaixo === null ? '—' : slAbaixo.toPrecision(8)}</b> abaixo
                  {' · '}
                  <b>{slAcima === null ? '—' : slAcima.toPrecision(8)}</b> acima
                </span>
              )}
              {tpValorN !== null && (
                <span className="mono">
                  Alvo {tpValorN}:{' '}
                  <b>{tpAbaixo === null ? '—' : tpAbaixo.toPrecision(8)}</b> abaixo
                  {' · '}
                  <b>{tpAcima === null ? '—' : tpAcima.toPrecision(8)}</b> acima
                </span>
              )}
              <span className="muted">
                Os niveis acompanham o preco de {preco ?? '—'}; o valor em dinheiro e o que voce definiu.
              </span>
            </div>
          </div>
        )}
      </div>

      {status && (
        <p className="robo-observacao" role="status">
          {status}
        </p>
      )}
    </section>
  );
}