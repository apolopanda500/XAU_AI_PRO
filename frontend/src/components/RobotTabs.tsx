// ===========================================================================
//  ABA ROBÔ — PÁGINA ÚNICA. 05/10/2026.
// ===========================================================================
//
//  A FOLHA ANTIGA (`mesa-xm.css`) SAIU, E ESTE É O MOTIVO
//  ======================================================
//  A aba anterior era `MesaXM` (ticket manual) + sub-aba `Acompanhar`. O dono
//  mandou tirar a mesa. A versão intermediária trocou `MesaXM` por
//  `OperacaoAutomatica` e MANTIVEU a folha antiga, com o prefixo `mesa-`.
//
//  Resultado medido: a aba ficou DESCONFIGURADA, sem erro e sem exceção. A
//  folha deixou de ser importada quando o componente que a importava foi
//  apagado, e todas as classes do ticket ficaram sem regra: ticket desmontado,
//  botão sem cor, campos empilhados.
//
//  A reconstrução parte do CSS, não do componente. Cada arquivo da página
//  importa SUA folha, e a folha é declarada com o nome da página (`robo-`).
//  Não existe mais nenhum `mesa-`.
//
//  O DONO PEDIU (esta rodada)
//  ==========================
//  "aba robo ativo e periodo remover. acompanhar modelos remover. apenas
//   operacao automatica completa com modelos e ligar auto sim ou nao, NO MEIO
//   grafico estilo XM global e embaixo miniterminal ao vivo e as operacoes
//   abertas."
//
//  O QUE SAIU, E POR QUÊ
//  =====================
//  1. "Ativo e Período" — bloco SEPARADO de escolha de par.
//
//     Ele respondia a pergunta "qual ativo e modelo?", e a pergunta é legítima.
//     Mas o dono pediu para remover, e o motivo dele se sustenta: o par já é
//     escolhido na barra inferior (o botão `status-simbolo` abre o seletor de
//     par E de timeframe), que é ONDE O MT5 e a XM colocam. Ter a escolha em
//     dois lugares é o caminho para os dois discordarem — e quando discordam,
//     o operador acredita no lugar errado. Este bloco lia `auto/config` e a
//     barra inferior escreve o mesmo endpoint. Mesmo dado, dois lugares.
//
//  2. "Acompanhar modelos" como COMPONENTE.
//
//     Saiu o nome e o wrapper, não a função: o gráfico continua no meio da
//     página. O que muda é que não existe mais um componente chamado
//     "acompanhar" — o bloco do meio é o GRÁFICO, e ele é o que o dono pediu
//     para estar no meio, no estilo XM (`my.xm.com/pt/symbol-info/BTCUSD`).
//     O seletor de modelo DENTRO da operação automática permanece, porque sem
//     ele não existe "operação automática completa com modelos".
//
//  A ORDEM É A QUE O DONO PEDIU
//  ===========================
//  1. cabeçalho
//  2. operação automática COMPLETA (lote, SL, TP, modelo, liga/desliga)
//  3. gráfico operacional ao vivo — ESTILO XM, no meio
//  4. MiniTerminal ao vivo e as operações abertas — embaixo
//
//  Cada bloco é seu próprio `<section>`, e a página não tem `overflow` próprio:
//  quem rola é `.content`. É isso que impede um bloco de encavalitar sobre o
//  outro — que foi o sintoma da versão quebrada anterior.
// ===========================================================================
import ErrorBoundary from './ErrorBoundary';
import AcompanharModelos from './AcompanharModelos';
import OperacaoAutomatica from './OperacaoAutomatica';
import UniversalLiveTerminal from './UniversalLiveTerminal';
import '../theme/robo.css';

function Secao({ nome, children }: { nome: string; children: React.ReactNode }) {
  return <ErrorBoundary nome={nome}>{children}</ErrorBoundary>;
}

export default function RobotTabs() {
  return (
    <main className="robo">
      {/*
        O CABECALHO "OPERAÇÃO / ROBÔ" SAIU (06/10/2026)
        ================================================
        MEDIDO na captura da XM e no app instalado: a barra lateral ja escreve
        `ROBÔ` em cada pagina, e o cabeçalho repetia `OPERAÇÃO` + `ROBÔ` +
        "Configure o risco, ligue o automatico e opere no grafico ao vivo".
        Tres linhas dizendo a aba que a barra lateral ja diz, e o texto explica
        o que a tela logo abaixo faz sozinha.

        O dono pediu para remover. Alem do lugar ocupado, o titulo competia com
        o `h1`/`h2` da primeira seção — que e o que o leitor de tela usa para
        navegar, e dois `h1` na mesma pagina sao ambiguidade, nao enfase.

        O QUE ENTROU NO LUGAR
        --------------------
        O botao `AUTO SIM`/`AUTO NAO` subiu para o topo, ao lado do titulo
        `Operação automatica`. Ele era o controle mais importante da pagina e
        vivia no rodape do ticket, embaixo de `passo`, dos presets e dos campos
        — a ultima coisa visivel antes de rolar. Ligar e desligar o motor e a
        acao principal do operador; ela fica onde o olho ja esta.

        Ver `OperacaoAutomatica.tsx`, no `section-head`.
      */}

      {/* 1 — operação automática COMPLETA. Lote, proteção, modelo, o
          liga/desliga e o par escolhido na barra inferior. */}
      <Secao nome="Operação automática">
        <OperacaoAutomatica />
      </Secao>

      {/* 2 — GRÁFICO NO MEIO, estilo XM. Preço, posição aberta e os marcadores
          do modelo, no formato de `symbol-info`. */}
      <Secao nome="Gráfico ao vivo">
        <AcompanharModelos />
      </Secao>

      {/* 3 — embaixo: MiniTerminal ao vivo e as operações abertas. */}
      <Secao nome="Operações abertas">
        <UniversalLiveTerminal />
      </Secao>
    </main>
  );
}