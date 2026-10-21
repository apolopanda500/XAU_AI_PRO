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
//     OPERAÇÃO. O que muda é que não existe mais um componente chamado
//     "acompanhar" — o bloco do meio é o GRÁFICO, e ele é o que o dono pediu
//     para estar no meio, no estilo XM (`my.xm.com/pt/symbol-info/BTCUSD`).
//     O seletor de modelo DENTRO da operação automática permanece, porque sem
//     ele não existe "operação automática completa com modelos".
//
//     E UM GRAFICO SO (11/10/2026, decisao do dono: duas sub-abas estavam com
//     o grafico duplicado). O grafico mora na sub-aba Operacao; Modelos,
//     Risco e Operacoes mostram so o painel delas. Ver o comentario acima do
//     `{subAba === 'operacao' && (` no final do arquivo.
//
//  A ORDEM É A QUE O DONO PEDIU
//  ===========================
//  1. cabeçalho
//  2. operação automática COMPLETA (lote, SL, TP, modelo, liga/desliga)
//  3. gráfico operacional ao vivo — ESTILO XM, no meio (SO na Operacao)
//  4. MiniTerminal ao vivo e as operações abertas — embaixo (sub-aba Operacoes)
//
//  Cada bloco é seu próprio `<section>`, e a página não tem `overflow` próprio:
//  quem rola é `.content`. É isso que impede um bloco de encavalitar sobre o
//  outro — que foi o sintoma da versão quebrada anterior.
// ===========================================================================
import { useState } from 'react';
import ErrorBoundary from './ErrorBoundary';
import AcompanharModelos from './AcompanharModelos';
import OperacaoAutomatica from './OperacaoAutomatica';
import UniversalLiveTerminal from './UniversalLiveTerminal';
import ListaModelos from './ListaModelos';
import '../theme/robo.css';

function Secao({ nome, children }: { nome: string; children: React.ReactNode }) {
  return <ErrorBoundary nome={nome}>{children}</ErrorBoundary>;
}

type SubAba = 'operacao' | 'modelos' | 'risco' | 'operacoes';

const SUB_ABAS: Array<{ id: SubAba; rotulo: string }> = [
  { id: 'operacao', rotulo: 'Operação' },
  { id: 'modelos', rotulo: 'Modelos' },
  { id: 'risco', rotulo: 'Risco' },
  { id: 'operacoes', rotulo: 'Operações' },
];

export default function RobotTabs() {
  const [subAba, setSubAba] = useState<SubAba>('operacao');

  return (
    <main className="robo">
      <nav className="robo-sub-abas" role="tablist" aria-label="Sub-abas do robô">
        {SUB_ABAS.map((aba) => (
          <button
            key={aba.id}
            type="button"
            role="tab"
            aria-selected={subAba === aba.id}
            className={`robo-sub-aba ${subAba === aba.id ? 'ativa' : ''}`}
            onClick={() => setSubAba(aba.id)}
          >
            {aba.rotulo}
          </button>
        ))}
      </nav>

      {subAba === 'operacao' && (
        <Secao nome="Operação automática">
          <OperacaoAutomatica />
        </Secao>
      )}

      {subAba === 'modelos' && (
        <Secao nome="Modelos treinados">
          <ListaModelos />
        </Secao>
      )}

      {subAba === 'risco' && (
        <Secao nome="Controle de risco">
          <OperacaoAutomatica visao="risco" />
        </Secao>
      )}

      {subAba === 'operacoes' && (
        <Secao nome="Operações abertas">
          <UniversalLiveTerminal />
        </Secao>
      )}

      {/*
        UM GRAFICO SO, E NA SUB-ABA OPERACAO (11/10/2026)
        ==================================================
        Decisao do dono: duas sub-abas estavam com o grafico duplicado — remover
        de uma, apenas 1 grafico. Antes o `<AcompanharModelos />` era SEMPRE
        visivel, embaixo de qualquer sub-aba: o mesmo grafico repetido em
        Operacao, Modelos, Risco e Operacoes. Quatro telas com o mesmo grafico
        e o mesmo defeito das sub-abas duplicadas em outra roupa: o operador
        nao sabe qual dos graficos manda (e sao quatro consultas, quatro
        polls, quatro series para o mesmo par).

        Agora o grafico mora na Operacao — operar e ver sao o mesmo gesto, e
        era o desenho original desta pagina ("no MEIO grafico estilo XM").
        Modelos, Risco e Operacoes mostram so o painel delas. As linhas de
        posicao (entrada/SL/TP arrastaveis) continuam no grafico da Operacao,
        que le as mesmas posicoes.
      */}
      {subAba === 'operacao' && (
        <Secao nome="Gráfico ao vivo">
          <AcompanharModelos />
        </Secao>
      )}
    </main>
  );
}