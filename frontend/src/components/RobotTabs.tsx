// ===========================================================================
//  ABAS ROBÔ — 05/10/2026. Reescrita do zero, sem a Mesa.
//
//  O DONO PEDIU
//  ============
//  "deletar aba e reconstruir sem mesa apenas:
//     CABECALHO EM CIMA
//     OPERACAO AUTOMATICO COMANDOS
//     GRAFICO OPERACIONAL AO VIVO EMBAIXO
//     MINITERMINAL AO VIVO"
//
//  O QUE TINHA E POR QUE FOI REESCRITO
//  ====================================
//  A aba anterior era `MesaXM` (ticket manual) + sub-aba `Acompanhar`. O dono
//  mandou tirar a mesa. A versão intermediária trocou `MesaXM` por
//  `OperacaoAutomatica` e manteve o CSS antigo com o prefixo `mesa-`.
//
//  Resultado medido: a aba ficou DESCONFIGURADA. Nenhum erro, nenhuma exceção —
//  a folha `mesa-xm.css` deixou de ser importada quando o componente que a
//  importava foi apagado, e todas as classes do ticket ficaram sem regra. Ticket
//  desmontado, botão sem cor, campos empilhados.
//
//  Aqui a reconstrução parte do CSS, não do componente. Cada arquivo da página
//  importa SUA folha, e a folha é declarada com o nome da página (`robo-`).
//  Não existe mais nenhum `mesa-`.
//
//  A ORDEM É A QUE O DONO PEDIU
//  ============================
//  1. cabeçalho
//  2. operação automática (comandos)
//  3. gráfico operacional ao vivo
//  4. MiniTerminal ao vivo
//
//  Cada bloco é seu próprio `<section>`, e a página não tem `overflow` próprio:
//  quem rola é `.content`. Isso é o que impede um bloco de encavalitar sobre o
//  outro — que foi o sintoma da versão quebrada.
// ===========================================================================
// ===========================================================================
//  ABA ROBÔ — TRÊS BLOCOS, NADA MAIS.
//
//  O DONO PEDIU
//  ============
//  "selecionar modelos periodos, controlar volume lote, tp sl, IA ajudando,
//   ver os modelos ativado operando no grafico do meio ao vivo, colocar
//   ordens no grafico arrastando, e no final embaixo o miniterminal ao vivo
//   mostrando as noticias"
//
//  E DEPOIS, DUAS VEZES:
//  "apenas os tres blocos... nao poluir tela"
//  "nada de prever tabela de previsao — isso nao ajuda em nada, o que importa
//   e operar, ordens ao vivo, grafico operacional"
//
//  O QUE FICOU E O QUE SAIU
//  ========================
//  FICOU: seletor de ATIVO e de MODELO/PERIODO. O operador precisa escolher
//  qual par o motor usa — sem isso, "qual ativo e modelo?" obriga a sair da
//  aba para responder.
//
//  SAIU: o botao "Prever" e a TABELA de previsao (sinal, confianca, probBuy,
//  probSell, etc.). Duas razoes, e a segunda e a que pesa:
//
//  1. O dono pediu explicitamente. Um sinal previsto nao abre posicao. Ele nao
//     decide se o operador compra, e sim informa o que o modelo acha —
//     enquanto o operador olha, o preco ja andou.
//
//  2. O painel era um segundo lugar para o mesmo dado. `AcompanharModelos`
//     (o grafico do meio) JA desenha os sinais do modelo como marcadores no
//     candle, com a fita embaixo. A tabela repetia numero que ja estava no
//     grafico, e a regra do projeto proibe exatamente isso: um controle ou um
//     painel que mostra o mesmo dado em dois lugares faz o operador desconfiar
//     dos dois.
//
//  A inferencia continua rodando no motor. O que mudou e so que ela NAO tem
//  mais uma tabela na tela: ela aparece como marcador no grafico, onde o
//  operador esta olhando o preco de qualquer forma.
//
//  A ORDEM E A QUE O DONO PEDIU
//  ===========================
//  1. cabecalho
//  2. comandos (lote, volume, SL, TP, AUTO) + seletor de modelo e periodo
//  3. grafico operacional ao vivo (ordem arrastando)
//  4. MiniTerminal ao vivo (posicoes e noticias)
//
//  Cada bloco e seu proprio `<section>`, e a pagina nao tem `overflow` proprio:
//  quem rola e `.content`. E isso que impede um bloco de encavalitar sobre o
//  outro — que foi o sintoma da versao quebrada.
// ===========================================================================
import ErrorBoundary from './ErrorBoundary';
import AcompanharModelos from './AcompanharModelos';
import OperacaoAutomatica from './OperacaoAutomatica';
import UniversalLiveTerminal from './UniversalLiveTerminal';
import SeletorModelo from './SeletorModelo';
import '../theme/robo.css';

function Secao({ nome, children }: { nome: string; children: React.ReactNode }) {
  return <ErrorBoundary nome={nome}>{children}</ErrorBoundary>;
}

export default function RobotTabs() {
  return (
    <main className="robo">
      {/* 1 — cabeçalho. Fica FORA do grid: a página usa `display: flex`
          com `gap`, e cabeçalho não é um bloco de conteúdo. */}
      <header className="robo-cabecalho">
        <div>
          <span className="eyebrow">OPERAÇÃO</span>
          <h1>ROBÔ</h1>
          <span className="muted">
            Escolha o par, configure o risco e opere no gráfico ao vivo.
          </span>
        </div>
      </header>

      {/* 2 — comandos. Lote, proteção e AUTO; o modelo decide o lado. */}
      <Secao nome="Operação automática">
        <OperacaoAutomatica />
      </Secao>

      {/* ATIVO e MODELO/PERIODO moram com os comandos: e a resposta da pergunta
          "qual ativo e modelo?" na mesma tela onde se define o risco. */}
      <Secao nome="Escolha do par">
        <SeletorModelo />
      </Secao>

      {/* 3 — gráfico operacional ao vivo. Compra e venda em 1 clique, TP/SL
          arrastável, marcadores do modelo. */}
      <Secao nome="Gráfico ao vivo">
        <AcompanharModelos />
      </Secao>

      {/* 4 — MiniTerminal ao vivo. Posições abertas, conta e notícias. */}
      <Secao nome="Posições ao vivo">
        <UniversalLiveTerminal />
      </Secao>
    </main>
  );
}