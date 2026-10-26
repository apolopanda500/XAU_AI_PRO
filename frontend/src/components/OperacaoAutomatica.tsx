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
import { useEffect, useMemo, useRef, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';
import { useAutoState } from '../hooks/queries';
import { useIaLigada } from '../hooks/useIaLigada';
import { notify } from '../lib/notify';
import { escopoAtivo as contaAtiva, contaAtivaId } from '../lib/escopoAtivo';
import { parNaTela } from '../lib/parNaTela';
import { unidadeDeVolume, fichaDoAtivo, faixaDoAtivo, rotuloQuantidade, mercadoDoAtivo } from '../lib/volumeUnidade';
import { valorDoNivel, nivelParaValor, contratoUtilizavel, SEM_CONTRATO } from '../lib/risco';
import { useCatalogoAtivos } from '../hooks/useCatalogoAtivos';
import SeletorModelo from './SeletorModelo';
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
];

const num = (v: string) => Number(String(v).replace(',', '.'));

/**
 * AS DUAS VISOES DO PAINEL (11/10/2026)
 * =====================================
 * O dono pediu sub-abas na ROBÔ: Operação, Modelos, Risco, Operações. A
 * primeira versão renderizava o painel INTEIRO em Operação e de novo em
 * Risco — dois interruptores AUTO, dois blocos "Par para operar", a mesma
 * tabela de modelos duas vezes. Era o mesmo dado em dois lugares, e o
 * AGENTS.md 5 é o que diz o preço: o operador não sabe qual dos dois manda.
 *
 * Agora é UM componente com duas leituras:
 *
 *   `operacao` (default) — o que se usa para LIGAR: par, modelo e o botão.
 *   `risco`             — o que se usa para LIMITAR: os campos de risco,
 *                         abertos, com um botão que aplica sem ligar nada.
 *
 * A lista dos modelos treinados saiu daqui: ela vive na sub-aba `Modelos`
 * (`RobotTabs`), que é o único lugar que a mostra.
 */
export type VisaoOperacao = 'operacao' | 'risco';

/*
  A RECUSA DE PLANO APONTA O DESBLOQUEIO (11/10/2026)
  ===================================================
  MEDIDO: ligar o motor numa conta Free recebia 403 de `/api/auto/start` com
  o corpo `plano_gate.resposta_bloqueio` — `code: PLAN_REQUIRED` e
  `required_plans` já no payload —, e a tela imprimia só `error`
  ("recurso nao liberado no plano atual: auto_engine"). O operador sabia o que
  faltava e não onde resolver: o caminho do desbloqueio estava fora da tela.

  A função é PURA e exportada para ser medida em teste: a mensagem nasce do
  payload que o gateway mandou (`required_plans` vem do catálogo real, via
  `planos_que_liberam`), não de nome de plano escrito à mão aqui.
*/
export function recusaDePlano(
  payload: { error?: string; code?: string; required_plans?: string[] },
  status: number,
): string {
  const ehPlano = status === 403 || payload?.code === 'PLAN_REQUIRED';
  if (!ehPlano) return '';
  const planos = (payload.required_plans ?? []).map((p) => String(p).trim()).filter(Boolean);
  const lista = planos.length ? planos.join(' ou ') : 'um plano superior';
  return `O motor automático exige ${lista} — ative em Configurações → Plano.`;
}

export default function OperacaoAutomatica({
  visao = 'operacao',
}: { visao?: VisaoOperacao } = {}) {
  const risco = visao === 'risco';
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
  const parDoMotor = String(auto?.simbolo ?? '').toUpperCase();
  /*
    O PAR DA TELA E O QUE O OPERADOR ESCOLHEU (22/10/2026)
    =====================================================
    MEDIDO no app instalado: a barra inferior dizia `BTCUSD` e o seletor
    "Par para operar" dizia `XAUUSD`, na mesma janela, na mesma sessao. A
    queixa do dono foi exata: "na lista da barra inferior tem um ativo
    selecionado, e na lista de cima tem outro".

    A CAUSA era esta linha, `auto?.simbolo` primeiro: o motor guardava
    `BTCUSD` de uma configuracao antiga, e um valor gravado vencia a escolha
    que o operador acabara de fazer. Ele trocava o par na tela, a tela
    continuava mostrando o par do motor - e o `ligar()` mandava o par do
    MOTOR junto com o mercado derivado dele. `BTCUSD` nao existe no
    MetaQuotes-Demo, a ficha vinha vazia, o mercado ia vazio e o gateway
    recusava com "escolha o mercado": o AUTO nunca ligava, e a recusa
    apontava um controle que nao existe nesta tela.

    Regra agora, uma so: DESLIGADO, o par da tela e a escolha do operador
    (o motor nao esta operando nada, entao o par dele nao vale); LIGADO, o
    par e o do motor, porque e o que ele esta operando de verdade. Nunca os
    dois valores misturados no mesmo cabecalho.
  */
  const motorLigado = Boolean(auto?.ativo);
  const simbolo = parNaTela(auto, parEscolhido);
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
    O QUE O MOTOR JA TEM, escrito nos campos (11/10/2026)
    ======================================================
    MEDIDO: a sub-aba Risco montava com os campos VAZIOS mesmo com o motor
    guardando `confianca_minima = 72` — cada aba era uma instância do painel,
    e o que se digitava numa não passava pra outra. O operador via "não
    declarada" e concluía que o limite tinha sumido.

    Preenche SÓ o campo que está vazio, e SÓ com número real (`0` no motor
    significa ausente, é o que `LimitesAuto` chama de não declarado). Quem já
    digitou alguma coisa não tem o valor reescrito — o efeito não decide pelo
    operador, ele só mostra o que já está guardado do outro lado.
  */
  useEffect(() => {
    const doMotor = (auto?.limites ?? null) as Record<string, unknown> | null;
    if (!doMotor) return;
    setLimites((atual) => {
      const proximo = { ...atual };
      let mudou = false;
      for (const item of LIMITES) {
        if ((proximo[item.chave] ?? '').trim() !== '') continue;
        const valor = doMotor[item.chave];
        if (typeof valor !== 'number' || !Number.isFinite(valor) || valor === 0) continue;
        proximo[item.chave] = String(valor);
        mudou = true;
      }
      // Sem mudança, devolve o MESMO objeto: `auto/state` refaz a cada 5s, e
      // um objeto novo a cada poll seria um re-render sem motivo.
      return mudou ? proximo : atual;
    });
  }, [auto]);
  /*
    INTERRUPTOR DA IA — NO STORE DA SESSAO, E NAO AQUI (09/10/2026)
    ===============================================================
    MEDIDO: era `useState(false)` NESTE componente, e a aba ROBÔ monta e
    desmonta este componente inteiro. Sair e voltar zerava o interruptor — o
    dono reportou: "quando desligo e volto novamente ele desliga". E nao era so
    a tela: `useInferenciaIA` usa este valor para decidir se chama o gateway,
    entao a inferencia PARAVA de rodar sem o operador pedir.

    Continua comecando DESLIGADA, e agora por decisao de ESCOPO: `useIaLigada`
    nao persiste no `localStorage`, entao sessao nova comeca desligada —
    inferencia consome CPU e escreve estado, e ligar sozinho e decidir pelo
    operador — e a troca de aba nao perde a escolha.

    O interruptor do MOTOR nao passa por aqui: ele vem de `useAutoState()`,
    que consulta `/api/auto/state` com cache no root, e esse ja sobrevivia.
  */
  const iaLigada = useIaLigada((s) => s.ligada);
  const setIaLigada = useIaLigada((s) => s.setLigada);
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
  /*
    SEM CORRETORA MEDIDA, SEM CORRETORA NA TELA (11/10/2026, decisao do dono:
    nada de MT5 fixo). Era `|| 'mt5'` — e o cabecalho nascia "MT5" antes de o
    operador escolher qualquer corretora. Vazio e vazio: o cabecalho diz
    "sem corretora" e o ligar recusa nomeando a barra inferior.
  */
  const broker = String(auto?.broker || brokerSalvo || '').toLowerCase();

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
    // SEM CORRETORA, SEM CONSULTA (11/10/2026): pedir quotes com `broker=`
    // vazio e consultar para receber erro — e o preco nulo que voltaria ja e
    // o estado inicial. A recusa com motivo esta no ligar e no cabecalho.
    if (!simbolo || !broker) return undefined;
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

  /*
    APLICAR OS LIMITES SEM LIGAR O MOTOR (11/10/2026)
    ==================================================
    A sub-aba Risco existe para declarar quanto se aceita perder. Se o único
    caminho fosse apertar AUTO, declarar limite arriscaria dinheiro — e um
    campo de risco que só serve junto com o botão de operar é o controle
    decorativo que o AGENTS.md 9 proíbe.

    `/api/auto/config` NÃO é rota de plano (`_ROTAS_POST` tem só start e
    tick), então isto funciona também no Free: o plano decide se o motor
    RODA, não se o operador pode declarar o próprio limite.

    O corpo são SÓ os campos declarados. `MotorAuto.configurar` faz merge —
    o que não veio continua valendo — e o campo vazio não vai no payload
    (mesma regra de `limitesNumericos` acima).
  */
  /*
    A IA SUGERE, O OPERADOR GRAVA (12/10/2026).
    ==================================================
    Decisao do dono: botao de IA no controle de risco para a IA estudar o
    momento e configurar os riscos sozinha — MAS com o botao (automatico) E
    a tabela (manual). A sugestao PREENCHE os campos e mostra o motivo de
    cada numero (`base`); o operador ajusta os padroes e grava pelo Aplicar.
    Nada aqui liga o motor e nada grava sozinho: preencher nao e aplicar.
  */
  const [baseIA, setBaseIA] = useState<Record<string, string> | null>(null);
  const sugerirPelaIA = async () => {
    if (ocupado) return;
    if (!simbolo) {
      setStatus('Escolha o par antes de pedir sugestão à IA.');
      return;
    }
    if (!broker) {
      setStatus('Escolha a conta em Configurações → Conexões antes de pedir sugestão à IA.');
      return;
    }
    if (!timeframe) {
      setStatus('IA sem sugestão: escolha o timeframe antes de pedir sugestão à IA.');
      return;
    }
    setOcupado(true);
    try {
      const r = await fetch(`${apiBase()}/api/auto/sugerir-limites`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ simbolo, timeframe, broker, market }),
        signal: AbortSignal.timeout(30000),
      });
      const d = (await r.json().catch(() => ({}))) as {
        ok?: boolean;
        error?: string;
        limites?: Record<string, number>;
        base?: Record<string, string>;
        serie?: { velas?: number; atr_pct?: number; edge?: number; confianca?: number };
      };
      if (!r.ok || d.ok === false || !d.limites) {
        setStatus(`IA sem sugestão: ${d.error ?? `HTTP ${r.status}`}`);
        notify('IA sem sugestão', String(d.error ?? ''));
        return;
      }
      const preenchidos: Record<string, string> = {};
      for (const [campo, valor] of Object.entries(d.limites)) {
        if (typeof valor === 'number' && Number.isFinite(valor)) preenchidos[campo] = String(valor);
      }
      setLimites((atual) => ({ ...atual, ...preenchidos }));
      setBaseIA(d.base ?? null);
      const s = d.serie;
      setStatus(
        `IA sugeriu pelos ${s?.velas ?? '?'} candles de ${simbolo} ${timeframe || ''}: ` +
          `edge ${s?.edge ?? '?'}, confiança ${s?.confianca ?? '?'}%, volatilidade ${s?.atr_pct ?? '?'}%. ` +
          `Confira, ajuste e aplique.`,
      );
      notify('IA sugeriu limites', 'Confira os valores e o motivo de cada um antes de aplicar.');
    } catch (e) {
      setStatus(`Gateway indisponível: ${e instanceof Error ? e.message : 'erro'}`);
    } finally {
      setOcupado(false);
    }
  };

    /*
    IA SEMPRE VIVA (13/10/2026, pedido do dono).
    ==================================================
    Com par + conta e TODOS os campos vazios, a sugestao chega sozinha ao
    trocar de cenario — uma vez por cenario (par, periodo, corretora,
    mercado). Nunca sobrescreve o que o operador digitou: so dispara com
    tudo vazio. E so dispara na visao de risco (onde os campos estao): na
    visao de operacao nao ha campo para preencher. Aplicar continua sendo
    gesto do operador — preencher nao e aplicar.
  */
  const chaveAutoIA = useRef('');
  useEffect(() => {
    if (!risco || !simbolo || !broker || ocupado) return;
    const vazios = Object.values(limites).every((v) => !String(v ?? '').trim());
    if (!vazios) return;
    const chave = `${simbolo}|${timeframe}|${broker}|${market}`;
    if (chaveAutoIA.current === chave) return;
    chaveAutoIA.current = chave;
    void sugerirPelaIA();
  });

  const aplicarLimites = async () => {
    if (ocupado) return;
    const corpo = limitesNumericos();

    if (Object.keys(corpo).length === 0) {
      setStatus('Nenhum limite declarado para aplicar.');
      return;
    }
    setOcupado(true);
    try {
      const r = await fetch(`${apiBase()}/api/auto/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo),
        signal: AbortSignal.timeout(10000),
      });
      const d = (await r.json().catch(() => ({}))) as { ok?: boolean; error?: string };
      const ok = r.ok && d.ok !== false;
      setStatus(
        ok
          ? 'Limites aplicados ao motor.'
          : `Limites recusados: ${d.error ?? `HTTP ${r.status}`}`,
      );
      notify(
        ok ? 'Limites aplicados' : 'Limites recusados',
        ok ? 'O motor já usa estes valores.' : String(d.error ?? ''),
      );
    } catch (e) {
      setStatus(`Gateway indisponível: ${e instanceof Error ? e.message : 'erro'}`);
    } finally {
      setOcupado(false);
    }
  };

  const ligar = async () => {
    if (ocupado) return;
    if (!broker) {
      // SEM CORRETORA, SEM LIGAR (11/10/2026, decisao do dono: nada de MT5
      // fixo). Antes o `broker` nascia `'mt5'` e o ligar mandava a config para
      // uma corretora que ninguem escolheu. A escolha esta em Configuracoes →
      // Conexoes (o botao Ativar grava a conta ativa) — a mensagem aponta para
      // la, como a do par aponta para o seletor desta mesma tela.
      setStatus(
        'Escolha a conta em Configurações → Conexões (botão Ativar da conexão) antes de ligar o AUTO.',
      );
      return;
    }
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
    /*
      SEM FICHA, SEM LIGAR - E A RECUSA NOMEIA O QUE FALTA (22/10/2026)
      ================================================================
      MEDIDO: "Configurado, mas nao ligou: escolha o mercado antes de ligar a
      operacao automatica: nenhum mercado e padrao". A frase vem do gateway e
      manda escolher um mercado - mas nao existe campo "Mercado" neste painel:
      ele era derivado da ficha do ativo. O par era `BTCUSD`, que o
      MetaQuotes-Demo nao publica, entao a ficha vinha vazia, o mercado ia
      vazio e o operador recebia uma instrucao impossivel (AGENTS.md §5).

      A recusa honesta e aqui, com o nome do par e da corretora. Sem catalogo
      nenhum a causa e outra: nao ha conta ativa, e a mensagem diz onde
      escolher. Nunca mandar `market: ''` para o gateway adivinhar.
    */
    if (!market) {
      setStatus(
        catalogo.length === 0
          ? 'Sem catálogo da corretora: ative a conta em Configurações → Conexões (botão Ativar) antes de ligar o AUTO.'
          : `A corretora ${broker ? broker.toUpperCase() : ''} não publica ${simbolo}. Escolha outro par em "Par para operar".`.replace(
              '  ',
              ' ',
            ),
      );
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
        // A CONTA ESCOLHIDA (22/10/2026): com duas contas MT5 ativas o
        // motor recusava "account_id e obrigatorio" — correto, mas sem
        // este campo a escolha era impossivel de fazer. O ID vem da mesma
        // chave que a Configuracoes → Conexoes grava ao ativar; vazio
        // significa "unica conta ativa", que o motor resolve sozinho.
        account_id: contaAtivaId(),
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
      const dCfg = (await cfg.json().catch(() => ({}))) as {
        ok?: boolean;
        error?: string;
        code?: string;
        required_plans?: string[];
      };
      if (!cfg.ok || dCfg.ok === false) {
        // `/api/auto/config` NÃO é rota de plano hoje (`_ROTAS_POST` tem só
        // start e tick), mas se virar, a mensagem já aponta o desbloqueio em
        // vez de repetir o `error` cru.
        const plano = recusaDePlano(dCfg, cfg.status);
        setStatus(plano || String(dCfg.error ?? `HTTP ${cfg.status}`));
        notify('Configuração recusada', plano || String(dCfg.error ?? ''));
        return;
      }
      const ini = await fetch(`${apiBase()}/api/auto/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
        signal: AbortSignal.timeout(10000),
      });
      const dIni = (await ini.json().catch(() => ({}))) as {
        ok?: boolean;
        error?: string;
        code?: string;
        required_plans?: string[];
      };
      const ok = ini.ok && dIni.ok !== false;
      // 403 PLAN_REQUIRED: o bloqueio tem de apontar o DESBLOQUEIO. O payload
      // já traz `required_plans`; a tela agora o lê.
      const plano = ok ? '' : recusaDePlano(dIni, ini.status);
      setStatus(
        ok ? 'Motor ligado.' : plano || `Configurado, mas não ligou: ${dIni.error ?? ''}`,
      );
      notify(
        ok ? 'Motor ligado' : 'Não ligou',
        ok ? `Operando ${simbolo}.` : plano || String(dIni.error ?? ''),
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

  /*
    A GRADE DOS LIMITES, em um lugar só.
    Ela é a MESMA nos dois modos: na operação dentro do `<details>`, na de
    risco em bloco aberto. Duplicar o JSX das oito entradas era ter dois
    lugares para o campo sair de sincronia — que é o mesmo defeito das sub-abas
    duplicadas, em escala menor.
  */
  const gradeDeLimites = (
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
  );

  return (
    <section
      className="card robo-comandos"
      aria-label={risco ? 'Controle de risco' : 'Operação automática'}
    >
      <div className="section-head">
        <div>
          <h2>{risco ? 'Controle de risco' : 'Operação automática'}</h2>
          <span className="muted">
            {simbolo ? `${simbolo} ${timeframe}`.trim() : 'Sem par escolhido'} · {broker ? broker.toUpperCase() : 'sem corretora'}
          </span>
        </div>
        {/* O INTERRUPTOR E A IA FICAM SÓ NA VISÃO DE OPERAÇÃO. Na de risco
            eles apareceriam como o segundo botão AUTO da página — o dono
            reportou "sub abas duplicadas" e era isto: dois painéis idênticos,
            um dentro de cada sub-aba, cada um com o seu próprio AUTO. Os
            chips de estado (linha, motor ligado) continuam, porque informar
            não duplica controle. */}
        {!risco && (
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
        )}
        {risco && (
        <div className="btn-row">
          <span className={`chip ${wsConnected ? 'ok' : 'warn'}`}>
            {wsConnected ? 'Tempo real' : 'Reconectando…'}
          </span>
          <span className={`chip ${autoAtivo ? 'ok' : 'neutral'}`}>
            {autoAtivo ? 'Ligado' : 'Parado'}
          </span>
        </div>
        )}
      </div>

      {/*
        O MODELO, DENTRO DA OPERAÇÃO AUTOMÁTICA (05/10/2026).

        Ele era um bloco separado, chamado "Ativo e Período". O dono pediu para
        remover, e o que sobra dessa decisão é este seletor: "operação automática
        COMPLETA com modelos" exige que a escolha do modelo esteja onde o
        automático é ligado — não numa seção que o operador precisa achar.

        O PAR foi para a barra inferior; aqui ele é apenas LIDO.

        Ele NÃO aparece na visão de risco: lá não se escolhe o que operar, se
        declara o que se aceita perder, e os dois controles no mesmo lugar é
        o caminho para trocar o modelo achando que estava mudando o limite.
      */}
      {!risco && (
        <>
          <SeletorModelo />

          {/*
            A LISTA DOS MODELOS TREINADOS SAIU DESTE PAINEL (11/10/2026)
            ===========================================================
            O dono pediu (05/10/2026): "tem que ter lista dos modelos
            treinados, eles vão operar automáticos". Ela continua existindo —
            agora na sub-aba `Modelos` da ROBÔ (`RobotTabs`), que é o único
            lugar que a monta.

            MEDIDO antes de tirar: a tabela aparecia DUAS VEZES na mesma tela,
            uma na sub-aba Operação (dentro deste painel) e outra na sub-aba
            Modelos, com o mesmo conteúdo. "Sub abas duplicadas" é o sintoma,
            e a causa é este `<ListaModelos />`.
          */}
        </>
      )}

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
      {/*
        NO MODO RISCO, A GAVETA ABRE: este bloco é o motivo de a sub-aba
        existir, e esconder em `<details>` o conteúdo da própria aba seria o
        operador ter de clicar duas vezes para chegar onde veio parar.

        E o botão de APLICAR fica aqui, e não junto do AUTO: declarar limite
        não pode depender de apertar o botão que liga o motor.
      */}
      {/*
        UM PAINEL DE RISCO SO, NA SUB-ABA RISCO (12/10/2026)
        =====================================================
        Decisao do dono: o painel de risco estava em duas sub-abas — a grade
        aberta aqui (visao `risco`) e a mesma grade numa gaveta `<details>` na
        Operacao. Duas telas para os mesmos limites, com estados SEPARADOS
        (cada visao e uma instancia): declarar num lugar e ligar no outro
        mandava limites diferentes sem o operador ver.

        Agora a grade mora SO na sub-aba Risco, com o botao Aplicar. Nesta
        visao (`operacao`) nao ha bloco de risco: o `ligar` manda lote/par e o
        que o motor ja guarda (declarado na Risco ou padrao do risk_gate).
      */}
      {risco && (
        <div className="robo-limites">
          {gradeDeLimites}
          <p className="hint">
            Campo vazio = nao declarado, e o motor usa o limite proprio do risk_gate.
            Preencher e declarar quanto voce aceita perder.
          </p>
          <div className="robo-limites-acoes">
            <button
              type="button"
              className="btn primary"
              onClick={() => void sugerirPelaIA()}
              disabled={ocupado}
              title="A IA estuda o momento (velas, edge, confiança, volatilidade) e preenche os campos. Não grava e não liga: confira, ajuste e aplique."
            >
              {ocupado ? 'Estudando…' : 'IA sugere limites'}
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => void aplicarLimites()}
              disabled={ocupado}
              title="Grava os limites declarados no motor. Nao liga a operação."
            >
              {ocupado ? 'Aplicando.' : 'Aplicar limites ao motor'}
            </button>
          </div>
          {/*
            O MOTIVO DE CADA NUMERO (12/10/2026). A IA devolve `base[campo]` e
            a tela mostra — sem isso a sugestao seria numero magico, e numero
            magico em tela de risco e o operador confiando no que nao entende.
            E aqui que ele ajusta "os padroes da IA": edita o campo e aplica.
          */}
          {baseIA && Object.keys(baseIA).length > 0 && (
            <ul className="hint robo-ia-base" data-testid="ia-base">
              {Object.entries(baseIA).map(([campo, motivo]) => (
                <li key={campo}>
                  <b>{campo}</b>: {motivo}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/*
        O BLOCO DO TICKET SAIU — decisao do dono, 08/10/2026
        =======================================================
        O QUE ESTAVA AQUI, e o que era o unico consumidor de cada coisa:

          Token(s)/Lote        -> `lote`     -> `/api/auto/config` -> `LimitesAuto.lote`
          Stop Loss            -> `sl`       -> `/api/auto/config` -> `LimitesAuto.sl_preco`
          Take Profit          -> `tp`       -> `/api/auto/config` -> `LimitesAuto.tp_preco`
          Valor no risco (SL)  -> LEITURA    -> `distancia * volume * contract_size`
          Preco / Quantidade   -> `modoProtecao`
          passo + 1:1..1:4     -> `aplicarPreset`

        O QUE O DONO DISSE: "nao esta bom", e o motivo medido na captura de
        08/10 19:36: `Stop loss (-2,00 USD) 2,00` e `Alvo (+2,00 USD) 2,00` sao
        VALOR FIXO, e as tres linhas de ordem sairam em 75670,29 / 75470,29 /
        75270,29 — exatamente +200,00 e -200,00 em volta do preco. Um painel
        que parece configuravel e escreve numero fixo e pior que nenhum painel.

        O QUE CAI, E PRECISO QUE SEJA CONSCIENTE:
        -----------------------------------------
        Este era o UNICO caminho de tela para `/api/auto/config`. MEDIDO em
        `backend/fastapi_gateway.py:484`, `/api/auto/start` diz "Exige limites
        validos", e `backend/auto_engine.py:256` `LimitesAuto.completo()` exige
        `lote > 0 AND sl_preco > 0 AND tp_preco > 0`.

        Entao: os limites que o motor esta usando AGORA continuam valendo — sao
        memoria do processo do gateway, nao disco (medido: nenhum JSON de
        limites em %APPDATA%). Remover a tela NAO desliga o AUTO e NAO apaga o
        que esta rodando.

        Mas depois de um reinicio do gateway, `/api/auto/config` deixa de ter
        interface: o motor sobe com o que a IA sugerir, ou nao sobe. Se o dono
        quiser voltar a definir limites pela tela, este e o lugar.
      */}

      {status && (
        <p className="robo-observacao" role="status">
          {status}
        </p>
      )}
    </section>
  );
}